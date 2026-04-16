"""DXF arrow drawing primitives."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from programmatic_pid.dxf_math import to_float


def add_arrow_head(
    msp: Any,
    s: Sequence[float],
    e: Sequence[float],
    layer: str,
    color: int | None = None,
    arrow_size: float = 1.6,
) -> None:
    """Draw an arrowhead solid at the end of a line segment."""
    sx, sy = to_float(s[0]), to_float(s[1])
    ex, ey = to_float(e[0]), to_float(e[1])
    attrs: dict[str, Any] = {"layer": layer}
    if color is not None:
        attrs["color"] = int(color)

    ang = math.atan2(ey - sy, ex - sx)
    ah = max(to_float(arrow_size, 1.6), 0.2)
    aw = ah * 0.45
    p1 = (ex, ey)
    p2 = (
        ex - ah * math.cos(ang) + aw * math.sin(ang),
        ey - ah * math.sin(ang) - aw * math.cos(ang),
    )
    p3 = (
        ex - ah * math.cos(ang) - aw * math.sin(ang),
        ey - ah * math.sin(ang) + aw * math.cos(ang),
    )
    msp.add_solid([p1, p2, p3, p3], dxfattribs=attrs)


def add_arrow(
    msp: Any,
    s: Sequence[float],
    e: Sequence[float],
    layer: str,
    color: int | None = None,
    arrow_size: float = 1.6,
) -> None:
    """Draw a line with an arrowhead at the end."""
    sx, sy = to_float(s[0]), to_float(s[1])
    ex, ey = to_float(e[0]), to_float(e[1])
    attrs: dict[str, Any] = {"layer": layer}
    if color is not None:
        attrs["color"] = int(color)

    msp.add_line((sx, sy), (ex, ey), dxfattribs=attrs)
    add_arrow_head(msp, (sx, sy), (ex, ey), layer=layer, color=color, arrow_size=arrow_size)


def add_poly_arrow(
    msp: Any,
    verts: list[Sequence[float]],
    layer: str,
    color: int | None = None,
    arrow_size: float = 1.6,
) -> None:
    """Draw a polyline with an arrowhead at the last vertex."""
    points = [(to_float(v[0]), to_float(v[1])) for v in verts if len(v) >= 2]
    if len(points) < 2:
        return

    attrs: dict[str, Any] = {"layer": layer}
    if color is not None:
        attrs["color"] = int(color)
    msp.add_lwpolyline(points, dxfattribs=attrs)
    add_arrow_head(msp, points[-2], points[-1], layer, color=color, arrow_size=arrow_size)
