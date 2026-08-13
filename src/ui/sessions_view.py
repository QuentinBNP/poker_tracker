from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable, Mapping, Sequence

SessionRow = Mapping[str, object]
SelectionCallback = Callable[[int], None]


class SessionsView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc | None = None,
        on_session_selected: SelectionCallback | None = None,
    ) -> None:
        super().__init__(master, padding=16)
        self.on_session_selected = on_session_selected
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        columns = ("started_at", "game_mode", "location", "hands_played", "result")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        headings = {
            "started_at": "Started",
            "game_mode": "Mode",
            "location": "Table / Tournament",
            "hands_played": "Hands",
            "result": "Result",
        }
        widths = {
            "started_at": 150,
            "game_mode": 110,
            "location": 300,
            "hands_played": 80,
            "result": 100,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def refresh(self, sessions: Sequence[SessionRow]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for session in sessions:
            started_at = _format_datetime(session.get("started_at"))
            location = session.get("table_name") or session.get("tournament_id") or "-"
            self.tree.insert(
                "",
                "end",
                iid=str(session["session_id"]),
                values=(
                    started_at,
                    session.get("game_mode") or "-",
                    location,
                    session.get("hands_played") or 0,
                    _format_amount(session.get("result")),
                ),
            )

    def _on_selection(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.tree.selection()
        if selection and self.on_session_selected is not None:
            self.on_session_selected(int(selection[0]))


def _format_datetime(value: object) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if isinstance(value, datetime) else "-"


def _format_amount(value: object) -> str:
    amount = float(value) if isinstance(value, int | float) else 0.0
    return f"{amount:+.2f}"