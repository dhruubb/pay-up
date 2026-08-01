from fastapi import FastAPI

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware
from app.modules.accounts.router import router as accounts_router
from app.modules.audit.router import router as audit_router
from app.modules.banks.router import router as banks_router
from app.modules.ledger.router import router as ledger_router
from app.modules.notifications.router import router as notifications_router
from app.modules.payments.router import router as payments_router
from app.modules.psps.router import router as psps_router
from app.modules.users.router import router as users_router
from app.modules.vpas.router import router as vpas_router

configure_logging()

app = FastAPI(title=settings.APP_NAME, description="My attempt at making a fully functional UPI System")

app.add_middleware(RequestIDMiddleware)

register_exception_handlers(app)
app.include_router(users_router)
app.include_router(banks_router)
app.include_router(accounts_router)
app.include_router(psps_router)
app.include_router(vpas_router)
app.include_router(ledger_router)
app.include_router(payments_router)
app.include_router(notifications_router)
app.include_router(audit_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Pay-Up",
    }

