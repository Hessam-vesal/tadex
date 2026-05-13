"""
Structured logging module for Nobitex Quant Trader.

Provides consistent, structured logging across the application
with both console and file output.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, Optional

from app.config import LoggingConfig, get_settings


class StructuredFormatter(logging.Formatter):
    """Structured JSON-compatible log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Add trade-specific fields
        for key in ["symbol", "side", "order_id", "strategy", "signal"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return super().format(record)


class ColorFormatter(logging.Formatter):
    """Colored formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        level_color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{level_color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


class LoggerManager:
    """Manages logger instances for the application."""

    _loggers: Dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(
        cls,
        name: str,
        config: Optional[LoggingConfig] = None,
        extra_handlers: Optional[list] = None,
    ) -> logging.Logger:
        """Get or create a logger with the specified name."""
        if name in cls._loggers:
            return cls._loggers[name]

        if config is None:
            config = get_settings().logging

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))
        logger.propagate = False

        # Clear existing handlers
        logger.handlers.clear()

        # Create console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColorFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Create file handler
        os.makedirs(os.path.dirname(config.log_file) or "logs", exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            filename=config.log_file,
            when="midnight",
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = StructuredFormatter(
            fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s", '
                '"module": "%(module)s", "function": "%(funcName)s", '
                '"line": %(lineno)s}',
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Add extra handlers if provided
        if extra_handlers:
            for handler in extra_handlers:
                logger.addHandler(handler)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def get_trade_logger(cls) -> logging.Logger:
        """Get the dedicated trade logger."""
        return cls.get_logger("nobitex_trader.trade")

    @classmethod
    def get_data_logger(cls) -> logging.Logger:
        """Get the dedicated data logger."""
        return cls.get_logger("nobitex_trader.data")

    @classmethod
    def get_strategy_logger(cls) -> logging.Logger:
        """Get the dedicated strategy logger."""
        return cls.get_logger("nobitex_trader.strategy")

    @classmethod
    def get_risk_logger(cls) -> logging.Logger:
        """Get the dedicated risk logger."""
        return cls.get_logger("nobitex_trader.risk")

    @classmethod
    def get_execution_logger(cls) -> logging.Logger:
        """Get the dedicated execution logger."""
        return cls.get_logger("nobitex_trader.execution")

    @classmethod
    def get_error_logger(cls) -> logging.Logger:
        """Get the dedicated error logger."""
        error_logger = cls.get_logger("nobitex_trader.error")
        error_logger.setLevel(logging.ERROR)
        return error_logger

    @classmethod
    def reset(cls):
        """Reset all loggers (useful for testing)."""
        for logger in cls._loggers.values():
            logger.handlers.clear()
        cls._loggers.clear()


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger."""
    return LoggerManager.get_logger(name)


# Module-level loggers
trade_logger = LoggerManager.get_trade_logger()
data_logger = LoggerManager.get_data_logger()
strategy_logger = LoggerManager.get_strategy_logger()
risk_logger = LoggerManager.get_risk_logger()
execution_logger = LoggerManager.get_execution_logger()
error_logger = LoggerManager.get_error_logger()
