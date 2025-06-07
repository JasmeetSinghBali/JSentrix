"""
gateway/src/application/services/logger
Singleton logger for the gateway, with rotating file and console handlers.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from core.config.settings import settings


class Logger:
    """
    Singleton logger utility for consistent logging across the gateway.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configure()
        return cls._instance

    def _configure(self):
        self.logger = logging.getLogger("gateway")
        self.logger.setLevel(settings.LOG_LEVEL.upper())

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # Rotating file handler
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "gateway.log",
            maxBytes=settings.LOG_FILE_MAX_SIZE_MB * 1024 * 1024,
            backupCount=settings.LOG_BACKUP_COUNT,
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def get_logger(self):
        return self.logger


logger = Logger().get_logger()
