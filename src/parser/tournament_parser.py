from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from game_modes import GameMode, classify_game_mode

SUMMARY_HEADER_PATTERN = re.compile(
    r"^Winamax Poker - Tournament summary : (?P<name>.+?)\((?P<tournament_id>\d+)\)",
    re.MULTILINE,
)


def parse_tournament_summary(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}

    header_match = SUMMARY_HEADER_PATTERN.search(text)
    if header_match is None:
        return {}

    player_name = _search_value(text, r"^Player : (?P<value>.+)$")
    buy_in_text = _search_value(text, r"^Buy-In : (?P<value>.+)$")
    prize_pool_text = _search_value(text, r"^Prizepool : (?P<value>.+)$")
    started_at_text = _search_value(text, r"^Tournament started (?P<value>.+)$")
    duration_text = _search_value(text, r"^You played (?P<value>.+)$")
    position_text = _search_value(text, r"^You finished in (?P<value>\d+)(?:st|nd|rd|th) place$")
    winnings_text = _search_value(text, r"^You won (?P<value>.+)$")

    name = header_match.group("name").strip()
    mode = _search_value(text, r"^Mode : (?P<value>.+)$")
    tournament_type = _search_value(text, r"^Type : (?P<value>.+)$")
    return {
        "tournament_id": header_match.group("tournament_id"),
        "name": name,
        "game_mode": classify_game_mode((name, mode, tournament_type), GameMode.TOURNAMENT),
        "player_name": player_name,
        "buy_in": _sum_money_parts(buy_in_text),
        "buy_in_components": _parse_money_parts(buy_in_text),
        "prize_pool": _parse_amount(prize_pool_text),
        "players_count": _parse_int(_search_value(text, r"^Registered players : (?P<value>\d+)$")),
        "started_at": _parse_datetime(started_at_text),
        "duration_seconds": _parse_duration_seconds(duration_text),
        "position": _parse_int(position_text),
        "mode": mode,
        "type": tournament_type,
        "speed": _search_value(text, r"^Speed : (?P<value>.+)$"),
        "winnings": _parse_primary_winnings(winnings_text),
        "bounty_winnings": _parse_bounty_winnings(winnings_text),
    }


def _search_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        return None

    return match.group("value").strip()


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    return datetime.strptime(value, "%Y/%m/%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)


def _parse_duration_seconds(value: str | None) -> int | None:
    if value is None:
        return None

    hours_match = re.search(r"(?P<hours>\d+)h", value)
    minutes_match = re.search(r"(?P<minutes>\d+)min", value)
    seconds_match = re.search(r"(?P<seconds>\d+)s", value)

    hours = int(hours_match.group("hours")) if hours_match else 0
    minutes = int(minutes_match.group("minutes")) if minutes_match else 0
    seconds = int(seconds_match.group("seconds")) if seconds_match else 0
    return hours * 3600 + minutes * 60 + seconds


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None

    return int(value)


def _parse_amount(value: str | None) -> float | None:
    if value is None:
        return None

    normalized = value.replace("€", "").replace(",", ".").strip()
    return float(normalized)


def _parse_money_parts(value: str | None) -> list[float]:
    if value is None:
        return []

    parts: list[float] = []
    for part in re.split(r"\s*\+\s*", value):
        if not part.strip():
            continue

        parsed_amount = _parse_amount(part)
        if parsed_amount is not None:
            parts.append(parsed_amount)

    return parts


def _sum_money_parts(value: str | None) -> float:
    return float(sum(part for part in _parse_money_parts(value) if part is not None))


def _parse_primary_winnings(value: str | None) -> float | None:
    if value is None:
        return None

    primary, *_ = value.split(" + Bounty ", maxsplit=1)
    return _parse_amount(primary)


def _parse_bounty_winnings(value: str | None) -> float:
    if value is None or " + Bounty " not in value:
        return 0.0

    _, bounty = value.split(" + Bounty ", maxsplit=1)
    parsed_bounty = _parse_amount(bounty)
    return parsed_bounty or 0.0