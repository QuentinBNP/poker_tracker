from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from database.database import Database
from database.filters import HistoryFilter
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


def test_importer_persists_expresso_summary_mode(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    summary_path = tmp_path / "Expresso(12345)_summary.txt"
    summary_path.write_text(
        """Winamax Poker - Tournament summary : Expresso Flash(12345)
Tournament started 2026/06/28 12:00:00 UTC
Mode : EXPRESSO
Buy-In : 1€
Prizepool : 3€
Registered players : 3
You finished in 1st place
You won 3€
""",
        encoding="utf-8",
    )

    report = DatabaseImporter(database).import_file(summary_path)
    stored_tournament = database.get_tournament("12345")

    assert report.status == "success"
    assert stored_tournament is not None
    assert stored_tournament.game_mode is GameMode.EXPRESSO


def test_importer_detects_reentries_from_repeated_summary_blocks(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    sample_path = (
        SAMPLES_DIR / "20260731_SPACE KO(1140932862)_real_holdem_no-limit_summary.txt"
    )

    report = DatabaseImporter(database).import_file(sample_path)
    entries = database.list_tournament_entries("1140932862")
    tournament = database.list_filtered_tournaments(HistoryFilter())[0]

    assert report.status == "success"
    assert report.tournaments_imported == 1
    assert [entry.entry_number for entry in entries] == [1, 2]
    assert [entry.nominal_buy_in for entry in entries] == [0.50, 0.50]
    assert [entry.cash_cost for entry in entries] == [0.50, 0.50]
    assert tournament["position"] == 701
    assert tournament["entry_count"] == 2
    assert tournament["total_entry_cost"] == 1.0
    assert tournament["profit"] == -0.87


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


def test_importer_persists_observed_cash_rake_without_changing_net_result(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()

    report = DatabaseImporter(database).import_file(
        SAMPLES_DIR / "20260628_Nice 23_real_holdem_no-limit.txt"
    )
    first_hand = database.get_hand("#22603906-296-1782665521")

    assert report.status == "success"
    assert first_hand is not None
    assert first_hand.rake == 0.04
    assert first_hand.result == -0.02


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