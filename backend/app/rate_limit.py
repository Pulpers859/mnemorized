from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from threading import Lock


class InMemoryRateLimiter:
    """Small per-client sliding-window limiter for local development."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, client_id: str) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            bucket = self._hits[client_id]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.limit:
                retry_after = max(1, math.ceil(bucket[0] + self.window_seconds - now))
                return False, retry_after

            bucket.append(now)
            return True, 0
