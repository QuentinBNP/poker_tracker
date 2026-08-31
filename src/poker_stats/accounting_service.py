from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from database.database import Database
from database.filters import HistoryFilter
from game_modes import GameMode


class AccountingEventType(StrEnum):
    CASH_HAND = "CASH_HAND"
    TOURNAMENT_ENTRY = "TOURNAMENT_ENTRY"
    TOURNAMENT_SETTLEMENT = "TOURNAMENT_SETTLEMENT"


@dataclass(frozen=True, slots=True)
class AccountingEvent:
    occurred_at: datetime
    amount: float
    game_mode: GameMode
    event_type: AccountingEventType
    source_id: str
    session_id: int | None = None
    tournament_id: str | None = None
    entry_number: int | None = None


@dataclass(frozen=True, slots=True)
class TournamentReconciliation:
    tournament_id: str
    game_mode: GameMode
    entry_count: int
    total_entry_cost: float
    winnings: float
    bounty_winnings: float
    profit: float


class AccountingService:
    def __init__(self, database: Database, hero_name: str) -> None:
        self.database = database
        self.hero_name = hero_name

    def events(self, filters: HistoryFilter | None = None) -> list[AccountingEvent]:
        active_filter = filters or HistoryFilter()
        events = [
            *self._cash_events(active_filter),
            *self._tournament_events(active_filter),
        ]
        return sorted(
            events,
            key=lambda event: (event.occurred_at, event.event_type, event.source_id),
        )

    def reconciliations(
        self,
        filters: HistoryFilter | None = None,
    ) -> list[TournamentReconciliation]:
        tournaments = self.database.list_filtered_tournaments(
            filters or HistoryFilter(),
            limit=1_000_000,
        )
        return [self._reconcile(tournament) for tournament in tournaments]

    def reconcile_tournament(self, tournament_id: str) -> TournamentReconciliation | None:
        tournaments = self.database.list_filtered_tournaments(
            HistoryFilter(tournament_id=tournament_id),
            limit=1,
        )
        return self._reconcile(tournaments[0]) if tournaments else None

    def _cash_events(self, filters: HistoryFilter) -> list[AccountingEvent]:
        hands = self.database.list_filtered_hands(self.hero_name, filters, limit=1_000_000)
        events: list[AccountingEvent] = []
        for hand in hands:
            occurred_at = hand["played_at"]
            if hand["tournament_id"] is not None or not isinstance(occurred_at, datetime):
                continue
            events.append(
                AccountingEvent(
                    occurred_at=occurred_at,
                    amount=_as_float(hand["result"]),
                    game_mode=GameMode.CASH_GAME,
                    event_type=AccountingEventType.CASH_HAND,
                    source_id=str(hand["hand_id"]),
                    session_id=_as_int_or_none(hand["session_id"]),
                )
            )
        return events

    def _tournament_events(self, filters: HistoryFilter) -> list[AccountingEvent]:
        tournaments = self.database.list_filtered_tournaments(filters, limit=1_000_000)
        events: list[AccountingEvent] = []
        for tournament in tournaments:
            game_mode = tournament["game_mode"]
            if not isinstance(game_mode, GameMode) or game_mode not in {
                GameMode.TOURNAMENT,
                GameMode.EXPRESSO,
            }:
                continue

            tournament_id = str(tournament["tournament_id"])
            for entry in self.database.list_tournament_entries(tournament_id):
                occurred_at = entry.entered_at or tournament["started_at"]
                if not isinstance(occurred_at, datetime):
                    continue
                events.append(
                    AccountingEvent(
                        occurred_at=occurred_at,
                        amount=-entry.cash_cost,
                        game_mode=game_mode,
                        event_type=AccountingEventType.TOURNAMENT_ENTRY,
                        source_id=f"{tournament_id}:{entry.entry_number}",
                        tournament_id=tournament_id,
                        entry_number=entry.entry_number,
                    )
                )

            settled_at = tournament["finished_at"] or tournament["started_at"]
            if isinstance(settled_at, datetime):
                events.append(
                    AccountingEvent(
                        occurred_at=settled_at,
                        amount=(
                            _as_float(tournament["winnings"])
                            + _as_float(tournament["bounty_winnings"])
                        ),
                        game_mode=game_mode,
                        event_type=AccountingEventType.TOURNAMENT_SETTLEMENT,
                        source_id=tournament_id,
                        tournament_id=tournament_id,
                    )
                )
        return events

    @staticmethod
    def _reconcile(tournament: dict[str, object]) -> TournamentReconciliation:
        total_entry_cost = _as_float(tournament["total_entry_cost"])
        winnings = _as_float(tournament["winnings"])
        bounty_winnings = _as_float(tournament["bounty_winnings"])
        game_mode_value = tournament["game_mode"]
        if isinstance(game_mode_value, GameMode):
            game_mode = game_mode_value
        elif isinstance(game_mode_value, str):
            game_mode = GameMode(game_mode_value)
        else:
            raise TypeError("Tournament game mode must be a GameMode or string")
        return TournamentReconciliation(
            tournament_id=str(tournament["tournament_id"]),
            game_mode=game_mode,
            entry_count=int(_as_float(tournament["entry_count"])),
            total_entry_cost=total_entry_cost,
            winnings=winnings,
            bounty_winnings=bounty_winnings,
            profit=winnings + bounty_winnings - total_entry_cost,
        )


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _as_int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None