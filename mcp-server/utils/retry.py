import time
from functools import wraps
from typing import Callable, Any

def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple[type[Exception]] = (Exception,)
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        raise
                    time.sleep(delay * retries)
            return None
        return wrapper
    return decorator
