"""
Dev-only utility: credit a user's account directly via the ledger.

There is no deposit API in Pay-Up, by design — UPI models money as only ever
moving between two existing accounts, never appearing "from nowhere". This
script writes a single unmatched CREDIT ledger entry, bypassing the API, so
you can fund a test account locally without inventing a fake deposit endpoint.

Usage (run as a module from the repo root, so `app` is importable):
    uv run python -m scripts.seed_balance <email> <amount_in_rupees> [--account-id ACCOUNT_ID]

Examples:
    uv run python -m scripts.seed_balance dhruv@example.com 5000
    uv run python -m scripts.seed_balance dhruv@example.com 500.50 --account-id 3ac2b4c6-...
"""

import argparse
import asyncio
import uuid

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.account import Account
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.user import User
from app.modules.ledger.repository import LedgerRepository


async def main(email: str, amount_rupees: float, account_id: str | None) -> None:
    amount_paise = round(amount_rupees * 100)

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if not user:
            print(f"No user found with email {email}")
            return

        if account_id:
            account = (
                await db.execute(select(Account).where(Account.id == uuid.UUID(account_id)))
            ).scalar_one_or_none()
        else:
            account = (
                (await db.execute(select(Account).where(Account.user_id == user.id)))
                .scalars()
                .first()
            )

        if not account:
            print(f"No account found for {email}")
            return

        current_balance = await LedgerRepository(db).get_balance_paise(account.id)

        db.add(
            LedgerEntry(
                account_id=account.id,
                entry_type=LedgerEntryType.CREDIT,
                amount_paise=amount_paise,
                balance_after_paise=current_balance + amount_paise,
            )
        )
        await db.commit()
        print(
            f"Credited ₹{amount_rupees:.2f} to A/C {account.account_number} ({email}). "
            f"New balance: ₹{(current_balance + amount_paise) / 100:.2f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email", help="Email of the user whose account to credit")
    parser.add_argument("amount", type=float, help="Amount in rupees")
    parser.add_argument(
        "--account-id", default=None, help="Specific account id (defaults to the user's first account)"
    )
    args = parser.parse_args()
    asyncio.run(main(args.email, args.amount, args.account_id))
