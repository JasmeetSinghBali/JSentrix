"""
mcp_server/utils/background_worker.py

Decorator to register coroutine as a background worker with:
- Auto-retry with exponential backoff
- Graceful shutdown
- Automatic task registry integration
- Coroutine validation
"""

import asyncio
import traceback
import inspect
from functools import wraps
from workers.task_registry import task_registry
from utils.logger import get_logger

logger = get_logger("background.worker")


def background_worker(
    name: str = "UnnamedWorker",
    retry: bool = True,
    max_retries: int = -1,
    backoff_base: float = 2.0,
    max_backoff: float = 60.0,  # ⏳ Optional cap to prevent infinite wait
):
    """
    Decorator for registering a background coroutine with optional auto-retry & exponential backoff.

    Args:
        name (str): Worker name for logging.
        retry (bool): Whether to retry the worker on failure.
        max_retries (int): Number of retries (-1 = infinite).
        backoff_base (float): Base for exponential backoff (e.g. 2.0 = 1s, 2s, 4s, 8s...).
        max_backoff (float): Maximum delay between retries (in seconds).
    """

    def decorator(coro_fn):
        if not inspect.iscoroutinefunction(coro_fn):
            raise TypeError(
                f"@background_worker can only decorate 'async def' functions, not '{coro_fn.__name__}'"
            )

        @wraps(coro_fn)
        async def runner(*args, **kwargs):
            retry_count = 0
            while True:
                try:
                    logger.info(f"🚀 Starting background worker: {name}")
                    await coro_fn(*args, **kwargs)
                    logger.warning(
                        f"⚠️ Background worker '{name}' exited normally (loop ended or return)"
                    )
                    break
                except asyncio.CancelledError:
                    logger.info(f"🛑 Background worker '{name}' cancelled gracefully")
                    break
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"💥 Error in background worker '{name}': {e}\n{tb}")

                    if not retry:
                        break

                    retry_count += 1
                    if 0 <= max_retries < retry_count:
                        logger.error(
                            f"🚫 Max retries reached for worker '{name}' — not retrying"
                        )
                        break

                    delay = min(backoff_base**retry_count, max_backoff)
                    logger.info(
                        f"⏳ Retrying '{name}' in {delay:.2f}s (retry #{retry_count} 🔁)..."
                    )
                    await asyncio.sleep(delay)

        @wraps(coro_fn)
        async def start_worker(*args, **kwargs):
            task = asyncio.create_task(runner(*args, **kwargs))
            task_registry.add(task)  # ✅ Register with global task manager

            async def shutdown():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"🛑 {name} shutdown cleanly")

            return shutdown

        return start_worker

    return decorator
