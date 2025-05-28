"""
utils/logger.py

Custom logger with sensitive info masking and caller location.
"""

import logging
import inspect
import sys
import re

SENSITIVE_PATTERNS = [
    r'[A-Z]:\\\\[^\s]+',           # Windows absolute paths
    r'[A-Z]:/[^\s]+',              # Windows absolute paths (forward slash)
    r'/Users/[^\s]+',              # macOS user paths
    r'/home/[^\s]+',               # Linux user paths
    r'localhost',                  # Hostname
    r'127\.0\.0\.1',               # Localhost IP
    r'\b\d{1,3}(?:\.\d{1,3}){3}\b',# Any IP address
    r'GB\d{2}[A-Z]{4}\d{14}',      # Example IBAN (tweak as needed)
    r'password\s*=\s*[^,\s]+',     # password=xxxx
    r'Authorization:\s*[^\s,]+',   # Authorization: xxxx
    r'(?i)C:\\Users\\[^\s\\]+'     # Windows user directory
    # Add more patterns as needed
]

def mask_sensitive_info(msg):
    for pattern in SENSITIVE_PATTERNS:
        msg = re.sub(pattern, '[MASKED]', msg)
    return msg

class MaskingFilter(logging.Filter):
    def filter(self, record):
        record.msg = mask_sensitive_info(str(record.msg))
        return True


class CustomLogger:
    """
    Custom logger that masks sensitive info and adds caller location.
    """
    def __init__(self, name: str = __name__, level: int = logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Prevent adding multiple handlers if already added
        if not self.logger.hasHandlers():
            stream_handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(funcName)s:%(lineno)d)'
            )
            stream_handler.setFormatter(formatter)
            stream_handler.addFilter(MaskingFilter())
            self.logger.addHandler(stream_handler)
        else:
            # Ensure all handlers have the masking filter
            for handler in self.logger.handlers:
                if not any(isinstance(f, MaskingFilter) for f in handler.filters):
                    handler.addFilter(MaskingFilter())

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
    
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)


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
