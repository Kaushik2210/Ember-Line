"""Sliding-window rate limiter for the FIRMS transaction budget.

FIRMS allows a fixed number of transactions per 10-minute window per key. The limiter keeps
a safety margin below the published limit. Clock and sleep are injectable for tests.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable


class RateLimiter:
    def __init__(
        self,
        max_calls: int,
        window_s: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be >= 1")
        self.max_calls = max_calls
        self.window_s = window_s
        self._clock = clock
        self._sleep = sleep
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    def _drop_expired(self, now: float) -> None:
        while self._calls and now - self._calls[0] >= self.window_s:
            self._calls.popleft()

    async def acquire(self) -> None:
        """Wait until a call slot is free, then take it."""
        async with self._lock:
            while True:
                now = self._clock()
                self._drop_expired(now)
                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return
                await self._sleep(self.window_s - (now - self._calls[0]))

    def charge(self, units: int) -> None:
        """Record extra budget used by a call already made (e.g. FIRMS bills ~1 per 1000 rows)."""
        now = self._clock()
        self._calls.extend([now] * max(0, units))

    @property
    def in_window(self) -> int:
        self._drop_expired(self._clock())
        return len(self._calls)
