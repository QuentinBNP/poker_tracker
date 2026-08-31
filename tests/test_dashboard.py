from __future__ import annotations

from datetime import datetime, timezone

from game_modes import GameMode
from poker_stats.bankroll_service import BankrollPoint, BankrollSourceType
from poker_stats.bb_history_service import BBHistoryPoint
from ui.bb_chart import BBChart
from ui.bb_chart import _detail_text as bb_detail_text
from ui.chart_math import chart_bounds, sampled_indices, scale_x, scale_y
from ui.dashboard import _resolve_period
from ui.result_chart import _detail_text as result_detail_text


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
    minimum, maximum = chart_bounds([0.0])

    assert (minimum, maximum) == (-1.0, 1.0)
    assert scale_x(0, 1, 50, 250) == 150.0
    assert scale_y(0.0, minimum, maximum, 20, 180) == 100.0


def test_chart_sampling_preserves_boundaries_and_extrema() -> None:
    values = [float(index) for index in range(2_000)]
    values[777] = -1_000.0
    values[1_555] = 3_000.0

    indexes = sampled_indices(values, 1_200)

    assert len(indexes) == 1_200
    assert indexes == sorted(set(indexes))
    assert {0, 777, 1_555, 1_999}.issubset(indexes)


def test_bb_chart_sampling_retains_global_source_indexes() -> None:
    occurred_at = datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc)
    points = [
        BBHistoryPoint(str(index), occurred_at, 1.0, float(index), 1.0, "As Ks")
        for index in range(2_000)
    ]

    rendered = BBChart._render_points(points, 400, 1_900)

    assert len(rendered) == BBChart.MAX_RENDERED_POINTS
    assert rendered[0] == (400, points[400])
    assert rendered[-1] == (1_899, points[1_899])


def test_chart_hover_details_label_utc_and_units() -> None:
    occurred_at = datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc)
    bb_point = BBHistoryPoint("42", occurred_at, 2.5, 7.5, 1.25, "As Ks")
    result_point = BankrollPoint(
        occurred_at=occurred_at,
        balance=-0.87,
        result=0.13,
        game_mode=GameMode.TOURNAMENT,
        source_type=BankrollSourceType.TOURNAMENT,
        source_id="1140932862",
        tournament_id="1140932862",
    )

    assert "2026-06-28 12:00 UTC" in bb_detail_text(bb_point)
    assert "+2.50 BB" in bb_detail_text(bb_point)
    assert "2026-06-28 12:00 UTC" in result_detail_text(result_point)
    assert "Settlement 1140932862" in result_detail_text(result_point)
    assert "+0.13 EUR  Total -0.87 EUR" in result_detail_text(result_point)