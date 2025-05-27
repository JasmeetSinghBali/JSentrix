"""
Usage
    from utils.lifecycle import register_shutdown_callback
    def stop_background_service():
        # shutdown logic 
        pass
    register_shutdown_callback(stop_background_service)
"""
from typing import Callable, List
from .logger import get_logger

logger = get_logger("lifecycle")

_shutdown_callbacks: List[Callable[[],None]] = []

def register_shutdown_callback(callback: Callable[[],None]):
    """
    Register a shutdown callback to be called when app stops.
    """
    logger.debug(f"Registered shutdown callback: {callback.__name__}")
    _shutdown_callbacks.append(callback)

def shutdown_all():
    """
    Execute all registered shutdown callbacks.
    """
    logger.info("Executing shutdown callbacks...")
    while _shutdown_callbacks:
        callback = _shutdown_callbacks.pop(0) # FIFO order in which the callback got registered first registerd first call
        try:
            callback()
            logger.info(f"Executed: {callback.__name__}")
        except Exception as e:
            logger.error(f"Error during shutdown of {callback.__name__}: {e}")

    
        