from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from database.database import Database
from database.filters import HistoryFilter
from database.models import Action, Hand, Tournament
from game_modes import GameMode
from poker_stats.bankroll_service import BankrollService, BankrollSourceType
from poker_stats.calculator import StatisticsCalculator
from poker_stats.statistics_service import StatisticsService


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
            winnings=12.50,
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
            big_blind=5.0,
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
            result=-10.0,
            big_blind=5.0,
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
    assert statistics["chip_result_bb"] == 3.0
    assert statistics["cash_result"] == 0.0
    assert statistics["tournament_profit"] == 12.50
    assert statistics["money_result"] == 12.50
    assert statistics["vpip"] == 100.0
    assert statistics["pfr"] == 50.0
    assert statistics["limp_percentage"] == 50.0
    assert statistics["aggression_factor"] == 1.0
    assert statistics["showdown_win_percentage"] == 100.0


def test_statistics_service_calculates_metrics_for_selected_game_mode(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    database.insert_tournament(
        Tournament(
            tournament_id="tournament-1",
            name="Tournament",
            buy_in=10.0,
            prize_pool=100.0,
            players_count=10,
            started_at=datetime(2026, 6, 28, tzinfo=timezone.utc),
            finished_at=None,
            position=1,
            winnings=20.0,
        )
    )
    database.insert_tournament(
        Tournament(
            tournament_id="expresso-1",
            name="Expresso",
            buy_in=2.0,
            prize_pool=6.0,
            players_count=3,
            started_at=datetime(2026, 6, 29, tzinfo=timezone.utc),
            finished_at=None,
            position=1,
            winnings=6.0,
            game_mode=GameMode.EXPRESSO,
        )
    )
    for hand_id, result, played_at in [
        ("cash-1", 1.0, datetime(2026, 6, 28, 12, tzinfo=timezone.utc)),
        ("cash-2", -0.5, datetime(2026, 6, 28, 13, tzinfo=timezone.utc)),
    ]:
        database.insert_hand(
            Hand(
                hand_id=hand_id,
                tournament_id=None,
                played_at=played_at,
                table_name="NL50",
                hero="MyPseudo",
                hero_cards="Ah Kh",
                board="",
                pot=0.0,
                result=result,
                big_blind=0.5,
            )
        )
    database.insert_hand(
        Hand(
            hand_id="tournament-hand",
            tournament_id="tournament-1",
            played_at=datetime(2026, 6, 28, 14, tzinfo=timezone.utc),
            table_name="Tournament(tournament-1)#1",
            hero="MyPseudo",
            hero_cards="Qs Qd",
            board="",
            pot=0.0,
            result=20.0,
            big_blind=10.0,
            game_mode=GameMode.TOURNAMENT,
        )
    )

    statistics = StatisticsService(database, "MyPseudo").calculate()
    cash_statistics = StatisticsService(database, "MyPseudo").calculate(
        HistoryFilter(game_mode=GameMode.CASH_GAME)
    )

    assert statistics["total_profit"] == 14.5
    assert statistics["tournament_profit"] == 10.0
    assert statistics["tournament_roi"] == 100.0
    assert statistics["expresso_profit"] == 4.0
    assert statistics["expresso_roi"] == 200.0
    assert cash_statistics["hands_played"] == 2.0
    assert cash_statistics["cash_result"] == 0.5
    assert cash_statistics["cash_bb"] == 1.0
    assert cash_statistics["cash_bb_per_100"] == 50.0


def test_bankroll_service_returns_chronological_source_linked_points(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    database.insert_tournament(
        Tournament(
            tournament_id="tournament-1",
            name="Tournament",
            buy_in=10.0,
            prize_pool=100.0,
            players_count=10,
            started_at=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            finished_at=datetime(2026, 6, 28, 15, tzinfo=timezone.utc),
            position=1,
            winnings=25.0,
        )
    )
    database.insert_hand(
        Hand(
            hand_id="cash-early",
            tournament_id=None,
            played_at=datetime(2026, 6, 28, 13, tzinfo=timezone.utc),
            table_name="NL50",
            hero="MyPseudo",
            hero_cards="Ah Kh",
            board="",
            pot=0.0,
            result=2.0,
        )
    )
    database.insert_hand(
        Hand(
            hand_id="cash-late",
            tournament_id=None,
            played_at=datetime(2026, 6, 28, 16, tzinfo=timezone.utc),
            table_name="NL50",
            hero="MyPseudo",
            hero_cards="Qs Qd",
            board="",
            pot=0.0,
            result=-1.0,
        )
    )

    points = BankrollService(database, "MyPseudo").calculate()
    cash_points = BankrollService(database, "MyPseudo").calculate(
        HistoryFilter(game_mode=GameMode.CASH_GAME)
    )

    assert [(point.source_type, point.source_id) for point in points] == [
        (BankrollSourceType.HAND, "cash-early"),
        (BankrollSourceType.TOURNAMENT, "tournament-1"),
        (BankrollSourceType.HAND, "cash-late"),
    ]
    assert [point.result for point in points] == [2.0, 15.0, -1.0]
    assert [point.balance for point in points] == [2.0, 17.0, 16.0]
    assert points[0].session_id is None
    assert points[1].tournament_id == "tournament-1"
    assert [point.source_id for point in cash_points] == ["cash-early", "cash-late"]