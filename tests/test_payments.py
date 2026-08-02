import uuid

from sqlalchemy import select

from app.models.account import Account, AccountStatus


async def test_successful_payment_full_flow(client, funded_user):
    sender = await funded_user("sender@okpayup", balance_paise=10_000_00, email="psender@example.com")
    receiver = await funded_user(
        "receiver@okpayup", balance_paise=0, email="preceiver@example.com"
    )

    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "sender@okpayup",
            "receiver_vpa": "receiver@okpayup",
            "amount_paise": 2_500_00,
        },
        headers={**sender["headers"], "Idempotency-Key": "test-key-success-1"},
    )
    assert resp.status_code == 201
    payment = resp.json()
    assert payment["status"] == "SUCCESS"

    sender_balance = await client.get(
        f"/accounts/{sender['account']['id']}/balance", headers=sender["headers"]
    )
    receiver_balance = await client.get(
        f"/accounts/{receiver['account']['id']}/balance", headers=receiver["headers"]
    )
    assert sender_balance.json()["balance_paise"] == 7_500_00
    assert receiver_balance.json()["balance_paise"] == 2_500_00

    events_resp = await client.get(
        f"/payments/{payment['id']}/events", headers=sender["headers"]
    )
    event_types = [e["event_type"] for e in events_resp.json()]
    assert event_types == ["INITIATED", "PROCESSING", "DEBITED", "CREDITED", "SUCCESS"]


async def test_insufficient_funds_no_side_effects(client, funded_user):
    sender = await funded_user("poor@okpayup", balance_paise=100, email="poor@example.com")
    _receiver = await funded_user(
        "richreceiver@okpayup", balance_paise=0, email="richreceiver@example.com"
    )

    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "poor@okpayup",
            "receiver_vpa": "richreceiver@okpayup",
            "amount_paise": 999_999_999,
        },
        headers={**sender["headers"], "Idempotency-Key": "test-key-insufficient"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INSUFFICIENT_FUNDS"

    sender_balance = await client.get(
        f"/accounts/{sender['account']['id']}/balance", headers=sender["headers"]
    )
    assert sender_balance.json()["balance_paise"] == 100


async def test_credit_failure_triggers_compensation(client, funded_user, db_session):
    sender = await funded_user("compsender@okpayup", balance_paise=10_000_00, email="compsender@example.com")
    receiver = await funded_user(
        "compreceiver@okpayup", balance_paise=0, email="compreceiver@example.com"
    )

    # Freeze the receiver's account so the credit leg fails after the debit succeeds.
    account_row = (
        await db_session.execute(
            select(Account).where(Account.id == uuid.UUID(receiver["account"]["id"]))
        )
    ).scalar_one()
    account_row.status = AccountStatus.FROZEN
    await db_session.commit()

    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "compsender@okpayup",
            "receiver_vpa": "compreceiver@okpayup",
            "amount_paise": 1_000_00,
        },
        headers={**sender["headers"], "Idempotency-Key": "test-key-compensation"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "ACCOUNT_NOT_ACTIVE"

    # The debit + compensating refund must net to exactly zero.
    sender_balance = await client.get(
        f"/accounts/{sender['account']['id']}/balance", headers=sender["headers"]
    )
    assert sender_balance.json()["balance_paise"] == 10_000_00

    ledger_resp = await client.get(
        f"/accounts/{sender['account']['id']}/ledger", headers=sender["headers"]
    )
    entries = ledger_resp.json()
    assert [e["entry_type"] for e in entries[-2:]] == ["DEBIT", "CREDIT"]
    assert entries[-2]["amount_paise"] == entries[-1]["amount_paise"] == 1_000_00


async def test_idempotent_replay_returns_cached_result_without_reprocessing(client, funded_user):
    sender = await funded_user("idemsender@okpayup", balance_paise=10_000_00, email="idemsender@example.com")
    _receiver = await funded_user(
        "idemreceiver@okpayup", balance_paise=0, email="idemreceiver@example.com"
    )
    payload = {
        "sender_vpa": "idemsender@okpayup",
        "receiver_vpa": "idemreceiver@okpayup",
        "amount_paise": 500_00,
    }
    headers = {**sender["headers"], "Idempotency-Key": "replay-key-1"}

    first = await client.post("/payments", json=payload, headers=headers)
    second = await client.post("/payments", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    sender_balance = await client.get(
        f"/accounts/{sender['account']['id']}/balance", headers=sender["headers"]
    )
    assert sender_balance.json()["balance_paise"] == 10_000_00 - 500_00


async def test_idempotency_key_reuse_with_different_payload_rejected(client, funded_user):
    sender = await funded_user("conflictsender@okpayup", balance_paise=10_000_00, email="conflictsender@example.com")
    await funded_user("conflictreceiver@okpayup", balance_paise=0, email="conflictreceiver@example.com")

    headers = {**sender["headers"], "Idempotency-Key": "conflict-key-1"}
    await client.post(
        "/payments",
        json={
            "sender_vpa": "conflictsender@okpayup",
            "receiver_vpa": "conflictreceiver@okpayup",
            "amount_paise": 100_00,
        },
        headers=headers,
    )
    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "conflictsender@okpayup",
            "receiver_vpa": "conflictreceiver@okpayup",
            "amount_paise": 200_00,  # different amount, same key
        },
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "IDEMPOTENCY_CONFLICT"


async def test_missing_idempotency_key_rejected(client, funded_user):
    sender = await funded_user("nokeysender@okpayup", email="nokeysender@example.com")
    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "nokeysender@okpayup",
            "receiver_vpa": "anyone@okpayup",
            "amount_paise": 100,
        },
        headers=sender["headers"],
    )
    assert resp.status_code == 422


