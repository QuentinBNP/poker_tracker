from __future__ import annotations

from database.database import Database
from database.filters import HistoryFilter
from game_modes import GameMode


class StatisticsService:
    def __init__(self, database: Database, hero_name: str) -> None:
        self.database = database
        self.hero_name = hero_name

    def calculate(self, filters: HistoryFilter | None = None) -> dict[str, float]:
        active_filter = filters or HistoryFilter()
        hands = self.database.list_filtered_hands(self.hero_name, active_filter, limit=1_000_000)
        actions = self.database.list_filtered_hero_actions(self.hero_name, active_filter)
        tournaments = self.database.list_filtered_tournaments(active_filter, limit=1_000_000)

        hands_played = float(len(hands))
        cash_hands = [hand for hand in hands if hand["game_mode"] is GameMode.CASH_GAME]
        cash_result = sum(_as_float(hand["result"]) for hand in cash_hands)
        cash_bb = sum(
            _as_float(hand["result"]) / _as_float(hand["big_blind"])
            for hand in cash_hands
            if _as_float(hand["big_blind"]) > 0
        )
        tournament_profit = sum(
            _as_float(tournament["profit"])
            for tournament in tournaments
            if tournament["game_mode"] is GameMode.TOURNAMENT
        )
        expresso_profit = sum(
            _as_float(tournament["profit"])
            for tournament in tournaments
            if tournament["game_mode"] is GameMode.EXPRESSO
        )
        tournament_buy_ins = sum(
            _as_float(tournament["buy_in"])
            for tournament in tournaments
            if tournament["game_mode"] is GameMode.TOURNAMENT
        )
        expresso_buy_ins = sum(
            _as_float(tournament["buy_in"])
            for tournament in tournaments
            if tournament["game_mode"] is GameMode.EXPRESSO
        )
        poker_metrics = _calculate_poker_metrics(actions, hands)

        return {
            "hands_played": hands_played,
            "cash_hands_played": float(len(cash_hands)),
            "cash_result": cash_result,
            "cash_bb": cash_bb,
            "cash_bb_per_100": (cash_bb / len(cash_hands)) * 100 if cash_hands else 0.0,
            "tournaments_played": float(
                sum(
                    1
                    for tournament in tournaments
                    if tournament["game_mode"] is GameMode.TOURNAMENT
                )
            ),
            "tournament_profit": tournament_profit,
            "tournament_roi": _percentage(tournament_profit, tournament_buy_ins),
            "expressos_played": float(
                sum(1 for tournament in tournaments if tournament["game_mode"] is GameMode.EXPRESSO)
            ),
            "expresso_profit": expresso_profit,
            "expresso_roi": _percentage(expresso_profit, expresso_buy_ins),
            "total_profit": cash_result + tournament_profit + expresso_profit,
            **poker_metrics,
        }


def _calculate_poker_metrics(
    actions: list[dict[str, object]], hands: list[dict[str, object]]
) -> dict[str, float]:
    preflop_actions_by_hand: dict[str, set[str]] = {}
    postflop_actions: list[str] = []
    showdown_hands: set[str] = set()
    hands_by_id = {str(hand["hand_id"]): hand for hand in hands}

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
    bets_and_raises = sum(1 for action_name in postflop_actions if action_name in {"BET", "RAISE"})
    calls = sum(1 for action_name in postflop_actions if action_name == "CALL")
    showdown_wins = sum(
        1
        for hand_id in showdown_hands
        if _as_float(hands_by_id.get(hand_id, {}).get("result")) > 0
    )
    hands_played = float(len(hands))

    return {
        "vpip": _percentage(vpip_hands, hands_played),
        "pfr": _percentage(pfr_hands, hands_played),
        "limp_percentage": _percentage(limp_hands, hands_played),
        "aggression_factor": float(bets_and_raises) / calls if calls else float(bets_and_raises),
        "showdown_win_percentage": _percentage(showdown_wins, float(len(showdown_hands))),
    }


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _percentage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return (numerator / denominator) * 100.0