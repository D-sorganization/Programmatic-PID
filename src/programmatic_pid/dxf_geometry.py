"""Equipment geometry helpers: anchors, bounds, endpoints, and instrument layout."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from programmatic_pid.dxf_math import to_float


def equipment_dims(eq: dict[str, Any]) -> tuple[float, float]:
    """Return ``(width, height)`` of an equipment entry."""
    return to_float(eq.get("w", eq.get("width", 0.0))), to_float(eq.get("h", eq.get("height", 0.0)))


def equipment_center(eq: dict[str, Any]) -> tuple[float, float]:
    """Return the centre point of an equipment item."""
    x = to_float(eq.get("x", 0.0))
    y = to_float(eq.get("y", 0.0))
    w, h = equipment_dims(eq)
    return x + w / 2, y + h / 2


def equipment_side_anchors(eq: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """Return named side-anchor points for an equipment item."""
    x = to_float(eq.get("x", 0.0))
    y = to_float(eq.get("y", 0.0))
    w, h = equipment_dims(eq)
    return {
        "left": (x, y + h / 2),
        "right": (x + w, y + h / 2),
        "top": (x + w / 2, y + h),
        "bottom": (x + w / 2, y),
    }


def equipment_anchor(eq: dict[str, Any], side: str | None, offset: float = 0.0) -> tuple[float, float]:
    """Return the anchor point for a given side of an equipment item."""
    x = to_float(eq.get("x", 0.0))
    y = to_float(eq.get("y", 0.0))
    w, h = equipment_dims(eq)
    side = str(side or "right").lower()
    offset = to_float(offset, 0.0)

    if side == "left":
        return x, y + h / 2 + offset
    if side == "top":
        return x + w / 2 + offset, y + h
    if side == "bottom":
        return x + w / 2 + offset, y
    return x + w, y + h / 2 + offset


def nearest_equipment_anchor(eq: dict[str, Any], source: Sequence[float]) -> tuple[float, float]:
    """Return the closest side-anchor on *eq* to *source*."""
    sx, sy = to_float(source[0]), to_float(source[1])
    anchors = equipment_side_anchors(eq).values()
    return min(anchors, key=lambda p: (p[0] - sx) ** 2 + (p[1] - sy) ** 2)


def get_equipment_bounds(spec: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return ``(x_min, y_min, x_max, y_max)`` bounding box of all equipment."""
    equipment = spec.get("equipment", [])
    if not equipment:
        return 0.0, 0.0, 240.0, 160.0
    x_min = min(to_float(eq.get("x", 0.0)) for eq in equipment)
    y_min = min(to_float(eq.get("y", 0.0)) for eq in equipment)
    x_max = max(to_float(eq.get("x", 0.0)) + equipment_dims(eq)[0] for eq in equipment)
    y_max = max(to_float(eq.get("y", 0.0)) + equipment_dims(eq)[1] for eq in equipment)
    return x_min, y_min, x_max, y_max


def resolve_endpoint(endpoint: dict[str, Any] | None, equipment_by_id: dict[str, Any]) -> tuple[float, float]:
    """Resolve a stream endpoint to ``(x, y)`` coordinates."""
    endpoint = endpoint or {}
    if "point" in endpoint:
        px, py = endpoint["point"]
        return to_float(px), to_float(py)

    eq_id = endpoint.get("equipment")
    if not eq_id or eq_id not in equipment_by_id:
        raise KeyError(f"Unknown equipment endpoint: {eq_id}")
    return equipment_anchor(
        equipment_by_id[eq_id],
        endpoint.get("side", "right"),
        endpoint.get("offset", 0.0),
    )


def spread_instrument_positions(
    instruments: list[dict[str, Any]], min_spacing: float = 3.5
) -> list[dict[str, Any]]:
    """Nudge overlapping instruments apart so they don't collide."""
    placed: list[tuple[float, float]] = []
    output: list[dict[str, Any]] = []
    ring = [
        (0.0, 0.0),
        (2.0, 0.0),
        (-2.0, 0.0),
        (0.0, 2.0),
        (0.0, -2.0),
        (2.0, 2.0),
        (-2.0, 2.0),
        (2.0, -2.0),
        (-2.0, -2.0),
    ]
    spacing = max(to_float(min_spacing, 3.5), 1.2)
    for ins in instruments:
        base_x = to_float(ins.get("x", 0.0))
        base_y = to_float(ins.get("y", 0.0))
        chosen = (base_x, base_y)
        for radius in (1.0, 1.8, 2.6, 3.6):
            found = None
            for ox, oy in ring:
                cand = (base_x + ox * radius, base_y + oy * radius)
                if all((cand[0] - px) ** 2 + (cand[1] - py) ** 2 >= spacing**2 for px, py in placed):
                    found = cand
                    break
            if found is not None:
                chosen = found
                break
        placed.append(chosen)
        copy = dict(ins)
        copy["x"] = chosen[0]
        copy["y"] = chosen[1]
        output.append(copy)
    return output
