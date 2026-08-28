from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

CONTRACT_PATH = Path(__file__).parent / "fixtures" / "accounting_contract.json"
CONTRACT: dict[str, Any] = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", CONTRACT["scenarios"], ids=lambda item: str(item["id"]))
def test_accounting_scenario_has_expected_eur_profit(scenario: dict[str, Any]) -> None:
    actual_profit = sum(
        (Decimal(event["amount_eur"]) for event in scenario["events"]),
        start=Decimal("0.00"),
    )

    assert actual_profit == Decimal(scenario["expected_profit_eur"])


@pytest.mark.parametrize("scenario", CONTRACT["scenarios"], ids=lambda item: str(item["id"]))
def test_entry_cost_contract_prevents_ticket_double_charging(scenario: dict[str, Any]) -> None:
    for entry in scenario["entries"]:
        nominal_buy_in = Decimal(entry["nominal_buy_in_eur"])
        cash_cost = Decimal(entry["cash_cost_eur"])
        payment_method = entry["payment_method"]

        if payment_method in {"TICKET", "FREE_TICKET"}:
            assert cash_cost == Decimal("0.00")
        else:
            assert cash_cost == nominal_buy_in


def test_reentries_have_sequential_entry_numbers() -> None:
    for scenario in CONTRACT["scenarios"]:
        assert [entry["entry_number"] for entry in scenario["entries"]] == list(
            range(1, len(scenario["entries"]) + 1)
        )


def test_timestamp_contract_preserves_parsed_utc_wall_clock() -> None:
    timestamp_policy = CONTRACT["timestamp_policy"]
    parsed = datetime.fromisoformat(timestamp_policy["parsed"])

    assert parsed.tzinfo is timezone.utc
    assert parsed.strftime("%Y-%m-%d %H:%M UTC") == timestamp_policy["display"]