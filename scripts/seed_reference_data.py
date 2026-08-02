"""
Seed the banks and psps registries with realistic reference data, so you
don't have to manually "Register Bank" / "Register PSP" one at a time
through the UI every time you want to open an account or create a VPA.

Idempotent — safe to re-run; entries that already exist (matched by code)
are skipped.

Usage:
    uv run python -m scripts.seed_reference_data
"""

import asyncio

from app.db.session import AsyncSessionLocal
from app.models.bank import Bank
from app.models.psp import Psp
from app.modules.banks.repository import BankRepository
from app.modules.psps.repository import PspRepository

# Real IFSC-style bank prefixes, for a bit of realism.
BANKS = [
    ("State Bank of India", "SBIN"),
    ("HDFC Bank", "HDFC"),
    ("ICICI Bank", "ICIC"),
    ("Axis Bank", "UTIB"),
    ("Kotak Mahindra Bank", "KKBK"),
    ("Punjab National Bank", "PUNB"),
    ("Bank of Baroda", "BARB"),
    ("Canara Bank", "CNRB"),
    ("Union Bank of India", "UBIN"),
    ("IndusInd Bank", "INDB"),
    ("Yes Bank", "YESB"),
    ("IDFC First Bank", "IDFB"),
]

PSPS = [
    ("Google Pay", "GPAY"),
    ("PhonePe", "PHONEPE"),
    ("Paytm", "PAYTM"),
    ("Amazon Pay", "AMAZONPAY"),
    ("BHIM", "BHIM"),
    ("WhatsApp Pay", "WHATSAPP"),
    ("CRED", "CRED"),
    ("Mobikwik", "MOBIKWIK"),
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        bank_repo = BankRepository(db)
        psp_repo = PspRepository(db)

        added_banks = 0
        for name, code in BANKS:
            if await bank_repo.get_by_code(code):
                print(f"  bank already exists: {name} ({code})")
                continue
            await bank_repo.create(Bank(name=name, code=code))
            added_banks += 1
            print(f"  + added bank: {name} ({code})")

        added_psps = 0
        for name, code in PSPS:
            if await psp_repo.get_by_code(code):
                print(f"  psp already exists: {name} ({code})")
                continue
            await psp_repo.create(Psp(name=name, code=code))
            added_psps += 1
            print(f"  + added psp: {name} ({code})")

        await db.commit()
        print(f"\nDone: {added_banks} bank(s) added, {added_psps} psp(s) added.")


if __name__ == "__main__":
    asyncio.run(main())
