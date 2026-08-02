async def test_login_rate_limited_after_five_attempts(client):
    # Register directly rather than via the register_user fixture — that
    # fixture also logs in once as part of setup, which would itself consume
    # one of the 5 login-attempt slots this test is trying to count exactly.
    await client.post(
        "/users/register",
        json={
            "name": "Rate Limited",
            "email": "ratelimited@example.com",
            "phone": "9123456789",
            "password": "secretpass123",
        },
    )

    # 5 failed attempts are allowed (wrong password each time).
    for _ in range(5):
        resp = await client.post(
            "/users/login",
            json={"email": "ratelimited@example.com", "password": "wrong-password"},
        )
        assert resp.status_code == 401

    # The 6th attempt within the window is rate-limited, not another 401.
    resp = await client.post(
        "/users/login",
        json={"email": "ratelimited@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 429
    assert resp.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in resp.headers


async def test_payment_initiation_rate_limited_per_user(client, funded_user):
    sender = await funded_user("ratelimitsender@okpayup", balance_paise=100_000_00, email="rlsender@example.com")
    await funded_user("ratelimitreceiver@okpayup", balance_paise=0, email="rlreceiver@example.com")

    for i in range(10):
        resp = await client.post(
            "/payments",
            json={
                "sender_vpa": "ratelimitsender@okpayup",
                "receiver_vpa": "ratelimitreceiver@okpayup",
                "amount_paise": 100,
            },
            headers={**sender["headers"], "Idempotency-Key": f"rl-key-{i}"},
        )
        assert resp.status_code == 201

    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "ratelimitsender@okpayup",
            "receiver_vpa": "ratelimitreceiver@okpayup",
            "amount_paise": 100,
        },
        headers={**sender["headers"], "Idempotency-Key": "rl-key-overflow"},
    )
    assert resp.status_code == 429


async def test_payment_rate_limit_does_not_affect_other_users(client, funded_user):
    sender_a = await funded_user("rlusera@okpayup", balance_paise=100_000_00, email="rlusera@example.com")
    sender_b = await funded_user("rluserb@okpayup", balance_paise=100_000_00, email="rluserb@example.com")
    _receiver = await funded_user("rlreceiver2@okpayup", balance_paise=0, email="rlreceiver2@example.com")

    for i in range(10):
        resp = await client.post(
            "/payments",
            json={
                "sender_vpa": "rlusera@okpayup",
                "receiver_vpa": "rlreceiver2@okpayup",
                "amount_paise": 100,
            },
            headers={**sender_a["headers"], "Idempotency-Key": f"rl-a-key-{i}"},
        )
        assert resp.status_code == 201

    # sender_a is now exhausted, but sender_b's own bucket is untouched.
    resp = await client.post(
        "/payments",
        json={
            "sender_vpa": "rluserb@okpayup",
            "receiver_vpa": "rlreceiver2@okpayup",
            "amount_paise": 100,
        },
        headers={**sender_b["headers"], "Idempotency-Key": "rl-b-key-1"},
    )
    assert resp.status_code == 201
