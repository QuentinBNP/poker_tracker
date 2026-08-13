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
from poker_stats.statistics_service import StatisticsService
from ui.bankroll_chart import BankrollChart
from ui.hands_view import HandsView
from ui.sessions_view import SessionsView
from ui.settings import SettingsDialog
from ui.tournaments_view import TournamentsView

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
        self.all_modes_value = tk.BooleanVar(value=True)
        self.mode_values = {mode: tk.BooleanVar() for mode in GameMode}
        self.period_value = tk.StringVar(value="All time")
        self.start_date_value = tk.StringVar()
        self.end_date_value = tk.StringVar()
        self.filter_message = tk.StringVar()

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
        self.sessions_view = SessionsView(notebook, self._show_session_hands)
        self.tournaments_view = TournamentsView(notebook)
        notebook.add(self.overview_tab, text="Dashboard")
        notebook.add(self.hands_view, text="Hands")
        notebook.add(self.sessions_view, text="Sessions")
        notebook.add(self.tournaments_view, text="Tournaments")

        self._build_overview_tab()
        self.refresh()

    def _build_filters(self) -> None:
        filters = ttk.LabelFrame(self, text="Scope", padding=10)
        filters.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        filters.columnconfigure(5, weight=1)

        ttk.Label(filters, text="Mode").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Checkbutton(
            filters,
            text="All",
            variable=self.all_modes_value,
            command=self._select_all_modes,
        ).grid(row=0, column=1, sticky="w", padx=(0, 8))
        for index, mode in enumerate(GameMode, start=2):
            ttk.Checkbutton(
                filters,
                text=_mode_label(mode),
                variable=self.mode_values[mode],
                command=self._select_specific_modes,
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
        self.bankroll_chart = BankrollChart(bankroll_frame)
        self.bankroll_chart.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))

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

        stats_frame = ttk.LabelFrame(self.overview_tab, text="Statistics", padding=12)
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
        bankroll_points = self.bankroll_service.calculate(filters)
        recent_hands = self.database.list_filtered_hands(self.hero_name, filters, limit=50)
        recent_tournaments = self.database.list_filtered_tournaments(filters, limit=50)
        sessions = self.database.list_sessions(self.hero_name, filters, limit=50)

        self._refresh_metrics(statistics)
        self._refresh_bankroll(bankroll_points)

        self.recent_hands_list.delete(0, tk.END)
        for hand in recent_hands[:8]:
            line = _format_recent_hand_line(hand)
            self.recent_hands_list.insert(tk.END, line)

        self.hands_view.refresh(recent_hands)
        self.sessions_view.refresh(sessions)
        self.tournaments_view.refresh(recent_tournaments)

        for key, label in self.stats_labels.items():
            value = float(statistics.get(key, 0.0))
            if key == "aggression_factor":
                label.configure(text=f"{value:.2f}")
            else:
                label.configure(text=f"{value:.1f}%")

    def _build_history_filter(self) -> HistoryFilter:
        game_modes = tuple(mode for mode, value in self.mode_values.items() if value.get())
        start_at, end_at, message = _resolve_period(
            self.period_value.get(),
            self.start_date_value.get(),
            self.end_date_value.get(),
        )
        self.filter_message.set(message)
        return HistoryFilter(start_at=start_at, end_at=end_at, game_modes=game_modes)

    def _refresh_metrics(self, statistics: Mapping[str, float]) -> None:
        selected_modes = [mode for mode, value in self.mode_values.items() if value.get()]
        if selected_modes == [GameMode.CASH_GAME]:
            metrics = [
                ("Hands", f"{statistics['cash_hands_played']:.0f}"),
                ("Profit", _format_money(statistics["cash_result"])),
                ("BB won", f"{statistics['cash_bb']:+.1f} BB"),
                ("BB / 100", f"{statistics['cash_bb_per_100']:+.1f}"),
            ]
        elif selected_modes == [GameMode.TOURNAMENT]:
            metrics = [
                ("Tournaments", f"{statistics['tournaments_played']:.0f}"),
                ("Net profit", _format_money(statistics["tournament_profit"])),
                ("ROI", f"{statistics['tournament_roi']:+.1f}%"),
                ("VPIP", f"{statistics['vpip']:.1f}%"),
            ]
        elif selected_modes == [GameMode.EXPRESSO]:
            metrics = [
                ("Expressos", f"{statistics['expressos_played']:.0f}"),
                ("Net profit", _format_money(statistics["expresso_profit"])),
                ("ROI", f"{statistics['expresso_roi']:+.1f}%"),
                ("VPIP", f"{statistics['vpip']:.1f}%"),
            ]
        else:
            metrics = [
                ("Hands", f"{statistics['hands_played']:.0f}"),
                ("Tournaments", f"{statistics['tournaments_played']:.0f}"),
                ("Expressos", f"{statistics['expressos_played']:.0f}"),
                ("Total profit", _format_money(statistics["total_profit"])),
            ]

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
        self.bankroll_chart.set_points(points)
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
            text=f"{len(points)} settled results through {timestamp}."
        )

    def _open_settings(self) -> None:
        SettingsDialog(self, self.settings_config, self._save_settings)

    def _save_settings(self, config: dict[str, str]) -> None:
        self.settings_config = config
        self.hero_name = config["player_name"]
        self.statistics_service = StatisticsService(self.database, self.hero_name)
        self.bankroll_service = BankrollService(self.database, self.hero_name)
        self.subtitle.configure(text=f"Hero: {self.hero_name}")
        self.on_settings_saved(config)
        self.refresh()

    def _select_all_modes(self) -> None:
        if self.all_modes_value.get():
            for value in self.mode_values.values():
                value.set(False)
        else:
            self.all_modes_value.set(True)
        self.refresh()

    def _select_specific_modes(self) -> None:
        selected = any(value.get() for value in self.mode_values.values())
        self.all_modes_value.set(not selected)
        self.refresh()

    def _show_session_hands(self, session_id: int) -> None:
        hands = self.database.list_hands_for_session(self.hero_name, session_id)
        self.hands_view.refresh(hands)
        self.notebook.select(self.hands_view)


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
    played_at = played_at_value.strftime("%m-%d %H:%M") if played_at_value else "-"
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