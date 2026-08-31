from __future__ import annotations

import sys
import tkinter as tk
from datetime import date, datetime, time, timedelta, timezone
from tkinter import ttk
from typing import Callable, Mapping

from app_info import APP_ICON_PATH, APP_NAME
from database.database import Database
from database.filters import HistoryFilter
from game_modes import GameMode
from poker_stats.bankroll_service import BankrollPoint, BankrollService
from poker_stats.bb_history_service import BBHistoryPoint, BBHistoryService
from poker_stats.statistics_service import StatisticsService
from ui.bb_chart import BBChart
from ui.hand_detail import HandDetailDialog
from ui.hands_view import HandsView
from ui.result_chart import ResultChart
from ui.sessions_view import SessionsView
from ui.settings import SettingsDialog
from ui.statistics_view import StatisticsView

HandRow = Mapping[str, object]
SettingsCallback = Callable[[dict[str, str]], None]


class DashboardView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        database: Database,
        config: Mapping[str, object],
        on_settings_saved: SettingsCallback,
    ) -> None:
        super().__init__(master, padding=16)
        self.database = database
        self.settings_config: dict[str, str] = {
            key: str(value) for key, value in config.items()
        }
        self.hero_name = str(config["player_name"])
        self.on_settings_saved = on_settings_saved
        self.statistics_service = StatisticsService(database, self.hero_name)
        self.bankroll_service = BankrollService(database, self.hero_name)
        self.bb_history_service = BBHistoryService(database, self.hero_name)
        self.mode_value = tk.StringVar(value="ALL")
        self.period_value = tk.StringVar(value="All time")
        self.start_date_value = tk.StringVar()
        self.end_date_value = tk.StringVar()
        self.filter_message = tk.StringVar()
        self.cash_chart_unit = tk.StringVar(value="BB")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        title = ttk.Label(header, text=APP_NAME, font=("TkHeadingFont", 18, "bold"))
        self.subtitle = ttk.Label(header, text=f"Hero: {self.hero_name}")
        settings_button = ttk.Button(header, text="Settings", command=self._open_settings)
        title.grid(row=0, column=0, sticky="w")
        settings_button.grid(row=0, column=1, sticky="e")
        self.subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self._build_filters()

        summary_frame = ttk.Frame(self)
        summary_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for column in range(4):
            summary_frame.columnconfigure(column, weight=1)

        self.metric_titles: list[ttk.Label] = []
        self.metric_values: list[ttk.Label] = []
        for column in range(4):
            title, value = _build_metric(summary_frame, column)
            self.metric_titles.append(title)
            self.metric_values.append(value)

        notebook = ttk.Notebook(self)
        notebook.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        self.rowconfigure(3, weight=1)

        self.overview_tab = ttk.Frame(notebook, padding=16)
        self.notebook = notebook
        self.hands_view = HandsView(notebook)
        self.sessions_view = SessionsView(
            notebook,
            self._show_session_hands,
            self._set_tournament_free_entry,
            self._show_tournament_hands,
        )
        self.statistics_view = StatisticsView(notebook)
        notebook.add(self.overview_tab, text="Dashboard")
        notebook.add(self.hands_view, text="Hands")
        notebook.add(self.sessions_view, text="Sessions")
        notebook.add(self.statistics_view, text="Statistics")

        self._build_overview_tab()
        self.refresh()

    def _build_filters(self) -> None:
        filters = ttk.LabelFrame(self, text="Scope", padding=10)
        filters.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        filters.columnconfigure(5, weight=1)

        ttk.Label(filters, text="Mode").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Radiobutton(
            filters,
            text="All",
            value="ALL",
            variable=self.mode_value,
            command=self.refresh,
        ).grid(row=0, column=1, sticky="w", padx=(0, 8))
        for index, mode in enumerate(GameMode, start=2):
            ttk.Radiobutton(
                filters,
                text=_mode_label(mode),
                value=mode.value,
                variable=self.mode_value,
                command=self.refresh,
            ).grid(row=0, column=index, sticky="w", padx=(0, 8))

        ttk.Label(filters, text="Period").grid(row=1, column=0, sticky="w", pady=(10, 0))
        period = ttk.Combobox(
            filters,
            textvariable=self.period_value,
            values=(
                "All time",
                "Today",
                "Last 7 days",
                "Last 30 days",
                "This month",
                "This year",
                "Custom",
            ),
            state="readonly",
            width=16,
        )
        period.grid(row=1, column=1, sticky="w", pady=(10, 0))
        period.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        ttk.Label(filters, text="Start").grid(
            row=1, column=2, sticky="e", padx=(16, 4), pady=(10, 0)
        )
        ttk.Entry(filters, textvariable=self.start_date_value, width=12).grid(
            row=1, column=3, sticky="w", pady=(10, 0)
        )
        ttk.Label(filters, text="End").grid(row=1, column=4, sticky="e", padx=(12, 4), pady=(10, 0))
        ttk.Entry(filters, textvariable=self.end_date_value, width=12).grid(
            row=1, column=5, sticky="w", pady=(10, 0)
        )
        ttk.Button(filters, text="Apply", command=self.refresh).grid(
            row=1, column=6, sticky="e", padx=(12, 0), pady=(10, 0)
        )
        ttk.Label(filters, textvariable=self.filter_message).grid(
            row=2, column=0, columnspan=7, sticky="w", pady=(8, 0)
        )

    def _build_overview_tab(self) -> None:
        self.overview_tab.columnconfigure(0, weight=3)
        self.overview_tab.columnconfigure(1, weight=2)
        self.overview_tab.rowconfigure(1, weight=1)

        bankroll_frame = ttk.LabelFrame(self.overview_tab, text="Bankroll", padding=12)
        bankroll_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 12))
        bankroll_frame.columnconfigure(1, weight=1)
        bankroll_frame.rowconfigure(2, weight=1)
        ttk.Label(bankroll_frame, text="Selected result").grid(row=0, column=0, sticky="w")
        self.bankroll_value = ttk.Label(bankroll_frame, font=("TkHeadingFont", 16, "bold"))
        self.bankroll_value.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.bankroll_detail = ttk.Label(bankroll_frame)
        self.bankroll_detail.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        chart_controls = ttk.Frame(bankroll_frame)
        chart_controls.grid(row=0, column=2, rowspan=2, sticky="e")
        self.bb_unit_button = ttk.Radiobutton(
            chart_controls,
            text="BB",
            value="BB",
            variable=self.cash_chart_unit,
            command=self.refresh,
        )
        self.eur_unit_button = ttk.Radiobutton(
            chart_controls,
            text="EUR",
            value="EUR",
            variable=self.cash_chart_unit,
            command=self.refresh,
        )
        self.bb_unit_button.grid(row=0, column=0)
        self.eur_unit_button.grid(row=0, column=1)
        self.bb_chart = BBChart(bankroll_frame, self._show_graph_hand)
        self.bb_chart.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        self.result_chart = ResultChart(bankroll_frame, self._show_graph_hand)
        self.result_chart.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        recent_hands_frame = ttk.LabelFrame(
            self.overview_tab,
            text="Recent hands",
            padding=12,
        )
        recent_hands_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        recent_hands_frame.columnconfigure(0, weight=1)
        recent_hands_frame.rowconfigure(0, weight=1)
        self.recent_hands_list = tk.Listbox(
            recent_hands_frame,
            height=10,
            borderwidth=0,
            highlightthickness=0,
        )
        self.recent_hands_list.grid(row=0, column=0, sticky="nsew")

        stats_frame = ttk.LabelFrame(
            self.overview_tab,
            text="Poker statistics (selected scope)",
            padding=12,
        )
        stats_frame.grid(row=1, column=1, sticky="nsew")
        stats_frame.columnconfigure(1, weight=1)
        self.stats_labels: dict[str, ttk.Label] = {}
        stats_rows = [
            ("vpip", "VPIP"),
            ("pfr", "PFR"),
            ("limp_percentage", "Limp %"),
            ("aggression_factor", "Aggression"),
            ("showdown_win_percentage", "Showdown win %"),
        ]
        for index, (key, label_text) in enumerate(stats_rows):
            ttk.Label(stats_frame, text=label_text).grid(row=index, column=0, sticky="w", pady=2)
            value_label = ttk.Label(stats_frame, text="0.0")
            value_label.grid(row=index, column=1, sticky="e", pady=2)
            self.stats_labels[key] = value_label

    def refresh(self) -> None:
        filters = self._build_history_filter()
        statistics = self.statistics_service.calculate(filters)
        advanced_statistics = self.statistics_service.calculate_advanced(filters)
        bankroll_points = self.bankroll_service.calculate(filters)
        recent_hands = self.database.list_filtered_hands(self.hero_name, filters, limit=50)
        bb_points = self.bb_history_service.calculate(filters)
        tournaments = self.database.list_filtered_tournaments(filters, limit=1_000_000)
        sessions = self.database.list_sessions(self.hero_name, filters, limit=1_000_000)

        self._refresh_metrics(statistics)
        self._refresh_bankroll(bankroll_points)
        self._refresh_chart(bankroll_points, bb_points)

        self.recent_hands_list.delete(0, tk.END)
        for hand in recent_hands[:8]:
            line = _format_recent_hand_line(hand)
            self.recent_hands_list.insert(tk.END, line)

        self.hands_view.refresh(recent_hands)
        self.sessions_view.refresh(sessions, tournaments)
        self.statistics_view.refresh(advanced_statistics)

        for key, label in self.stats_labels.items():
            value = float(statistics.get(key, 0.0))
            if key == "aggression_factor":
                label.configure(text=f"{value:.2f}")
            else:
                label.configure(text=f"{value:.1f}%")

    def _build_history_filter(self) -> HistoryFilter:
        selected_mode = self.mode_value.get()
        game_mode = None if selected_mode == "ALL" else GameMode(selected_mode)
        start_at, end_at, message = _resolve_period(
            self.period_value.get(),
            self.start_date_value.get(),
            self.end_date_value.get(),
        )
        self.filter_message.set(message)
        return HistoryFilter(start_at=start_at, end_at=end_at, game_mode=game_mode)

    def _refresh_metrics(self, statistics: Mapping[str, float]) -> None:
        metrics = _dashboard_metrics(self.mode_value.get(), statistics)

        for title, value, label, value_label in zip(
            (metric[0] for metric in metrics),
            (metric[1] for metric in metrics),
            self.metric_titles,
            self.metric_values,
            strict=True,
        ):
            label.configure(text=title)
            value_label.configure(text=value)

    def _refresh_bankroll(self, points: list[BankrollPoint]) -> None:
        if not points:
            self.bankroll_value.configure(text="No settled results")
            self.bankroll_detail.configure(
                text="Import hand histories or tournament summaries to build a bankroll timeline."
            )
            return

        last_point = points[-1]
        self.bankroll_value.configure(text=_format_money(last_point.balance))
        timestamp = last_point.occurred_at.strftime("%Y-%m-%d %H:%M")
        self.bankroll_detail.configure(
            text=f"{len(points)} accounting events through {timestamp} UTC."
        )

    def _refresh_chart(
        self,
        bankroll_points: list[BankrollPoint],
        bb_points: list[BBHistoryPoint],
    ) -> None:
        cash_only = self.mode_value.get() == GameMode.CASH_GAME.value
        state = ["!disabled"] if cash_only else ["disabled"]
        self.bb_unit_button.state(state)
        self.eur_unit_button.state(state)

        if cash_only and self.cash_chart_unit.get() == "BB":
            self.result_chart.grid_remove()
            self.bb_chart.grid()
            self.bb_chart.set_points(bb_points)
        else:
            self.bb_chart.grid_remove()
            self.result_chart.grid()
            self.result_chart.set_points(bankroll_points)

    def _open_settings(self) -> None:
        SettingsDialog(self, self.settings_config, self._save_settings)

    def _save_settings(self, config: dict[str, str]) -> None:
        self.settings_config = config
        self.hero_name = config["player_name"]
        self.statistics_service = StatisticsService(self.database, self.hero_name)
        self.bankroll_service = BankrollService(self.database, self.hero_name)
        self.bb_history_service = BBHistoryService(self.database, self.hero_name)
        self.subtitle.configure(text=f"Hero: {self.hero_name}")
        self.on_settings_saved(config)
        self.refresh()

    def _show_session_hands(self, session_id: int) -> None:
        hands = self.database.list_hands_for_session(self.hero_name, session_id)
        self.hands_view.refresh(hands)
        self.notebook.select(self.hands_view)

    def _show_tournament_hands(self, tournament_id: str) -> None:
        hands = self.database.list_filtered_hands(
            self.hero_name,
            HistoryFilter(tournament_id=tournament_id),
            limit=1_000_000,
        )
        self.hands_view.refresh(hands)
        self.notebook.select(self.hands_view)

    def _show_graph_hand(self, hand_id: str) -> None:
        hand = self.database.get_hand(hand_id)
        if hand is None:
            return
        HandDetailDialog(self, hand, self.database.list_actions_for_hand(hand_id))

    def _set_tournament_free_entry(self, tournament_id: str, is_free: bool) -> None:
        self.database.set_tournament_entry_free(tournament_id, is_free)
        self.refresh()


