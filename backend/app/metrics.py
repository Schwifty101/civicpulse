"""Prometheus metrics, exposed as text format on GET /metrics."""

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "civicpulse_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "civicpulse_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)

TRIAGE_LATENCY = Histogram(
    "civicpulse_triage_duration_seconds",
    "Triage provider call latency",
    ["provider"],
)

TRIAGE_FALLBACK_COUNT = Counter(
    "civicpulse_triage_fallback_total",
    "Number of triage calls that fell back to rules",
)
