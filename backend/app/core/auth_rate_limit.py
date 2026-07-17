from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LoginRateLimiter:
    def __init__(self, *, attempts: int = 5, window_sec: int = 900, lockout_sec: int = 900) -> None:
        self.attempts = attempts
        self.window_sec = window_sec
        self.lockout_sec = lockout_sec
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}
        self._lock = threading.RLock()

    def retry_after(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            until = self._locked_until.get(key, 0.0)
            if until <= now:
                self._locked_until.pop(key, None)
                return 0
            return max(int(until - now), 1)

    def record_failure(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            failures = self._failures[key]
            while failures and now - failures[0] > self.window_sec:
                failures.popleft()
            failures.append(now)
            if len(failures) >= self.attempts:
                self._locked_until[key] = now + self.lockout_sec
                failures.clear()
                return self.lockout_sec
            return 0

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()


login_rate_limiter = LoginRateLimiter()
