"""
Central registry for all Prometheus metrics. Defining them here (rather than
inline at each call site) keeps names/labels consistent and makes it obvious
at a glance what this app actually measures.
"""

from prometheus_client import Counter, Histogram

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

payments_total = Counter(
    "payments_total",
    "Total payments processed, by terminal status",
    ["status"],
)

payment_amount_paise = Histogram(
    "payment_amount_paise",
    "Distribution of successful payment amounts, in paise",
    buckets=(100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000, 100_000_000),
)

idempotency_replays_total = Counter(
    "idempotency_replays_total",
    "Payment initiations served from an idempotency-key cache hit instead of reprocessing",
)

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Requests rejected by the rate limiter",
    ["scope"],
)
