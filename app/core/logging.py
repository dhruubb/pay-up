import logging

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure structlog for the whole process (API or a worker).

    structlog.contextvars is what makes this useful across a single request
    or a single Kafka message: bind_contextvars() once (in middleware, or in
    the notification worker before processing a message) and every log call
    downstream — including deep inside a service — automatically includes
    that context, without threading a request_id/logger through every
    function signature.
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.ENV == "development":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    # structlog.stdlib.LoggerFactory() emits through Python's logging module,
    # which defaults the root logger to WARNING with no handler — INFO logs
    # would be silently dropped without this.
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    structlog.configure(
        processors=shared_processors + [renderer],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
