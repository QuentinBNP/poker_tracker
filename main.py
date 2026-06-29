from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database.database import Database


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "config.json"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def bootstrap_application(config_path: Path | None = None) -> Database:
    config = load_config(config_path)
    database = Database(Path(config["database_path"]))
    database.initialize()
    return database


def main() -> None:
    database = bootstrap_application()
    print(f"Poker Tracker ready. Database: {database.database_path}")


if __name__ == "__main__":
    main()