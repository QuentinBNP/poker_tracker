from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

HAND_SPLIT_PATTERN = re.compile(r"\n{2,}(?=Winamax Poker - )")
SEAT_PATTERN = re.compile(r"^Seat (?P<seat>\d+): (?P<name>.+?) \((?P<details>.+)\)$")
ACTION_AMOUNT_PATTERN = re.compile(r"(?P<amount>\d+(?:[.,]\d+)?)€?")


def parse_hand_history(text: str) -> list[dict[str, Any]]:
    if not text.strip():
        return []

    hands: list[dict[str, Any]] = []

    for hand_text in HAND_SPLIT_PATTERN.split(text.strip()):
        parsed_hand = _parse_single_hand(hand_text)
        if parsed_hand:
            hands.append(parsed_hand)

    return hands


def _parse_single_hand(hand_text: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in hand_text.splitlines() if line.strip()]
    if not lines:
        return {}

    header = lines[0]
    table_line = next((line for line in lines if line.startswith("Table:")), "")
    hero_line = next((line for line in lines if line.startswith("Dealt to ")), "")
    summary_index = next(
        (index for index, line in enumerate(lines) if line == "*** SUMMARY ***"),
        len(lines),
    )
    summary_lines = lines[summary_index + 1 :]

    parsed_header = _parse_header(header)
    hero_name, hero_cards = _parse_hero_line(hero_line)
    players = _parse_players(lines, table_line)
    all_actions = _parse_actions(lines)
    actions = [
        action
        for action in all_actions
        if action["action"] not in {"POST_ANTE", "POST_SMALL_BLIND", "POST_BIG_BLIND"}
    ]
    board = _extract_board(lines, summary_lines)
    winners = _parse_winners(summary_lines)
    hero_result = _calculate_hero_net_result(all_actions, summary_lines, hero_name)
    table_name = _parse_table_name(table_line)
    tournament_id = parsed_header["tournament_id"] or _parse_tournament_id_from_table_name(
        table_name
    )

    return {
        **parsed_header,
        "tournament_id": tournament_id,
        "table_name": table_name,
        "hero": hero_name,
        "hero_cards": hero_cards,
        "board": board,
        "players": players,
        "actions": actions,
        "pot": _parse_total_pot(summary_lines),
        "result": hero_result,
        "winners": winners,
    }


def _parse_header(header: str) -> dict[str, Any]:
    hand_id_match = re.search(r"HandId: (?P<hand_id>#.+?) - Holdem no limit", header)
    played_at_match = re.search(
        r"- (?P<played_at>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} UTC)$",
        header,
    )
    buy_in_match = re.search(r"buyIn: (?P<buy_in>.+?) level:", header)
    tournament_name_match = re.search(r'^Winamax Poker - Tournament "(?P<name>.+?)"', header)
    tournament_id_match = re.search(r"\((?P<tournament_id>\d+)\)", header)
    game_type = "tournament" if tournament_name_match else "cashgame"
    blind_match = re.search(r"Holdem no limit \((?P<blinds>[^)]+)\)", header)

    return {
        "hand_id": hand_id_match.group("hand_id") if hand_id_match else "",
        "game_type": game_type,
        "tournament_name": (
            tournament_name_match.group("name") if tournament_name_match else None
        ),
        "tournament_id": (
            tournament_id_match.group("tournament_id") if tournament_id_match else None
        ),
        "buy_in": _sum_money_parts(buy_in_match.group("buy_in")) if buy_in_match else None,
        "big_blind": _parse_big_blind(blind_match.group("blinds")) if blind_match else 0.0,
        "played_at": (
            _parse_datetime(played_at_match.group("played_at"))
            if played_at_match
            else None
        ),
    }


def _parse_hero_line(line: str) -> tuple[str, str]:
    match = re.match(r"^Dealt to (?P<hero>.+?) \[(?P<cards>[^\]]+)\]$", line)
    if match is None:
        return "", ""

    return match.group("hero"), match.group("cards")


def _parse_table_name(line: str) -> str:
    match = re.search(r"Table: '(?P<table_name>[^']+)'", line)
    if match is None:
        return ""

    return match.group("table_name")


