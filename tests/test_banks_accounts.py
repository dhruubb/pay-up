async def test_create_bank(client, register_user, create_bank):
    identity = await register_user()
    bank = await create_bank(identity["headers"], name="HDFC Bank", code="HDFC0001")
    assert bank["name"] == "HDFC Bank"
    assert bank["code"] == "HDFC0001"


async def test_duplicate_bank_code_rejected(client, register_user, create_bank):
    identity = await register_user()
    await create_bank(identity["headers"], code="DUPCODE")
    resp = await client.post(
        "/banks",
        json={"name": "Another Bank", "code": "DUPCODE"},
        headers=identity["headers"],
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "DUPLICATE_BANK"


async def test_open_account(client, register_user, create_bank, open_account):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])
    assert account["bank_id"] == bank["id"]
    assert account["status"] == "ACTIVE"
    assert len(account["account_number"]) == 12


async def test_duplicate_account_same_bank_rejected(client, register_user, create_bank, open_account):
    """One account per bank per user — the invariant Phase 1 was built around."""
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    await open_account(identity["headers"], bank["id"])

    resp = await client.post(
        "/accounts", json={"bank_id": bank["id"]}, headers=identity["headers"]
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "DUPLICATE_ACCOUNT"


async def test_two_different_banks_allowed(client, register_user, create_bank, open_account):
    identity = await register_user()
    bank_a = await create_bank(identity["headers"])
    bank_b = await create_bank(identity["headers"])
    account_a = await open_account(identity["headers"], bank_a["id"])
    account_b = await open_account(identity["headers"], bank_b["id"])
    assert account_a["id"] != account_b["id"]


async def test_cannot_access_another_users_account(
    client, register_user, create_bank, open_account
):
    owner = await register_user(email="owner@example.com")
    other = await register_user(email="other@example.com")
    bank = await create_bank(owner["headers"])
    account = await open_account(owner["headers"], bank["id"])

    resp = await client.get(f"/accounts/{account['id']}", headers=other["headers"])
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "ACCESS_DENIED"


async def test_account_not_found(client, register_user):
    identity = await register_user()
    resp = await client.get(
        "/accounts/00000000-0000-0000-0000-000000000000", headers=identity["headers"]
    )
    assert resp.status_code == 404


async def test_account_balance_starts_at_zero(client, register_user, create_bank, open_account):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])
    resp = await client.get(f"/accounts/{account['id']}/balance", headers=identity["headers"])
    assert resp.status_code == 200
    assert resp.json()["balance_paise"] == 0
