import logging
import inspect
import sys

class CustomLogger:
    def __init__(self, name: str = __name__, level: int = logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Prevent adding multiple handlers if already added
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(funcName)s:%(lineno)d)'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level: int, msg: str, *args, **kwargs):
        # Inspect stack to find caller frame (2 steps up from here)
        frame = inspect.currentframe()
        if frame is not None:
            caller_frame = frame.f_back.f_back
            if caller_frame is not None:
                # Extract info from caller frame
                filename = caller_frame.f_code.co_filename
                lineno = caller_frame.f_lineno
                funcname = caller_frame.f_code.co_name
                # Prepend location info to message
                location_info = f"{filename}:{funcname}:{lineno}"
                msg = f"{msg} [{location_info}]"
        self.logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
        
    def warning (self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)


# Singleton logger instance for easy import
default_logger = CustomLogger()

def get_logger(name: str = __name__, level: int = logging.DEBUG) -> CustomLogger:
    """
    Get a new logger instance with the specified name and level.

    Args:
        name (str): Logger name, usually __name__ from caller
        level (int): Logging level

    Returns:
        CustomLogger instance
    """
    return CustomLogger(name, level)
