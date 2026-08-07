from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from database.database import Database
from database.importer import DatabaseImporter
from database.models import ImportRecord
from game_modes import GameMode

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def test_importer_persists_tournament_summary_and_import_history(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    importer = DatabaseImporter(database)

    report = importer.import_file(
        SAMPLES_DIR / "20260628_Freeroll(1119027769)_real_holdem_no-limit_summary.txt"
    )

    stored_tournament = database.get_tournament("1119027769")

    assert report.status == "success"
    assert report.tournaments_imported == 1
    assert stored_tournament is not None
    assert stored_tournament.name == "Freeroll"
    assert stored_tournament.position == 3925
    assert database.has_import(
        "20260628_Freeroll(1119027769)_real_holdem_no-limit_summary.txt"
    )


def test_importer_persists_hand_history_without_existing_tournament_summary(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    importer = DatabaseImporter(database)

    report = importer.import_file(
        SAMPLES_DIR / "20260628_Freeroll(1119027769)_real_holdem_no-limit.txt"
    )

    first_hand = database.get_hand("#4806187671170843057-9-1782664923")
    seeded_tournament = database.get_tournament("1119027769")
    actions = database.list_actions_for_hand("#4806187671170843057-9-1782664923")
    players = database.list_players()

    assert report.status == "success"
    assert report.hands_imported >= 4
    assert first_hand is not None
    assert first_hand.hero == "MyPseudo"
    assert first_hand.game_mode is GameMode.TOURNAMENT
    assert first_hand.session_id is not None
    assert seeded_tournament is not None
    assert seeded_tournament.name == "Freeroll"
    assert any(action.action == "FOLD" and action.player == "MyPseudo" for action in actions)
    assert any(player.name == "MyPseudo" for player in players)


def test_importer_reimport_does_not_duplicate_actions(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    importer = DatabaseImporter(database)
    sample_path = SAMPLES_DIR / "20260628_Freeroll(1119027769)_real_holdem_no-limit.txt"

    first_report = importer.import_file(sample_path)
    second_report = importer.import_file(sample_path)

    with sqlite3.connect(database.database_path) as connection:
        action_count = connection.execute(
            "SELECT COUNT(*) FROM actions WHERE hand_id = ?",
            ("#4806187671170843057-9-1782664923",),
        ).fetchone()[0]

    assert first_report.status == "success"
    assert second_report.status == "skipped"
    assert action_count == len(
        database.list_actions_for_hand("#4806187671170843057-9-1782664923")
    )


def test_importer_skips_an_unchanged_previously_imported_file(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    importer = DatabaseImporter(database)
    sample_path = SAMPLES_DIR / "20260628_Freeroll(1119027769)_real_holdem_no-limit.txt"

    first_report = importer.import_file(sample_path)
    second_report = importer.import_file(sample_path)

    assert first_report.status == "success"
    assert second_report.status == "skipped"


def test_importer_reprocesses_file_cached_by_an_older_import_format(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    importer = DatabaseImporter(database)
    sample_path = SAMPLES_DIR / "20260628_Freeroll(1119027769)_real_holdem_no-limit.txt"
    stats = sample_path.stat()
    database.record_import(
        ImportRecord(
            filename=sample_path.name,
            imported_at=datetime.now(timezone.utc),
            status="success",
            modified_at_ns=stats.st_mtime_ns,
            file_size=stats.st_size,
            import_version=DatabaseImporter.IMPORT_FORMAT_VERSION - 1,
        )
    )

    report = importer.import_file(sample_path)

    assert report.status == "success"
    assert report.hands_imported >= 4
    assert database.get_hand("#4806187671170843057-9-1782664923") is not None