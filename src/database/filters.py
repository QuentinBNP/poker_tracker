from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from game_modes import GameMode


@dataclass(frozen=True, slots=True)
class HistoryFilter:
    start_at: datetime | None = None
    end_at: datetime | None = None
    game_mode: GameMode | None = None
    table_name: str | None = None
    tournament_id: str | None = None

    def hand_conditions(self, table_alias: str = "h") -> tuple[list[str], list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        if self.start_at is not None:
            conditions.append(f"{table_alias}.played_at >= ?")
            parameters.append(self.start_at.isoformat())
        if self.end_at is not None:
            conditions.append(f"{table_alias}.played_at <= ?")
            parameters.append(self.end_at.isoformat())
        if self.game_mode is not None:
            conditions.append(f"{table_alias}.game_mode = ?")
            parameters.append(self.game_mode.value)
        if self.table_name is not None:
            conditions.append(f"{table_alias}.table_name = ?")
            parameters.append(self.table_name)
        if self.tournament_id is not None:
            conditions.append(f"{table_alias}.tournament_id = ?")
            parameters.append(self.tournament_id)
        return conditions, parameters

    def tournament_conditions(self, table_alias: str = "t") -> tuple[list[str], list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        if self.start_at is not None:
            conditions.append(f"{table_alias}.started_at >= ?")
            parameters.append(self.start_at.isoformat())
        if self.end_at is not None:
            conditions.append(f"{table_alias}.started_at <= ?")
            parameters.append(self.end_at.isoformat())
        if self.game_mode is not None:
            conditions.append(f"{table_alias}.game_mode = ?")
            parameters.append(self.game_mode.value)
        if self.tournament_id is not None:
            conditions.append(f"{table_alias}.tournament_id = ?")
            parameters.append(self.tournament_id)
        return conditions, parameters