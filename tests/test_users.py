async def test_register_creates_user(client):
    resp = await client.post(
        "/users/register",
        json={
            "name": "Dhruv",
            "email": "dhruv@example.com",
            "phone": "9999999999",
            "password": "secretpass123",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "dhruv@example.com"
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_rejected(client, register_user):
    await register_user(email="dupe@example.com", phone="1111111111")
    resp = await client.post(
        "/users/register",
        json={
            "name": "Someone Else",
            "email": "dupe@example.com",
            "phone": "2222222222",
            "password": "secretpass123",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "DUPLICATE_USER"


async def test_register_duplicate_phone_rejected(client, register_user):
    """Regression test: duplicate phone used to 500 instead of a clean 409."""
    await register_user(email="first@example.com", phone="3333333333")
    resp = await client.post(
        "/users/register",
        json={
            "name": "Someone Else",
            "email": "second@example.com",
            "phone": "3333333333",
            "password": "secretpass123",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "DUPLICATE_USER"


async def test_login_success(client, register_user):
    identity = await register_user(email="loginok@example.com", password="secretpass123")
    resp = await client.post(
        "/users/login",
        json={"email": identity["email"], "password": "secretpass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]


async def test_login_wrong_password_rejected(client, register_user):
    identity = await register_user(email="wrongpass@example.com")
    resp = await client.post(
        "/users/login",
        json={"email": identity["email"], "password": "not-the-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "AUTHENTICATION_FAILED"


async def test_login_unknown_email_rejected(client):
    resp = await client.post(
        "/users/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "AUTHENTICATION_FAILED"


async def test_me_requires_auth(client):
    resp = await client.get("/users/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(client, register_user):
    identity = await register_user(email="me@example.com")
    resp = await client.get("/users/me", headers=identity["headers"])
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


async def test_me_rejects_tampered_token(client, register_user):
    identity = await register_user(email="tampered@example.com")
    bad_token = identity["headers"]["Authorization"] + "tampered"
    resp = await client.get("/users/me", headers={"Authorization": bad_token})
    assert resp.status_code == 401
