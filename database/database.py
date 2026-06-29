from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(self._schema())
            connection.commit()

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