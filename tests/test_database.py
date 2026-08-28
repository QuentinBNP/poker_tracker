from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from database.database import Database
from database.filters import HistoryFilter
from database.models import Action, EntryPaymentMethod, Hand, ImportRecord, Player, Tournament
from game_modes import GameMode


def test_database_can_store_and_read_tournament(tmp_path: Path) -> None:
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


def test_tournament_entry_defaults_to_nominal_cost_and_can_be_marked_free(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    tournament = Tournament(
        tournament_id="expresso-1",
        name="Expresso",
        buy_in=2.0,
        prize_pool=6.0,
        players_count=3,
        started_at=datetime(2026, 6, 28, 16, 30, tzinfo=timezone.utc),
        finished_at=None,
        position=1,
        game_mode=GameMode.EXPRESSO,
    )

    database.insert_tournament(tournament)
    imported_entry = database.list_tournament_entries("expresso-1")[0]
    database.set_tournament_entry_free("expresso-1", True)
    free_entry = database.list_tournament_entries("expresso-1")[0]

    assert imported_entry.nominal_buy_in == 2.0
    assert imported_entry.cash_cost == 2.0
    assert imported_entry.payment_method is EntryPaymentMethod.UNKNOWN
    assert free_entry.cash_cost == 0.0
    assert free_entry.payment_method is EntryPaymentMethod.FREE_TICKET
    assert free_entry.is_manually_adjusted is True


def test_tournament_reentry_is_charged_and_free_entry_survives_reimport(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    tournament = Tournament(
        tournament_id="tournament-1",
        name="Tournament",
        buy_in=10.0,
        prize_pool=100.0,
        players_count=10,
        started_at=datetime(2026, 6, 28, tzinfo=timezone.utc),
        finished_at=None,
        position=1,
    )
    database.insert_tournament(tournament)
    database.set_tournament_entry_free("tournament-1", True)
    reentry = database.add_tournament_reentry("tournament-1", 10.0)

    database.insert_tournament(tournament)
    entries = database.list_tournament_entries("tournament-1")

    assert reentry.entry_number == 2
    assert reentry.cash_cost == 10.0
    assert [entry.cash_cost for entry in entries] == [0.0, 10.0]
    assert entries[0].payment_method is EntryPaymentMethod.FREE_TICKET


def test_database_can_store_hand_players_actions_and_import(tmp_path: Path) -> None:
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


def test_database_initialization_migrates_existing_result_columns(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "tracker.db"
    database_path.parent.mkdir()
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE tournaments (
                id INTEGER PRIMARY KEY,
                tournament_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                buy_in REAL NOT NULL,
                prize_pool REAL NOT NULL DEFAULT 0,
                players_count INTEGER NOT NULL DEFAULT 0,
                started_at TEXT,
                finished_at TEXT,
                position INTEGER
            );
            CREATE TABLE hands (
                id INTEGER PRIMARY KEY,
                hand_id TEXT NOT NULL UNIQUE,
                tournament_id TEXT,
                played_at TEXT,
                table_name TEXT NOT NULL,
                hero TEXT NOT NULL,
                hero_cards TEXT,
                board TEXT,
                pot REAL NOT NULL DEFAULT 0,
                result REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE imports (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                imported_at TEXT NOT NULL,
                status TEXT NOT NULL,
                modified_at_ns INTEGER,
                file_size INTEGER
            );
            """
        )

    Database(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        hand_columns = {row[1] for row in connection.execute("PRAGMA table_info(hands)")}
        tournament_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(tournaments)")
        }
        import_columns = {row[1] for row in connection.execute("PRAGMA table_info(imports)")}

    assert "big_blind" in hand_columns
    assert {"winnings", "bounty_winnings"}.issubset(tournament_columns)
    assert "import_version" in import_columns


def test_database_migrates_legacy_hands_to_game_modes_and_sessions(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "tracker.db"
    database_path.parent.mkdir()
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE tournaments (
                id INTEGER PRIMARY KEY,
                tournament_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                buy_in REAL NOT NULL,
                prize_pool REAL NOT NULL DEFAULT 0,
                players_count INTEGER NOT NULL DEFAULT 0,
                started_at TEXT,
                finished_at TEXT,
                position INTEGER
            );
            CREATE TABLE hands (
                id INTEGER PRIMARY KEY,
                hand_id TEXT NOT NULL UNIQUE,
                tournament_id TEXT,
                played_at TEXT,
                table_name TEXT NOT NULL,
                hero TEXT NOT NULL,
                hero_cards TEXT,
                board TEXT,
                pot REAL NOT NULL DEFAULT 0,
                result REAL NOT NULL DEFAULT 0
            );
            INSERT INTO tournaments (tournament_id, name, buy_in)
            VALUES ('tournament-1', 'Freeroll', 0);
            INSERT INTO hands (hand_id, tournament_id, played_at, table_name, hero)
            VALUES ('tournament-hand', 'tournament-1', '2026-06-28T16:42:03+00:00',
                    'Freeroll(tournament-1)#1', 'MyPseudo');
            INSERT INTO hands (hand_id, played_at, table_name, hero)
            VALUES ('cash-hand', '2026-06-28T16:52:01+00:00', 'Nice 23', 'MyPseudo');
            """
        )

    database = Database(database_path)
    database.initialize()

    tournament_hand = database.get_hand("tournament-hand")
    cash_hand = database.get_hand("cash-hand")

    assert tournament_hand is not None
    assert tournament_hand.game_mode is GameMode.TOURNAMENT
    assert tournament_hand.session_id is not None
    assert cash_hand is not None
    assert cash_hand.game_mode is GameMode.CASH_GAME
    assert cash_hand.session_id is not None


def test_cash_hands_more_than_thirty_minutes_apart_get_distinct_sessions(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    first_hand = Hand(
        hand_id="cash-hand-1",
        tournament_id=None,
        played_at=datetime(2026, 6, 28, 16, 0, tzinfo=timezone.utc),
        table_name="Nice 23",
        hero="MyPseudo",
        hero_cards="Ah Kh",
        board="",
        pot=0.0,
        result=0.0,
        game_mode=GameMode.CASH_GAME,
    )
    second_hand = Hand(
        hand_id="cash-hand-2",
        tournament_id=None,
        played_at=datetime(2026, 6, 28, 16, 31, tzinfo=timezone.utc),
        table_name="Nice 23",
        hero="MyPseudo",
        hero_cards="Qs Qd",
        board="",
        pot=0.0,
        result=0.0,
        game_mode=GameMode.CASH_GAME,
    )

    first_hand.session_id = database.assign_hand_to_session(first_hand)
    database.insert_hand(first_hand)
    second_hand.session_id = database.assign_hand_to_session(second_hand)
    database.insert_hand(second_hand)

    assert first_hand.session_id != second_hand.session_id


def test_history_filters_apply_to_hands_actions_and_tournaments(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    database.insert_tournament(
        Tournament(
            tournament_id="tournament-1",
            name="Freeroll",
            buy_in=0.0,
            prize_pool=100.0,
            players_count=10,
            started_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
            finished_at=None,
            position=1,
        )
    )
    database.insert_tournament(
        Tournament(
            tournament_id="expresso-1",
            name="Expresso One",
            buy_in=1.0,
            prize_pool=3.0,
            players_count=3,
            started_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
            finished_at=None,
            position=1,
            game_mode=GameMode.EXPRESSO,
        )
    )
    database.insert_hand(
        Hand(
            hand_id="cash-alpha",
            tournament_id=None,
            played_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            table_name="Alpha",
            hero="MyPseudo",
            hero_cards="Ah Kh",
            board="",
            pot=0.0,
            result=1.0,
        )
    )
    database.insert_hand(
        Hand(
            hand_id="tournament-hand",
            tournament_id="tournament-1",
            played_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
            table_name="Freeroll(tournament-1)#1",
            hero="MyPseudo",
            hero_cards="Qs Qd",
            board="",
            pot=0.0,
            result=0.0,
            game_mode=GameMode.TOURNAMENT,
        )
    )
    database.replace_actions_for_hand(
        "cash-alpha",
        [Action("cash-alpha", "MyPseudo", "PRE_FLOP", "RAISE", 1.0)],
    )

    cash_filter = HistoryFilter(
        start_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end_at=datetime(2026, 6, 1, 23, 59, tzinfo=timezone.utc),
        game_mode=GameMode.CASH_GAME,
        table_name="Alpha",
    )
    tournament_filter = HistoryFilter(
        game_mode=GameMode.TOURNAMENT,
        tournament_id="tournament-1",
    )

    assert [hand["hand_id"] for hand in database.list_filtered_hands("MyPseudo", cash_filter)] == [
        "cash-alpha"
    ]
    filtered_actions = database.list_filtered_hero_actions("MyPseudo", cash_filter)
    assert [action["hand_id"] for action in filtered_actions] == [
        "cash-alpha"
    ]
    filtered_tournament_hands = database.list_filtered_hands("MyPseudo", tournament_filter)
    assert [hand["hand_id"] for hand in filtered_tournament_hands] == [
        "tournament-hand"
    ]
    assert [
        tournament["tournament_id"]
        for tournament in database.list_filtered_tournaments(
            HistoryFilter(game_mode=GameMode.EXPRESSO)
        )
    ] == ["expresso-1"]


def test_multi_mode_filter_lists_matching_sessions_and_ordered_hands(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    earlier_hand = Hand(
        hand_id="cash-early",
        tournament_id=None,
        played_at=datetime(2026, 6, 1, 10, tzinfo=timezone.utc),
        table_name="Alpha",
        hero="MyPseudo",
        hero_cards="Ah Kh",
        board="",
        pot=0.0,
        result=1.0,
    )
    later_hand = Hand(
        hand_id="cash-late",
        tournament_id=None,
        played_at=datetime(2026, 6, 1, 10, 10, tzinfo=timezone.utc),
        table_name="Alpha",
        hero="MyPseudo",
        hero_cards="Qs Qd",
        board="",
        pot=0.0,
        result=-0.5,
    )
    for hand in (earlier_hand, later_hand):
        hand.session_id = database.assign_hand_to_session(hand)
        database.insert_hand(hand)

    filters = HistoryFilter(
        game_modes=(GameMode.CASH_GAME, GameMode.EXPRESSO),
    )
    sessions = database.list_sessions("MyPseudo", filters)

    assert len(sessions) == 1
    assert sessions[0]["game_mode"] is GameMode.CASH_GAME
    assert sessions[0]["hands_played"] == 2
    assert sessions[0]["result"] == 0.5
    session_id = sessions[0]["session_id"]
    assert isinstance(session_id, int)
    assert [
        hand["hand_id"]
        for hand in database.list_hands_for_session("MyPseudo", session_id)
    ] == ["cash-early", "cash-late"]


def test_filtered_hands_derive_bb_results_per_hand_blind(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "tracker.db")
    database.initialize()
    database.insert_tournament(
        Tournament(
            tournament_id="event-1",
            name="Event",
            buy_in=1.0,
            prize_pool=3.0,
            players_count=3,
            started_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
            finished_at=None,
            position=None,
        )
    )
    for hand_id, result, big_blind in (
        ("nl2-win", 0.07, 0.02),
        ("nl10-loss", -0.25, 0.10),
    ):
        database.insert_hand(
            Hand(
                hand_id=hand_id,
                tournament_id=None,
                played_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                table_name="Cash",
                hero="MyPseudo",
                hero_cards="Ah Kh",
                board="",
                pot=0.0,
                result=result,
                big_blind=big_blind,
            )
        )
    database.insert_hand(
        Hand(
            hand_id="tournament-hand",
            tournament_id="event-1",
            played_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
            table_name="Event",
            hero="MyPseudo",
            hero_cards="Qs Qd",
            board="",
            pot=0.0,
            result=100.0,
            big_blind=10.0,
            game_mode=GameMode.TOURNAMENT,
        )
    )

    hands = database.list_filtered_hands("MyPseudo", HistoryFilter(), limit=10)
    results_by_hand = {str(hand["hand_id"]): hand["result_bb"] for hand in hands}

    assert results_by_hand["nl2-win"] == pytest.approx(3.5)
    assert results_by_hand["nl10-loss"] == pytest.approx(-2.5)
    assert results_by_hand["tournament-hand"] == pytest.approx(10.0)