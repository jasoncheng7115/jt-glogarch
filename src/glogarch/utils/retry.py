"""Retry decorator with exponential backoff."""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, TypeVar

from glogarch.utils.logging import get_logger

log = get_logger("retry")

F = TypeVar("F", bound=Callable[..., Any])


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorator for async functions with exponential backoff retry."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        break
                    delay = min(base_delay * (2**attempt), max_delay)
                    log.warning(
                        "Retrying",
                        func=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
