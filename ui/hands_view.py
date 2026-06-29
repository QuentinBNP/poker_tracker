from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class HandsView(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, padding=16)
        ttk.Label(self, text="Hands").grid(row=0, column=0, sticky="w")