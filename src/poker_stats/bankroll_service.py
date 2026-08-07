from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from database.database import Database
from database.filters import HistoryFilter
from game_modes import GameMode


class BankrollSourceType(StrEnum):
    HAND = "HAND"
    TOURNAMENT = "TOURNAMENT"


@dataclass(frozen=True, slots=True)
class BankrollPoint:
    occurred_at: datetime
    balance: float
    result: float
    game_mode: GameMode
    source_type: BankrollSourceType
    source_id: str
    session_id: int | None = None
    tournament_id: str | None = None


class BankrollService:
    def __init__(self, database: Database, hero_name: str) -> None:
        self.database = database
        self.hero_name = hero_name

    def calculate(self, filters: HistoryFilter | None = None) -> list[BankrollPoint]:
        active_filter = filters or HistoryFilter()
        events = [
            *self._cash_hand_events(active_filter),
            *self._tournament_events(active_filter),
        ]
        events.sort(key=lambda event: (event.occurred_at, event.source_type, event.source_id))

        balance = 0.0
        points: list[BankrollPoint] = []
        for event in events:
            balance += event.result
            points.append(
                BankrollPoint(
                    occurred_at=event.occurred_at,
                    balance=balance,
                    result=event.result,
                    game_mode=event.game_mode,
                    source_type=event.source_type,
                    source_id=event.source_id,
                    session_id=event.session_id,
                    tournament_id=event.tournament_id,
                )
            )
        return points

    def _cash_hand_events(self, filters: HistoryFilter) -> list[BankrollPoint]:
        hands = self.database.list_filtered_hands(self.hero_name, filters, limit=1_000_000)
        events: list[BankrollPoint] = []
        for hand in hands:
            if hand["game_mode"] is not GameMode.CASH_GAME:
                continue
            occurred_at = hand["played_at"]
            if not isinstance(occurred_at, datetime):
                continue
            events.append(
                BankrollPoint(
                    occurred_at=occurred_at,
                    balance=0.0,
                    result=_as_float(hand["result"]),
                    game_mode=GameMode.CASH_GAME,
                    source_type=BankrollSourceType.HAND,
                    source_id=str(hand["hand_id"]),
                    session_id=_as_int_or_none(hand["session_id"]),
                )
            )
        return events

    def _tournament_events(self, filters: HistoryFilter) -> list[BankrollPoint]:
        tournaments = self.database.list_filtered_tournaments(filters, limit=1_000_000)
        events: list[BankrollPoint] = []
        for tournament in tournaments:
            game_mode = tournament["game_mode"]
            if not isinstance(game_mode, GameMode) or game_mode not in {
                GameMode.TOURNAMENT,
                GameMode.EXPRESSO,
            }:
                continue
            occurred_at = tournament["finished_at"] or tournament["started_at"]
            if not isinstance(occurred_at, datetime):
                continue
            tournament_id = str(tournament["tournament_id"])
            events.append(
                BankrollPoint(
                    occurred_at=occurred_at,
                    balance=0.0,
                    result=_as_float(tournament["profit"]),
                    game_mode=game_mode,
                    source_type=BankrollSourceType.TOURNAMENT,
                    source_id=tournament_id,
                    tournament_id=tournament_id,
                )
            )
        return events


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _as_int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None