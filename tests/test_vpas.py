async def test_first_vpa_is_auto_primary(
    client, register_user, create_bank, create_psp, open_account, create_vpa
):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    psp = await create_psp(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])

    vpa = await create_vpa(identity["headers"], account["id"], psp["id"], "dhruv@okpayup")
    assert vpa["is_primary"] is True


async def test_second_vpa_is_not_primary(
    client, register_user, create_bank, create_psp, open_account, create_vpa
):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    psp = await create_psp(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])

    await create_vpa(identity["headers"], account["id"], psp["id"], "dhruv@okpayup")
    second = await create_vpa(identity["headers"], account["id"], psp["id"], "dhruv.alt@okpayup")
    assert second["is_primary"] is False


async def test_set_primary_switches_correctly(
    client, register_user, create_bank, create_psp, open_account, create_vpa
):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    psp = await create_psp(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])

    first = await create_vpa(identity["headers"], account["id"], psp["id"], "first@okpayup")
    second = await create_vpa(identity["headers"], account["id"], psp["id"], "second@okpayup")

    resp = await client.patch(f"/vpas/{second['id']}/primary", headers=identity["headers"])
    assert resp.status_code == 200
    assert resp.json()["is_primary"] is True

    first_resp = await client.get(f"/vpas/{first['id']}", headers=identity["headers"])
    assert first_resp.json()["is_primary"] is False


async def test_duplicate_vpa_address_rejected(
    client, register_user, create_bank, create_psp, open_account, create_vpa
):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    psp = await create_psp(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])
    await create_vpa(identity["headers"], account["id"], psp["id"], "taken@okpayup")

    resp = await client.post(
        "/vpas",
        json={"account_id": account["id"], "psp_id": psp["id"], "address": "taken@okpayup"},
        headers=identity["headers"],
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "DUPLICATE_VPA"


async def test_invalid_vpa_address_format_rejected(
    client, register_user, create_bank, create_psp, open_account
):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    psp = await create_psp(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])

    resp = await client.post(
        "/vpas",
        json={"account_id": account["id"], "psp_id": psp["id"], "address": "not-a-valid-vpa"},
        headers=identity["headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


async def test_resolve_vpa_by_address(
    client, register_user, create_bank, create_psp, open_account, create_vpa
):
    identity = await register_user()
    bank = await create_bank(identity["headers"])
    psp = await create_psp(identity["headers"])
    account = await open_account(identity["headers"], bank["id"])
    await create_vpa(identity["headers"], account["id"], psp["id"], "resolvable@okpayup")

    resp = await client.get("/vpas/resolve/resolvable@okpayup", headers=identity["headers"])
    assert resp.status_code == 200
    assert resp.json()["account_id"] == account["id"]


async def test_cannot_create_vpa_on_someone_elses_account(
    client, register_user, create_bank, create_psp, open_account
):
    owner = await register_user(email="vpaowner@example.com")
    intruder = await register_user(email="vpaintruder@example.com")
    bank = await create_bank(owner["headers"])
    psp = await create_psp(owner["headers"])
    account = await open_account(owner["headers"], bank["id"])

    resp = await client.post(
        "/vpas",
        json={"account_id": account["id"], "psp_id": psp["id"], "address": "intruder@okpayup"},
        headers=intruder["headers"],
    )
    assert resp.status_code == 403
