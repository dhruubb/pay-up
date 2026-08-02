import os

# Must happen before any `app.*` import — Settings() is instantiated at import
# time in app/core/config.py, and env vars take priority over .env values.
os.environ["DATABASE_URL"] = "sqlite:///./test_payup.db"
os.environ["JWT_SECRET"] = "test-secret-key-thats-long-enough-for-hs256"

import uuid  # noqa: E402
from collections.abc import Awaitable, Callable  # noqa: E402
from typing import Any  # noqa: E402

import pytest_asyncio  # noqa: E402
from fakeredis import FakeAsyncRedis  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.models  # noqa: E402, F401 — populates Base.metadata for create_all
from app.core.redis import get_redis  # noqa: E402
from app.db.base_class import Base  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.ledger_entry import LedgerEntry, LedgerEntryType  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _clean_database():
    """Every test starts against a fresh, empty schema."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(autouse=True)
async def _fake_redis():
    """A fresh in-memory Redis per test — no real Redis server needed, and no
    rate-limit state leaking between tests."""
    fake = FakeAsyncRedis()
    app.dependency_overrides[get_redis] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_redis, None)
    await fake.aclose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
def register_user(
    client: AsyncClient,
) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Factory: register + log in a user, returning {user, headers, email, password}."""
    counter = {"n": 0}

    async def _factory(**overrides: Any) -> dict[str, Any]:
        counter["n"] += 1
        n = counter["n"]
        payload = {
            "name": overrides.get("name", f"Test User {n}"),
            "email": overrides.get("email", f"user{n}@example.com"),
            "phone": overrides.get("phone", f"9{n:09d}"),
            "password": overrides.get("password", "secretpass123"),
        }
        reg_resp = await client.post("/users/register", json=payload)
        assert reg_resp.status_code == 201, reg_resp.text

        login_resp = await client.post(
            "/users/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]

        return {
            "user": reg_resp.json(),
            "headers": {"Authorization": f"Bearer {token}"},
            "email": payload["email"],
            "password": payload["password"],
        }

    return _factory


@pytest_asyncio.fixture
def create_bank(client: AsyncClient) -> Callable[..., Awaitable[dict[str, Any]]]:
    counter = {"n": 0}

    async def _factory(headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
        counter["n"] += 1
        n = counter["n"]
        payload = {
            "name": overrides.get("name", f"Test Bank {n}"),
            "code": overrides.get("code", f"TB{n:04d}"),
        }
        resp = await client.post("/banks", json=payload, headers=headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _factory


@pytest_asyncio.fixture
def create_psp(client: AsyncClient) -> Callable[..., Awaitable[dict[str, Any]]]:
    counter = {"n": 0}

    async def _factory(headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
        counter["n"] += 1
        n = counter["n"]
        payload = {
            "name": overrides.get("name", f"Test PSP {n}"),
            "code": overrides.get("code", f"PSP{n:04d}"),
        }
        resp = await client.post("/psps", json=payload, headers=headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _factory


@pytest_asyncio.fixture
def open_account(client: AsyncClient) -> Callable[..., Awaitable[dict[str, Any]]]:
    async def _factory(headers: dict[str, str], bank_id: str) -> dict[str, Any]:
        resp = await client.post("/accounts", json={"bank_id": bank_id}, headers=headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _factory


@pytest_asyncio.fixture
def create_vpa(client: AsyncClient) -> Callable[..., Awaitable[dict[str, Any]]]:
    async def _factory(
        headers: dict[str, str], account_id: str, psp_id: str, address: str
    ) -> dict[str, Any]:
        resp = await client.post(
            "/vpas",
            json={"account_id": account_id, "psp_id": psp_id, "address": address},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _factory


@pytest_asyncio.fixture
def seed_balance(
    db_session: AsyncSession,
) -> Callable[[str, int], Awaitable[None]]:
    """Directly credit an account via the ledger — there is no deposit API by design."""

    async def _factory(account_id: str, amount_paise: int) -> None:
        db_session.add(
            LedgerEntry(
                account_id=uuid.UUID(account_id),
                entry_type=LedgerEntryType.CREDIT,
                amount_paise=amount_paise,
                balance_after_paise=amount_paise,
            )
        )
        await db_session.commit()

    return _factory


@pytest_asyncio.fixture
async def funded_user(
    register_user, create_bank, create_psp, open_account, create_vpa, seed_balance
) -> Callable[..., Awaitable[dict[str, Any]]]:
    """One-shot setup: a registered user with a funded account and a primary VPA."""

    async def _factory(
        vpa_address: str, balance_paise: int = 10_000_00, **user_overrides: Any
    ) -> dict[str, Any]:
        identity = await register_user(**user_overrides)
        bank = await create_bank(identity["headers"])
        psp = await create_psp(identity["headers"])
        account = await open_account(identity["headers"], bank["id"])
        vpa = await create_vpa(identity["headers"], account["id"], psp["id"], vpa_address)
        if balance_paise:
            await seed_balance(account["id"], balance_paise)
        return {**identity, "bank": bank, "psp": psp, "account": account, "vpa": vpa}

    return _factory
