from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from database.models import Action, Hand


class HandDetailDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, hand: Hand, actions: list[Action]) -> None:
        super().__init__(master)
        self.title(f"Hand {hand.hand_id}")
        self.transient(master.winfo_toplevel())
        self.resizable(True, True)
        self.minsize(560, 360)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        result_bb = hand.result / hand.big_blind if hand.big_blind > 0 else None
        details = (
            f"{hand.played_at.strftime('%Y-%m-%d %H:%M') if hand.played_at else '-'}    "
            f"{hand.table_name}\n"
            f"Cards: {hand.hero_cards or '-'}    Board: {hand.board or '-'}    "
            f"Pot: {hand.pot:.2f}    Result: {hand.result:+.2f}"
        )
        if result_bb is not None:
            details += f"    BB: {result_bb:+.2f}"
        ttk.Label(self, text=details, justify="left").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 10)
        )

        frame = ttk.Frame(self, padding=(16, 0, 16, 16))
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("street", "player", "action", "amount")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column, label, width in (
            ("street", "Street", 100),
            ("player", "Player", 180),
            ("action", "Action", 110),
            ("amount", "Amount", 100),
        ):
            tree.heading(column, text=label)
            tree.column(column, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        for action in actions:
            amount = f"{action.amount:.2f}" if action.amount is not None else "-"
            tree.insert("", "end", values=(action.street, action.player, action.action, amount))

        ttk.Button(self, text="Close", command=self.destroy).grid(
            row=2, column=0, sticky="e", padx=16, pady=(0, 16)
        )
        self.grab_set()