async def test_self_payment_rejected(client, funded_user):
    identity = await funded_user("selfpay@okpayup", balance_paise=10_000_00, email="selfpay@example.com")
    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "selfpay@okpayup",
            "receiver_vpa": "selfpay@okpayup",
            "amount_paise": 100,
        },
        headers={**identity["headers"], "Idempotency-Key": "self-pay-key"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_OPERATION"


async def test_cannot_pay_from_someone_elses_vpa(client, funded_user):
    _owner = await funded_user("vpaowner2@okpayup", balance_paise=10_000_00, email="vpaowner2@example.com")
    intruder = await funded_user(
        "intruder2@okpayup", balance_paise=10_000_00, email="intruder2@example.com"
    )

    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "vpaowner2@okpayup",
            "receiver_vpa": "intruder2@okpayup",
            "amount_paise": 100,
        },
        headers={**intruder["headers"], "Idempotency-Key": "steal-key"},
    )
    assert resp.status_code == 403


async def test_unknown_receiver_vpa_404(client, funded_user):
    sender = await funded_user("unknownreceiversender@okpayup", balance_paise=10_000_00, email="urs@example.com")
    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "unknownreceiversender@okpayup",
            "receiver_vpa": "nobody@okpayup",
            "amount_paise": 100,
        },
        headers={**sender["headers"], "Idempotency-Key": "unknown-vpa-key"},
    )
    assert resp.status_code == 404


async def test_payment_visible_to_both_sender_and_receiver(client, funded_user):
    sender = await funded_user("bothsender@okpayup", balance_paise=10_000_00, email="bothsender@example.com")
    receiver = await funded_user(
        "bothreceiver@okpayup", balance_paise=0, email="bothreceiver@example.com"
    )
    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "bothsender@okpayup",
            "receiver_vpa": "bothreceiver@okpayup",
            "amount_paise": 100,
        },
        headers={**sender["headers"], "Idempotency-Key": "both-visible-key"},
    )
    payment_id = resp.json()["id"]

    sender_get = await client.get(f"/payments/{payment_id}", headers=sender["headers"])
    receiver_get = await client.get(f"/payments/{payment_id}", headers=receiver["headers"])
    assert sender_get.status_code == 200
    assert receiver_get.status_code == 200


async def test_unrelated_user_cannot_view_payment(client, funded_user):
    sender = await funded_user("unrelatedsender@okpayup", balance_paise=10_000_00, email="unrelatedsender@example.com")
    _receiver = await funded_user(
        "unrelatedreceiver@okpayup", balance_paise=0, email="unrelatedreceiver@example.com"
    )
    bystander = await funded_user(
        "bystander@okpayup", balance_paise=0, email="bystander@example.com"
    )
    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "unrelatedsender@okpayup",
            "receiver_vpa": "unrelatedreceiver@okpayup",
            "amount_paise": 100,
        },
        headers={**sender["headers"], "Idempotency-Key": "unrelated-key"},
    )
    payment_id = resp.json()["id"]

    resp = await client.get(f"/payments/{payment_id}", headers=bystander["headers"])
    assert resp.status_code == 403
