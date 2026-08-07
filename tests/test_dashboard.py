from __future__ import annotations

from datetime import datetime, timezone

from ui.bankroll_chart import _chart_bounds, _scale_x, _scale_y
from ui.dashboard import _resolve_period


def test_custom_period_uses_inclusive_utc_day_boundaries() -> None:
    start_at, end_at, message = _resolve_period("Custom", "2026-06-01", "2026-06-30")

    assert start_at == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert end_at == datetime(2026, 6, 30, 23, 59, 59, 999999, tzinfo=timezone.utc)
    assert message == "Custom period"


def test_custom_period_reports_invalid_dates_without_applying_a_filter() -> None:
    start_at, end_at, message = _resolve_period("Custom", "2026/06/01", "2026-06-30")

    assert start_at is None
    assert end_at is None
    assert message == "Use YYYY-MM-DD for custom dates"


def test_bankroll_chart_scaling_keeps_zero_and_single_points_visible() -> None:
    minimum, maximum = _chart_bounds([0.0])

    assert (minimum, maximum) == (-1.0, 1.0)
    assert _scale_x(0, 1, 50, 250) == 150.0
    assert _scale_y(0.0, minimum, maximum, 20, 180) == 100.0