from __future__ import annotations

import argparse
from pathlib import Path

from bootstrap import bootstrap_application, load_config, resolve_config_path
from database.importer import DatabaseImporter


def main() -> None:
    args = _parse_args()
    config = load_config(args.config)
    database = bootstrap_application(args.config)
    importer = DatabaseImporter(database)

    base_config_path = args.config or Path("config/config.json")
    source_path = args.path or resolve_config_path(base_config_path, config["winamax_folder"])

    if source_path.is_file():
        reports = [importer.import_file(source_path)]
    else:
        reports = [
            importer.import_file(path)
            for path in sorted(source_path.glob("*.txt"))
        ]

    for report in reports:
        print(
            report.path.name,
            report.status,
            report.hands_imported,
            report.tournaments_imported,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Winamax hand history and summary files into the local database.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Optional file or directory to import. Defaults to winamax_folder from config/config.json.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to a JSON config file. Defaults to config/config.json.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()