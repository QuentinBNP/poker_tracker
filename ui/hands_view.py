from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class HandsView(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, padding=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        columns = ("played_at", "table_name", "hero_cards", "board", "pot", "result")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        headings = {
            "played_at": "Played",
            "table_name": "Table",
            "hero_cards": "Cards",
            "board": "Board",
            "pot": "Pot",
            "result": "Result",
        }
        widths = {
            "played_at": 150,
            "table_name": 180,
            "hero_cards": 90,
            "board": 170,
            "pot": 80,
            "result": 80,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")


    def refresh(self, hands: list[dict[str, object]]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for hand in hands:
            played_at = hand["played_at"].strftime("%Y-%m-%d %H:%M") if hand.get("played_at") else "-"
            self.tree.insert(
                "",
                "end",
                values=(
                    played_at,
                    hand.get("table_name") or "-",
                    hand.get("hero_cards") or "-",
                    hand.get("board") or "-",
                    _format_amount(float(hand.get("pot") or 0.0)),
                    _format_amount(float(hand.get("result") or 0.0)),
                ),
            )


def _format_amount(value: float) -> str:
    return f"{value:.2f}"