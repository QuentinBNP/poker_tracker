from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from poker_stats.bankroll_service import BankrollPoint, BankrollSourceType


class BankrollChart(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master)
        self.points: list[BankrollPoint] = []
        self.zoom = 1.0
        self.pan_fraction = 0.0
        self._drag_x: int | None = None
        self._visible_points: list[BankrollPoint] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, height=220, highlightthickness=0, background="#ffffff")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.detail = ttk.Label(self, text="Hover a point for details")
        self.detail.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.canvas.bind("<Configure>", self._draw)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda _event: self._change_zoom(1.2))
        self.canvas.bind("<Button-5>", lambda _event: self._change_zoom(1 / 1.2))

    def set_points(self, points: list[BankrollPoint]) -> None:
        self.points = points
        self.zoom = 1.0
        self.pan_fraction = 0.0
        self.detail.configure(text="Hover a point for details")
        self._draw()

    def _draw(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 20 or height < 20:
            return
        if not self.points:
            self.canvas.create_text(
                width / 2,
                height / 2,
                text="No settled results in this scope",
                fill="#666666",
            )
            self._visible_points = []
            return

        visible_count = max(2, min(len(self.points), round(len(self.points) / self.zoom)))
        max_start = max(0, len(self.points) - visible_count)
        start = round(max_start * self.pan_fraction)
        self._visible_points = self.points[start : start + visible_count]
        balances = [point.balance for point in self._visible_points]
        minimum, maximum = _chart_bounds(balances)
        left, top, right, bottom = 50, 18, width - 14, height - 30

        zero_y = _scale_y(0.0, minimum, maximum, top, bottom)
        self.canvas.create_line(left, zero_y, right, zero_y, fill="#d8d8d8")
        self.canvas.create_text(left - 6, top, text=f"{maximum:+.2f}", anchor="e", fill="#666666")
        self.canvas.create_text(
            left - 6, bottom, text=f"{minimum:+.2f}", anchor="e", fill="#666666"
        )
        self.canvas.create_text(
            left,
            bottom + 14,
            text=self._visible_points[0].occurred_at.strftime("%d %b"),
            anchor="w",
            fill="#666666",
        )
        self.canvas.create_text(
            right,
            bottom + 14,
            text=self._visible_points[-1].occurred_at.strftime("%d %b"),
            anchor="e",
            fill="#666666",
        )

        coordinates = [
            (
                _scale_x(index, len(self._visible_points), left, right),
                _scale_y(point.balance, minimum, maximum, top, bottom),
            )
            for index, point in enumerate(self._visible_points)
        ]
        if len(coordinates) > 1:
            line_coordinates = [coordinate for point in coordinates for coordinate in point]
            self.canvas.create_line(*line_coordinates, fill="#167c80", width=2)
        for x, y in coordinates:
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#167c80", outline="")

    def _on_motion(self, event: tk.Event[tk.Misc]) -> None:
        point = self._point_at(event.x, event.y)
        if point is None:
            self.detail.configure(text="Hover a point for details")
            return
        source = "Hand" if point.source_type is BankrollSourceType.HAND else "Tournament"
        self.detail.configure(
            text=(
                f"{point.occurred_at.strftime('%Y-%m-%d %H:%M')}  "
                f"{source} {point.source_id}  {point.result:+.2f} EUR  "
                f"Balance {point.balance:+.2f} EUR"
            )
        )

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        self.detail.configure(text="Hover a point for details")

    def _on_drag_start(self, event: tk.Event[tk.Misc]) -> None:
        self._drag_x = event.x

    def _on_drag(self, event: tk.Event[tk.Misc]) -> None:
        if self._drag_x is None or self.zoom <= 1.0:
            return
        width = max(1, self.canvas.winfo_width())
        self.pan_fraction = min(1.0, max(0.0, self.pan_fraction - (event.x - self._drag_x) / width))
        self._drag_x = event.x
        self._draw()

    def _on_drag_end(self, _event: tk.Event[tk.Misc]) -> None:
        self._drag_x = None

    def _on_mouse_wheel(self, event: tk.Event[tk.Misc]) -> None:
        self._change_zoom(1.2 if event.delta > 0 else 1 / 1.2)

    def _change_zoom(self, multiplier: float) -> None:
        self.zoom = min(12.0, max(1.0, self.zoom * multiplier))
        if self.zoom == 1.0:
            self.pan_fraction = 0.0
        self._draw()

    def _point_at(self, x: int, y: int) -> BankrollPoint | None:
        if not self._visible_points:
            return None
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        minimum, maximum = _chart_bounds([point.balance for point in self._visible_points])
        left, top, right, bottom = 50, 18, width - 14, height - 30
        closest: tuple[float, BankrollPoint] | None = None
        for index, point in enumerate(self._visible_points):
            point_x = _scale_x(index, len(self._visible_points), left, right)
            point_y = _scale_y(point.balance, minimum, maximum, top, bottom)
            distance = (point_x - x) ** 2 + (point_y - y) ** 2
            if closest is None or distance < closest[0]:
                closest = (distance, point)
        return closest[1] if closest is not None and closest[0] <= 144 else None


def _chart_bounds(values: list[float]) -> tuple[float, float]:
    minimum = min(0.0, min(values))
    maximum = max(0.0, max(values))
    if minimum == maximum:
        return minimum - 1.0, maximum + 1.0
    padding = (maximum - minimum) * 0.1
    return minimum - padding, maximum + padding


def _scale_x(index: int, count: int, left: int, right: int) -> float:
    if count <= 1:
        return (left + right) / 2
    return left + ((right - left) * index / (count - 1))


def _scale_y(value: float, minimum: float, maximum: float, top: int, bottom: int) -> float:
    return bottom - ((value - minimum) / (maximum - minimum) * (bottom - top))