"""Bounded, process-local fixed-window rate limiting primitives."""
from __future__ import annotations

import hashlib
import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request, Response, status


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class FixedWindowRateLimiter:
    """Thread-safe fixed-window limiter with bounded in-process storage.

    The limiter is intentionally local to one API process. Deployments with
    multiple replicas must replace it with a shared store before claiming a
    fleet-wide rate-limit guarantee.
    """

    def __init__(
        self,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_keys < 1:
            raise ValueError("max_keys must be at least 1")
        self._max_keys = max_keys
        self._clock = clock
        self._buckets: OrderedDict[str, tuple[int, float]] = OrderedDict()
        self._lock = threading.Lock()

    def clear(self) -> None:
        """Clear all counters; primarily useful for isolated tests."""
        with self._lock:
            self._buckets.clear()

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")

        now = self._clock()
        with self._lock:
            count, reset_at = self._buckets.get(key, (0, now + window_seconds))
            if now >= reset_at:
                count = 0
                reset_at = now + window_seconds

            if key not in self._buckets and len(self._buckets) >= self._max_keys:
                self._evict(now)

            retry_after = max(1, math.ceil(reset_at - now))
            if count >= limit:
                self._buckets[key] = (count, reset_at)
                self._buckets.move_to_end(key)
                return RateLimitDecision(False, 0, retry_after)

            count += 1
            self._buckets[key] = (count, reset_at)
            self._buckets.move_to_end(key)
            return RateLimitDecision(True, max(0, limit - count), retry_after)

    def _evict(self, now: float) -> None:
        expired = [key for key, (_, reset_at) in self._buckets.items() if now >= reset_at]
        for key in expired:
            self._buckets.pop(key, None)
        while len(self._buckets) >= self._max_keys:
            self._buckets.popitem(last=False)


def _opaque_key(scope: str, subject: str) -> str:
    return hashlib.sha256(f"{scope}:{subject}".encode("utf-8")).hexdigest()


def enforce_rate_limit(
    request: Request,
    response: Response,
    *,
    scope: str,
    subject: str,
    limit: int,
    window_seconds: int,
) -> None:
    limiter: FixedWindowRateLimiter = request.app.state.rate_limiter
    decision = limiter.check(
        _opaque_key(scope, subject),
        limit=limit,
        window_seconds=window_seconds,
    )
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(decision.remaining),
        "X-RateLimit-Reset": str(decision.retry_after_seconds),
    }
    if not decision.allowed:
        headers["Retry-After"] = str(decision.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Retry later.",
            headers=headers,
        )
    response.headers.update(headers)
