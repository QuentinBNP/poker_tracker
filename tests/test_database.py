from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from database.database import Database
from database.models import Action, Hand, ImportRecord, Player, Tournament
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
            """
        )

    Database(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        hand_columns = {row[1] for row in connection.execute("PRAGMA table_info(hands)")}
        tournament_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(tournaments)")
        }

    assert "big_blind" in hand_columns
    assert {"winnings", "bounty_winnings"}.issubset(tournament_columns)


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