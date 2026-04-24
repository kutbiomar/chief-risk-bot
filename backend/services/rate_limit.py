from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        if limit <= 0:
            return True, 0

        now = time.monotonic()
        cutoff = now - max(window_seconds, 1)
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = int(max(1, events[0] + max(window_seconds, 1) - now))
                return False, retry_after
            events.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_limiter = SlidingWindowRateLimiter()


def allow_request(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    return _limiter.allow(key, limit=limit, window_seconds=window_seconds)


def reset_rate_limiter() -> None:
    _limiter.reset()
