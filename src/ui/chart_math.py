from __future__ import annotations


def chart_bounds(values: list[float]) -> tuple[float, float]:
    minimum = min(0.0, min(values))
    maximum = max(0.0, max(values))
    if minimum == maximum:
        return minimum - 1.0, maximum + 1.0
    padding = (maximum - minimum) * 0.1
    return minimum - padding, maximum + padding


def scale_x(index: int, count: int, left: int, right: int) -> float:
    if count <= 1:
        return (left + right) / 2
    return left + ((right - left) * index / (count - 1))


def scale_y(value: float, minimum: float, maximum: float, top: int, bottom: int) -> float:
    return bottom - ((value - minimum) / (maximum - minimum) * (bottom - top))