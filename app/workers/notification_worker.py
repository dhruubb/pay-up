"""
Standalone process: consumes payment events from Kafka and creates
notifications.

Run separately from the API process:
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

        if event_type == "SUCCESS":
            receiver_account = await account_repo.get_by_id(payment.receiver_account_id)
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


async def main() -> None:
    configure_logging()
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    logger.info("notification_worker_started", topic=TOPIC)
    try:
        async for message in consumer:
            event = json.loads(message.value)
            # Re-bind the request_id carried on the event so every log line
            # for this message correlates back to the API request that
            # originally triggered the payment — same ID as in the API's
            # and the outbox publisher's logs for this payment.
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
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
