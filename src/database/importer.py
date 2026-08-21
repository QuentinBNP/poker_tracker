from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any

from database.database import Database
from database.models import ImportRecord, Tournament
from game_modes import GameMode
from logging_system import get_logger
from parser.hand_parser import parse_hand_history
from parser.tournament_parser import parse_tournament_summary


@dataclass(slots=True)
class ImportReport:
    path: Path
    file_type: str
    status: str
    tournaments_imported: int = 0
    hands_imported: int = 0
    players_imported: int = 0
    actions_imported: int = 0


class DatabaseImporter:
    IMPORT_FORMAT_VERSION = 3

    def __init__(self, database: Database) -> None:
        self.database = database
        self.logger = get_logger("imports")

    def import_file(self, path: Path, file_type: str | None = None) -> ImportReport:
        resolved_type = file_type or self._classify_file(path)
        if self.database.has_current_import(path, self.IMPORT_FORMAT_VERSION):
            return ImportReport(path=path, file_type=resolved_type, status="skipped")

        try:
            text = path.read_text(encoding="utf-8")
            if resolved_type == "tournament_summary":
                report = self._import_tournament_summary(path, text)
            else:
                report = self._import_hand_history(path, text)
        except Exception:
            self.logger.exception("Failed to import %s", path.name)
            self.database.record_import(
                ImportRecord(
                    filename=path.name,
                    imported_at=self._imported_at(),
                    status="failed",
                    import_version=self.IMPORT_FORMAT_VERSION,
                )
            )
            return ImportReport(path=path, file_type=resolved_type, status="failed")

        self.database.record_import(
            self._import_record(path, report.status)
        )
        return report

    def _import_tournament_summary(self, path: Path, text: str) -> ImportReport:
        parsed = parse_tournament_summary(text)
        if not parsed:
            self.logger.warning("Tournament summary parsing returned no data for %s", path.name)
            return ImportReport(path=path, file_type="tournament_summary", status="failed")

        tournament = Tournament(
            tournament_id=parsed["tournament_id"],
            name=parsed["name"],
            buy_in=parsed["buy_in"] or 0.0,
            prize_pool=parsed["prize_pool"] or 0.0,
            players_count=parsed["players_count"] or 0,
            started_at=parsed["started_at"],
            finished_at=self._calculate_finished_at(parsed),
            position=parsed["position"],
            winnings=parsed["winnings"] or 0.0,
            bounty_winnings=parsed["bounty_winnings"],
            game_mode=GameMode(parsed["game_mode"]),
        )
        self.database.insert_tournament(tournament)
        self.logger.info("Imported tournament summary %s", path.name)
        return ImportReport(
            path=path,
            file_type="tournament_summary",
            status="success",
            tournaments_imported=1,
        )

    def _import_hand_history(self, path: Path, text: str) -> ImportReport:
        parsed_hands = parse_hand_history(text)
        if not parsed_hands:
            self.logger.warning("Hand history parsing returned no hands for %s", path.name)
            return ImportReport(path=path, file_type="hand_history", status="failed")

        tournaments_imported, players_imported, actions_imported = (
            self.database.import_hand_history(parsed_hands)
        )

        self.logger.info("Imported hand history %s", path.name)
        return ImportReport(
            path=path,
            file_type="hand_history",
            status="success",
            tournaments_imported=tournaments_imported,
            hands_imported=len(parsed_hands),
            players_imported=players_imported,
            actions_imported=actions_imported,
        )

    @staticmethod
    def _calculate_finished_at(parsed: dict[str, Any]) -> Any:
        started_at = parsed.get("started_at")
        duration_seconds = parsed.get("duration_seconds")
        if started_at is None or duration_seconds is None:
            return None

        return started_at + timedelta(seconds=duration_seconds)

    @staticmethod
    def _classify_file(path: Path) -> str:
        if path.name.endswith("_summary.txt"):
            return "tournament_summary"

        return "hand_history"

    @staticmethod
    def _imported_at():
        from datetime import datetime

        return datetime.now(timezone.utc)

    @classmethod
    def _import_record(cls, path: Path, status: str) -> ImportRecord:
        stats = path.stat()
        return ImportRecord(
            filename=path.name,
            imported_at=cls._imported_at(),
            status=status,
            modified_at_ns=stats.st_mtime_ns,
            file_size=stats.st_size,
            import_version=cls.IMPORT_FORMAT_VERSION,
        )