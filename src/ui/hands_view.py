from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Mapping, Sequence

HandRow = Mapping[str, object]


class HandsView(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, padding=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        columns = ("played_at", "table_name", "hero_cards", "board", "pot", "result", "result_bb")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        headings = {
            "played_at": "Played (UTC)",
            "table_name": "Table",
            "hero_cards": "Cards",
            "board": "Board",
            "pot": "Pot",
            "result": "Result",
            "result_bb": "BB result",
        }
        widths = {
            "played_at": 150,
            "table_name": 180,
            "hero_cards": 90,
            "board": 170,
            "pot": 80,
            "result": 80,
            "result_bb": 80,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")


    def refresh(self, hands: Sequence[HandRow]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for hand in hands:
            played_at_value = _as_datetime(hand.get("played_at"))
            played_at = (
                played_at_value.strftime("%Y-%m-%d %H:%M UTC") if played_at_value else "-"
            )
            self.tree.insert(
                "",
                "end",
                values=(
                    played_at,
                    hand.get("table_name") or "-",
                    hand.get("hero_cards") or "-",
                    hand.get("board") or "-",
                    _format_amount(_as_float(hand.get("pot"))),
                    _format_amount(_as_float(hand.get("result"))),
                    _format_bb(hand.get("result_bb")),
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


def _format_bb(value: object) -> str:
    if not isinstance(value, int | float):
        return "-"
    return f"{value:+.2f}"