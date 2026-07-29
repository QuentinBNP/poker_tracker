from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from parser.hand_parser import parse_hand_history
from parser.tournament_parser import parse_tournament_summary

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def test_parse_freeroll_tournament_summary() -> None:
    text = (
        SAMPLES_DIR / "20260628_Freeroll(1119027769)_real_holdem_no-limit_summary.txt"
    ).read_text(
        encoding="utf-8"
    )

    parsed = parse_tournament_summary(text)

    assert parsed["tournament_id"] == "1119027769"
    assert parsed["name"] == "Freeroll"
    assert parsed["player_name"] == "MyPseudo"
    assert parsed["buy_in"] == 0.0
    assert parsed["prize_pool"] == 150.0
    assert parsed["players_count"] == 6564
    assert parsed["started_at"] == datetime(2026, 6, 28, 16, 30, 2, tzinfo=timezone.utc)
    assert parsed["duration_seconds"] == 1203
    assert parsed["position"] == 3925
    assert parsed["winnings"] is None


def test_parse_knockout_tournament_summary_with_bounty() -> None:
    text = (
        SAMPLES_DIR
        / "20260628_Kill The Fish(1119034571)_real_holdem_no-limit_summary.txt"
    ).read_text(
        encoding="utf-8"
    )

    parsed = parse_tournament_summary(text)

    assert parsed["tournament_id"] == "1119034571"
    assert parsed["name"] == "Kill The Fish"
    assert parsed["buy_in"] == 0.25
    assert parsed["prize_pool"] == 73.26
    assert parsed["position"] == 63
    assert parsed["winnings"] == 0.24
    assert parsed["bounty_winnings"] == 0.20


def test_parse_tournament_hand_history_extracts_core_fields() -> None:
    text = (SAMPLES_DIR / "20260628_Freeroll(1119027769)_real_holdem_no-limit.txt").read_text(
        encoding="utf-8"
    )

    hands = parse_hand_history(text)

    assert len(hands) >= 4
    first_hand = hands[0]
    third_hand = hands[2]

    assert first_hand["hand_id"] == "#4806187671170843057-9-1782664923"
    assert first_hand["game_type"] == "tournament"
    assert first_hand["tournament_id"] == "1119027769"
    assert first_hand["table_name"] == "Freeroll(1119027769)#0432"
    assert first_hand["hero"] == "MyPseudo"
    assert first_hand["hero_cards"] == "8h 2s"
    assert first_hand["board"] == "Kc 7s 3c"
    assert first_hand["pot"] == 20225.0
    assert first_hand["result"] == 0.0
    assert first_hand["winners"] == ["Nelson71"]
    assert any(action["action"] == "POST_BIG_BLIND" for action in first_hand["actions"]) is False
    assert any(
        action["action"] == "FOLD" and action["player"] == "MyPseudo"
        for action in first_hand["actions"]
    )

    assert third_hand["hero_cards"] == "Jh Ah"
    assert third_hand["board"] == "2s 9c Qh Td Tc"
    assert third_hand["pot"] == 3226.0
    assert any(
        action["action"] == "RAISE" and action["player"] == "MyPseudo"
        for action in third_hand["actions"]
    )


def test_parse_cash_game_hand_history_supports_decimal_amounts() -> None:
    text = (SAMPLES_DIR / "20260628_Nice 23_real_holdem_no-limit.txt").read_text(
        encoding="utf-8"
    )

    hands = parse_hand_history(text)

    first_hand = hands[0]
    second_hand = hands[1]

    assert first_hand["game_type"] == "cashgame"
    assert first_hand["tournament_id"] is None
    assert first_hand["table_name"] == "Nice 23"
    assert first_hand["pot"] == 1.36
    assert first_hand["board"] == "Qd Ad 5d 4d"
    assert second_hand["hero"] == "MyPseudo"
    assert second_hand["hero_cards"] == "Ac 8d"
    assert any(
        action["amount"] == 0.12
        for action in second_hand["actions"]
        if action["action"] == "RAISE"
    )