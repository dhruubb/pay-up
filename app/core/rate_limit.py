"""
Fixed-window rate limiting backed by Redis.

Fixed window (not sliding window/log) is a deliberate simplicity tradeoff: a
client can burst up to ~2x the limit right at a window boundary (e.g. maxing
out the last second of one window and the first second of the next). That's
an acceptable inaccuracy for brute-force/abuse protection in a learning
project — a sliding window counter or log would be more precise but adds
real complexity for a marginal gain here.
"""

import time

import structlog
from fastapi import Depends, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.dependencies import get_current_user
from app.core.exceptions import RateLimitExceededError
from app.core.metrics import rate_limit_exceeded_total
from app.core.redis import get_redis
from app.models.user import User

logger = structlog.get_logger(__name__)


async def _check_and_increment(
    redis: Redis, key: str, limit: int, window_seconds: int, scope: str
) -> None:
    # Fail OPEN, not closed: if Redis is unreachable, let the request through
    # rather than 500ing every login/payment. Rate limiting is abuse
    # protection, not a correctness guarantee — losing it temporarily during
    # a Redis outage is far better than losing auth/payments entirely.
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except RedisError:
        logger.warning("rate_limit_backend_unavailable", key=key)
        return

    if count > limit:
        rate_limit_exceeded_total.labels(scope=scope).inc()
        ttl = await redis.ttl(key)
        raise RateLimitExceededError(retry_after=max(ttl, 1))


def rate_limit_by_ip(scope: str, limit: int, window_seconds: int):
    """For unauthenticated endpoints (e.g. login) where there's no user yet."""

    async def _dependency(request: Request, redis: Redis = Depends(get_redis)) -> None:
        identifier = request.client.host if request.client else "unknown"
        window = int(time.time() // window_seconds)
        key = f"ratelimit:{scope}:{identifier}:{window}"
        await _check_and_increment(redis, key, limit, window_seconds, scope)

    return _dependency


def rate_limit_by_user(scope: str, limit: int, window_seconds: int):
    """For authenticated endpoints — keyed by user, not IP, since a shared
    office/NAT IP shouldn't rate-limit unrelated users off of each other."""

    async def _dependency(
        current_user: User = Depends(get_current_user),
        redis: Redis = Depends(get_redis),
    ) -> None:
        window = int(time.time() // window_seconds)
        key = f"ratelimit:{scope}:{current_user.id}:{window}"
        await _check_and_increment(redis, key, limit, window_seconds, scope)

    return _dependency
