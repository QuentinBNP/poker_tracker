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


def sampled_indices(values: list[float], maximum_points: int) -> list[int]:
    if maximum_points < 2:
        raise ValueError("maximum_points must be at least 2")
    if len(values) <= maximum_points:
        return list(range(len(values)))

    required = {0, len(values) - 1, values.index(min(values)), values.index(max(values))}
    step = (len(values) - 1) / (maximum_points - 1)
    candidates = [round(index * step) for index in range(maximum_points)]
    selected = set(required)
    for index in candidates:
        if len(selected) >= maximum_points:
            break
        selected.add(index)
    if len(selected) < maximum_points:
        for index in range(len(values)):
            selected.add(index)
            if len(selected) >= maximum_points:
                break
    return sorted(selected)