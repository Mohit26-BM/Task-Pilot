"""A small in-memory attempt limiter, enough to stop password guessing.

Counts are kept per process, so with several Gunicorn workers each one counts separately (the real limit is a
multiple of the setting). For a stricter limit across workers, put a shared store (Redis) behind this."""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key, limit, window_seconds):
        """Record an attempt. Returns (allowed, seconds_until_allowed)."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False, max(1, int(window_seconds - (now - hits[0])) + 1)
            hits.append(now)
            return True, 0

    def clear(self, key):
        with self._lock:
            self._hits.pop(key, None)

    def reset_all(self):
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()
