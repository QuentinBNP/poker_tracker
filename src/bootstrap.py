from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from app_info import APP_NAME, APP_SLUG
from database.database import Database
from logging_system import configure_logging, get_logger

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "config.json"


def get_default_config_path() -> Path:
    return _get_config_directory() / "config.json"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or get_default_config_path()

    if config_path is None and not path.exists():
        _write_default_config(path)

    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def save_config(config: dict[str, str], config_path: Path | None = None) -> None:
    path = config_path or get_default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def bootstrap_application(config_path: Path | None = None) -> Database:
    path = config_path or get_default_config_path()
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
    if _looks_like_windows_absolute_path(configured_path):
        return Path(configured_path)

    path = Path(configured_path)
    if path.is_absolute():
        return path

    base_directory = config_path.parent
    if config_path.parent.name == "config":
        base_directory = config_path.parent.parent

    return base_directory / path


def _write_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_default_config(), indent=2),
        encoding="utf-8",
    )


def _default_config() -> dict[str, str]:
    player_name, winamax_folder = _default_winamax_settings()
    return {
        "player_name": player_name,
        "winamax_folder": winamax_folder,
        "database_path": str(_get_data_directory() / "data" / f"{APP_SLUG}.db"),
        "log_directory": str(_get_data_directory() / "logs"),
    }


def _default_winamax_settings() -> tuple[str, str]:
    if os.name == "nt":
        appdata_root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        accounts_directory = appdata_root / "winamax" / "documents" / "accounts"
        account_names = _find_winamax_account_names(accounts_directory)
        player_name = account_names[0] if len(account_names) == 1 else _default_player_name()
        return player_name, str(accounts_directory / player_name / "history")

    return _default_player_name(), "C:/Users/YourUser/AppData/Roaming/winamax/documents"


def _find_winamax_account_names(accounts_directory: Path) -> list[str]:
    if not accounts_directory.is_dir():
        return []

    return sorted(
        path.name
        for path in accounts_directory.iterdir()
        if path.is_dir() and (path / "history").is_dir()
    )


def _default_player_name() -> str:
    return os.environ.get("USERNAME") or os.environ.get("USER") or Path.home().name


def _get_config_directory() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return root / APP_NAME

    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / APP_NAME


def _get_data_directory() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / APP_NAME

    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / APP_NAME


def _looks_like_windows_absolute_path(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", path)) or path.startswith("\\\\")