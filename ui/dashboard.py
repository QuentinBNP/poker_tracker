from __future__ import annotations

import tkinter as tk
from datetime import datetime
from statistics.calculator import StatisticsCalculator
from tkinter import ttk
from typing import Mapping

from database.database import Database
from ui.hands_view import HandsView
from ui.tournaments_view import TournamentsView

HandRow = Mapping[str, object]


class DashboardView(ttk.Frame):
    def __init__(self, master: tk.Misc, database: Database, hero_name: str) -> None:
        super().__init__(master, padding=16)
        self.database = database
        self.hero_name = hero_name
        self.statistics = StatisticsCalculator(database, hero_name)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        title = ttk.Label(self, text="Poker Tracker", font=("TkHeadingFont", 18, "bold"))
        subtitle = ttk.Label(self, text=f"Hero: {hero_name}")
        title.grid(row=0, column=0, sticky="w")
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 12))

        summary_frame = ttk.Frame(self)
        summary_frame.grid(row=2, column=0, sticky="ew")
        for column in range(3):
            summary_frame.columnconfigure(column, weight=1)

        self.hands_value = _build_metric(summary_frame, 0, "Hands Played")
        self.tournaments_value = _build_metric(summary_frame, 1, "Tournaments")
        self.result_value = _build_metric(summary_frame, 2, "Result")

        notebook = ttk.Notebook(self)
        notebook.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        self.rowconfigure(3, weight=1)

        self.overview_tab = ttk.Frame(notebook, padding=16)
        self.hands_view = HandsView(notebook)
        self.tournaments_view = TournamentsView(notebook)
        notebook.add(self.overview_tab, text="Dashboard")
        notebook.add(self.hands_view, text="Hands")
        notebook.add(self.tournaments_view, text="Tournaments")

        self._build_overview_tab()
        self.refresh()


    def _build_overview_tab(self) -> None:
        self.overview_tab.columnconfigure(0, weight=3)
        self.overview_tab.columnconfigure(1, weight=2)

        recent_hands_frame = ttk.LabelFrame(
            self.overview_tab,
            text="Recent hands",
            padding=12,
        )
        recent_hands_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
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
        stats_frame.grid(row=0, column=1, sticky="nsew")
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
        summary = self.database.get_hero_summary(self.hero_name)
        recent_hands = self.database.list_recent_hands(self.hero_name, limit=12)
        recent_tournaments = self.database.list_recent_tournaments(limit=12)
        statistics = self.statistics.calculate()

        self.hands_value.configure(text=str(summary["hands_played"]))
        self.tournaments_value.configure(text=str(summary["tournaments_played"]))
        self.result_value.configure(text=_format_result(float(summary["total_result"])))

        self.recent_hands_list.delete(0, tk.END)
        for hand in recent_hands[:8]:
            line = _format_recent_hand_line(hand)
            self.recent_hands_list.insert(tk.END, line)

        self.hands_view.refresh(recent_hands)
        self.tournaments_view.refresh(recent_tournaments)

        for key, label in self.stats_labels.items():
            value = float(statistics.get(key, 0.0))
            if key == "aggression_factor":
                label.configure(text=f"{value:.2f}")
            else:
                label.configure(text=f"{value:.1f}%")


def _build_metric(master: ttk.Frame, column: int, title: str) -> ttk.Label:
    card = ttk.LabelFrame(master, text=title, padding=12)
    card.grid(row=0, column=column, sticky="ew", padx=(0, 8) if column < 2 else 0)
    value = ttk.Label(card, text="0", font=("TkHeadingFont", 16, "bold"))
    value.grid(row=0, column=0, sticky="w")
    return value


def _format_result(value: float) -> str:
    return f"{value:+.2f}"


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


def create_main_window(database: Database, hero_name: str) -> tk.Tk:
    root, _ = create_main_window_with_view(database, hero_name)
    return root


def create_main_window_with_view(
    database: Database,
    hero_name: str,
) -> tuple[tk.Tk, DashboardView]:
    root = tk.Tk()
    root.title("Poker Tracker")
    root.geometry("1100x720")
    root.minsize(900, 600)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    view = DashboardView(root, database=database, hero_name=hero_name)
    view.grid(row=0, column=0, sticky="nsew")
    return root, view