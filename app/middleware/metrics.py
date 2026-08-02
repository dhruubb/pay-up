import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import http_request_duration_seconds, http_requests_total


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Labels by the route's path *template* (e.g. "/payments/{payment_id}"),
    never the resolved path — labeling by raw path would mean one label
    value per UUID ever requested, an unbounded-cardinality time bomb for
    Prometheus. Unmatched routes (404s on made-up paths) collapse to a single
    "unmatched" label for the same reason.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        path = route.path if route else "unmatched"

        http_requests_total.labels(
            method=request.method, path=path, status_code=response.status_code
        ).inc()
        http_request_duration_seconds.labels(method=request.method, path=path).observe(duration)

        return response
