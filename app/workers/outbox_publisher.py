"""
Standalone process: relays PaymentEvent rows to Kafka.

Run separately from the API process:
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
BATCH_SIZE = 100


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


async def main() -> None:
    configure_logging()
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    logger.info(
        "outbox_publisher_started",
        poll_interval_seconds=POLL_INTERVAL_SECONDS,
        topic=TOPIC,
    )
    try:
        while True:
            count = await publish_pending(producer)
            if count:
                logger.info("batch_published", count=count)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
