from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from database.filters import HistoryFilter
from database.models import Action, Hand, ImportRecord, Player, Session, Tournament
from game_modes import GameMode


class Database:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(self._schema())
            self._migrate_schema(connection)
            self._backfill_legacy_game_modes(connection)
            self._backfill_legacy_sessions(connection)
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
                    position,
                    winnings,
                    bounty_winnings,
                    game_mode
                ) VALUES (
                    :tournament_id,
                    :name,
                    :buy_in,
                    :prize_pool,
                    :players_count,
                    :started_at,
                    :finished_at,
                    :position,
                    :winnings,
                    :bounty_winnings,
                    :game_mode
                )
                ON CONFLICT(tournament_id) DO UPDATE SET
                    name = excluded.name,
                    buy_in = excluded.buy_in,
                    prize_pool = excluded.prize_pool,
                    players_count = excluded.players_count,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    position = excluded.position,
                    winnings = excluded.winnings,
                    bounty_winnings = excluded.bounty_winnings,
                    game_mode = excluded.game_mode
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
            winnings=row["winnings"],
            bounty_winnings=row["bounty_winnings"],
            game_mode=GameMode(row["game_mode"]),
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
                    result,
                    big_blind,
                    game_mode,
                    session_id
                ) VALUES (
                    :hand_id,
                    :tournament_id,
                    :played_at,
                    :table_name,
                    :hero,
                    :hero_cards,
                    :board,
                    :pot,
                    :result,
                    :big_blind,
                    :game_mode,
                    :session_id
                )
                ON CONFLICT(hand_id) DO UPDATE SET
                    tournament_id = excluded.tournament_id,
                    played_at = excluded.played_at,
                    table_name = excluded.table_name,
                    hero = excluded.hero,
                    hero_cards = excluded.hero_cards,
                    board = excluded.board,
                    pot = excluded.pot,
                    result = excluded.result,
                    big_blind = excluded.big_blind,
                    game_mode = excluded.game_mode,
                    session_id = excluded.session_id
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
            big_blind=row["big_blind"],
            game_mode=GameMode(row["game_mode"]),
            session_id=row["session_id"],
        )

    def assign_hand_to_session(self, hand: Hand) -> int:
        if hand.game_mode is GameMode.TOURNAMENT or hand.game_mode is GameMode.EXPRESSO:
            return self._assign_tournament_session(hand)
        return self._assign_cash_session(hand)

    def get_session(self, session_id: int) -> Session | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()

        return self._session_from_row(row) if row is not None else None

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
                INSERT INTO actions (hand_id, player, street, action, amount, is_all_in)
                VALUES (:hand_id, :player, :street, :action, :amount, :is_all_in)
                """,
                payload,
            )

    def replace_actions_for_hand(self, hand_id: str, actions: list[Action]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM actions WHERE hand_id = ?", (hand_id,))
            connection.executemany(
                """
                INSERT INTO actions (hand_id, player, street, action, amount, is_all_in)
                VALUES (:hand_id, :player, :street, :action, :amount, :is_all_in)
                """,
                [asdict(action) for action in actions],
            )

    def list_actions_for_hand(self, hand_id: str) -> list[Action]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT hand_id, player, street, action, amount, is_all_in
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
                is_all_in=bool(row["is_all_in"]),
            )
            for row in rows
        ]

    def record_import(self, record: ImportRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO imports (
                    filename, imported_at, status, modified_at_ns, file_size, import_version
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(filename) DO UPDATE SET
                    imported_at = excluded.imported_at,
                    status = excluded.status,
                    modified_at_ns = excluded.modified_at_ns,
                    file_size = excluded.file_size,
                    import_version = excluded.import_version
                """,
                (
                    record.filename,
                    self._serialize_datetime(record.imported_at),
                    record.status,
                    record.modified_at_ns,
                    record.file_size,
                    record.import_version,
                ),
            )

    def has_import(self, filename: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM imports WHERE filename = ?",
                (filename,),
            ).fetchone()

        return row is not None

    def has_current_import(self, path: Path, import_version: int) -> bool:
        stats = path.stat()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM imports
                WHERE filename = ? AND status = 'success'
                  AND modified_at_ns = ? AND file_size = ? AND import_version = ?
                """,
                (path.name, stats.st_mtime_ns, stats.st_size, import_version),
            ).fetchone()

        return row is not None

    def get_hero_summary(self, hero_name: str) -> dict[str, float | int]:
        with self._connect() as connection:
            hands_played = connection.execute(
                "SELECT COUNT(*) FROM hands WHERE hero = ?",
                (hero_name,),
            ).fetchone()[0]
            tournaments_played = connection.execute(
                (
                    "SELECT COUNT(DISTINCT tournament_id) FROM hands "
                    "WHERE hero = ? AND tournament_id IS NOT NULL"
                ),
                (hero_name,),
            ).fetchone()[0]
            total_result = connection.execute(
                (
                    "SELECT COALESCE(SUM(result), 0) FROM hands "
                    "WHERE hero = ? AND tournament_id IS NULL"
                ),
                (hero_name,),
            ).fetchone()[0]
            chip_result_bb = connection.execute(
                """
                SELECT COALESCE(SUM(result / big_blind), 0)
                FROM hands
                WHERE hero = ? AND tournament_id IS NOT NULL AND big_blind > 0
                """,
                (hero_name,),
            ).fetchone()[0]
            tournament_profit = connection.execute(
                "SELECT COALESCE(SUM(winnings + bounty_winnings - buy_in), 0) FROM tournaments"
            ).fetchone()[0]

        return {
            "hands_played": int(hands_played),
            "tournaments_played": int(tournaments_played),
            "cash_result": float(total_result),
            "tournament_profit": float(tournament_profit),
            "money_result": float(total_result + tournament_profit),
            "chip_result_bb": float(chip_result_bb),
        }

    def list_recent_hands(self, hero_name: str, limit: int = 10) -> list[dict[str, object]]:
        return self.list_filtered_hands(hero_name, HistoryFilter(), limit=limit)

    def list_recent_tournaments(self, limit: int = 10) -> list[dict[str, object]]:
        return self.list_filtered_tournaments(HistoryFilter(), limit=limit)

    def list_hero_actions(self, hero_name: str) -> list[dict[str, object]]:
        return self.list_filtered_hero_actions(hero_name, HistoryFilter())

    def list_filtered_hands(
        self,
        hero_name: str,
        filters: HistoryFilter,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        conditions, parameters = filters.hand_conditions()
        where_clause = " AND ".join(["h.hero = ?", *conditions])
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT h.hand_id, h.tournament_id, h.session_id, h.game_mode, h.played_at,
                       h.table_name, h.hero_cards, h.board, h.pot, h.result, h.big_blind
                FROM hands h
                WHERE {where_clause}
                ORDER BY h.played_at DESC, h.id DESC
                LIMIT ? OFFSET ?
                """,
                (hero_name, *parameters, limit, offset),
            ).fetchall()

        return [self._hand_row(row) for row in rows]

    def list_hands_for_session(
        self,
        hero_name: str,
        session_id: int,
    ) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT h.hand_id, h.tournament_id, h.session_id, h.game_mode, h.played_at,
                       h.table_name, h.hero_cards, h.board, h.pot, h.result, h.big_blind
                FROM hands h
                WHERE h.hero = ? AND h.session_id = ?
                ORDER BY h.played_at ASC, h.id ASC
                """,
                (hero_name, session_id),
            ).fetchall()

        return [self._hand_row(row) for row in rows]

    def list_sessions(
        self,
        hero_name: str,
        filters: HistoryFilter,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        conditions, parameters = filters.hand_conditions()
        where_clause = " AND ".join(["h.hero = ?", "h.session_id IS NOT NULL", *conditions])
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT s.id, s.game_mode, s.table_name, s.tournament_id, s.started_at,
                       s.finished_at, COUNT(h.id) AS hands_played,
                       CASE WHEN s.tournament_id IS NULL THEN SUM(h.result)
                            ELSE COALESCE(MAX(t.winnings + t.bounty_winnings - t.buy_in), 0)
                       END AS result
                FROM sessions s
                INNER JOIN hands h ON h.session_id = s.id
                LEFT JOIN tournaments t ON t.tournament_id = s.tournament_id
                WHERE {where_clause}
                GROUP BY s.id
                ORDER BY s.started_at DESC, s.id DESC
                LIMIT ? OFFSET ?
                """,
                (hero_name, *parameters, limit, offset),
            ).fetchall()

        return [
            {
                "session_id": int(row["id"]),
                "game_mode": GameMode(row["game_mode"]),
                "table_name": row["table_name"],
                "tournament_id": row["tournament_id"],
                "started_at": self._parse_datetime(row["started_at"]),
                "finished_at": self._parse_datetime(row["finished_at"]),
                "hands_played": int(row["hands_played"]),
                "result": float(row["result"]),
            }
            for row in rows
        ]

    def list_filtered_hero_actions(
        self,
        hero_name: str,
        filters: HistoryFilter,
    ) -> list[dict[str, object]]:
        conditions, parameters = filters.hand_conditions()
        where_clause = " AND ".join(["h.hero = ?", "a.player = ?", *conditions])
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT a.hand_id, a.street, a.action, a.amount, h.result
                FROM actions a
                INNER JOIN hands h ON h.hand_id = a.hand_id
                WHERE {where_clause}
                ORDER BY h.played_at ASC, a.id ASC
                """,
                (hero_name, hero_name, *parameters),
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

    def list_filtered_actions(self, filters: HistoryFilter) -> list[dict[str, object]]:
        conditions, parameters = filters.hand_conditions()
        where_clause = " AND ".join(conditions) if conditions else "1 = 1"
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT a.hand_id, a.player, a.street, a.action, a.amount, a.is_all_in, h.result
                FROM actions a
                INNER JOIN hands h ON h.hand_id = a.hand_id
                WHERE {where_clause}
                ORDER BY h.played_at ASC, h.id ASC, a.id ASC
                """,
                parameters,
            ).fetchall()

        return [
            {
                "hand_id": row["hand_id"],
                "player": row["player"],
                "street": row["street"],
                "action": row["action"],
                "amount": row["amount"],
                "is_all_in": bool(row["is_all_in"]),
                "result": float(row["result"]),
            }
            for row in rows
        ]

    def list_filtered_tournaments(
        self,
        filters: HistoryFilter,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        conditions, parameters = filters.tournament_conditions()
        where_clause = " AND ".join(conditions) if conditions else "1 = 1"
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT t.tournament_id, t.name, t.game_mode, t.buy_in, t.prize_pool,
                       t.winnings, t.bounty_winnings, t.players_count, t.started_at,
                       t.finished_at, t.position
                FROM tournaments t
                WHERE {where_clause}
                ORDER BY t.started_at DESC, t.id DESC
                LIMIT ? OFFSET ?
                """,
                (*parameters, limit, offset),
            ).fetchall()

        return [self._tournament_row(row) for row in rows]

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
            ,winnings REAL NOT NULL DEFAULT 0
            ,bounty_winnings REAL NOT NULL DEFAULT 0
            ,game_mode TEXT NOT NULL DEFAULT 'TOURNAMENT'
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
            big_blind REAL NOT NULL DEFAULT 0,
            game_mode TEXT NOT NULL DEFAULT 'CASH_GAME',
            session_id INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_mode TEXT NOT NULL,
            table_name TEXT,
            tournament_id TEXT,
            started_at TEXT,
            finished_at TEXT,
            UNIQUE (game_mode, tournament_id),
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
            is_all_in INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (hand_id) REFERENCES hands (hand_id)
        );

        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            imported_at TEXT NOT NULL,
            status TEXT NOT NULL,
            modified_at_ns INTEGER,
            file_size INTEGER,
            import_version INTEGER NOT NULL DEFAULT 0
        );
        """

    @staticmethod
    def _migrate_schema(connection: sqlite3.Connection) -> None:
        Database._add_column_if_missing(connection, "hands", "big_blind", "REAL NOT NULL DEFAULT 0")
        Database._add_column_if_missing(
            connection,
            "hands",
            "game_mode",
            "TEXT NOT NULL DEFAULT 'CASH_GAME'",
        )
        Database._add_column_if_missing(connection, "hands", "session_id", "INTEGER")
        Database._add_column_if_missing(
            connection,
            "actions",
            "is_all_in",
            "INTEGER NOT NULL DEFAULT 0",
        )
        Database._add_column_if_missing(
            connection,
            "tournaments",
            "winnings",
            "REAL NOT NULL DEFAULT 0",
        )
        Database._add_column_if_missing(
            connection,
            "tournaments",
            "bounty_winnings",
            "REAL NOT NULL DEFAULT 0",
        )
        Database._add_column_if_missing(
            connection,
            "tournaments",
            "game_mode",
            "TEXT NOT NULL DEFAULT 'TOURNAMENT'",
        )
        Database._add_column_if_missing(connection, "imports", "modified_at_ns", "INTEGER")
        Database._add_column_if_missing(connection, "imports", "file_size", "INTEGER")
        Database._add_column_if_missing(
            connection,
            "imports",
            "import_version",
            "INTEGER NOT NULL DEFAULT 0",
        )
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_hands_played_at ON hands (played_at);
            CREATE INDEX IF NOT EXISTS idx_hands_tournament_id ON hands (tournament_id);
            CREATE INDEX IF NOT EXISTS idx_hands_session_id ON hands (session_id);
            CREATE INDEX IF NOT EXISTS idx_hands_game_mode ON hands (game_mode);
            CREATE INDEX IF NOT EXISTS idx_hands_table_name ON hands (table_name);
            CREATE INDEX IF NOT EXISTS idx_sessions_game_mode ON sessions (game_mode);
            CREATE INDEX IF NOT EXISTS idx_sessions_tournament_id ON sessions (tournament_id);
            CREATE INDEX IF NOT EXISTS idx_tournaments_game_mode ON tournaments (game_mode);
            """
        )

    @staticmethod
    def _backfill_legacy_game_modes(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            UPDATE tournaments
            SET game_mode = 'EXPRESSO'
            WHERE LOWER(name) LIKE '%expresso%'
            """
        )
        connection.execute(
            """
            UPDATE hands
            SET game_mode = CASE
                WHEN tournament_id IS NULL THEN 'CASH_GAME'
                WHEN LOWER(table_name) LIKE '%expresso%' THEN 'EXPRESSO'
                ELSE 'TOURNAMENT'
            END
            WHERE game_mode IS NULL OR game_mode = 'CASH_GAME'
            """
        )
        connection.execute(
            """
            UPDATE hands
            SET game_mode = 'EXPRESSO'
            WHERE tournament_id IN (
                SELECT tournament_id FROM tournaments WHERE game_mode = 'EXPRESSO'
            )
            """
        )
        connection.execute(
            """
            UPDATE sessions
            SET game_mode = 'EXPRESSO'
            WHERE tournament_id IN (
                SELECT tournament_id FROM tournaments WHERE game_mode = 'EXPRESSO'
            )
            """
        )

    def _backfill_legacy_sessions(self, connection: sqlite3.Connection) -> None:
        tournament_rows = connection.execute(
            """
            SELECT game_mode, tournament_id, MIN(played_at), MAX(played_at)
            FROM hands
            WHERE tournament_id IS NOT NULL AND session_id IS NULL
            GROUP BY game_mode, tournament_id
            """
        ).fetchall()
        for game_mode, tournament_id, started_at, finished_at in tournament_rows:
            connection.execute(
                """
                INSERT INTO sessions (game_mode, tournament_id, started_at, finished_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(game_mode, tournament_id) DO UPDATE SET
                    started_at = MIN(sessions.started_at, excluded.started_at),
                    finished_at = MAX(sessions.finished_at, excluded.finished_at)
                """,
                (game_mode, tournament_id, started_at, finished_at),
            )
            connection.execute(
                """
                UPDATE hands
                SET session_id = (
                    SELECT id FROM sessions
                    WHERE game_mode = hands.game_mode AND tournament_id = hands.tournament_id
                )
                WHERE tournament_id = ? AND game_mode = ? AND session_id IS NULL
                """,
                (tournament_id, game_mode),
            )

        cash_rows = connection.execute(
            """
            SELECT id, game_mode, table_name, played_at
            FROM hands
            WHERE tournament_id IS NULL AND session_id IS NULL
            ORDER BY table_name, played_at, id
            """
        ).fetchall()
        for row in cash_rows:
            hand = Hand(
                hand_id="",
                tournament_id=None,
                played_at=self._parse_datetime(row[3]),
                table_name=row[2],
                hero="",
                hero_cards="",
                board="",
                pot=0.0,
                result=0.0,
                game_mode=GameMode(row[1]),
            )
            session_id = self._find_or_create_cash_session(connection, hand)
            connection.execute("UPDATE hands SET session_id = ? WHERE id = ?", (session_id, row[0]))

    def _assign_tournament_session(self, hand: Hand) -> int:
        if hand.tournament_id is None:
            return self._assign_cash_session(hand)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (game_mode, tournament_id, started_at, finished_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(game_mode, tournament_id) DO UPDATE SET
                    started_at = MIN(sessions.started_at, excluded.started_at),
                    finished_at = MAX(sessions.finished_at, excluded.finished_at)
                """,
                (
                    hand.game_mode.value,
                    hand.tournament_id,
                    self._serialize_datetime(hand.played_at),
                    self._serialize_datetime(hand.played_at),
                ),
            )
            return int(
                connection.execute(
                    "SELECT id FROM sessions WHERE game_mode = ? AND tournament_id = ?",
                    (hand.game_mode.value, hand.tournament_id),
                ).fetchone()[0]
            )

    def _assign_cash_session(self, hand: Hand) -> int:
        with self._connect() as connection:
            return self._find_or_create_cash_session(connection, hand)

    def _find_or_create_cash_session(self, connection: sqlite3.Connection, hand: Hand) -> int:
        played_at = self._serialize_datetime(hand.played_at)
        if played_at is not None:
            row = connection.execute(
                """
                SELECT id FROM sessions
                WHERE game_mode = ? AND tournament_id IS NULL AND table_name = ?
                                    AND julianday(finished_at) >= julianday(?) - (30.0 / 1440.0)
                                    AND julianday(started_at) <= julianday(?) + (30.0 / 1440.0)
                ORDER BY started_at ASC
                LIMIT 1
                """,
                (hand.game_mode.value, hand.table_name, played_at, played_at),
            ).fetchone()
            if row is not None:
                session_id = int(row[0])
                connection.execute(
                    """
                    UPDATE sessions
                    SET started_at = MIN(started_at, ?), finished_at = MAX(finished_at, ?)
                    WHERE id = ?
                    """,
                    (played_at, played_at, session_id),
                )
                return session_id

        cursor = connection.execute(
            """
            INSERT INTO sessions (game_mode, table_name, started_at, finished_at)
            VALUES (?, ?, ?, ?)
            """,
            (hand.game_mode.value, hand.table_name, played_at, played_at),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an ID for the new session")
        return cursor.lastrowid

    def _session_from_row(self, row: sqlite3.Row) -> Session:
        return Session(
            id=int(row["id"]),
            game_mode=GameMode(row["game_mode"]),
            table_name=row["table_name"],
            tournament_id=row["tournament_id"],
            started_at=self._parse_datetime(row["started_at"]),
            finished_at=self._parse_datetime(row["finished_at"]),
        )

    def _hand_row(self, row: sqlite3.Row) -> dict[str, object]:
        return {
            "hand_id": row["hand_id"],
            "tournament_id": row["tournament_id"],
            "session_id": row["session_id"],
            "game_mode": GameMode(row["game_mode"]),
            "played_at": self._parse_datetime(row["played_at"]),
            "table_name": row["table_name"],
            "hero_cards": row["hero_cards"] or "",
            "board": row["board"] or "",
            "pot": float(row["pot"]),
            "result": float(row["result"]),
            "big_blind": float(row["big_blind"]),
        }

    def _tournament_row(self, row: sqlite3.Row) -> dict[str, object]:
        return {
            "tournament_id": row["tournament_id"],
            "name": row["name"],
            "game_mode": GameMode(row["game_mode"]),
            "buy_in": float(row["buy_in"]),
            "prize_pool": float(row["prize_pool"]),
            "winnings": float(row["winnings"]),
            "bounty_winnings": float(row["bounty_winnings"]),
            "profit": float(row["winnings"] + row["bounty_winnings"] - row["buy_in"]),
            "players_count": int(row["players_count"]),
            "started_at": self._parse_datetime(row["started_at"]),
            "finished_at": self._parse_datetime(row["finished_at"]),
            "position": row["position"],
        }

    @staticmethod
    def _add_column_if_missing(
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table_name})")
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            )