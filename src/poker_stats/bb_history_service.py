from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from database.database import Database
from database.filters import HistoryFilter
from game_modes import GameMode


@dataclass(frozen=True, slots=True)
class BBHistoryPoint:
    hand_id: str
    occurred_at: datetime
    result_bb: float
    balance_bb: float
    pot: float
    hero_cards: str


class BBHistoryService:
    def __init__(self, database: Database, hero_name: str) -> None:
        self.database = database
        self.hero_name = hero_name

    def calculate(self, filters: HistoryFilter | None = None) -> list[BBHistoryPoint]:
        hands = self.database.list_filtered_hands(
            self.hero_name,
            filters or HistoryFilter(),
            limit=1_000_000,
        )
        balance_bb = 0.0
        points: list[BBHistoryPoint] = []
        for hand in reversed(hands):
            if hand["game_mode"] is not GameMode.CASH_GAME:
                continue
            result_bb = hand["result_bb"]
            occurred_at = hand["played_at"]
            if not isinstance(result_bb, int | float) or not isinstance(occurred_at, datetime):
                continue
            balance_bb += float(result_bb)
            points.append(
                BBHistoryPoint(
                    hand_id=str(hand["hand_id"]),
                    occurred_at=occurred_at,
                    result_bb=float(result_bb),
                    balance_bb=balance_bb,
                    pot=_as_float(hand["pot"]),
                    hero_cards=str(hand["hero_cards"]),
                )
            )
        return points


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return 0.0