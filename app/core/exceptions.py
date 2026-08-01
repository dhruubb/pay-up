"""
Domain exception hierarchy for Pay-Up.

Design principles:
- Every exception carries an HTTP status code, machine-readable error code,
  and human-readable message.
- HTTP status code: for the HTTP response.
- Error code: for API consumers to programmatically handle specific errors
  (e.g., mobile app shows different UI for DUPLICATE_EMAIL vs INVALID_PHONE).
- Message: human-readable, safe to return to clients.

All service-layer errors should be a subclass of AppException.
The global exception handler catches AppException and converts it
to a consistent JSON response — no try/except needed in routers.
"""

from fastapi import status


class AppException(Exception):
    """Base exception for all domain/business errors."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


# --- Authentication & Authorization ---


class AuthenticationError(AppException):
    """Raised when credentials are invalid or missing."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(AppException):
    """Raised when an authenticated user cannot access a resource they don't own."""

    def __init__(self, message: str = "You do not have access to this resource"):
        super().__init__(
            message=message,
            error_code="ACCESS_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
        )


# --- Resource Errors ---


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with identifier '{identifier}' not found"
        super().__init__(
            message=message,
            error_code=f"{resource.upper().replace(' ', '_')}_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateError(AppException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource: str = "Resource", field: str = ""):
        message = f"{resource} already exists"
        if field:
            message = f"{resource} with this {field} already exists"
        super().__init__(
            message=message,
            error_code=f"DUPLICATE_{resource.upper().replace(' ', '_')}",
            status_code=status.HTTP_409_CONFLICT,
        )


# --- Money / Ledger Errors ---


class InsufficientFundsError(AppException):
    """Raised when an account's balance can't cover a debit."""

    def __init__(self, message: str = "Insufficient funds"):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_FUNDS",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class AccountNotActiveError(AppException):
    """Raised when an operation targets a frozen or closed account."""

    def __init__(self, message: str = "Account is not active"):
        super().__init__(
            message=message,
            error_code="ACCOUNT_NOT_ACTIVE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class InvalidOperationError(AppException):
    """Raised when a request is well-formed but semantically nonsensical."""

    def __init__(self, message: str = "Invalid operation"):
        super().__init__(
            message=message,
            error_code="INVALID_OPERATION",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class IdempotencyConflictError(AppException):
    """Raised on idempotency key reuse with a different payload, or a
    duplicate request still being processed."""

    def __init__(self, message: str = "Idempotency key conflict"):
        super().__init__(
            message=message,
            error_code="IDEMPOTENCY_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )
