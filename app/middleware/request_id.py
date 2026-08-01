import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Binds a request ID to structlog's contextvars for the lifetime of the
    request, so every log line emitted anywhere during that request — router,
    service, repository — carries it automatically. Also the seam that lets
    a payment's logs be correlated across the API and the two worker
    processes: PaymentService stashes this same ID on the PaymentEvent row it
    writes, the outbox publisher carries it into the Kafka message, and the
    notification worker re-binds it before processing.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        logger.info("request_started", method=request.method, path=request.url.path)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request_finished", status_code=response.status_code)

        return response
