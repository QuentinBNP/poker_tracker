from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class TournamentsView(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, padding=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        columns = ("started_at", "name", "buy_in", "prize_pool", "players_count", "position")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        headings = {
            "started_at": "Started",
            "name": "Tournament",
            "buy_in": "Buy-in",
            "prize_pool": "Prize Pool",
            "players_count": "Players",
            "position": "Position",
        }
        widths = {
            "started_at": 150,
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


    def refresh(self, tournaments: list[dict[str, object]]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for tournament in tournaments:
            started_at = (
                tournament["started_at"].strftime("%Y-%m-%d %H:%M")
                if tournament.get("started_at")
                else "-"
            )
            self.tree.insert(
                "",
                "end",
                values=(
                    started_at,
                    tournament.get("name") or "-",
                    _format_amount(float(tournament.get("buy_in") or 0.0)),
                    _format_amount(float(tournament.get("prize_pool") or 0.0)),
                    tournament.get("players_count") or 0,
                    tournament.get("position") or "-",
                ),
            )


def _format_amount(value: float) -> str:
    return f"{value:.2f}"