def _build_metric(master: ttk.Frame, column: int) -> tuple[ttk.Label, ttk.Label]:
    card = ttk.LabelFrame(master, padding=12)
    card.grid(row=0, column=column, sticky="ew", padx=(0, 8) if column < 2 else 0)
    title = ttk.Label(card, text="")
    value = ttk.Label(card, text="0", font=("TkHeadingFont", 16, "bold"))
    title.grid(row=0, column=0, sticky="w")
    value.grid(row=1, column=0, sticky="w", pady=(2, 0))
    return title, value


def _format_result(value: float) -> str:
    return f"{value:+.2f}"


def _format_money(value: float) -> str:
    return f"{value:+.2f} EUR"


def _dashboard_metrics(
    selected_mode: str,
    statistics: Mapping[str, float],
) -> list[tuple[str, str]]:
    if selected_mode == GameMode.CASH_GAME.value:
        return [
            ("Hands", f"{statistics['cash_hands_played']:.0f}"),
            ("Profit", _format_money(statistics["cash_result"])),
            ("BB won", f"{statistics['cash_bb']:+.1f} BB"),
            ("BB / 100", f"{statistics['cash_bb_per_100']:+.1f}"),
        ]
    if selected_mode == GameMode.TOURNAMENT.value:
        return [
            ("Events played", f"{statistics['tournaments_played']:.0f}"),
            ("Net profit", _format_money(statistics["tournament_profit"])),
            ("ROI", f"{statistics['tournament_roi']:+.1f}%"),
            ("Re-entries", f"{statistics['tournament_reentries']:.0f}"),
        ]
    if selected_mode == GameMode.EXPRESSO.value:
        return [
            ("Expressos", f"{statistics['expressos_played']:.0f}"),
            ("Net profit", _format_money(statistics["expresso_profit"])),
            ("ROI", f"{statistics['expresso_roi']:+.1f}%"),
            ("Tickets used", f"{statistics['expresso_tickets_used']:.0f}"),
        ]
    return [
        ("Total profit", _format_money(statistics["total_profit"])),
        ("Cash profit", _format_money(statistics["cash_result"])),
        ("Tournament profit", _format_money(statistics["tournament_profit"])),
        ("Expresso profit", _format_money(statistics["expresso_profit"])),
    ]


