import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class CustomLogger:
    _instance = None
    _initialized = False

    @classmethod
    def get_logger(
        cls, name: str = "app", level: str = "INFO", log_file: Optional[str] = None
    ) -> logging.Logger:
        """
        Singleton logger instance that can be called anywhere in the application
        """
        if not cls._instance:
            cls._instance = cls._setup_logger(name, level, log_file)
        return cls._instance

    @staticmethod
    def _setup_logger(name: str, level: str, log_file: Optional[str]) -> logging.Logger:
        """Set up the logger with color formatting"""
        logger = logging.getLogger(name)
        logger.setLevel(level.upper())

        if logger.hasHandlers():
            logger.handlers.clear()

        # Color codes for console output
        colors = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[41m",  # Red background
        }
        reset_color = "\033[0m"

        class ColorFormatter(logging.Formatter):
            def format(self, record):
                color = colors.get(record.levelname, reset_color)
                record.levelname_colored = f"{color}{record.levelname:<8}{reset_color}"
                record.msg_colored = f"{color}{record.getMessage()}{reset_color}"
                return super().format(record)

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColorFormatter(
            "%(asctime)s | %(levelname_colored)s | %(msg_colored)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler if log_file is specified
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger


# Create a convenience function
def get_logger(
    name: str = "app", level: str = "INFO", log_file: Optional[str] = None
) -> logging.Logger:
    return CustomLogger.get_logger(name, level, log_file)


# Optional: Create default logger instance
logger = get_logger()
