from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable, Mapping, Sequence

TournamentRow = Mapping[str, object]
FreeEntryCallback = Callable[[str, bool], None]


class TournamentsView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc | None = None,
        on_free_entry_changed: FreeEntryCallback | None = None,
    ) -> None:
        super().__init__(master, padding=16)
        self.on_free_entry_changed = on_free_entry_changed
        self.free_entry_value = tk.BooleanVar(value=False)
        self._free_entries: dict[str, bool] = {}
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
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)
        self.free_entry_toggle = ttk.Checkbutton(
            self,
            text="Free entry",
            variable=self.free_entry_value,
            command=self._on_free_entry_changed,
        )
        self.free_entry_toggle.grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.free_entry_toggle.state(["disabled"])

    def refresh(self, tournaments: Sequence[TournamentRow]) -> None:
        self._free_entries.clear()
        self.free_entry_value.set(False)
        self.free_entry_toggle.state(["disabled"])
        for item in self.tree.get_children():
            self.tree.delete(item)

        for tournament in tournaments:
            tournament_id = str(tournament["tournament_id"])
            self._free_entries[tournament_id] = bool(tournament.get("is_free_entry"))
            started_at_value = _as_datetime(tournament.get("started_at"))
            started_at = started_at_value.strftime("%Y-%m-%d %H:%M") if started_at_value else "-"
            self.tree.insert(
                "",
                "end",
                iid=tournament_id,
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

    def _on_selection(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.tree.selection()
        if not selection:
            self.free_entry_value.set(False)
            self.free_entry_toggle.state(["disabled"])
            return

        self.free_entry_value.set(self._free_entries.get(selection[0], False))
        self.free_entry_toggle.state(["!disabled"])

    def _on_free_entry_changed(self) -> None:
        selection = self.tree.selection()
        if not selection or self.on_free_entry_changed is None:
            return

        self.on_free_entry_changed(selection[0], self.free_entry_value.get())


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