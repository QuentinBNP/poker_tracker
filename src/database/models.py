from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from game_modes import GameMode


@dataclass(slots=True)
class Tournament:
    tournament_id: str
    name: str
    buy_in: float
    prize_pool: float
    players_count: int
    started_at: datetime | None
    finished_at: datetime | None
    position: int | None
    winnings: float = 0.0
    bounty_winnings: float = 0.0
    game_mode: GameMode = GameMode.TOURNAMENT


@dataclass(slots=True)
class Hand:
    hand_id: str
    tournament_id: str | None
    played_at: datetime | None
    table_name: str
    hero: str
    hero_cards: str
    board: str
    pot: float
    result: float
    big_blind: float = 0.0
    game_mode: GameMode = GameMode.CASH_GAME
    session_id: int | None = None


@dataclass(slots=True)
class Session:
    id: int | None
    game_mode: GameMode
    table_name: str | None
    tournament_id: str | None
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(slots=True)
class Player:
    name: str


@dataclass(slots=True)
class Action:
    hand_id: str
    player: str
    street: str
    action: str
    amount: float | None
    is_all_in: bool = False


@dataclass(slots=True)
class ImportRecord:
    filename: str
    imported_at: datetime
    status: str
    modified_at_ns: int | None = None
    file_size: int | None = None
    import_version: int = 0