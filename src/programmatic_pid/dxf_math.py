"""Numeric and geometric math helpers for DXF drawing."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def to_float(value: Any, default: float = 0.0) -> float:
    """Convert *value* to float, returning *default* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* between *lo* and *hi*."""
    return max(lo, min(hi, value))


def text_box(
    text: str, x: float, y: float, h: float, align: str = "MIDDLE_CENTER"
) -> tuple[float, float, float, float]:
    """Return an approximate bounding rectangle ``(x1, y1, x2, y2)`` for placed text."""
    text = str(text)
    h = max(to_float(h, 1.0), 0.1)
    width = max(len(text), 1) * h * 0.55
    height = h * 1.2
    align = str(align or "MIDDLE_CENTER").upper()
    if "LEFT" in align:
        x1, x2 = x, x + width
    elif "RIGHT" in align:
        x1, x2 = x - width, x
    else:
        x1, x2 = x - width / 2, x + width / 2

    if "TOP" in align:
        y1, y2 = y - height, y
    elif "BOTTOM" in align:
        y1, y2 = y, y + height
    else:
        y1, y2 = y - height / 2, y + height / 2
    return (x1, y1, x2, y2)


def rects_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    pad: float = 0.0,
) -> bool:
    """Return ``True`` if rectangles *a* and *b* overlap (with optional padding)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 + pad <= bx1 or bx2 + pad <= ax1 or ay2 + pad <= by1 or by2 + pad <= ay1)


def closest_point_on_rect(
    point: Sequence[float], rect: tuple[float, float, float, float]
) -> tuple[float, float]:
    """Return the closest point on *rect* to *point*."""
    px, py = to_float(point[0]), to_float(point[1])
    x1, y1, x2, y2 = rect
    return clamp(px, x1, x2), clamp(py, y1, y2)


def dedupe_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Remove consecutive duplicate points."""
    cleaned: list[tuple[float, float]] = []
    for p in points:
        if not cleaned:
            cleaned.append((to_float(p[0]), to_float(p[1])))
            continue
        px, py = cleaned[-1]
        qx, qy = to_float(p[0]), to_float(p[1])
        if abs(px - qx) < 1e-9 and abs(py - qy) < 1e-9:
            continue
        cleaned.append((qx, qy))
    return cleaned
