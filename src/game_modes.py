from enum import StrEnum
from typing import Iterable


class GameMode(StrEnum):
    CASH_GAME = "CASH_GAME"
    TOURNAMENT = "TOURNAMENT"
    EXPRESSO = "EXPRESSO"


def classify_game_mode(values: Iterable[str | None], default: GameMode) -> GameMode:
    normalized_values = " ".join(value or "" for value in values).casefold()
    if "expresso" in normalized_values:
        return GameMode.EXPRESSO
    if "cashgame" in normalized_values or "cash game" in normalized_values:
        return GameMode.CASH_GAME
    return default