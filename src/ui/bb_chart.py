from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from poker_stats.bb_history_service import BBHistoryPoint
from ui.chart_math import chart_bounds, scale_x, scale_y


class BBChart(ttk.Frame):
    MAX_RENDERED_POINTS = 1_200

    def __init__(
        self,
        master: tk.Misc | None = None,
        on_hand_selected: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.points: list[BBHistoryPoint] = []
        self._window_start = 0
        self._window_end = 0
        self._selection_start: int | None = None
        self._selection_end: int | None = None
        self._visible_points: list[BBHistoryPoint] = []
        self.on_hand_selected = on_hand_selected
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, height=220, highlightthickness=0, background="#ffffff")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.detail = ttk.Label(self, text="Hover a hand for BB details")
        self.detail.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.canvas.bind("<Configure>", self._draw)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<Button-3>", self._reset_zoom)

    def set_points(self, points: list[BBHistoryPoint]) -> None:
        self.points = points
        self._window_start = 0
        self._window_end = len(points)
        self.detail.configure(text="Hover a hand for BB details")
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
                text="No cash hands with blinds in this scope",
                fill="#666666",
            )
            self._visible_points = []
            return
        selected_points = self.points[self._window_start : self._window_end]
        self._visible_points = self._render_points(selected_points)
        values = [point.balance_bb for point in self._visible_points]
        minimum, maximum = chart_bounds(values)
        left, top, right, bottom = 50, 18, width - 14, height - 30
        zero_y = scale_y(0.0, minimum, maximum, top, bottom)
        self.canvas.create_line(left, zero_y, right, zero_y, fill="#d8d8d8")
        self.canvas.create_text(
            left - 6, top, text=f"{maximum:+.1f}", anchor="e", fill="#666666"
        )
        self.canvas.create_text(
            left - 6, bottom, text=f"{minimum:+.1f}", anchor="e", fill="#666666"
        )
        coordinates = [
            (
                scale_x(index, len(self._visible_points), left, right),
                scale_y(point.balance_bb, minimum, maximum, top, bottom),
            )
            for index, point in enumerate(self._visible_points)
        ]
        if len(coordinates) > 1:
            line_coordinates = [value for coordinate in coordinates for value in coordinate]
            self.canvas.create_line(*line_coordinates, fill="#a95522", width=2)
        for x, y in coordinates:
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#a95522", outline="")
        if self._selection_start is not None and self._selection_end is not None:
            self.canvas.create_rectangle(
                self._selection_start,
                top,
                self._selection_end,
                bottom,
                outline="#a95522",
                dash=(3, 3),
            )

    def _on_motion(self, event: tk.Event[tk.Misc]) -> None:
        point = self._point_at(event.x, event.y)
        self.detail.configure(text=_detail_text(point) if point else "Hover a hand for BB details")

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        self.detail.configure(text="Hover a hand for BB details")

    def _on_drag_start(self, event: tk.Event[tk.Misc]) -> None:
        self._selection_start = event.x
        self._selection_end = event.x

    def _on_drag(self, event: tk.Event[tk.Misc]) -> None:
        if self._selection_start is None:
            return
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
            if point is not None and self.on_hand_selected is not None:
                self.on_hand_selected(point.hand_id)
            return
        selected_start = self._index_at_x(start_x)
        selected_end = self._index_at_x(end_x)
        if selected_start is not None and selected_end is not None:
            self._window_start += min(selected_start, selected_end)
            self._window_end = self._window_start + abs(selected_end - selected_start) + 1
        self._draw()

    def _reset_zoom(self, _event: tk.Event[tk.Misc]) -> None:
        self._window_start = 0
        self._window_end = len(self.points)
        self._draw()

    def _point_at(self, x: int, y: int) -> BBHistoryPoint | None:
        if not self._visible_points:
            return None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        minimum, maximum = chart_bounds([point.balance_bb for point in self._visible_points])
        left, top, right, bottom = 50, 18, width - 14, height - 30
        closest: tuple[float, BBHistoryPoint] | None = None
        for index, point in enumerate(self._visible_points):
            point_x = scale_x(index, len(self._visible_points), left, right)
            point_y = scale_y(point.balance_bb, minimum, maximum, top, bottom)
            distance = (point_x - x) ** 2 + (point_y - y) ** 2
            if closest is None or distance < closest[0]:
                closest = (distance, point)
        return closest[1] if closest and closest[0] <= 144 else None

    def _index_at_x(self, x: int) -> int | None:
        if not self._visible_points:
            return None
        left, right = 50, self.canvas.winfo_width() - 14
        if right <= left:
            return None
        fraction = min(1.0, max(0.0, (x - left) / (right - left)))
        return round(fraction * (len(self._visible_points) - 1))

    @classmethod
    def _render_points(cls, points: list[BBHistoryPoint]) -> list[BBHistoryPoint]:
        if len(points) <= cls.MAX_RENDERED_POINTS:
            return points

        step = (len(points) - 1) / (cls.MAX_RENDERED_POINTS - 1)
        return [points[round(index * step)] for index in range(cls.MAX_RENDERED_POINTS)]


def _detail_text(point: BBHistoryPoint) -> str:
    return (
        f"{point.occurred_at.strftime('%Y-%m-%d %H:%M')}  Hand {point.hand_id}  "
        f"{point.hero_cards or '--'}  Pot {point.pot:.2f}  "
        f"{point.result_bb:+.2f} BB  Total {point.balance_bb:+.2f} BB"
    )