def _parse_tournament_id_from_table_name(table_name: str) -> str | None:
    match = re.search(r"\((?P<tournament_id>\d+)\)", table_name)
    if match is None:
        return None

    return match.group("tournament_id")


def _parse_players(lines: list[str], table_line: str) -> list[dict[str, Any]]:
    button_seat_match = re.search(r"Seat #(?P<button_seat>\d+) is the button", table_line)
    button_seat = int(button_seat_match.group("button_seat")) if button_seat_match else None
    players: list[dict[str, Any]] = []

    for line in lines:
        match = SEAT_PATTERN.match(line)
        if match is None:
            continue

        details = match.group("details")
        parts = [part.strip() for part in details.split(",")]
        stack = _parse_amount(parts[0])
        bounty = None
        if len(parts) > 1:
            bounty_match = re.search(r"(?P<bounty>\d+(?:[.,]\d+)?)€ bounty", parts[1])
            if bounty_match:
                bounty = float(bounty_match.group("bounty").replace(",", "."))

        seat_number = int(match.group("seat"))
        players.append(
            {
                "seat": seat_number,
                "name": match.group("name"),
                "stack": stack,
                "bounty": bounty,
                "is_button": seat_number == button_seat,
            }
        )

    return players


def _parse_actions(lines: list[str]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    street = ""
    ignored_actions = {"POST_ANTE", "POST_SMALL_BLIND", "POST_BIG_BLIND"}

    for line in lines:
        if line.startswith("*** ANTE/BLINDS ***"):
            street = "ANTE_BLINDS"
            continue
        if line.startswith("*** PRE-FLOP"):
            street = "PRE_FLOP"
            continue
        if line.startswith("*** FLOP"):
            street = "FLOP"
            continue
        if line.startswith("*** TURN"):
            street = "TURN"
            continue
        if line.startswith("*** RIVER"):
            street = "RIVER"
            continue
        if line.startswith("*** SHOW DOWN ***"):
            street = "SHOW_DOWN"
            continue
        if (
            line.startswith("*** SUMMARY ***")
            or line.startswith("Seat ")
            or line.startswith("Table:")
        ):
            continue
        if line.startswith("Winamax Poker -") or line.startswith("Dealt to ") or not street:
            continue

        parsed_action = _parse_action_line(line, street)
        if parsed_action is not None:
            if parsed_action["action"] in ignored_actions:
                continue
            actions.append(parsed_action)

    return actions


def _parse_action_line(line: str, street: str) -> dict[str, Any] | None:
    patterns: list[tuple[str, str]] = [
        (r"^(?P<player>.+?) posts ante (?P<amount>.+?)(?: out of position)?$", "POST_ANTE"),
        (
            r"^(?P<player>.+?) posts small blind (?P<amount>.+?)(?: out of position)?$",
            "POST_SMALL_BLIND",
        ),
        (
            r"^(?P<player>.+?) posts big blind (?P<amount>.+?)(?: out of position)?$",
            "POST_BIG_BLIND",
        ),
        (r"^(?P<player>.+?) folds$", "FOLD"),
        (r"^(?P<player>.+?) checks$", "CHECK"),
        (r"^(?P<player>.+?) calls (?P<amount>.+?)$", "CALL"),
        (r"^(?P<player>.+?) bets (?P<amount>.+?)(?: and is all-in)?$", "BET"),
        (
            r"^(?P<player>.+?) raises (?P<amount>.+?) to (?P<to_amount>.+?)(?: and is all-in)?$",
            "RAISE",
        ),
        (
            r"^(?P<player>.+?) collected (?P<amount>.+?) from (?:side pot \d+|main pot|pot)$",
            "COLLECT",
        ),
        (r"^(?P<player>.+?) shows \[(?P<cards>[^\]]+)\] \((?P<description>.+)\)$", "SHOW"),
    ]

    for pattern, action_name in patterns:
        match = re.match(pattern, line)
        if match is None:
            continue

        amount_source = match.groupdict().get("to_amount") or match.groupdict().get("amount")
        action: dict[str, Any] = {
            "player": match.group("player"),
            "street": street,
            "action": action_name,
            "amount": _parse_amount(amount_source),
        }

        if "cards" in match.groupdict():
            action["cards"] = match.group("cards")
        if "description" in match.groupdict():
            action["description"] = match.group("description")
        if "all-in" in line:
            action["is_all_in"] = True

        return action

    return None


def _extract_board(lines: list[str], summary_lines: list[str]) -> str:
    for line in summary_lines:
        match = re.match(r"^Board: \[(?P<board>[^\]]+)\]$", line)
        if match:
            return match.group("board")

    board = ""
    for line in lines:
        street_board_match = re.match(r"^\*\*\* (?:FLOP|TURN|RIVER) \*\*\* (.+)$", line)
        if street_board_match:
            board = street_board_match.group(1).replace("][", " ").replace("[", "").replace("]", "")

    return board


def _parse_total_pot(summary_lines: list[str]) -> float:
    for line in summary_lines:
        match = re.match(r"^Total pot (?P<pot>.+?) \|", line)
        if match:
            amount = _parse_amount(match.group("pot"))
            return amount or 0.0

    return 0.0


def _parse_winners(summary_lines: list[str]) -> list[str]:
    winners: list[str] = []
    for line in summary_lines:
        if not line.startswith("Seat ") or " won " not in line:
            continue

        winner_match = re.match(
            r"^Seat \d+: (?P<name>.+?)(?: \([^)]+\))?(?: showed \[[^\]]+\] and)? won ",
            line,
        )
        if winner_match:
            winners.append(winner_match.group("name"))

    return winners


def _calculate_hero_net_result(
    actions: list[dict[str, Any]],
    summary_lines: list[str],
    hero_name: str,
) -> float:
    contributions = 0.0
    collected = 0.0
    committed_by_street: dict[str, float] = {}

    for action in actions:
        if action["player"] != hero_name:
            continue

        action_name = action["action"]
        amount = float(action.get("amount") or 0.0)
        street = "PRE_FLOP" if action["street"] == "ANTE_BLINDS" else action["street"]
        committed = committed_by_street.get(street, 0.0)

        if action_name in {"POST_ANTE", "POST_SMALL_BLIND", "POST_BIG_BLIND", "CALL", "BET"}:
            contributions += amount
            committed_by_street[street] = committed + amount
        elif action_name == "RAISE":
            contribution = max(0.0, amount - committed)
            contributions += contribution
            committed_by_street[street] = max(committed, amount)
        elif action_name == "COLLECT":
            collected += amount

    if collected == 0.0:
        collected = _parse_hero_collected(summary_lines, hero_name)

    return collected - contributions


def _parse_hero_collected(summary_lines: list[str], hero_name: str) -> float:
    if not hero_name:
        return 0.0

    hero_pattern = re.compile(
        rf"^Seat \d+: {re.escape(hero_name)}(?: \([^)]+\))?(?: showed \[[^\]]+\] and)? "
        rf"(?P<outcome>won|lost)(?: (?P<amount>.+?))?(?: with .+)?$"
    )
    for line in summary_lines:
        match = hero_pattern.match(line)
        if match is None:
            continue

        if match.group("outcome") == "won":
            return _parse_amount(match.group("amount")) or 0.0

        return 0.0

    return 0.0


def _parse_big_blind(value: str) -> float:
    amounts = [_parse_amount(part) for part in value.split("/")]
    parsed_amounts = [amount for amount in amounts if amount is not None]
    return parsed_amounts[-1] if parsed_amounts else 0.0


def _parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y/%m/%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)


def _parse_amount(value: str | None) -> float | None:
    if value is None:
        return None

    match = ACTION_AMOUNT_PATTERN.search(value)
    if match is None:
        return None

    return float(match.group("amount").replace(",", "."))


def _sum_money_parts(value: str | None) -> float:
    if value is None:
        return 0.0

    return sum(
        parsed_amount
        for parsed_amount in (_parse_amount(part) for part in re.split(r"\s*\+\s*", value))
        if parsed_amount is not None
    )