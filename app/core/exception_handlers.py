"""
Global exception handlers for the FastAPI application.

These are registered once on the app and automatically catch exceptions
that propagate up from any route handler or dependency. This eliminates
the need for try/except blocks in routers entirely.

The response format is consistent across all error types:
{
    "error_code": "MACHINE_READABLE_CODE",
    "message": "Human-readable description",
    "detail": null  // optional, for validation errors or extra context
}

Why this format?
- error_code: lets API consumers (mobile apps, frontend) handle errors
  programmatically without parsing strings.
- message: human-readable, safe to display to end users.
- detail: extra context when needed (e.g., which fields failed validation).
"""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """
        Catches all domain/business exceptions (subclasses of AppException).

        The exception already carries its status code, error code, and message,
        so we just unpack it into a consistent response shape.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Catches Pydantic validation errors (malformed request bodies,
        missing required fields, wrong types, etc.).

        FastAPI's default handler returns 422 with a complex nested structure.
        We normalize it to match our standard error format while preserving
        the field-level details that are useful for debugging.

        exc.errors()'s "ctx" key can hold the raw exception instance that
        triggered a custom validator (e.g. a ValueError from a field_validator),
        which isn't JSON-serializable — drop it before returning.
        """
        errors = [
            {k: v for k, v in error.items() if k != "ctx"} for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for any exception we didn't anticipate.

        CRITICAL for production:
        - Log the full traceback server-side (for debugging).
        - Return a generic message to the client (for security).
        - Never leak stack traces, file paths, or DB structure to clients.
        """
        logger.exception(
            "unhandled_exception",
            method=request.method,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "detail": None,
            },
        )