def _mode_label(mode: GameMode) -> str:
    return {
        GameMode.CASH_GAME: "Cash",
        GameMode.TOURNAMENT: "Tournament",
        GameMode.EXPRESSO: "Expresso",
    }[mode]


def _resolve_period(
    period: str,
    start_text: str,
    end_text: str,
) -> tuple[datetime | None, datetime | None, str]:
    now = datetime.now(timezone.utc)
    today = now.date()
    if period == "Today":
        return _day_range(today, today, "Today")
    if period == "Last 7 days":
        return _day_range(today - timedelta(days=6), today, "Last 7 days")
    if period == "Last 30 days":
        return _day_range(today - timedelta(days=29), today, "Last 30 days")
    if period == "This month":
        return _day_range(today.replace(day=1), today, "This month")
    if period == "This year":
        return _day_range(today.replace(month=1, day=1), today, "This year")
    if period != "Custom":
        return None, None, "All imported history"

    try:
        start_date = date.fromisoformat(start_text) if start_text else None
        end_date = date.fromisoformat(end_text) if end_text else None
    except ValueError:
        return None, None, "Use YYYY-MM-DD for custom dates"
    if start_date is not None and end_date is not None and start_date > end_date:
        return None, None, "Custom start date must not be after end date"
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc) if start_date else None,
        datetime.combine(end_date, time.max, tzinfo=timezone.utc) if end_date else None,
        "Custom period",
    )


