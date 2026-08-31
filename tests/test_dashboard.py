from __future__ import annotations

from datetime import datetime, timezone

from game_modes import GameMode
from poker_stats.bankroll_service import BankrollPoint, BankrollSourceType
from poker_stats.bb_history_service import BBHistoryPoint
from ui.bb_chart import BBChart
from ui.bb_chart import _detail_text as bb_detail_text
from ui.chart_math import chart_bounds, sampled_indices, scale_x, scale_y
from ui.dashboard import _dashboard_metrics, _resolve_period
from ui.result_chart import _detail_text as result_detail_text
from ui.sessions_view import _format_datetime, build_activity_rows


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


def test_activity_rows_merge_cash_sessions_and_summary_tournaments() -> None:
    cash_time = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
    tournament_time = datetime(2026, 7, 2, 12, tzinfo=timezone.utc)
    sessions = [
        {
            "session_id": 1,
            "game_mode": GameMode.CASH_GAME,
            "table_name": "NL10",
            "started_at": cash_time,
            "hands_played": 25,
            "result": 1.5,
            "result_bb": 3.0,
        },
        {
            "session_id": 2,
            "game_mode": GameMode.TOURNAMENT,
            "tournament_id": "event-1",
            "started_at": tournament_time,
            "hands_played": 10,
            "result": -0.87,
        },
    ]
    tournaments = [
        {
            "tournament_id": "event-1",
            "game_mode": GameMode.TOURNAMENT,
            "name": "SPACE KO",
            "started_at": tournament_time,
            "entry_count": 2,
            "total_entry_cost": 1.0,
            "winnings": 0.0,
            "bounty_winnings": 0.13,
            "profit": -0.87,
            "entry_payment_method": "UNKNOWN",
            "is_free_entry": False,
        },
        {
            "tournament_id": "summary-only",
            "game_mode": GameMode.EXPRESSO,
            "name": "Summary only",
            "started_at": datetime(2026, 7, 3, 12, tzinfo=timezone.utc),
            "entry_count": 1,
            "total_entry_cost": 2.0,
            "winnings": 6.0,
            "bounty_winnings": 0.0,
            "profit": 4.0,
            "entry_payment_method": "CASH",
            "is_free_entry": False,
        },
    ]

    activities = build_activity_rows(sessions, tournaments)

    assert [activity.key for activity in activities] == [
        "tournament:summary-only",
        "tournament:event-1",
        "session:1",
    ]
    assert activities[1].volume == "2 entries"
    assert "cost 1.00 EUR" in activities[1].detail
    assert "initial payment UNKNOWN" in activities[1].detail
    assert activities[2].result_bb == 3.0
    assert "+3.00 BB" in activities[2].detail
    assert _format_datetime(tournament_time) == "2026-07-02 12:00 UTC"


def test_dashboard_metrics_follow_selected_mode() -> None:
    statistics = {
        "total_profit": 3.0,
        "cash_result": -1.0,
        "tournament_profit": 2.5,
        "expresso_profit": 1.5,
        "cash_hands_played": 25.0,
        "cash_bb": 4.0,
        "cash_bb_per_100": 16.0,
        "tournaments_played": 3.0,
        "tournament_roi": 25.0,
        "tournament_reentries": 2.0,
        "expressos_played": 4.0,
        "expresso_roi": 18.0,
        "expresso_tickets_used": 1.0,
    }

    assert _dashboard_metrics("ALL", statistics) == [
        ("Total profit", "+3.00 EUR"),
        ("Cash profit", "-1.00 EUR"),
        ("Tournament profit", "+2.50 EUR"),
        ("Expresso profit", "+1.50 EUR"),
    ]
    assert _dashboard_metrics(GameMode.CASH_GAME.value, statistics)[2:] == [
        ("BB won", "+4.0 BB"),
        ("BB / 100", "+16.0"),
    ]
    assert _dashboard_metrics(GameMode.TOURNAMENT.value, statistics)[-1] == (
        "Re-entries",
        "2",
    )
    assert _dashboard_metrics(GameMode.EXPRESSO.value, statistics)[-1] == (
        "Tickets used",
        "1",
    )