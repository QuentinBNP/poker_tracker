from __future__ import annotations

import json
import sqlite3
import tomllib
from pathlib import Path
from typing import Any

import bootstrap
from app_info import APP_ICON_PATH, APP_VERSION
from bootstrap import bootstrap_application, load_config


def test_load_config_reads_json(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "player_name": "MyPseudo",
                "winamax_folder": "C:/Winamax/documents",
                "database_path": str(tmp_path / "data" / "tracker.db"),
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["player_name"] == "MyPseudo"
    assert config["database_path"].endswith("tracker.db")


def test_bootstrap_application_initializes_database(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "tracker.db"
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "player_name": "MyPseudo",
                "winamax_folder": "C:/Winamax/documents",
                "database_path": str(database_path),
            }
        ),
        encoding="utf-8",
    )

    bootstrap_application(config_path)

    assert database_path.exists()

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"tournaments", "hands", "players", "actions", "imports"}.issubset(table_names)


def test_load_config_creates_default_config_in_user_directory(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config-home"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data-home"))

    config = bootstrap.load_config()
    config_path = bootstrap.get_default_config_path()

    assert config_path.exists()
    assert config_path.parent.name == "MyPokerTracker"
    assert config["database_path"].endswith("mypokertracker.db")
    assert "MyPokerTracker" in config["database_path"]
    assert "MyPokerTracker" in config["log_directory"]


def test_app_version_comes_from_project_metadata() -> None:
    project_root = Path(__file__).resolve().parent.parent
    with (project_root / "pyproject.toml").open("rb") as pyproject_file:
        project_version = tomllib.load(pyproject_file)["project"]["version"]

    assert APP_VERSION == project_version
    assert APP_ICON_PATH == project_root / "assets" / "MyPokerTracker.ico"