from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from database.database import Database
from database.models import Hand, Tournament
from poker_stats.accounting_service import AccountingEventType, AccountingService


def test_accounting_service_emits_auditable_chronological_events(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    database.insert_tournament(
        Tournament(
            tournament_id="tournament-1",
            name="Tournament",
            buy_in=10.0,
            prize_pool=100.0,
            players_count=10,
            started_at=datetime(2026, 6, 1, 11, tzinfo=timezone.utc),
            finished_at=datetime(2026, 6, 1, 14, tzinfo=timezone.utc),
            position=1,
            winnings=25.0,
            bounty_winnings=2.0,
        )
    )
    database.set_tournament_entry_free("tournament-1", True)
    database.add_tournament_reentry(
        "tournament-1",
        10.0,
        datetime(2026, 6, 1, 12, tzinfo=timezone.utc),
    )
    database.insert_hand(
        Hand(
            hand_id="cash-1",
            tournament_id=None,
            played_at=datetime(2026, 6, 1, 13, tzinfo=timezone.utc),
            table_name="Cash",
            hero="MyPseudo",
            hero_cards="Ah Kh",
            board="",
            pot=1.0,
            result=-0.2,
        )
    )

    service = AccountingService(database, "MyPseudo")
    events = service.events()
    reconciliation = service.reconcile_tournament("tournament-1")

    assert [event.event_type for event in events] == [
        AccountingEventType.TOURNAMENT_ENTRY,
        AccountingEventType.TOURNAMENT_ENTRY,
        AccountingEventType.CASH_HAND,
        AccountingEventType.TOURNAMENT_SETTLEMENT,
    ]
    assert [event.amount for event in events] == [-0.0, -10.0, -0.2, 27.0]
    assert reconciliation is not None
    assert reconciliation.entry_count == 2
    assert reconciliation.total_entry_cost == 10.0
    assert reconciliation.winnings == 25.0
    assert reconciliation.bounty_winnings == 2.0
    assert reconciliation.profit == 17.0
    assert sum(event.amount for event in events) == 16.8