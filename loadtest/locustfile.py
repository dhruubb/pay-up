"""
Load test against a real, already-running Pay-Up API (not a mock).

Run (with the API up on :8123 and this project's venv active):
    uv run locust -f loadtest/locustfile.py --host http://localhost:8123

Then open http://localhost:8089 for Locust's UI, or run headless:
    uv run locust -f loadtest/locustfile.py --host http://localhost:8123 \
        --headless -u 20 -r 5 --run-time 2m

Each simulated user registers, opens a bank/account/VPA, and gets a balance
seeded directly via the DB — there's no deposit endpoint in this app by
design (UPI only ever moves money between two existing accounts), so this
writes a ledger entry directly, same idea as scripts/seed_balance.py.
Watch it show up in real time at http://localhost:9090 (Prometheus) or by
curling http://localhost:8123/metrics directly.

Seeding uses plain synchronous sqlite3, not the app's async SQLAlchemy
session — Locust monkey-patches the runtime with gevent, and mixing that
with asyncio.run() silently dropped writes in testing here (some seeded
accounts ended up with a balance of 0, no error raised). Raw sqlite3 sidesteps
the gevent/asyncio interaction entirely for this one write.
"""

import random
import re
import sqlite3
import uuid

from locust import HttpUser, between, task

from app.core.config import settings

# Shared across all simulated users in this process — lets send_payment()
# target a real VPA belonging to some other simulated user.
_known_vpas: list[str] = []

STARTING_BALANCE_PAISE = 100_000_00  # ₹100,000 — enough headroom for a long run of small payments


def _sqlite_path_from_url(database_url: str) -> str:
    match = re.match(r"^sqlite:///(.+)$", database_url)
    if not match:
        raise RuntimeError(
            f"This load test's seeding helper only supports a sqlite DATABASE_URL, got: {database_url}"
        )
    return match.group(1)


_DB_PATH = _sqlite_path_from_url(settings.DATABASE_URL)


def _seed_balance_sync(account_id: str, amount_paise: int) -> None:
    entry_id = uuid.uuid4().hex
    account_id_hex = account_id.replace("-", "")
    con = sqlite3.connect(_DB_PATH)
    try:
        con.execute(
            "INSERT INTO ledger_entries "
            "(id, account_id, payment_id, entry_type, amount_paise, balance_after_paise) "
            "VALUES (?, ?, NULL, 'CREDIT', ?, ?)",
            (entry_id, account_id_hex, amount_paise, amount_paise),
        )
        con.commit()
    finally:
        con.close()


class PayUpUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        tag = uuid.uuid4().hex[:10]
        self.email = f"loadtest_{tag}@example.com"
        password = "secretpass123"

        self.client.post(
            "/users/register",
            json={
                "name": f"Load Test {tag}",
                "email": self.email,
                "phone": f"9{tag[:9]}",
                "password": password,
            },
            name="/users/register",
        )
        login_resp = self.client.post(
            "/users/login",
            json={"email": self.email, "password": password},
            name="/users/login",
        )
        token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

        bank = self.client.post(
            "/banks",
            json={"name": f"Load Bank {tag}", "code": f"LB{tag}"},
            headers=self.headers,
            name="/banks",
        ).json()
        psp = self.client.post(
            "/psps",
            json={"name": f"Load PSP {tag}", "code": f"LP{tag}"},
            headers=self.headers,
            name="/psps",
        ).json()
        account = self.client.post(
            "/accounts",
            json={"bank_id": bank["id"]},
            headers=self.headers,
            name="/accounts [POST]",
        ).json()

        self.vpa_address = f"loadtest{tag}@okpayup"
        self.client.post(
            "/vpas",
            json={
                "account_id": account["id"],
                "psp_id": psp["id"],
                "address": self.vpa_address,
            },
            headers=self.headers,
            name="/vpas [POST]",
        )

        _seed_balance_sync(account["id"], STARTING_BALANCE_PAISE)
        _known_vpas.append(self.vpa_address)

    @task(5)
    def view_accounts(self) -> None:
        self.client.get("/accounts", headers=self.headers, name="/accounts [GET]")

    @task(3)
    def view_payments(self) -> None:
        self.client.get("/payments", headers=self.headers, name="/payments [GET]")

    @task(2)
    def view_notifications(self) -> None:
        self.client.get("/notifications", headers=self.headers, name="/notifications [GET]")

    @task(4)
    def send_payment(self) -> None:
        candidates = [v for v in _known_vpas if v != self.vpa_address]
        if not candidates:
            return
        receiver = random.choice(candidates)
        self.client.post(
            "/payments",
            json={
                "sender_vpa": self.vpa_address,
                "receiver_vpa": receiver,
                "amount_paise": random.randint(10, 5_000),
            },
            headers={**self.headers, "Idempotency-Key": str(uuid.uuid4())},
            name="/payments [POST]",
        )
