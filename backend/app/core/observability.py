"""Low-cardinality HTTP metrics and request correlation middleware."""
from __future__ import annotations

import json
import logging
import re
import time
import uuid

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

LOGGER = logging.getLogger("roboops.http")
REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

HTTP_REQUESTS = Counter(
    "roboops_http_requests_total",
    "Total HTTP requests handled by the API.",
    ("method", "route", "status"),
)
HTTP_REQUEST_DURATION = Histogram(
    "roboops_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "roboops_http_requests_in_progress",
    "HTTP requests currently being processed.",
    ("method",),
)


def _request_id(request: Request) -> str:
    supplied = request.headers.get(REQUEST_ID_HEADER)
    if supplied and _REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return str(uuid.uuid4())


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Record bounded-label metrics and emit one JSON access log per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _request_id(request)
        request.state.request_id = request_id
        method = request.method
        started = time.perf_counter()
        status_code = 500
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration = time.perf_counter() - started
            route = request.scope.get("route")
            route_template = getattr(route, "path", "__unmatched__")
            HTTP_REQUESTS.labels(
                method=method,
                route=route_template,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION.labels(method=method, route=route_template).observe(duration)
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()
            LOGGER.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": method,
                        "route": route_template,
                        "status": status_code,
                        "duration_ms": round(duration * 1000, 3),
                    },
                    separators=(",", ":"),
                )
            )


router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose Prometheus text-format process and RoboOps HTTP metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
