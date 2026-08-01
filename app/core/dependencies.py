from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.modules.users.repository import UserRepository

# tokenUrl tells Swagger where the login endpoint is.
# It does NOT affect runtime — it's metadata for the OpenAPI docs
# so the "Authorize" button in Swagger knows where to POST credentials.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    This dependency does three things:
    1. Extracts the Bearer token from the Authorization header
       (handled by oauth2_scheme).
    2. Decodes and validates the JWT (checks signature, expiry).
    3. Looks up the user in the database to confirm they still exist.

    Why step 3? Because JWTs are stateless — if a user gets deleted
    or deactivated after the token was issued, the token is still
    technically valid. In production fintech systems, you ALWAYS
    verify the user still exists and is active on every request.
    This is a deliberate trade-off: one extra DB query per request
    in exchange for the ability to revoke access immediately.

    In high-scale systems, you'd cache the user lookup in Redis
    with a short TTL (30-60s) to avoid hitting the DB on every
    request. We'll add that when we implement Redis caching.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        # WWW-Authenticate header is part of the HTTP spec (RFC 6750).
        # It tells the client "you need a Bearer token to access this."
        # Most clients ignore it, but standards-compliant ones use it,
        # and security scanners check for it.
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")

        if user_id_str is None:
            raise credentials_exception

        user_id = UUID(user_id_str)

    except InvalidTokenError:
        # Covers: expired, bad signature, malformed, wrong algorithm
        raise credentials_exception
    except ValueError:
        # UUID parsing failed — someone tampered with the "sub" claim
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise credentials_exception

    return user
