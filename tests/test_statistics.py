from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics.calculator import StatisticsCalculator

from database.database import Database
from database.models import Action, Hand, Tournament


def test_statistics_calculator_uses_existing_hand_and_action_data(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    database.insert_tournament(
        Tournament(
            tournament_id="1119027769",
            name="Freeroll",
            buy_in=0.0,
            prize_pool=150.0,
            players_count=6564,
            started_at=datetime(2026, 6, 28, 16, 30, 2, tzinfo=timezone.utc),
            finished_at=None,
            position=3925,
        )
    )
    database.insert_hand(
        Hand(
            hand_id="hand-1",
            tournament_id="1119027769",
            played_at=datetime(2026, 6, 28, 16, 42, 3, tzinfo=timezone.utc),
            table_name="Freeroll(1119027769)#0432",
            hero="MyPseudo",
            hero_cards="Ah Kh",
            board="2c 3d 4h 5s 6c",
            pot=100.0,
            result=25.0,
        )
    )
    database.insert_hand(
        Hand(
            hand_id="hand-2",
            tournament_id="1119027769",
            played_at=datetime(2026, 6, 28, 16, 45, 0, tzinfo=timezone.utc),
            table_name="Freeroll(1119027769)#0432",
            hero="MyPseudo",
            hero_cards="Qs Qd",
            board="As Kd 7h",
            pot=60.0,
            result=0.0,
        )
    )
    database.replace_actions_for_hand(
        "hand-1",
        [
            Action(
                hand_id="hand-1",
                player="MyPseudo",
                street="PRE_FLOP",
                action="CALL",
                amount=10.0,
            ),
            Action(
                hand_id="hand-1",
                player="MyPseudo",
                street="FLOP",
                action="BET",
                amount=15.0,
            ),
            Action(
                hand_id="hand-1",
                player="MyPseudo",
                street="SHOW_DOWN",
                action="SHOW",
                amount=None,
            ),
        ],
    )
    database.replace_actions_for_hand(
        "hand-2",
        [
            Action(
                hand_id="hand-2",
                player="MyPseudo",
                street="PRE_FLOP",
                action="RAISE",
                amount=12.0,
            ),
            Action(
                hand_id="hand-2",
                player="MyPseudo",
                street="FLOP",
                action="CALL",
                amount=8.0,
            ),
        ],
    )

    statistics = StatisticsCalculator(database, "MyPseudo").calculate()

    assert statistics["hands_played"] == 2.0
    assert statistics["tournaments_played"] == 1.0
    assert statistics["total_result"] == 25.0
    assert statistics["vpip"] == 100.0
    assert statistics["pfr"] == 50.0
    assert statistics["limp_percentage"] == 50.0
    assert statistics["aggression_factor"] == 1.0
    assert statistics["showdown_win_percentage"] == 100.0