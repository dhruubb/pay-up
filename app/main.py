import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.metrics import MetricsMiddleware
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
from app.workers.notification_worker import run_forever as run_notification_worker
from app.workers.outbox_publisher import run_forever as run_outbox_publisher

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Embedding these two background loops in the API process means
    # `uv run uvicorn app.main:app` alone is enough for the whole
    # notification pipeline to work — no separate worker terminals to
    # remember to start. Kafka itself still needs
    # `docker compose up -d zookeeper kafka` (a separate broker process,
    # not something this app can start on its own), but both loops retry
    # quietly and self-heal once it's reachable, so startup order doesn't
    # matter. See the docstrings in app/workers/ for the production tradeoff
    # this makes.
    outbox_task = asyncio.create_task(run_outbox_publisher())
    notification_task = asyncio.create_task(run_notification_worker())
    try:
        yield
    finally:
        outbox_task.cancel()
        notification_task.cancel()
        await asyncio.gather(outbox_task, notification_task, return_exceptions=True)


app = FastAPI(
    title=settings.APP_NAME,
    description="My attempt at making a fully functional UPI System",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

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


@app.get("/metrics")
async def metrics():
    # Unauthenticated by design — this is the Prometheus scrape endpoint. In
    # a real deployment this would sit behind network-level restriction
    # (private network, not exposed to the internet), not app-level auth,
    # since the scraper isn't a logged-in user.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

