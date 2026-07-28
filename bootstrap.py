from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database.database import Database
from logging_system import configure_logging, get_logger


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "config.json"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def bootstrap_application(config_path: Path | None = None) -> Database:
    path = config_path or DEFAULT_CONFIG_PATH
    config = load_config(path)
    log_directory = _resolve_config_path(path, config.get("log_directory", "logs"))
    configure_logging(log_directory)

    database = Database(_resolve_config_path(path, config["database_path"]))
    database.initialize()
    get_logger("app").info("Application bootstrap completed")
    return database


def resolve_config_path(config_path: Path, configured_path: str) -> Path:
    return _resolve_config_path(config_path, configured_path)


def _resolve_config_path(config_path: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute():
        return path

    base_directory = config_path.parent
    if config_path.parent.name == "config":
        base_directory = config_path.parent.parent

    return base_directory / path