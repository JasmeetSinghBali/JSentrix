"""
utils/retry.py

Generic retry decorator for functions that may fail transiently.
Usage:
    # Sync
    @retry(max_retries=5, delay=2, exceptions=(ValueError,))
    def my_func(...):
        ...

    # Async
    @async_retry(max_retries=5, delay=2, exceptions=(ValueError,))
    async def my_async_func(...):
        ...
"""

import time
import asyncio
import traceback
from functools import wraps
from typing import Callable, Any, Type, Tuple, Union, Awaitable


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Callable[[str], None] = None,
) -> Callable:
    """
    Decorator to retry a function if specified exceptions occur.

    Args:
        max_retries (int): Number of attempts before giving up.
        delay (float): Initial delay (in seconds) between retries (increases linearly).
        exceptions (tuple): Exceptions to catch and retry on.
        logger (callable): Optional logger function to log retry attempts.

    Returns:
        Callable: Decorated function with retry logic.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if logger:
                        logger(
                            f"[retry] Attempt {attempt} failed with {e.__class__.__name__}: {e}"
                        )
                    if attempt == max_retries:
                        if logger:
                            logger(
                                f"[retry] All {max_retries} attempts failed. Last exception caught: {last_exception}"
                            )
                            logger("[retry] All attempts failed. Traceback:")
                            logger(traceback.format_exc())
                        raise
                    time.sleep(delay * attempt)
            return None

        return wrapper

    return decorator


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Callable[[str], None] = None,
) -> Callable:
    """
    Async decorator to retry a coroutine if specified exceptions occur.

    Args:
        max_retries (int): Number of attempts before giving up.
        delay (float): Initial delay (in seconds) between retries (increases linearly).
        exceptions (tuple): Exceptions to catch and retry on.
        logger (callable): Optional logger function to log retry attempts.

    Returns:
        Callable: Decorated async function with retry logic.
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if logger:
                        logger(
                            f"[retry] Attempt {attempt} failed with {e.__class__.__name__}: {e}"
                        )
                    if attempt == max_retries:
                        if logger:
                            logger(
                                f"[retry] All {max_retries} attempts failed. Last exception caught: {last_exception}"
                            )
                            logger("[retry] All attempts failed. Traceback:")
                            logger(traceback.format_exc())
                        raise
                    await asyncio.sleep(delay * attempt)
            raise last_exception

        return wrapper

    return decorator
