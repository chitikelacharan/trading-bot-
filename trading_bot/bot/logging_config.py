"""
logging_config.py
Configures structured logging for the trading bot.
Logs go to both the console (INFO level) and a rotating file (DEBUG level).
"""

import logging
import os
from logging.handlers import RotatingFileHandler


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
_FILE_FORMAT    = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
_DATE_FMT       = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "DEBUG") -> logging.Logger:
    """
    Initialise and return the root logger for the trading bot.

    Args:
        log_level: Minimum log level to write to the file (default DEBUG).

    Returns:
        Configured root logger instance.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger("trading_bot")
    # Avoid adding duplicate handlers if called more than once
    if root_logger.handlers:
        return root_logger

    root_logger.setLevel(logging.DEBUG)

    # ── Console handler (INFO and above) ──────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(fmt=_CONSOLE_FORMAT, datefmt=_DATE_FMT)
    )

    # ── Rotating file handler (DEBUG and above, max 5 MB × 3 files) ──────
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
    file_handler.setFormatter(
        logging.Formatter(fmt=_FILE_FORMAT, datefmt=_DATE_FMT)
    )

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    root_logger.info("Logging initialised → %s", LOG_FILE)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'trading_bot' namespace."""
    return logging.getLogger(f"trading_bot.{name}")
