from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Sequence

from poker_stats.statistics_service import AdvancedStatistic


class StatisticsView(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, padding=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.summary = ttk.Label(self, text="Advanced statistics for the selected scope")
        self.summary.grid(row=0, column=0, sticky="w", pady=(0, 10))

        columns = ("metric", "value", "sample_size")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=14)
        self.tree.heading("metric", text="Metric")
        self.tree.heading("value", text="Value")
        self.tree.heading("sample_size", text="Sample")
        self.tree.column("metric", width=260, anchor="w")
        self.tree.column("value", width=130, anchor="e")
        self.tree.column("sample_size", width=120, anchor="e")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

    def refresh(self, statistics: Sequence[AdvancedStatistic]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.summary.configure(
            text=(
                "Rates with fewer than 20 relevant opportunities are hidden. "
                "Counts remain visible."
            )
        )
        for statistic in statistics:
            sample_size = str(statistic.sample_size) if statistic.sample_size is not None else "-"
            self.tree.insert(
                "",
                "end",
                values=(
                    statistic.label,
                    _format_statistic(statistic),
                    sample_size,
                ),
            )


def _format_statistic(statistic: AdvancedStatistic) -> str:
    if statistic.percent:
        return f"{statistic.value:.1f}%"
    if statistic.key in {"cash_bb", "cash_bb_per_100"}:
        return f"{statistic.value:+.2f}"
    if statistic.key == "aggression_factor":
        return f"{statistic.value:.2f}"
    return f"{statistic.value:.0f}"