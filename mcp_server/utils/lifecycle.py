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
import threading
from typing import Callable, List, Literal, Union, Awaitable
from .logger import get_logger

logger = get_logger("lifecycle")

# Internal list of shutdown callbacks (can be sync or async)
ShutdownCallback = Callable[[], Union[None, Awaitable[None]]]
_shutdown_callbacks: List[ShutdownCallback] = []
_callback_lock = threading.Lock()


def _callback_name(cb):
    return getattr(cb, "__name__", repr(cb))


def register_shutdown_callback(callback: ShutdownCallback):
    """
    Register a shutdown callback (sync or async) to be called when app stops.
    Thread-safe.

    Args:
        callback: A no-argument function or coroutine function to run on shutdown.

    Raises:
        ValueError: If the callback is not callable or expects arguments.

    Notes:
        - Only no-argument functions or coroutines should be registered.
        - If a callback is not valid, it will not be registered and a warning will be logged.
        - Register all important shutdown callbacks early in the application's lifecycle.
    """
    # Validation: must be callable
    if not callable(callback):
        logger.error(f"Failed to register shutdown callback: not callable ({callback})")
        raise ValueError("Shutdown callback must be callable (function or coroutine).")

    # Validation: must accept no required arguments
    import inspect

    sig = inspect.signature(callback)
    for param in sig.parameters.values():
        if (param.default is param.empty) and (
            param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
        ):
            logger.error(
                f"Failed to register shutdown callback: {callback} expects arguments."
            )
            raise ValueError("Shutdown callback must not require arguments.")

    with _callback_lock:
        logger.debug(f"Registered shutdown callback: {_callback_name(callback)}")
        _shutdown_callbacks.append(callback)


def shutdown_all(order: Literal["fifo", "lifo"] = "fifo"):
    """
    Execute all registered shutdown callbacks in FIFO order.
    Sync version: only runs sync callbacks, skips async ones with a warning

    Thread safe

    Use async_shutdown_all() for mixed sync/async environments.
    """
    logger.info(f"Executing shutdown callbacks in {order.upper()} order (sync)...")
    while True:
        with _callback_lock:
            if not _shutdown_callbacks:
                break
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
                    f"Skipping async shutdown callback {_callback_name(callback)} in sync shutdown. Use async_shutdown_all()."
                )
                continue
            callback()
            logger.info(f"Executed: {_callback_name(callback)}")
        except Exception as e:
            logger.error(f"Error during shutdown of {_callback_name(callback)}: {e}")


async def async_shutdown_all(order: Literal["fifo", "lifo"] = "fifo"):
    """
    Execute all registered shutdown callbacks in FIFO or LIFO order.
    Runs both sync and async callbacks. Awaits async ones.
    Thread safe
    Args:
        order: 'fifo' (default) or 'lifo'
    """
    logger.info(f"Executing shutdown callbacks in {order.upper()} order (async)...")
    while True:
        with _callback_lock:
            if not _shutdown_callbacks:
                break
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
            logger.info(f"Executed: {_callback_name(callback)}")
        except Exception as e:
            logger.error(f"Error during shutdown of {_callback_name(callback)}: {e}")


def reset_shutdown_callbacks():
    """
    Clears all registered shutdown callbacks (useful for testing).
    thread safe
    """
    with _callback_lock:
        _shutdown_callbacks.clear()
