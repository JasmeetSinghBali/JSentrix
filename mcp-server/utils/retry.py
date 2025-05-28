"""
utils/retry.py

Generic retry decorator for functions that may fail transiently.
Usage:
    @retry(max_retries=5, delay=2, exceptions=(ValueError,))
    def my_func(...):
        ...
"""

import time
import asyncio
import traceback
from functools import wraps
from typing import Callable, Any, Type, Tuple, Union


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Callable[[str], None] = None,
) -> Callable:  # Outer function (decorator factory)
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

    def decorator(func: Callable) -> Callable:  # Actual decorator
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
                        raise  # Re-raises the same `e`, which is still in scope here
                    time.sleep(delay * attempt)
            return None

        return wrapper  # decorator returns this function

    return decorator  # factory returns the decorator


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Callable[[str], None] = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
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
                        raise  # Re-raises the same `e`, which is still in scope here
                    await asyncio.sleep(delay * attempt)
            raise last_exception

        return wrapper

    return decorator
