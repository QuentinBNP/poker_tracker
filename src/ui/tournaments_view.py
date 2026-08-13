from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Mapping, Sequence

TournamentRow = Mapping[str, object]


class TournamentsView(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, padding=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        columns = (
            "started_at",
            "game_mode",
            "name",
            "buy_in",
            "prize_pool",
            "players_count",
            "position",
        )
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        headings = {
            "started_at": "Started",
            "game_mode": "Mode",
            "name": "Tournament",
            "buy_in": "Buy-in",
            "prize_pool": "Prize Pool",
            "players_count": "Players",
            "position": "Position",
        }
        widths = {
            "started_at": 150,
            "game_mode": 110,
            "name": 220,
            "buy_in": 90,
            "prize_pool": 100,
            "players_count": 90,
            "position": 80,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")


    def refresh(self, tournaments: Sequence[TournamentRow]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for tournament in tournaments:
            started_at_value = _as_datetime(tournament.get("started_at"))
            started_at = started_at_value.strftime("%Y-%m-%d %H:%M") if started_at_value else "-"
            self.tree.insert(
                "",
                "end",
                values=(
                    started_at,
                    tournament.get("game_mode") or "-",
                    tournament.get("name") or "-",
                    _format_amount(_as_float(tournament.get("buy_in"))),
                    _format_amount(_as_float(tournament.get("prize_pool"))),
                    tournament.get("players_count") or 0,
                    tournament.get("position") or "-",
                ),
            )


def _as_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _format_amount(value: float) -> str:
    return f"{value:.2f}"