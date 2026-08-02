import asyncio
import uuid

from sqlalchemy import select

from app.models.account import Account, AccountStatus


async def _open_funded_pair(register_user, create_bank, open_account, seed_balance):
    sender = await register_user(email="ledger_sender@example.com")
    receiver = await register_user(email="ledger_receiver@example.com")
    bank = await create_bank(sender["headers"])
    sender_account = await open_account(sender["headers"], bank["id"])
    receiver_account = await open_account(receiver["headers"], bank["id"])
    await seed_balance(sender_account["id"], 100_000)  # ₹1000.00
    return sender, receiver, sender_account, receiver_account


async def test_transfer_moves_money_correctly(
    client, register_user, create_bank, open_account, seed_balance
):
    sender, _receiver, sender_account, receiver_account = await _open_funded_pair(
        register_user, create_bank, open_account, seed_balance
    )

    resp = await client.post(
        "/ledger/transfer",
        json={
            "from_account_id": sender_account["id"],
            "to_account_id": receiver_account["id"],
            "amount_paise": 25_000,
        },
        headers=sender["headers"],
    )
    assert resp.status_code == 201

    sender_balance = await client.get(
        f"/accounts/{sender_account['id']}/balance", headers=sender["headers"]
    )
    assert sender_balance.json()["balance_paise"] == 75_000


async def test_insufficient_funds_rejected(
    client, register_user, create_bank, open_account, seed_balance
):
    sender, _receiver, sender_account, receiver_account = await _open_funded_pair(
        register_user, create_bank, open_account, seed_balance
    )

    resp = await client.post(
        "/ledger/transfer",
        json={
            "from_account_id": sender_account["id"],
            "to_account_id": receiver_account["id"],
            "amount_paise": 999_999_999,
        },
        headers=sender["headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INSUFFICIENT_FUNDS"


async def test_self_transfer_rejected(
    client, register_user, create_bank, open_account, seed_balance
):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])
    await seed_balance(account["id"], 10_000)

    resp = await client.post(
        "/ledger/transfer",
        json={
            "from_account_id": account["id"],
            "to_account_id": account["id"],
            "amount_paise": 100,
        },
        headers=identity["headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_OPERATION"


async def test_cannot_debit_someone_elses_account(
    client, register_user, create_bank, open_account, seed_balance
):
    sender, receiver, sender_account, receiver_account = await _open_funded_pair(
        register_user, create_bank, open_account, seed_balance
    )

    # receiver tries to move money OUT of sender's account
    resp = await client.post(
        "/ledger/transfer",
        json={
            "from_account_id": sender_account["id"],
            "to_account_id": receiver_account["id"],
            "amount_paise": 100,
        },
        headers=receiver["headers"],
    )
    assert resp.status_code == 403


async def test_frozen_account_rejected(
    client, register_user, create_bank, open_account, seed_balance, db_session
):
    sender, _receiver, sender_account, receiver_account = await _open_funded_pair(
        register_user, create_bank, open_account, seed_balance
    )

    account_row = (
        await db_session.execute(
            select(Account).where(Account.id == uuid.UUID(receiver_account["id"]))
        )
    ).scalar_one()
    account_row.status = AccountStatus.FROZEN
    await db_session.commit()

    resp = await client.post(
        "/ledger/transfer",
        json={
            "from_account_id": sender_account["id"],
            "to_account_id": receiver_account["id"],
            "amount_paise": 100,
        },
        headers=sender["headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "ACCOUNT_NOT_ACTIVE"


async def test_concurrent_transfers_never_overdraw_account(
    client, register_user, create_bank, open_account, seed_balance
):
    """
    The real invariant under test: fire more concurrent debit requests than
    the balance can cover, and verify the account never goes negative and the
    final balance always matches exactly (initial - sum of what *actually*
    succeeded) — no lost updates, no double-spend, regardless of how many of
    the concurrent requests happened to win.
    """
    sender, receiver, sender_account, receiver_account = await _open_funded_pair(
        register_user, create_bank, open_account, seed_balance
    )
    # Balance is 100_000 paise. Fire 20 concurrent transfers of 10_000 each —
    # only 10 can possibly succeed.
    amount_per_transfer = 10_000
    num_requests = 20

    async def attempt():
        return await client.post(
            "/ledger/transfer",
            json={
                "from_account_id": sender_account["id"],
                "to_account_id": receiver_account["id"],
                "amount_paise": amount_per_transfer,
            },
            headers=sender["headers"],
        )

    responses = await asyncio.gather(*[attempt() for _ in range(num_requests)])

    successes = [r for r in responses if r.status_code == 201]
    failures = [r for r in responses if r.status_code != 201]
    assert all(r.status_code == 422 for r in failures)

    sender_balance_resp = await client.get(
        f"/accounts/{sender_account['id']}/balance", headers=sender["headers"]
    )
    receiver_balance_resp = await client.get(
        f"/accounts/{receiver_account['id']}/balance", headers=receiver["headers"]
    )
    sender_balance = sender_balance_resp.json()["balance_paise"]
    receiver_balance = receiver_balance_resp.json()["balance_paise"]

    assert sender_balance >= 0, "account went negative under concurrent load"
    assert sender_balance == 100_000 - len(successes) * amount_per_transfer
    assert receiver_balance == len(successes) * amount_per_transfer
    assert len(successes) <= 10
