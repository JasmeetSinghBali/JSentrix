import os
import logging
from utils.logger import MaskingFilter

os.makedirs("tests/logs", exist_ok=True)

file_handler = logging.FileHandler("tests/logs/test_run.log", encoding="utf-8")
file_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(funcName)s:%(lineno)d)'
)
file_handler.setFormatter(file_formatter)
file_handler.addFilter(MaskingFilter())

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers
if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
    root_logger.addHandler(file_handler)
