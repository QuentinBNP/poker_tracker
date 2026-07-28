from __future__ import annotations

import json
from pathlib import Path

from logging_system import get_logger
from main import bootstrap_application


def test_bootstrap_application_configures_log_files(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "player_name": "MyPseudo",
                "winamax_folder": "C:/Winamax/documents",
                "database_path": "data/tracker.db",
                "log_directory": "logs",
            }
        ),
        encoding="utf-8",
    )

    bootstrap_application(config_path)
    get_logger("database").info("database log message")
    get_logger("parser").warning("parser log message")

    app_log = tmp_path / "logs" / "app.log"
    database_log = tmp_path / "logs" / "database.log"
    parser_log = tmp_path / "logs" / "parser.log"

    assert app_log.exists()
    assert database_log.exists()
    assert parser_log.exists()
    assert "Application bootstrap completed" in app_log.read_text(encoding="utf-8")
    assert "database log message" in database_log.read_text(encoding="utf-8")
    assert "parser log message" in parser_log.read_text(encoding="utf-8")