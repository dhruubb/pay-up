"""
Fire a fixed number of real payment transactions against a running Pay-Up
API, for load/metrics observation.

Unlike loadtest/locustfile.py (a realistic *mix* of traffic, where payments
are a minority of requests), this fires exactly N payments and nothing else
— useful when you want a specific, countable number of transactions rather
than a sustained realistic session.

Usage (API must already be running):
    uv run python -m scripts.simulate_transactions --count 1000
    uv run python -m scripts.simulate_transactions --count 1000 --replay 200

Options:
    --count        number of payment transactions to fire (default 1000)
    --users        size of the funded-user pool payments are drawn from (default 20)
    --concurrency  max in-flight requests at once (default 20)
    --base-url     API base URL (default http://localhost:8123)
    --replay       number of already-sent payments to re-send with their
                   original idempotency key, to exercise the dedup path
                   (default 0)
"""

import argparse
import asyncio
import random
import re
import sqlite3
import time
import uuid

import httpx

from app.core.config import settings

STARTING_BALANCE_PAISE = 1_000_000_00  # ₹1,000,000 — plenty of headroom for a bulk run


def _sqlite_path_from_url(database_url: str) -> str:
    match = re.match(r"^sqlite:///(.+)$", database_url)
    if not match:
        raise RuntimeError(
            f"This script's seeding step only supports a sqlite DATABASE_URL, got: {database_url}"
        )
    return match.group(1)


def _seed_balance(db_path: str, account_id: str, amount_paise: int) -> None:
    entry_id = uuid.uuid4().hex
    account_id_hex = account_id.replace("-", "")
    con = sqlite3.connect(db_path)
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


async def _setup_user(client: httpx.AsyncClient, db_path: str) -> dict:
    tag = uuid.uuid4().hex[:10]
    email = f"simtx_{tag}@example.com"
    password = "secretpass123"

    await client.post(
        "/users/register",
        json={"name": f"SimTx {tag}", "email": email, "phone": f"9{tag[:9]}", "password": password},
    )
    login = await client.post("/users/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    bank = (
        await client.post("/banks", json={"name": f"SimBank {tag}", "code": f"SB{tag}"}, headers=headers)
    ).json()
    psp = (
        await client.post("/psps", json={"name": f"SimPSP {tag}", "code": f"SP{tag}"}, headers=headers)
    ).json()
    account = (
        await client.post("/accounts", json={"bank_id": bank["id"]}, headers=headers)
    ).json()
    address = f"simtx{tag}@okpayup"
    await client.post(
        "/vpas",
        json={"account_id": account["id"], "psp_id": psp["id"], "address": address},
        headers=headers,
    )

    _seed_balance(db_path, account["id"], STARTING_BALANCE_PAISE)
    return {"headers": headers, "vpa": address}


async def _send_one(
    client: httpx.AsyncClient,
    sender: dict,
    receiver_vpa: str,
    semaphore: asyncio.Semaphore,
    results: dict,
    idem_key: str | None = None,
    sent_keys: list | None = None,
) -> None:
    async with semaphore:
        key_used = idem_key or str(uuid.uuid4())
        try:
            resp = await client.post(
                "/payments",
                json={
                    "sender_vpa": sender["vpa"],
                    "receiver_vpa": receiver_vpa,
                    "amount_paise": random.randint(10, 5_000),
                },
                headers={**sender["headers"], "Idempotency-Key": key_used},
            )
            tag = "replay" if idem_key else "success"
            key = tag if resp.status_code == 201 else f"http_{resp.status_code}"
            results[key] = results.get(key, 0) + 1
            # record original (non-replay) successes so we can replay them later
            if idem_key is None and sent_keys is not None and resp.status_code == 201:
                sent_keys.append((key_used, sender, receiver_vpa))
        except httpx.HTTPError as exc:
            results["transport_error"] = results.get("transport_error", 0) + 1
            print(f"transport error: {exc}")


async def main(count: int, num_users: int, concurrency: int, base_url: str, replay: int) -> None:
    db_path = _sqlite_path_from_url(settings.DATABASE_URL)

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        print(f"Setting up {num_users} funded users...")
        users = [await _setup_user(client, db_path) for _ in range(num_users)]

        print(f"Firing {count} payment transactions (concurrency={concurrency})...")
        semaphore = asyncio.Semaphore(concurrency)
        results: dict[str, int] = {}
        sent_keys: list = []
        start = time.perf_counter()

        tasks = []
        for _ in range(count):
            sender, receiver = random.sample(users, 2)
            tasks.append(
                _send_one(client, sender, receiver["vpa"], semaphore, results, sent_keys=sent_keys)
            )

        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        print(f"\nDone: {count} transactions in {elapsed:.1f}s ({count / elapsed:.1f} tx/sec)")

        if replay > 0:
            replay_count = min(replay, len(sent_keys))
            if replay_count < replay:
                print(
                    f"\nOnly {len(sent_keys)} successful payments available to replay "
                    f"(requested {replay})."
                )
            print(f"\nReplaying {replay_count} payments with their original idempotency keys...")
            replay_start = time.perf_counter()
            replay_tasks = [
                _send_one(client, sender, receiver_vpa, semaphore, results, idem_key=idem_key)
                for idem_key, sender, receiver_vpa in random.sample(sent_keys, replay_count)
            ]
            await asyncio.gather(*replay_tasks)
            replay_elapsed = time.perf_counter() - replay_start
            print(f"Done: {replay_count} replays in {replay_elapsed:.1f}s")

        print("\nResults:")
        for key, value in sorted(results.items()):
            print(f"  {key}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--base-url", default="http://localhost:8123")
    parser.add_argument(
        "--replay",
        type=int,
        default=0,
        help="number of payments to re-send with their original idempotency key",
    )
    args = parser.parse_args()
    asyncio.run(main(args.count, args.users, args.concurrency, args.base_url, args.replay))