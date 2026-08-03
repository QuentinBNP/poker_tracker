from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Mapping, cast

SettingsSavedCallback = Callable[[dict[str, str]], None]


class SettingsDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        config: Mapping[str, object],
        on_save: SettingsSavedCallback,
    ) -> None:
        super().__init__(master)
        self.on_save = on_save
        self.title("Settings")
        self.resizable(False, False)
        self.transient(cast(tk.Wm, master.winfo_toplevel()))
        self.grab_set()

        content = ttk.Frame(self, padding=16)
        content.grid(sticky="nsew")
        content.columnconfigure(1, weight=1)

        self.values: dict[str, tk.StringVar] = {}
        fields = [
            ("player_name", "Player name", None),
            ("winamax_folder", "Winamax folder", self._choose_winamax_folder),
            ("database_path", "Database path", self._choose_database_path),
            ("log_directory", "Log folder", self._choose_log_directory),
        ]
        for row, (key, label, choose_path) in enumerate(fields):
            ttk.Label(content, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
            value = tk.StringVar(value=str(config.get(key, "")))
            self.values[key] = value
            ttk.Entry(content, textvariable=value, width=54).grid(row=row,
                                                                  column=1,
                                                                  sticky="ew",
                                                                  pady=4)
            if choose_path is not None:
                ttk.Button(content, text="Browse", command=choose_path).grid(
                    row=row,
                    column=2,
                    padx=(8, 0),
                    pady=4,
                )

        actions = ttk.Frame(content)
        actions.grid(row=len(fields), column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text="Save", command=self._save).grid(row=0, column=1)

    def _choose_winamax_folder(self) -> None:
        self._choose_directory("winamax_folder")

    def _choose_log_directory(self) -> None:
        self._choose_directory("log_directory")

    def _choose_directory(self, key: str) -> None:
        path = filedialog.askdirectory(parent=self, initialdir=self.values[key].get())
        if path:
            self.values[key].set(path)

    def _choose_database_path(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            initialfile=self.values["database_path"].get(),
            defaultextension=".db",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
        )
        if path:
            self.values["database_path"].set(path)

    def _save(self) -> None:
        config = {key: value.get().strip() for key, value in self.values.items()}
        missing = [key.replace("_", " ") for key, value in config.items() if not value]
        if missing:
            messagebox.showerror("Settings", f"Required: {', '.join(missing)}", parent=self)
            return

        self.on_save(config)
        self.destroy()