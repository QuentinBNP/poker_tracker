from __future__ import annotations

from database.database import Database


class StatisticsCalculator:
    def __init__(self, database: Database, hero_name: str) -> None:
        self.database = database
        self.hero_name = hero_name

    def calculate(self) -> dict[str, float]:
        summary = self.database.get_hero_summary(self.hero_name)
        recent_hands = self.database.list_recent_hands(self.hero_name, limit=500)
        actions = self.database.list_hero_actions(self.hero_name)

        hands_played = float(summary["hands_played"])
        preflop_actions_by_hand: dict[str, set[str]] = {}
        postflop_actions: list[str] = []
        showdown_hands: set[str] = set()
        showdown_wins = 0

        for action in actions:
            hand_id = str(action["hand_id"])
            action_name = str(action["action"])
            street = str(action["street"])

            if street == "PRE_FLOP":
                preflop_actions_by_hand.setdefault(hand_id, set()).add(action_name)
            elif street in {"FLOP", "TURN", "RIVER"}:
                postflop_actions.append(action_name)
            elif street == "SHOW_DOWN" and action_name == "SHOW":
                showdown_hands.add(hand_id)

        recent_hands_by_id = {str(hand["hand_id"]): hand for hand in recent_hands}
        for hand_id in showdown_hands:
            hand = recent_hands_by_id.get(hand_id)
            if hand and _as_float(hand.get("result")) > 0:
                showdown_wins += 1

        vpip_hands = sum(
            1
            for action_names in preflop_actions_by_hand.values()
            if action_names & {"CALL", "RAISE", "BET"}
        )
        pfr_hands = sum(
            1 for action_names in preflop_actions_by_hand.values() if "RAISE" in action_names
        )
        limp_hands = sum(
            1
            for action_names in preflop_actions_by_hand.values()
            if "CALL" in action_names and "RAISE" not in action_names
        )
        bets_and_raises = sum(
            1 for action_name in postflop_actions if action_name in {"BET", "RAISE"}
        )
        calls = sum(1 for action_name in postflop_actions if action_name == "CALL")

        return {
            "hands_played": hands_played,
            "tournaments_played": float(summary["tournaments_played"]),
            "chip_result_bb": float(summary["chip_result_bb"]),
            "cash_result": float(summary["cash_result"]),
            "tournament_profit": float(summary["tournament_profit"]),
            "money_result": float(summary["money_result"]),
            "vpip": _percentage(vpip_hands, hands_played),
            "pfr": _percentage(pfr_hands, hands_played),
            "limp_percentage": _percentage(limp_hands, hands_played),
            "aggression_factor": (
                float(bets_and_raises) / float(calls)
                if calls
                else float(bets_and_raises)
            ),
            "showdown_win_percentage": _percentage(showdown_wins, float(len(showdown_hands))),
        }


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _percentage(numerator: int, denominator: float) -> float:
    if denominator <= 0:
        return 0.0

    return (float(numerator) / denominator) * 100.0