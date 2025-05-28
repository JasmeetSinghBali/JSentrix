"""
utils/lifecycle.py

Lifecycle utility for registering and running shutdown callbacks.
Useful for gracefully stopping background services, closing DB connections, etc.
Supports FIFO (default) and LIFO shutdown order.

Usage:
    from utils.lifecycle import register_shutdown_callback, shutdown_all

    def stop_background_service():
        # shutdown logic
        pass

    register_shutdown_callback(stop_background_service)
    # Later, on shutdown:
    shutdown_all()
"""
from typing import Callable, List, Literal
from .logger import get_logger

logger = get_logger("lifecycle")

_shutdown_callbacks: List[Callable[[],None]] = []

def register_shutdown_callback(callback: Callable[[],None]):
    """
    Register a shutdown callback to be called when app stops.
    """
    logger.debug(f"Registered shutdown callback: {callback.__name__}")
    _shutdown_callbacks.append(callback)

def shutdown_all(order: Literal["fifo", "lifo"] = "fifo"):
    """
    Execute all registered shutdown callbacks in FIFO order.
    """
    logger.info(f"Executing shutdown callbacks in {order.upper()} order...")
    while _shutdown_callbacks:
        if order == "fifo":
            callback = _shutdown_callbacks.pop(0)
        elif order == "lifo":
            callback = _shutdown_callbacks.pop()
        else:
            logger.error(f"Unknown shutdown order: {order}. Defaulting to FIFO.")
            callback = _shutdown_callbacks.pop(0)
        try:
            callback()
            logger.info(f"Executed: {getattr(callback, '__name__', str(callback))}")
        except Exception as e:
            logger.error(f"Error during shutdown of {getattr(callback, '__name__', str(callback))}: {e}")

    
        