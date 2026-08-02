"""
Relays PaymentEvent rows to Kafka.

Runs two ways:
  1. Embedded in the API process — app/main.py starts run_forever() as a
     background asyncio task on startup, so `uv run uvicorn app.main:app`
     alone is enough for the whole notification pipeline to work (Kafka
     itself still needs `docker compose up -d zookeeper kafka` — that's a
     separate broker process, not something this app can start on its own).
     This is a dev-convenience tradeoff: a real production deployment would
     run this as its own independently-scalable process instead, exactly
     like option 2.
  2. Standalone:
         uv run python -m app.workers.outbox_publisher

Why a separate polling relay instead of publishing to Kafka directly inside
PaymentService? Because "commit to the DB" and "publish to Kafka" can't be
done as one atomic operation. Publishing directly from the request path means
a crash between the two leaves the event silently lost. Writing the event to
the DB in the same transaction as the payment state change (the outbox), then
relaying it here on a best-effort loop, means the event is never lost — at
worst it's delayed or (on producer retry) published twice, which is why
consumers must treat delivery as at-least-once, not exactly-once.
"""

import asyncio
import json
from datetime import UTC, datetime

import structlog
from aiokafka import AIOKafkaProducer
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.models.payment_event import PaymentEvent

logger = structlog.get_logger("outbox_publisher")

TOPIC = "payment-events"
POLL_INTERVAL_SECONDS = 2
BATCH_SIZE = 5000
RECONNECT_DELAY_SECONDS = 5


async def publish_pending(producer: AIOKafkaProducer) -> int:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(PaymentEvent)
            .where(PaymentEvent.published_at.is_(None))
            .order_by(PaymentEvent.created_at)
            .limit(BATCH_SIZE)
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        for event in events:
            message = json.dumps(
                {
                    "event_id": str(event.id),
                    "payment_id": str(event.payment_id),
                    "event_type": event.event_type.value,
                    "payload": json.loads(event.payload),
                    "request_id": event.request_id,
                    "created_at": event.created_at.isoformat(),
                }
            ).encode()

            await producer.send_and_wait(TOPIC, message, key=str(event.payment_id).encode())

            event.published_at = datetime.now(UTC)
            await db.commit()

            # Re-bind the request_id this event carries so this log line
            # correlates with the API request that produced it.
            with structlog.contextvars.bound_contextvars(request_id=event.request_id):
                logger.info(
                    "event_published",
                    event_id=str(event.id),
                    event_type=event.event_type.value,
                    payment_id=str(event.payment_id),
                )

        return len(events)


async def run_forever() -> None:
    """
    Never returns under normal operation — safe to launch as a background
    asyncio task (see app/main.py's lifespan) or drive from main() below.

    If Kafka isn't reachable (not started yet, or restarting), this retries
    the connection every RECONNECT_DELAY_SECONDS instead of crashing the
    whole task — it'll pick up right where the outbox left off as soon as
    Kafka becomes available, with no need to restart the API.
    """
    while True:
        producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        try:
            await producer.start()
            logger.info(
                "outbox_publisher_started",
                poll_interval_seconds=POLL_INTERVAL_SECONDS,
                topic=TOPIC,
            )
            while True:
                count = await publish_pending(producer)
                if count:
                    logger.info("batch_published", count=count)
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise  # let the app shut this down cleanly, don't treat it as a retryable failure
        except Exception:
            logger.warning(
                "outbox_publisher_lost_connection_retrying",
                retry_in_seconds=RECONNECT_DELAY_SECONDS,
            )
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
        finally:
            await producer.stop()


async def main() -> None:
    configure_logging()
    await run_forever()


if __name__ == "__main__":
    asyncio.run(main())
