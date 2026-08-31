from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import ttk
from typing import Callable, Mapping, Sequence

from game_modes import GameMode

SourceRow = Mapping[str, object]
SessionSelectionCallback = Callable[[int], None]
FreeEntryCallback = Callable[[str, bool], None]


@dataclass(frozen=True, slots=True)
class ActivityRow:
    key: str
    started_at: datetime | None
    game_mode: GameMode
    name: str
    volume: str
    cost: float | None
    winnings: float | None
    result: float
    result_bb: float | None
    detail: str
    tournament_id: str | None = None
    session_id: int | None = None
    is_free_entry: bool = False


class SessionsView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc | None = None,
        on_session_selected: SessionSelectionCallback | None = None,
        on_free_entry_changed: FreeEntryCallback | None = None,
    ) -> None:
        super().__init__(master, padding=16)
        self.on_session_selected = on_session_selected
        self.on_free_entry_changed = on_free_entry_changed
        self.free_entry_value = tk.BooleanVar(value=False)
        self._activities: dict[str, ActivityRow] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        columns = (
            "started_at",
            "game_mode",
            "activity",
            "volume",
            "cost",
            "winnings",
            "result",
            "result_bb",
        )
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        headings = {
            "started_at": "Started (UTC)",
            "game_mode": "Mode",
            "activity": "Table / Tournament",
            "volume": "Hands / Entries",
            "cost": "Cost",
            "winnings": "Winnings",
            "result": "Net result",
            "result_bb": "BB result",
        }
        widths = {
            "started_at": 150,
            "game_mode": 100,
            "activity": 250,
            "volume": 105,
            "cost": 85,
            "winnings": 85,
            "result": 95,
            "result_bb": 85,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        details = ttk.Frame(self)
        details.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        details.columnconfigure(0, weight=1)
        self.detail = ttk.Label(details, text="Select an activity for details")
        self.detail.grid(row=0, column=0, sticky="w")
        self.free_entry_toggle = ttk.Checkbutton(
            details,
            text="Free entry",
            variable=self.free_entry_value,
            command=self._on_free_entry_changed,
        )
        self.free_entry_toggle.grid(row=0, column=1, sticky="e")
        self.free_entry_toggle.state(["disabled"])

    def refresh(
        self,
        sessions: Sequence[SourceRow],
        tournaments: Sequence[SourceRow] = (),
    ) -> None:
        activities = build_activity_rows(sessions, tournaments)
        self._activities = {activity.key: activity for activity in activities}
        self.free_entry_value.set(False)
        self.free_entry_toggle.state(["disabled"])
        self.detail.configure(text="Select an activity for details")
        for item in self.tree.get_children():
            self.tree.delete(item)

        for activity in activities:
            self.tree.insert(
                "",
                "end",
                iid=activity.key,
                values=(
                    _format_datetime(activity.started_at),
                    _mode_label(activity.game_mode),
                    activity.name,
                    activity.volume,
                    _format_optional_amount(activity.cost),
                    _format_optional_amount(activity.winnings),
                    _format_amount(activity.result),
                    _format_optional_bb(activity.result_bb),
                ),
            )

    def _on_selection(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.tree.selection()
        activity = self._activities.get(selection[0]) if selection else None
        if activity is None:
            self.free_entry_value.set(False)
            self.free_entry_toggle.state(["disabled"])
            return

        self.detail.configure(text=activity.detail)
        if activity.tournament_id is not None:
            self.free_entry_value.set(activity.is_free_entry)
            self.free_entry_toggle.state(["!disabled"])
        else:
            self.free_entry_value.set(False)
            self.free_entry_toggle.state(["disabled"])
            if activity.session_id is not None and self.on_session_selected is not None:
                self.on_session_selected(activity.session_id)

    def _on_free_entry_changed(self) -> None:
        selection = self.tree.selection()
        activity = self._activities.get(selection[0]) if selection else None
        if (
            activity is not None
            and activity.tournament_id is not None
            and self.on_free_entry_changed is not None
        ):
            self.on_free_entry_changed(activity.tournament_id, self.free_entry_value.get())


def build_activity_rows(
    sessions: Sequence[SourceRow],
    tournaments: Sequence[SourceRow],
) -> list[ActivityRow]:
    activities = [
        _cash_activity(session)
        for session in sessions
        if session.get("game_mode") is GameMode.CASH_GAME
    ]
    activities.extend(_tournament_activity(tournament) for tournament in tournaments)
    return sorted(
        activities,
        key=lambda activity: activity.started_at.isoformat() if activity.started_at else "",
        reverse=True,
    )


def _cash_activity(session: SourceRow) -> ActivityRow:
    session_id = int(_as_float(session.get("session_id")))
    hands = int(_as_float(session.get("hands_played")))
    result = _as_float(session.get("result"))
    result_bb = _as_optional_float(session.get("result_bb"))
    return ActivityRow(
        key=f"session:{session_id}",
        session_id=session_id,
        started_at=_as_datetime(session.get("started_at")),
        game_mode=GameMode.CASH_GAME,
        name=str(session.get("table_name") or "Cash session"),
        volume=f"{hands} hands",
        cost=None,
        winnings=None,
        result=result,
        result_bb=result_bb,
        detail=(
            f"{hands} hands, net result {result:+.2f} EUR, {result_bb:+.2f} BB"
            if result_bb is not None
            else f"{hands} hands, net result {result:+.2f} EUR"
        ),
    )


def _tournament_activity(tournament: SourceRow) -> ActivityRow:
    tournament_id = str(tournament["tournament_id"])
    entry_count = int(_as_float(tournament.get("entry_count")))
    cost = _as_float(tournament.get("total_entry_cost"))
    winnings = _as_float(tournament.get("winnings")) + _as_float(
        tournament.get("bounty_winnings")
    )
    result = _as_float(tournament.get("profit"))
    payment_method = str(tournament.get("entry_payment_method") or "UNKNOWN")
    return ActivityRow(
        key=f"tournament:{tournament_id}",
        tournament_id=tournament_id,
        started_at=_as_datetime(tournament.get("started_at")),
        game_mode=_as_game_mode(tournament.get("game_mode")),
        name=str(tournament.get("name") or tournament_id),
        volume=f"{entry_count} entries",
        cost=cost,
        winnings=winnings,
        result=result,
        result_bb=None,
        detail=(
            f"Tournament {tournament_id}: {entry_count} entries, cost {cost:.2f} EUR, "
            f"winnings {winnings:.2f} EUR, net {result:+.2f} EUR, "
            f"initial payment {payment_method}"
        ),
        is_free_entry=bool(tournament.get("is_free_entry")),
    )


def _as_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    return float(value) if isinstance(value, int | float) else 0.0


def _as_optional_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _as_game_mode(value: object) -> GameMode:
    return value if isinstance(value, GameMode) else GameMode(str(value))


def _mode_label(mode: GameMode) -> str:
    return {
        GameMode.CASH_GAME: "Cash",
        GameMode.TOURNAMENT: "Tournament",
        GameMode.EXPRESSO: "Expresso",
    }[mode]


def _format_datetime(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC") if value is not None else "-"


def _format_optional_amount(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f} EUR"


def _format_amount(value: float) -> str:
    return f"{value:+.2f} EUR"


def _format_optional_bb(value: float | None) -> str:
    return "-" if value is None else f"{value:+.2f} BB"