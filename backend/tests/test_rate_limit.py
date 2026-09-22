from __future__ import annotations

from app.core.rate_limit import FixedWindowRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_fixed_window_allows_limit_then_rejects_until_reset():
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(clock=clock)

    first = limiter.check("client", limit=2, window_seconds=60)
    second = limiter.check("client", limit=2, window_seconds=60)
    rejected = limiter.check("client", limit=2, window_seconds=60)

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert rejected.allowed is False
    assert rejected.retry_after_seconds == 60

    clock.now += 60
    reset = limiter.check("client", limit=2, window_seconds=60)
    assert reset.allowed is True
    assert reset.remaining == 1


def test_fixed_window_bounds_key_storage_with_lru_eviction():
    limiter = FixedWindowRateLimiter(max_keys=2)

    assert limiter.check("one", limit=1, window_seconds=60).allowed is True
    assert limiter.check("two", limit=1, window_seconds=60).allowed is True
    assert limiter.check("three", limit=1, window_seconds=60).allowed is True

    # "one" was the least-recently-used bucket and can start a new window.
    assert limiter.check("one", limit=1, window_seconds=60).allowed is True
