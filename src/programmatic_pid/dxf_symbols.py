"""DXF equipment shape symbols and drawing primitives."""

from __future__ import annotations

from typing import Any

from programmatic_pid.dxf_math import to_float


def add_box(msp: Any, x: float, y: float, w: float, h: float, layer: str) -> None:
    """Draw a rectangular polyline on *layer*."""
    if w <= 0 or h <= 0:
        raise ValueError(f"Box dimensions must be positive, got w={w}, h={h}")
    x = to_float(x)
    y = to_float(y)
    w = to_float(w)
    h = to_float(h)
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


def add_hopper(msp: Any, x: float, y: float, w: float, h: float, layer: str) -> None:
    """Draw a hopper (tapered trapezoid) symbol."""
    x = to_float(x)
    y = to_float(y)
    w = to_float(w)
    h = to_float(h)
    bot_w = w * 0.72
    cx = x + w / 2
    pts = [(x, y + h), (x + w, y + h), (cx + bot_w / 2, y), (cx - bot_w / 2, y)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


def add_fan_symbol(msp: Any, x: float, y: float, w: float, h: float, layer: str) -> None:
    """Draw a fan symbol (circle + blade)."""
    cx = x + w / 2
    cy = y + h / 2
    r = max(min(w, h) * 0.42, 0.5)
    msp.add_circle((cx, cy), radius=r, dxfattribs={"layer": layer})
    blade = [(cx - r * 0.25, cy), (cx + r * 0.45, cy + r * 0.20), (cx + r * 0.45, cy - r * 0.20)]
    msp.add_lwpolyline(blade, close=True, dxfattribs={"layer": layer})


def add_rotary_valve_symbol(msp: Any, x: float, y: float, w: float, h: float, layer: str) -> None:
    """Draw a rotary valve symbol."""
    cx = x + w / 2
    cy = y + h / 2
    r = max(min(w, h) * 0.35, 0.5)
    msp.add_circle((cx, cy), radius=r, dxfattribs={"layer": layer})
    msp.add_line((cx - r * 0.85, cy - r * 0.85), (cx + r * 0.85, cy + r * 0.85), dxfattribs={"layer": layer})
    msp.add_line((cx - r * 0.85, cy + r * 0.85), (cx + r * 0.85, cy - r * 0.85), dxfattribs={"layer": layer})


def add_burner_symbol(msp: Any, x: float, y: float, w: float, h: float, layer: str) -> None:
    """Draw a burner symbol (box + flame)."""
    add_box(msp, x, y, w, h, layer)
    cx = x + w / 2
    flame = [
        (cx, y + h * 0.76),
        (cx + w * 0.10, y + h * 0.48),
        (cx, y + h * 0.22),
        (cx - w * 0.10, y + h * 0.48),
    ]
    msp.add_lwpolyline(flame, close=True, dxfattribs={"layer": layer})


def add_bin_symbol(msp: Any, x: float, y: float, w: float, h: float, layer: str) -> None:
    """Draw a bin/silo symbol."""
    add_box(msp, x, y, w, h, layer)
    msp.add_line((x, y + h), (x + w, y + h), dxfattribs={"layer": layer})
    msp.add_line(
        (x + w * 0.1, y + h + h * 0.12), (x + w * 0.9, y + h + h * 0.12), dxfattribs={"layer": layer}
    )


def draw_equipment_symbol(msp: Any, eq: dict[str, Any], layer: str) -> None:
    """Dispatch to the appropriate equipment shape renderer."""
    from programmatic_pid.dxf_geometry import equipment_dims

    x = to_float(eq.get("x", 0.0))
    y = to_float(eq.get("y", 0.0))
    w, h = equipment_dims(eq)
    eq_type = str(eq.get("type", "")).lower()
    subtype = str(eq.get("subtype", "")).lower()

    if eq_type == "hopper":
        add_hopper(msp, x, y, w, h, layer)
        return
    if eq_type == "fan":
        add_fan_symbol(msp, x, y, w, h, layer)
        return
    if eq_type == "rotary_valve":
        add_rotary_valve_symbol(msp, x, y, w, h, layer)
        return
    if eq_type == "burner":
        add_burner_symbol(msp, x, y, w, h, layer)
        return
    if eq_type == "bin":
        add_bin_symbol(msp, x, y, w, h, layer)
        return

    add_box(msp, x, y, w, h, layer)

    if eq_type == "vertical_retort" or subtype == "vertical_retort":
        for zone in eq.get("zones", []):
            zy = y + h * to_float(zone.get("y_frac", 0.0))
            msp.add_line((x + 0.6, zy), (x + w - 0.6, zy), dxfattribs={"layer": layer})
