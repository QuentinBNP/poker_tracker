from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from poker_stats.bankroll_service import BankrollPoint, BankrollSourceType
from ui.chart_math import chart_bounds, sampled_indices, scale_x, scale_y


class ResultChart(ttk.Frame):
    MAX_RENDERED_POINTS = 1_200

    def __init__(
        self,
        master: tk.Misc | None = None,
        on_hand_selected: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.points: list[BankrollPoint] = []
        self._window_start = 0
        self._window_end = 0
        self._selection_start: int | None = None
        self._selection_end: int | None = None
        self._visible_points: list[tuple[int, BankrollPoint]] = []
        self.on_hand_selected = on_hand_selected
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, height=220, highlightthickness=0, background="#ffffff")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ttk.Button(self, text="Reset zoom", command=self._reset_zoom).grid(
            row=1, column=0, sticky="e", pady=(6, 0)
        )
        self.detail = ttk.Label(self, text="Hover a result for EUR details")
        self.detail.grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.canvas.bind("<Configure>", self._draw)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<Button-3>", self._reset_zoom)

    def set_points(self, points: list[BankrollPoint]) -> None:
        self.points = points
        self._window_start = 0
        self._window_end = len(points)
        self.detail.configure(text="Hover a result for EUR details")
        self._draw()

    def _draw(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 20 or height < 20:
            return
        if not self.points:
            self.canvas.create_text(
                width / 2,
                height / 2,
                text="No monetary results in this scope",
                fill="#666666",
            )
            self._visible_points = []
            return

        selected = self.points[self._window_start : self._window_end]
        indexes = sampled_indices(
            [point.balance for point in selected], self.MAX_RENDERED_POINTS
        )
        self._visible_points = [
            (self._window_start + index, selected[index]) for index in indexes
        ]
        minimum, maximum = chart_bounds(
            [point.balance for _, point in self._visible_points]
        )
        left, top, right, bottom = 58, 18, width - 14, height - 30
        zero_y = scale_y(0.0, minimum, maximum, top, bottom)
        self.canvas.create_line(left, zero_y, right, zero_y, fill="#d8d8d8")
        self.canvas.create_text(
            left - 6, top, text=f"{maximum:+.2f}", anchor="e", fill="#666666"
        )
        self.canvas.create_text(
            left - 6, bottom, text=f"{minimum:+.2f}", anchor="e", fill="#666666"
        )
        coordinates = [
            (
                scale_x(index, len(self._visible_points), left, right),
                scale_y(point.balance, minimum, maximum, top, bottom),
            )
            for index, (_, point) in enumerate(self._visible_points)
        ]
        if len(coordinates) > 1:
            line_coordinates = [value for coordinate in coordinates for value in coordinate]
            self.canvas.create_line(*line_coordinates, fill="#176b67", width=2)
        for x, y in coordinates:
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#176b67", outline="")
        if self._selection_start is not None and self._selection_end is not None:
            self.canvas.create_rectangle(
                self._selection_start,
                top,
                self._selection_end,
                bottom,
                outline="#176b67",
                dash=(3, 3),
            )

    def _on_motion(self, event: tk.Event[tk.Misc]) -> None:
        point = self._point_at(event.x, event.y)
        text = _detail_text(point) if point else "Hover a result for EUR details"
        self.detail.configure(text=text)

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        self.detail.configure(text="Hover a result for EUR details")

    def _on_drag_start(self, event: tk.Event[tk.Misc]) -> None:
        self._selection_start = event.x
        self._selection_end = event.x

    def _on_drag(self, event: tk.Event[tk.Misc]) -> None:
        if self._selection_start is not None:
            self._selection_end = event.x
            self._draw()

    def _on_drag_end(self, event: tk.Event[tk.Misc]) -> None:
        if self._selection_start is None:
            return
        start_x, end_x = sorted((self._selection_start, event.x))
        self._selection_start = None
        self._selection_end = None
        if end_x - start_x < 8:
            point = self._point_at(event.x, event.y)
            if (
                point is not None
                and point.source_type is BankrollSourceType.HAND
                and self.on_hand_selected is not None
            ):
                self.on_hand_selected(point.source_id)
            return
        start_index = self._global_index_at_x(start_x)
        end_index = self._global_index_at_x(end_x)
        if start_index is not None and end_index is not None:
            self._window_start = min(start_index, end_index)
            self._window_end = max(start_index, end_index) + 1
        self._draw()

    def _reset_zoom(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._window_start = 0
        self._window_end = len(self.points)
        self._draw()

    def _point_at(self, x: int, y: int) -> BankrollPoint | None:
        if not self._visible_points:
            return None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        minimum, maximum = chart_bounds(
            [point.balance for _, point in self._visible_points]
        )
        left, top, right, bottom = 58, 18, width - 14, height - 30
        closest: tuple[float, BankrollPoint] | None = None
        for index, (_, point) in enumerate(self._visible_points):
            point_x = scale_x(index, len(self._visible_points), left, right)
            point_y = scale_y(point.balance, minimum, maximum, top, bottom)
            distance = (point_x - x) ** 2 + (point_y - y) ** 2
            if closest is None or distance < closest[0]:
                closest = (distance, point)
        return closest[1] if closest and closest[0] <= 144 else None

    def _global_index_at_x(self, x: int) -> int | None:
        if not self._visible_points:
            return None
        left, right = 58, self.canvas.winfo_width() - 14
        if right <= left:
            return None
        fraction = min(1.0, max(0.0, (x - left) / (right - left)))
        rendered_index = round(fraction * (len(self._visible_points) - 1))
        return self._visible_points[rendered_index][0]


def _detail_text(point: BankrollPoint) -> str:
    source = {
        BankrollSourceType.HAND: f"Hand {point.source_id}",
        BankrollSourceType.TOURNAMENT_ENTRY: f"Entry {point.source_id}",
        BankrollSourceType.TOURNAMENT: f"Settlement {point.source_id}",
    }[point.source_type]
    return (
        f"{point.occurred_at.strftime('%Y-%m-%d %H:%M UTC')}  {source}  "
        f"{point.result:+.2f} EUR  Total {point.balance:+.2f} EUR"
    )