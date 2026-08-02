import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppException,
    AuthorizationError,
    IdempotencyConflictError,
    InvalidOperationError,
    NotFoundError,
)
from app.core.metrics import idempotency_replays_total, payment_amount_paise, payments_total
from app.models.audit_log import AuditActorType
from app.models.idempotency_key import IdempotencyStatus
from app.models.ledger_entry import LedgerEntryType
from app.models.payment import Payment, PaymentStatus
from app.models.payment_event import PaymentEventType
from app.modules.accounts.repository import AccountRepository
from app.modules.audit.service import AuditLogService
from app.modules.ledger.service import LedgerService
from app.modules.payments.event_repository import PaymentEventRepository
from app.modules.payments.idempotency_repository import IdempotencyKeyRepository
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schema import (
    PaymentCreateRequest,
    PaymentEventResponse,
    PaymentResponse,
)
from app.modules.vpas.repository import VpaRepository

# How long an IN_PROGRESS idempotency record blocks retries before it's
# treated as abandoned (e.g. the process crashed mid-request) and reprocessed.
STALE_IN_PROGRESS_SECONDS = 120


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaymentRepository(db)
        self.idempotency_repo = IdempotencyKeyRepository(db)
        self.account_repo = AccountRepository(db)
        self.vpa_repo = VpaRepository(db)
        self.ledger_service = LedgerService(db)
        self.event_repo = PaymentEventRepository(db)
        self.audit_service = AuditLogService(db)

    @staticmethod
    def _event_payload(payment: Payment) -> str:
        return json.dumps(
            {
                "payment_id": str(payment.id),
                "status": payment.status.value,
                "amount_paise": payment.amount_paise,
                "sender_account_id": str(payment.sender_account_id),
                "receiver_account_id": str(payment.receiver_account_id),
                "failure_reason": payment.failure_reason,
            }
        )

    async def _record_event(self, payment: Payment, event_type: PaymentEventType) -> None:
        # request_id lets this event's downstream Kafka message (and the
        # notification worker log lines that process it) be correlated back
        # to the API request that caused it — see app/middleware/request_id.py.
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        await self.event_repo.record(
            payment.id, event_type, self._event_payload(payment), request_id
        )

    @staticmethod
    def _hash_request(request: PaymentCreateRequest) -> str:
        payload = json.dumps(request.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _serialize_success(response: PaymentResponse) -> str:
        return json.dumps({"outcome": "success", "payment": response.model_dump(mode="json")})

    @staticmethod
    def _serialize_error(exc: AppException) -> str:
        return json.dumps(
            {
                "outcome": "error",
                "error_code": exc.error_code,
                "message": exc.message,
                "status_code": exc.status_code,
            }
        )

    @staticmethod
    def _replay(snapshot: str) -> PaymentResponse:
        data = json.loads(snapshot)
        if data["outcome"] == "success":
            return PaymentResponse(**data["payment"])
        raise AppException(
            message=data["message"],
            error_code=data["error_code"],
            status_code=data["status_code"],
        )

    async def initiate_payment(
        self,
        user_id: UUID,
        idempotency_key: str,
        request: PaymentCreateRequest,
    ) -> PaymentResponse:
        request_hash = self._hash_request(request)
        now = datetime.now(UTC)

        key_row = await self.idempotency_repo.get_by_key(idempotency_key)

        if key_row and key_row.request_hash != request_hash:
            raise IdempotencyConflictError(
                "This idempotency key was already used with a different request"
            )

        if key_row and key_row.status == IdempotencyStatus.COMPLETED:
            # response_snapshot is always set at the same time status is set
            # to COMPLETED (see the two commit sites below) — the type is
            # nullable only because the column starts NULL for IN_PROGRESS rows.
            assert key_row.response_snapshot is not None
            idempotency_replays_total.inc()
            return self._replay(key_row.response_snapshot)

        if key_row and key_row.status == IdempotencyStatus.IN_PROGRESS:
            age_seconds = (now - key_row.created_at).total_seconds()
            if age_seconds < STALE_IN_PROGRESS_SECONDS:
                raise IdempotencyConflictError(
                    "A request with this idempotency key is already being processed"
                )
            # else: stale — fall through and reprocess, reusing the same row.

        if not key_row:
            key_row = await self.idempotency_repo.create(idempotency_key, request_hash)
            await self.db.commit()

        try:
            response = await self._process_payment(user_id, request)
        except AppException as exc:
            key_row.response_snapshot = self._serialize_error(exc)
            key_row.status = IdempotencyStatus.COMPLETED
            await self.db.commit()
            raise

        key_row.response_snapshot = self._serialize_success(response)
        key_row.status = IdempotencyStatus.COMPLETED
        await self.db.commit()
        return response

    async def _process_payment(
        self, user_id: UUID, request: PaymentCreateRequest
    ) -> PaymentResponse:
        sender_vpa = await self.vpa_repo.get_by_address(request.sender_vpa.lower())
        if not sender_vpa:
            raise NotFoundError("VPA", request.sender_vpa)

        sender_account = await self.account_repo.get_by_id(sender_vpa.account_id)
        # A VPA's account_id always resolves — accounts are never deleted.
        assert sender_account is not None
        if sender_account.user_id != user_id:
            raise AuthorizationError("You can only pay from your own VPA")

        receiver_vpa = await self.vpa_repo.get_by_address(request.receiver_vpa.lower())
        if not receiver_vpa:
            raise NotFoundError("VPA", request.receiver_vpa)

        if sender_vpa.id == receiver_vpa.id:
            raise InvalidOperationError("Cannot pay your own VPA")

        payment = Payment(
            sender_account_id=sender_account.id,
            receiver_account_id=receiver_vpa.account_id,
            initiated_by_psp_id=sender_vpa.psp_id,
            amount_paise=request.amount_paise,
            status=PaymentStatus.INITIATED,
        )
        payment = await self.repo.create(payment)
        await self._record_event(payment, PaymentEventType.INITIATED)
        await self.db.commit()

        payment.status = PaymentStatus.PROCESSING
        await self._record_event(payment, PaymentEventType.PROCESSING)
        await self.db.commit()

        # Leg 1: debit the sender. This is its own commit — simulating a real
        # call to the sender's bank, which is a separate system that has no
        # idea whether the receiver's bank will ever be reachable. Locked on
        # the sender account so a concurrent payment/transfer against it
        # can't read a stale balance mid-flight (see LedgerService.locked).
        try:
            async with self.ledger_service.locked(payment.sender_account_id):
                await self.ledger_service.post_entry(
                    payment.sender_account_id,
                    LedgerEntryType.DEBIT,
                    payment.amount_paise,
                    payment_id=payment.id,
                )
                await self._record_event(payment, PaymentEventType.DEBITED)
                await self.db.commit()
        except AppException as exc:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = f"Debit failed: {exc.message}"
            payment.completed_at = datetime.now(UTC)
            await self._record_event(payment, PaymentEventType.FAILED)
            payments_total.labels(status="FAILED").inc()
            await self.audit_service.log(
                actor_type=AuditActorType.USER,
                actor_id=user_id,
                action="PAYMENT_FAILED",
                resource_type="Payment",
                resource_id=payment.id,
                details={"amount_paise": payment.amount_paise, "reason": payment.failure_reason},
            )
            await self.db.commit()
            raise

        # Leg 2: credit the receiver. If this fails, the debit already landed,
        # so we must compensate by refunding the sender — there is no shared
        # transaction spanning both legs to roll back.
        try:
            async with self.ledger_service.locked(payment.receiver_account_id):
                await self.ledger_service.post_entry(
                    payment.receiver_account_id,
                    LedgerEntryType.CREDIT,
                    payment.amount_paise,
                    payment_id=payment.id,
                )
                await self._record_event(payment, PaymentEventType.CREDITED)
                await self.db.commit()
        except AppException as exc:
            async with self.ledger_service.locked(payment.sender_account_id):
                await self.ledger_service.post_entry(
                    payment.sender_account_id,
                    LedgerEntryType.CREDIT,
                    payment.amount_paise,
                    payment_id=payment.id,
                )
                await self.db.commit()
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = f"Credit failed, sender refunded: {exc.message}"
            payment.completed_at = datetime.now(UTC)
            await self._record_event(payment, PaymentEventType.FAILED)
            payments_total.labels(status="FAILED").inc()
            await self.audit_service.log(
                actor_type=AuditActorType.USER,
                actor_id=user_id,
                action="PAYMENT_FAILED",
                resource_type="Payment",
                resource_id=payment.id,
                details={"amount_paise": payment.amount_paise, "reason": payment.failure_reason},
            )
            await self.db.commit()
            raise

        payment.status = PaymentStatus.SUCCESS
        payment.completed_at = datetime.now(UTC)
        await self._record_event(payment, PaymentEventType.SUCCESS)
        payments_total.labels(status="SUCCESS").inc()
        payment_amount_paise.observe(payment.amount_paise)
        await self.audit_service.log(
            actor_type=AuditActorType.USER,
            actor_id=user_id,
            action="PAYMENT_SUCCEEDED",
            resource_type="Payment",
            resource_id=payment.id,
            details={
                "amount_paise": payment.amount_paise,
                "sender_account_id": str(payment.sender_account_id),
                "receiver_account_id": str(payment.receiver_account_id),
            },
        )
        await self.db.commit()

        return PaymentResponse.model_validate(payment)

    async def get_payment(self, user_id: UUID, payment_id: UUID) -> PaymentResponse:
        payment = await self.repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment")

        sender_account = await self.account_repo.get_by_id(payment.sender_account_id)
        receiver_account = await self.account_repo.get_by_id(payment.receiver_account_id)
        assert sender_account is not None
        assert receiver_account is not None
        owner_ids = {sender_account.user_id, receiver_account.user_id}
        if user_id not in owner_ids:
            raise AuthorizationError("You do not have access to this payment")

        return PaymentResponse.model_validate(payment)

    async def list_my_payments(self, user_id: UUID) -> list[PaymentResponse]:
        accounts = await self.account_repo.list_for_user(user_id)
        account_ids = [account.id for account in accounts]
        payments = await self.repo.list_for_accounts(account_ids)
        return [PaymentResponse.model_validate(payment) for payment in payments]

    async def get_events(self, user_id: UUID, payment_id: UUID) -> list[PaymentEventResponse]:
        # Reuses the same ownership check as get_payment.
        await self.get_payment(user_id, payment_id)
        events = await self.event_repo.list_for_payment(payment_id)
        return [
            PaymentEventResponse(
                id=event.id,
                event_type=event.event_type,
                payload=json.loads(event.payload),
                published_at=event.published_at,
                created_at=event.created_at,
            )
            for event in events
        ]
