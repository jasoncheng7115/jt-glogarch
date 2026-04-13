"""Token bucket rate limiter with adaptive backoff."""

from __future__ import annotations

import asyncio
import time

from glogarch.core.config import RateLimitConfig
from glogarch.utils.logging import get_logger

log = get_logger("ratelimit")


class RateLimiter:
    """Token bucket rate limiter with optional adaptive backoff based on Graylog load."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._tokens: float = config.requests_per_second
        self._max_tokens: float = config.requests_per_second * 2  # allow burst
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()
        self._backed_off = False

    async def acquire(self) -> None:
        """Wait until a token is available."""
        async with self._lock:
            self._refill()
            while self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self.config.requests_per_second
                await asyncio.sleep(wait)
                self._refill()
            self._tokens -= 1.0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._max_tokens,
            self._tokens + elapsed * self.config.requests_per_second,
        )
        self._last_refill = now

    async def adaptive_backoff(self, cpu_percent: float) -> None:
        """Back off if Graylog server CPU is too high."""
        if not self.config.adaptive:
            return
        if cpu_percent > self.config.max_cpu_percent:
            if not self._backed_off:
                log.warning(
                    "Graylog CPU high, backing off",
                    cpu_percent=cpu_percent,
                    backoff_seconds=self.config.backoff_seconds,
                )
                self._backed_off = True
            await asyncio.sleep(self.config.backoff_seconds)
        else:
            if self._backed_off:
                log.info("Graylog CPU normal, resuming", cpu_percent=cpu_percent)
                self._backed_off = False
