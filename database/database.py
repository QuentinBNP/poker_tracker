from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from database.models import Action, Hand, ImportRecord, Player, Tournament


class Database:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(self._schema())
            connection.commit()

    def insert_tournament(self, tournament: Tournament) -> None:
        payload = asdict(tournament)
        payload["started_at"] = self._serialize_datetime(tournament.started_at)
        payload["finished_at"] = self._serialize_datetime(tournament.finished_at)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tournaments (
                    tournament_id,
                    name,
                    buy_in,
                    prize_pool,
                    players_count,
                    started_at,
                    finished_at,
                    position
                ) VALUES (
                    :tournament_id,
                    :name,
                    :buy_in,
                    :prize_pool,
                    :players_count,
                    :started_at,
                    :finished_at,
                    :position
                )
                ON CONFLICT(tournament_id) DO UPDATE SET
                    name = excluded.name,
                    buy_in = excluded.buy_in,
                    prize_pool = excluded.prize_pool,
                    players_count = excluded.players_count,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    position = excluded.position
                """,
                payload,
            )

    def get_tournament(self, tournament_id: str) -> Tournament | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tournaments WHERE tournament_id = ?",
                (tournament_id,),
            ).fetchone()

        if row is None:
            return None

        return Tournament(
            tournament_id=row["tournament_id"],
            name=row["name"],
            buy_in=row["buy_in"],
            prize_pool=row["prize_pool"],
            players_count=row["players_count"],
            started_at=self._parse_datetime(row["started_at"]),
            finished_at=self._parse_datetime(row["finished_at"]),
            position=row["position"],
        )

    def insert_hand(self, hand: Hand) -> None:
        payload = asdict(hand)
        payload["played_at"] = self._serialize_datetime(hand.played_at)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO hands (
                    hand_id,
                    tournament_id,
                    played_at,
                    table_name,
                    hero,
                    hero_cards,
                    board,
                    pot,
                    result
                ) VALUES (
                    :hand_id,
                    :tournament_id,
                    :played_at,
                    :table_name,
                    :hero,
                    :hero_cards,
                    :board,
                    :pot,
                    :result
                )
                ON CONFLICT(hand_id) DO UPDATE SET
                    tournament_id = excluded.tournament_id,
                    played_at = excluded.played_at,
                    table_name = excluded.table_name,
                    hero = excluded.hero,
                    hero_cards = excluded.hero_cards,
                    board = excluded.board,
                    pot = excluded.pot,
                    result = excluded.result
                """,
                payload,
            )

    def get_hand(self, hand_id: str) -> Hand | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM hands WHERE hand_id = ?",
                (hand_id,),
            ).fetchone()

        if row is None:
            return None

        return Hand(
            hand_id=row["hand_id"],
            tournament_id=row["tournament_id"],
            played_at=self._parse_datetime(row["played_at"]),
            table_name=row["table_name"],
            hero=row["hero"],
            hero_cards=row["hero_cards"] or "",
            board=row["board"] or "",
            pot=row["pot"],
            result=row["result"],
        )

    def insert_player(self, player: Player) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO players (name) VALUES (?)",
                (player.name,),
            )

    def list_players(self) -> list[Player]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM players ORDER BY name ASC"
            ).fetchall()

        return [Player(name=row["name"]) for row in rows]

    def insert_action(self, action: Action) -> None:
        payload = asdict(action)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO actions (hand_id, player, street, action, amount)
                VALUES (:hand_id, :player, :street, :action, :amount)
                """,
                payload,
            )

    def replace_actions_for_hand(self, hand_id: str, actions: list[Action]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM actions WHERE hand_id = ?", (hand_id,))
            connection.executemany(
                """
                INSERT INTO actions (hand_id, player, street, action, amount)
                VALUES (:hand_id, :player, :street, :action, :amount)
                """,
                [asdict(action) for action in actions],
            )

    def list_actions_for_hand(self, hand_id: str) -> list[Action]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT hand_id, player, street, action, amount
                FROM actions
                WHERE hand_id = ?
                ORDER BY id ASC
                """,
                (hand_id,),
            ).fetchall()

        return [
            Action(
                hand_id=row["hand_id"],
                player=row["player"],
                street=row["street"],
                action=row["action"],
                amount=row["amount"],
            )
            for row in rows
        ]

    def record_import(self, record: ImportRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO imports (filename, imported_at, status)
                VALUES (?, ?, ?)
                ON CONFLICT(filename) DO UPDATE SET
                    imported_at = excluded.imported_at,
                    status = excluded.status
                """,
                (
                    record.filename,
                    self._serialize_datetime(record.imported_at),
                    record.status,
                ),
            )

    def has_import(self, filename: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM imports WHERE filename = ?",
                (filename,),
            ).fetchone()

        return row is not None

    def get_hero_summary(self, hero_name: str) -> dict[str, float | int]:
        with self._connect() as connection:
            hands_played = connection.execute(
                "SELECT COUNT(*) FROM hands WHERE hero = ?",
                (hero_name,),
            ).fetchone()[0]
            tournaments_played = connection.execute(
                "SELECT COUNT(DISTINCT tournament_id) FROM hands WHERE hero = ? AND tournament_id IS NOT NULL",
                (hero_name,),
            ).fetchone()[0]
            total_result = connection.execute(
                "SELECT COALESCE(SUM(result), 0) FROM hands WHERE hero = ?",
                (hero_name,),
            ).fetchone()[0]

        return {
            "hands_played": int(hands_played),
            "tournaments_played": int(tournaments_played),
            "total_result": float(total_result),
        }

    def list_recent_hands(self, hero_name: str, limit: int = 10) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT hand_id, tournament_id, played_at, table_name, hero_cards, board, pot, result
                FROM hands
                WHERE hero = ?
                ORDER BY played_at DESC, id DESC
                LIMIT ?
                """,
                (hero_name, limit),
            ).fetchall()

        return [
            {
                "hand_id": row["hand_id"],
                "tournament_id": row["tournament_id"],
                "played_at": self._parse_datetime(row["played_at"]),
                "table_name": row["table_name"],
                "hero_cards": row["hero_cards"] or "",
                "board": row["board"] or "",
                "pot": float(row["pot"]),
                "result": float(row["result"]),
            }
            for row in rows
        ]

    def list_recent_tournaments(self, limit: int = 10) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT tournament_id, name, buy_in, prize_pool, players_count, started_at, finished_at, position
                FROM tournaments
                ORDER BY started_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "tournament_id": row["tournament_id"],
                "name": row["name"],
                "buy_in": float(row["buy_in"]),
                "prize_pool": float(row["prize_pool"]),
                "players_count": int(row["players_count"]),
                "started_at": self._parse_datetime(row["started_at"]),
                "finished_at": self._parse_datetime(row["finished_at"]),
                "position": row["position"],
            }
            for row in rows
        ]

    def list_hero_actions(self, hero_name: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT a.hand_id, a.street, a.action, a.amount, h.result
                FROM actions a
                INNER JOIN hands h ON h.hand_id = a.hand_id
                WHERE h.hero = ? AND a.player = ?
                ORDER BY h.played_at ASC, a.id ASC
                """,
                (hero_name, hero_name),
            ).fetchall()

        return [
            {
                "hand_id": row["hand_id"],
                "street": row["street"],
                "action": row["action"],
                "amount": row["amount"],
                "result": float(row["result"]),
            }
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None

        return datetime.fromisoformat(value)

    def _schema(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            buy_in REAL NOT NULL,
            prize_pool REAL NOT NULL DEFAULT 0,
            players_count INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            finished_at TEXT,
            position INTEGER
        );

        CREATE TABLE IF NOT EXISTS hands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_id TEXT NOT NULL UNIQUE,
            tournament_id TEXT,
            played_at TEXT,
            table_name TEXT NOT NULL,
            hero TEXT NOT NULL,
            hero_cards TEXT,
            board TEXT,
            pot REAL NOT NULL DEFAULT 0,
            result REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id)
        );

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_id TEXT NOT NULL,
            player TEXT NOT NULL,
            street TEXT NOT NULL,
            action TEXT NOT NULL,
            amount REAL,
            FOREIGN KEY (hand_id) REFERENCES hands (hand_id)
        );

        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            imported_at TEXT NOT NULL,
            status TEXT NOT NULL
        );
        """