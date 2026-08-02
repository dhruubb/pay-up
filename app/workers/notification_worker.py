"""
Consumes payment events from Kafka and creates notifications.

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
         uv run python -m app.workers.notification_worker

Delivery is at-least-once: the Kafka offset is only committed after the
notification is durably written, so a crash mid-processing replays the event
on restart rather than losing it — at the cost of possible duplicate
notifications on redelivery, which this worker does not deduplicate. That's
a deliberate, documented tradeoff, not an oversight.
"""

import asyncio
import json
from uuid import UUID

import structlog
from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.models.notification import Notification, NotificationChannel, NotificationStatus
from app.modules.accounts.repository import AccountRepository
from app.modules.notifications.repository import NotificationRepository
from app.modules.payments.repository import PaymentRepository

logger = structlog.get_logger("notification_worker")

TOPIC = "payment-events"
GROUP_ID = "notification-worker"
RECONNECT_DELAY_SECONDS = 5


def _format_amount(amount_paise: int) -> str:
    return f"₹{amount_paise / 100:.2f}"


async def handle_event(event: dict) -> None:
    event_type = event["event_type"]
    if event_type not in ("SUCCESS", "FAILED"):
        return  # INITIATED/PROCESSING/DEBITED/CREDITED are audit-only, not user-facing.

    payload = event["payload"]
    payment_id = UUID(payload["payment_id"])
    amount = _format_amount(payload["amount_paise"])

    async with AsyncSessionLocal() as db:
        payment_repo = PaymentRepository(db)
        account_repo = AccountRepository(db)
        notification_repo = NotificationRepository(db)

        payment = await payment_repo.get_by_id(payment_id)
        if not payment:
            logger.warning("payment_not_found", payment_id=str(payment_id))
            return

        sender_account = await account_repo.get_by_id(payment.sender_account_id)
        # Accounts are never deleted in this app — a payment's account FK is
        # always resolvable. Asserting documents that invariant for readers
        # (and mypy) rather than silently handling a case that can't happen.
        assert sender_account is not None

        if event_type == "SUCCESS":
            receiver_account = await account_repo.get_by_id(payment.receiver_account_id)
            assert receiver_account is not None
            await notification_repo.create(
                Notification(
                    user_id=sender_account.user_id,
                    payment_id=payment.id,
                    channel=NotificationChannel.PUSH,
                    message=f"You paid {amount}",
                    status=NotificationStatus.SENT,
                )
            )
            await notification_repo.create(
                Notification(
                    user_id=receiver_account.user_id,
                    payment_id=payment.id,
                    channel=NotificationChannel.PUSH,
                    message=f"You received {amount}",
                    status=NotificationStatus.SENT,
                )
            )
        else:  # FAILED — the receiver never got anything, so only notify the sender.
            reason = payload.get("failure_reason") or "unknown reason"
            await notification_repo.create(
                Notification(
                    user_id=sender_account.user_id,
                    payment_id=payment.id,
                    channel=NotificationChannel.PUSH,
                    message=f"Your payment of {amount} failed: {reason}",
                    status=NotificationStatus.SENT,
                )
            )

        await db.commit()
        logger.info(
            "notification_recorded", payment_id=str(payment_id), event_type=event_type
        )


async def run_forever() -> None:
    """
    Never returns under normal operation — safe to launch as a background
    asyncio task (see app/main.py's lifespan) or drive from main() below.

    If Kafka isn't reachable (not started yet, or restarting), this retries
    the connection every RECONNECT_DELAY_SECONDS instead of crashing the
    whole task — consumer group offsets pick up right where they left off
    once Kafka becomes available, with no need to restart the API.
    """
    while True:
        consumer = AIOKafkaConsumer(
            TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=GROUP_ID,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        try:
            await consumer.start()
            logger.info("notification_worker_started", topic=TOPIC)
            async for message in consumer:
                event = json.loads(message.value)
                # Re-bind the request_id carried on the event so every log
                # line for this message correlates back to the API request
                # that originally triggered the payment — same ID as in the
                # API's and the outbox publisher's logs for this payment.
                with structlog.contextvars.bound_contextvars(request_id=event.get("request_id")):
                    try:
                        await handle_event(event)
                    except Exception:
                        logger.exception(
                            "event_processing_failed",
                            event_id=event.get("event_id"),
                        )
                        continue
                    await consumer.commit()
        except asyncio.CancelledError:
            raise  # let the app shut this down cleanly, don't treat it as a retryable failure
        except Exception:
            logger.warning(
                "notification_worker_lost_connection_retrying",
                retry_in_seconds=RECONNECT_DELAY_SECONDS,
            )
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
        finally:
            await consumer.stop()


async def main() -> None:
    configure_logging()
    await run_forever()


if __name__ == "__main__":
    asyncio.run(main())
