"""
utils/lifecycle.py

Lifecycle utility for registering and running shutdown callbacks.
Useful for gracefully stopping background services, closing DB connections, etc.
Supports FIFO (default) and LIFO shutdown order.
Supports both sync and asyn callbacks.

Usage:
    from utils.lifecycle import register_shutdown_callback, shutdown_all, async_shutdown_all

    def stop_background_service():
        # shutdown logic
        pass
    async def close_async_db():
        # async shutdown logic
        await ...

    register_shutdown_callback(stop_background_service)
    register_shutdown_callback(close_async_db)
    # Later, on shutdown:
    shutdown_all()
    or
    await async_shutdown_all()
"""

import asyncio
from typing import Callable, List, Literal, Union, Awaitable
from .logger import get_logger

logger = get_logger("lifecycle")

# Internal list of shutdown callbacks (can be sync or async)
_shutdown_callbacks: List[Callable[[], Union[None, Awaitable[None]]]] = []


def register_shutdown_callback(callback: Callable[[], Union[None, Awaitable[None]]]):
    """
    Register a shutdown callback(sync or async) to be called when app stops.

    Args:
        callback: A no-argument function or coroutine function to run on shutdown.
    """
    logger.debug(
        f"Registered shutdown callback: {getattr(callback, '__name__', str(callback))}"
    )
    _shutdown_callbacks.append(callback)


def shutdown_all(order: Literal["fifo", "lifo"] = "fifo"):
    """
    Execute all registered shutdown callbacks in FIFO order.
    Sync version: only runs sync callbacks, skips async ones with a warning
    """
    logger.info(f"Executing shutdown callbacks in {order.upper()} order (sync)...")
    while _shutdown_callbacks:
        if order == "fifo":
            callback = _shutdown_callbacks.pop(0)
        elif order == "lifo":
            callback = _shutdown_callbacks.pop()
        else:
            logger.error(f"Unknown shutdown order: {order}. Defaulting to FIFO.")
            callback = _shutdown_callbacks.pop(0)
        try:
            if asyncio.iscoroutinefunction(callback):
                logger.warning(
                    f"Skipping async shutdown callback {getattr(callback, '__name__', str(callback))} in sync shutdown. Use async_shutdown_all()."
                )
                continue
            callback()
            logger.info(f"Executed: {getattr(callback, '__name__', str(callback))}")
        except Exception as e:
            logger.error(
                f"Error during shutdown of {getattr(callback, '__name__', str(callback))}: {e}"
            )


async def async_shutdown_all(order: Literal["fifo", "lifo"] = "fifo"):
    """
    Execute all registered shutdown callbacks in FIFO or LIFO order.
    Runs both sync and async callbacks. Awaits async ones.

    Args:
        order: 'fifo' (default) or 'lifo'
    """
    logger.info(f"Executing shutdown callbacks in {order.upper()} order (async)...")
    while _shutdown_callbacks:
        if order == "fifo":
            callback = _shutdown_callbacks.pop(0)
        elif order == "lifo":
            callback = _shutdown_callbacks.pop()
        else:
            logger.error(f"Unknown shutdown order: {order}. Defaulting to FIFO.")
            callback = _shutdown_callbacks.pop(0)
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()
            logger.info(f"Executed: {getattr(callback, '__name__', str(callback))}")
        except Exception as e:
            logger.error(
                f"Error during shutdown of {getattr(callback, '__name__', str(callback))}: {e}"
            )
