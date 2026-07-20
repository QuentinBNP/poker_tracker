from __future__ import annotations

from datetime import datetime, timezone

from database.database import Database
from database.models import Action, Hand, ImportRecord, Player, Tournament


def test_database_can_store_and_read_tournament(tmp_path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()

    tournament = Tournament(
        tournament_id="1119027769",
        name="Freeroll",
        buy_in=0.0,
        prize_pool=150.0,
        players_count=6564,
        started_at=datetime(2026, 6, 28, 16, 30, 2, tzinfo=timezone.utc),
        finished_at=None,
        position=3925,
    )

    database.insert_tournament(tournament)
    stored_tournament = database.get_tournament("1119027769")

    assert stored_tournament == tournament


def test_database_can_store_hand_players_actions_and_import(tmp_path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()

    database.insert_tournament(
        Tournament(
            tournament_id="1119034571",
            name="Kill The Fish",
            buy_in=0.25,
            prize_pool=73.26,
            players_count=541,
            started_at=datetime(2026, 6, 28, 19, 30, 1, tzinfo=timezone.utc),
            finished_at=None,
            position=63,
        )
    )

    hand = Hand(
        hand_id="#4806216885538390028-14-1782675934",
        tournament_id="1119034571",
        played_at=datetime(2026, 6, 28, 19, 45, 34, tzinfo=timezone.utc),
        table_name="Kill The Fish(1119034571)#011",
        hero="MyPseudo",
        hero_cards="5s As",
        board="9d 3s 8s 4h Js",
        pot=31533,
        result=31533,
    )

    database.insert_hand(hand)
    database.insert_player(Player(name="MyPseudo"))
    database.insert_player(Player(name="Je m en Fish"))
    database.insert_action(
        Action(
            hand_id=hand.hand_id,
            player="MyPseudo",
            street="TURN",
            action="CALL",
            amount=11489,
        )
    )
    database.record_import(
        ImportRecord(
            filename="20260628_Kill The Fish(1119034571)_real_holdem_no-limit.txt",
            imported_at=datetime(2026, 6, 28, 19, 46, 0, tzinfo=timezone.utc),
            status="success",
        )
    )

    stored_hand = database.get_hand(hand.hand_id)
    stored_players = database.list_players()
    stored_actions = database.list_actions_for_hand(hand.hand_id)

    assert stored_hand == hand
    assert stored_players == [Player(name="Je m en Fish"), Player(name="MyPseudo")]
    assert stored_actions == [
        Action(
            hand_id=hand.hand_id,
            player="MyPseudo",
            street="TURN",
            action="CALL",
            amount=11489,
        )
    ]
    assert database.has_import(
        "20260628_Kill The Fish(1119034571)_real_holdem_no-limit.txt"
    )