from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAMESPACE = "poker_tracker"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
MAX_LOG_BYTES = 1_048_576
BACKUP_COUNT = 3
COMPONENT_LOG_FILES = {
    "app": "app.log",
    "database": "database.log",
    "parser": "parser.log",
    "watcher": "watcher.log",
    "imports": "imports.log",
}


def configure_logging(log_directory: Path) -> None:
    log_directory.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger(LOGGER_NAMESPACE)
    configured_directory = getattr(root_logger, "_poker_tracker_log_directory", None)
    if getattr(root_logger, "_poker_tracker_configured", False):
        if configured_directory == log_directory:
            return

        _reset_logger(root_logger)
        for component in COMPONENT_LOG_FILES:
            if component == "app":
                continue
            _reset_logger(logging.getLogger(_logger_name(component)))

    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)
    root_logger.addHandler(_build_handler(log_directory / "app.log", formatter))

    for component, filename in COMPONENT_LOG_FILES.items():
        logger = logging.getLogger(_logger_name(component))
        logger.setLevel(logging.INFO)
        logger.propagate = True
        if component != "app":
            logger.addHandler(_build_handler(log_directory / filename, formatter))

    root_logger._poker_tracker_configured = True  # type: ignore[attr-defined]
    root_logger._poker_tracker_log_directory = log_directory  # type: ignore[attr-defined]


def get_logger(component: str) -> logging.Logger:
    if component == "app":
        return logging.getLogger(LOGGER_NAMESPACE)

    return logging.getLogger(_logger_name(component))


def _build_handler(path: Path, formatter: logging.Formatter) -> RotatingFileHandler:
    handler = RotatingFileHandler(path, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT)
    handler.setFormatter(formatter)
    return handler


def _reset_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def _logger_name(component: str) -> str:
    return f"{LOGGER_NAMESPACE}.{component}"