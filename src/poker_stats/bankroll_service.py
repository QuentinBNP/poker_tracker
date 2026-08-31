from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from database.database import Database
from database.filters import HistoryFilter
from game_modes import GameMode
from poker_stats.accounting_service import AccountingEventType, AccountingService


class BankrollSourceType(StrEnum):
    HAND = "CASH_HAND"
    TOURNAMENT_ENTRY = "TOURNAMENT_ENTRY"
    TOURNAMENT = "TOURNAMENT_SETTLEMENT"


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
        self.accounting_service = AccountingService(database, hero_name)

    def calculate(self, filters: HistoryFilter | None = None) -> list[BankrollPoint]:
        balance = 0.0
        points: list[BankrollPoint] = []
        for event in self.accounting_service.events(filters):
            balance += event.amount
            points.append(
                BankrollPoint(
                    occurred_at=event.occurred_at,
                    balance=balance,
                    result=event.amount,
                    game_mode=event.game_mode,
                    source_type=_bankroll_source_type(event.event_type),
                    source_id=event.source_id,
                    session_id=event.session_id,
                    tournament_id=event.tournament_id,
                )
            )
        return points


def _bankroll_source_type(event_type: AccountingEventType) -> BankrollSourceType:
    return {
        AccountingEventType.CASH_HAND: BankrollSourceType.HAND,
        AccountingEventType.TOURNAMENT_ENTRY: BankrollSourceType.TOURNAMENT_ENTRY,
        AccountingEventType.TOURNAMENT_SETTLEMENT: BankrollSourceType.TOURNAMENT,
    }[event_type]