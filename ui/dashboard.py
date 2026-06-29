from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class DashboardView(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, padding=16)
        ttk.Label(self, text="Poker Tracker").grid(row=0, column=0, sticky="w")