def _day_range(start_date: date, end_date: date, label: str) -> tuple[datetime, datetime, str]:
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date, time.max, tzinfo=timezone.utc),
        label,
    )


def _format_recent_hand_line(hand: HandRow) -> str:
    played_at_value = _as_datetime(hand.get("played_at"))
    played_at = played_at_value.strftime("%m-%d %H:%M UTC") if played_at_value else "-"
    hero_cards = str(hand.get("hero_cards") or "--")
    table_name = str(hand.get("table_name") or "-")
    result = _format_result(_as_float(hand.get("result")))
    return f"{played_at}  {hero_cards}  {table_name}  {result}"


def _as_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def create_main_window(
    database: Database,
    config: Mapping[str, object],
    on_settings_saved: SettingsCallback,
) -> tk.Tk:
    root, _ = create_main_window_with_view(database, config, on_settings_saved)
    return root


def create_main_window_with_view(
    database: Database,
    config: Mapping[str, object],
    on_settings_saved: SettingsCallback,
) -> tuple[tk.Tk, DashboardView]:
    root = tk.Tk()
    root.title(APP_NAME)
    _configure_window_icon(root)
    root.geometry("1100x720")
    root.minsize(900, 600)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    view = DashboardView(
        root,
        database=database,
        config=config,
        on_settings_saved=on_settings_saved,
    )
    view.grid(row=0, column=0, sticky="nsew")
    return root, view


def _configure_window_icon(root: tk.Tk) -> None:
    if sys.platform != "win32" or not APP_ICON_PATH.exists():
        return

    try:
        root.iconbitmap(default=str(APP_ICON_PATH))
    except tk.TclError:
        return