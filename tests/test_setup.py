from __future__ import annotations

import json
import sqlite3
from pathlib import Path

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

    database = bootstrap_application(config_path)

    assert database_path.exists()

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"tournaments", "hands", "players", "actions", "imports"}.issubset(table_names)