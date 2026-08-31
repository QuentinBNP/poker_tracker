from __future__ import annotations

from dataclasses import dataclass

from database.database import Database
from database.filters import HistoryFilter
from game_modes import GameMode

MINIMUM_RATE_SAMPLE = 20


@dataclass(frozen=True, slots=True)
class AdvancedStatistic:
    key: str
    label: str
    value: float
    sample_size: int | None = None
    percent: bool = False


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
        cash_rake_observed = sum(_as_float(hand["rake"]) for hand in cash_hands)
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
            _as_float(tournament["total_entry_cost"])
            for tournament in tournaments
            if tournament["game_mode"] is GameMode.TOURNAMENT
        )
        expresso_buy_ins = sum(
            _as_float(tournament["total_entry_cost"])
            for tournament in tournaments
            if tournament["game_mode"] is GameMode.EXPRESSO
        )
        poker_metrics = _calculate_poker_metrics(actions, hands)

        return {
            "hands_played": hands_played,
            "cash_hands_played": float(len(cash_hands)),
            "cash_result": cash_result,
            "cash_rake_observed": cash_rake_observed,
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

    def calculate_advanced(
        self,
        filters: HistoryFilter | None = None,
    ) -> list[AdvancedStatistic]:
        active_filter = filters or HistoryFilter()
        hands = self.database.list_filtered_hands(
            self.hero_name,
            active_filter,
            limit=1_000_000,
        )
        actions = self.database.list_filtered_actions(active_filter)
        hero_actions = [action for action in actions if action["player"] == self.hero_name]
        cash_hands = [hand for hand in hands if hand["game_mode"] is GameMode.CASH_GAME]
        statistics = self.calculate(active_filter)
        outcomes = _calculate_hand_outcomes(hands, hero_actions)
        preflop_rates = _calculate_preflop_rates(actions, self.hero_name)
        metrics = [
            AdvancedStatistic("hands_won", "Hands won", outcomes["hands_won"]),
            AdvancedStatistic("hands_lost", "Hands lost", outcomes["hands_lost"]),
            AdvancedStatistic("showdown_hands", "Showdown hands", outcomes["showdown_hands"]),
            AdvancedStatistic(
                "non_showdown_hands",
                "Non-showdown hands",
                outcomes["non_showdown_hands"],
            ),
            AdvancedStatistic("all_in_hands", "All-in hands", outcomes["all_in_hands"]),
            AdvancedStatistic("vpip", "VPIP", statistics["vpip"], len(hands), percent=True),
            AdvancedStatistic("pfr", "PFR", statistics["pfr"], len(hands), percent=True),
            AdvancedStatistic(
                "aggression_factor",
                "Aggression factor",
                statistics["aggression_factor"],
            ),
        ]
        if outcomes["all_in_hands"] >= MINIMUM_RATE_SAMPLE:
            metrics.append(
                AdvancedStatistic(
                    "all_in_win_rate",
                    "All-in win rate",
                    _percentage(outcomes["all_in_wins"], outcomes["all_in_hands"]),
                    int(outcomes["all_in_hands"]),
                    percent=True,
                )
            )
        for key, label in (
            ("three_bet", "3-Bet"),
            ("fold_to_three_bet", "Fold to 3-Bet"),
            ("four_bet", "4-Bet"),
            ("fold_to_four_bet", "Fold to 4-Bet"),
        ):
            successes, opportunities = preflop_rates[key]
            if opportunities >= MINIMUM_RATE_SAMPLE:
                metrics.append(
                    AdvancedStatistic(
                        key,
                        label,
                        _percentage(successes, opportunities),
                        opportunities,
                        percent=True,
                    )
                )
        if cash_hands:
            metrics.extend(
                [
                    AdvancedStatistic(
                        "cash_rake_observed",
                        "Observed table rake",
                        statistics["cash_rake_observed"],
                    ),
                    AdvancedStatistic("cash_bb", "BB won", statistics["cash_bb"]),
                    AdvancedStatistic(
                        "cash_bb_per_100",
                        "BB / 100",
                        statistics["cash_bb_per_100"],
                    ),
                ]
            )
        return metrics


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


def _calculate_hand_outcomes(
    hands: list[dict[str, object]],
    hero_actions: list[dict[str, object]],
) -> dict[str, float]:
    showdown_hands = {
        str(action["hand_id"])
        for action in hero_actions
        if action["action"] == "SHOW"
    }
    all_in_hands = {
        str(action["hand_id"])
        for action in hero_actions
        if bool(action.get("is_all_in"))
    }
    hands_by_id = {str(hand["hand_id"]): hand for hand in hands}
    hands_won = sum(1 for hand in hands if _as_float(hand["result"]) > 0)
    hands_lost = sum(1 for hand in hands if _as_float(hand["result"]) < 0)
    return {
        "hands_won": float(hands_won),
        "hands_lost": float(hands_lost),
        "showdown_hands": float(len(showdown_hands)),
        "non_showdown_hands": float(len(hands) - len(showdown_hands)),
        "all_in_hands": float(len(all_in_hands)),
        "all_in_wins": float(
            sum(1 for hand_id in all_in_hands if _as_float(hands_by_id[hand_id]["result"]) > 0)
        ),
    }


def _calculate_preflop_rates(
    actions: list[dict[str, object]],
    hero_name: str,
) -> dict[str, tuple[int, int]]:
    grouped_actions: dict[str, list[dict[str, object]]] = {}
    for action in actions:
        if action["street"] == "PRE_FLOP":
            grouped_actions.setdefault(str(action["hand_id"]), []).append(action)

    results = {
        "three_bet": [0, 0],
        "fold_to_three_bet": [0, 0],
        "four_bet": [0, 0],
        "fold_to_four_bet": [0, 0],
    }
    for hand_actions in grouped_actions.values():
        raises = 0
        hero_raise_level: int | None = None
        for action in hand_actions:
            player = str(action["player"])
            action_name = str(action["action"])
            if player == hero_name and action_name in {"FOLD", "CALL", "RAISE"}:
                if raises == 1:
                    results["three_bet"][1] += 1
                    if action_name == "RAISE":
                        results["three_bet"][0] += 1
                        hero_raise_level = 2
                elif raises == 2 and hero_raise_level == 1:
                    results["fold_to_three_bet"][1] += 1
                    if action_name == "FOLD":
                        results["fold_to_three_bet"][0] += 1
                    results["four_bet"][1] += 1
                    if action_name == "RAISE":
                        results["four_bet"][0] += 1
                        hero_raise_level = 3
                elif raises == 3 and hero_raise_level == 2:
                    results["fold_to_four_bet"][1] += 1
                    if action_name == "FOLD":
                        results["fold_to_four_bet"][0] += 1
            if action_name == "RAISE":
                raises += 1
                if player == hero_name:
                    hero_raise_level = raises
    return {key: (values[0], values[1]) for key, values in results.items()}


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