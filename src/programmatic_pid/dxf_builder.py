"""Low-level DXF creation primitives: shapes, text, arrows, layers."""

from __future__ import annotations

import logging
import math
import textwrap
from collections.abc import Sequence
from typing import Any

import ezdxf
from ezdxf.enums import TextEntityAlignment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def to_float(value: Any, default: float = 0.0) -> float:
    """Convert *value* to float, returning *default* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* between *lo* and *hi*."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------


def parse_alignment(align: Any) -> TextEntityAlignment:
    """Return a :class:`TextEntityAlignment` from a string or pass-through."""
    if isinstance(align, TextEntityAlignment):
        return align
    key = str(align or "MIDDLE_CENTER").upper()
    return getattr(TextEntityAlignment, key, TextEntityAlignment.MIDDLE_CENTER)


def wrap_text_lines(text: str, width: int) -> list[str]:
    """Word-wrap *text* to *width* characters."""
    if not isinstance(text, str):
        text = str(text)
    if not isinstance(width, int) or width < 12:
        width = 12
    chunks = textwrap.wrap(
        text,
        width=max(int(width), 12),
        break_long_words=False,
        break_on_hyphens=False,
    )
    return chunks if chunks else [text]


# ---------------------------------------------------------------------------
# Bounding-box helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Label collision avoidance
# ---------------------------------------------------------------------------


class LabelPlacer:
    """Tracks occupied rectangles and finds non-overlapping label positions."""

    def __init__(self) -> None:
        self.occupied: list[tuple[float, float, float, float]] = []

    def reserve_rect(self, rect: tuple[float, float, float, float]) -> None:
        """Register *rect* as occupied space."""
        self.occupied.append(rect)

    def reserve_text(self, text: str, x: float, y: float, h: float, align: str = "MIDDLE_CENTER") -> None:
        """Reserve the bounding box of a text label."""
        self.reserve_rect(text_box(text, x, y, h, align=align))

    def find_position(
        self,
        text: str,
        anchor: tuple[float, float],
        h: float,
        preferred: list[tuple[float, float, str]],
    ) -> tuple[float, float, str]:
        """Find the first non-overlapping position from *preferred* offsets."""
        ax, ay = to_float(anchor[0]), to_float(anchor[1])
        for dx, dy, align in preferred:
            x = ax + dx
            y = ay + dy
            candidate = text_box(text, x, y, h, align=align)
            if not any(rects_overlap(candidate, r, pad=h * 0.20) for r in self.occupied):
                self.reserve_rect(candidate)
                return x, y, align
        fallback = preferred[0]
        x = ax + fallback[0]
        y = ay + fallback[1]
        align = fallback[2]
        self.reserve_rect(text_box(text, x, y, h, align=align))
        return x, y, align


# ---------------------------------------------------------------------------
# Layer helpers
# ---------------------------------------------------------------------------


def ensure_layer(doc: Any, name: str, color: int = 7, linetype: str = "CONTINUOUS") -> None:
    """Create a DXF layer if it does not already exist."""
    if not name:
        return
    if name in doc.layers:
        return
    attrs = {"color": int(color), "linetype": str(linetype)}
    try:
        doc.layers.new(name=name, dxfattribs=attrs)
    except ezdxf.DXFValueError:
        attrs["linetype"] = "CONTINUOUS"
        doc.layers.new(name=name, dxfattribs=attrs)


def ensure_layers(doc: Any, spec: dict[str, Any]) -> None:
    """Create all layers referenced in *spec* plus sensible defaults."""
    from programmatic_pid.generator import get_layer_config

    for name, cfg in get_layer_config(spec).items():
        cfg = cfg or {}
        ensure_layer(doc, name, color=cfg.get("color", 7), linetype=cfg.get("linetype", "CONTINUOUS"))

    for name, color in (
        ("TEXT", 7),
        ("NOTES", 3),
        ("LEADERS", 8),
        ("EQUIPMENT", 7),
        ("INSTRUMENTS", 2),
        ("PROCESS", 5),
    ):
        ltype = "DASHED" if name == "LEADERS" else "CONTINUOUS"
        ensure_layer(doc, name, color=color, linetype=ltype)


def layer_name(layer_index: dict[str, str], *candidates: str, default: str = "0") -> str:
    """Resolve the first matching layer name from *candidates*."""
    for candidate in candidates:
        if not candidate:
            continue
        actual = layer_index.get(str(candidate).lower())
        if actual:
            return actual
    return default


# ---------------------------------------------------------------------------
# DXF drawing primitives
# ---------------------------------------------------------------------------


def add_text(
    msp: Any,
    text: str,
    x: float,
    y: float,
    h: float,
    layer: str = "TEXT",
    align: str = "MIDDLE_CENTER",
) -> Any:
    """Add a text entity to *msp*."""
    t = msp.add_text(str(text), dxfattribs={"height": max(to_float(h, 1.0), 0.1), "layer": layer})
    t.set_placement((to_float(x), to_float(y)), align=parse_alignment(align))
    return t


def add_text_panel(
    msp: Any,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: list[str],
    text_h: float,
    text_layer: str,
    border_layer: str,
    max_chars: int = 42,
) -> None:
    """Draw a bordered text panel with a title and wrapped body lines."""
    add_box(msp, x, y, w, h, border_layer)
    inset_x = x + 1.1
    inset_top = y + h - 1.0
    add_text(msp, title, inset_x, inset_top, text_h * 1.05, layer=text_layer, align="TOP_LEFT")

    step = max(text_h * 1.16, 0.9)
    available = max(int((h - 2.6) / step), 1)
    out: list[str] = []
    for line in lines:
        if line is None:
            out.append("")
            continue
        out.extend(wrap_text_lines(line, max_chars))
    out = out[:available]

    cy = inset_top - max(text_h * 1.55, 1.1)
    for line in out:
        add_text(msp, line, inset_x, cy, text_h, layer=text_layer, align="TOP_LEFT")
        cy -= step


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


# ---------------------------------------------------------------------------
# Equipment geometry helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Equipment and instrument rendering
# ---------------------------------------------------------------------------


def add_equipment(
    msp: Any,
    eq: dict[str, Any],
    text_h: float,
    text_layer: str,
    notes_layer: str,
    show_inline_notes: bool = False,
) -> None:
    """Draw a single equipment item with its label and optional notes."""
    x = to_float(eq.get("x", 0.0))
    y = to_float(eq.get("y", 0.0))
    w, hh = equipment_dims(eq)
    if w <= 0 or hh <= 0:
        return

    layer = eq.get("layer", "EQUIPMENT")
    eq_type = str(eq.get("type", "")).lower()
    subtype = str(eq.get("subtype", "")).lower()

    draw_equipment_symbol(msp, eq, layer)

    eq_id = str(eq.get("id", "")).strip()
    service = str(eq.get("service") or eq.get("name") or eq.get("tag") or "").strip()
    if eq_id and service and service != eq_id:
        add_text(msp, eq_id, x + w / 2, y + hh / 2 + text_h * 0.48, text_h, layer=text_layer)
        add_text(msp, service, x + w / 2, y + hh / 2 - text_h * 0.52, text_h * 0.82, layer=text_layer)
    elif eq_id:
        add_text(msp, eq_id, x + w / 2, y + hh / 2, text_h, layer=text_layer)

    if eq_type == "vertical_retort" or subtype == "vertical_retort":
        for zone in eq.get("zones", []):
            zy = y + hh * to_float(zone.get("y_frac", 0.0))
            add_text(msp, zone.get("name", ""), x + w / 2, zy + text_h * 0.6, text_h * 0.7, layer=text_layer)

    if show_inline_notes:
        note_step = max(text_h * 1.2, 0.8)
        for i, note in enumerate(eq.get("notes", [])[:2]):
            add_text(
                msp,
                f"- {note}",
                x,
                y - note_step * (i + 1),
                text_h * 0.62,
                layer=notes_layer,
                align="TOP_LEFT",
            )


def add_instrument(
    msp: Any,
    instrument: dict[str, Any],
    text_h: float,
    text_layer: str,
    default_layer: str,
    radius: float,
    show_number_suffix: bool = False,
    label_placer: LabelPlacer | None = None,
) -> None:
    """Draw a single instrument bubble with its tag."""
    layer = instrument.get("layer", default_layer)
    x = to_float(instrument.get("x", 0.0))
    y = to_float(instrument.get("y", 0.0))
    bubble = str(instrument.get("tag") or instrument.get("id") or "").strip()
    number = str(instrument.get("id", "")).split("-", 1)[-1]

    r = max(to_float(radius, 1.8), 0.4)
    msp.add_circle((x, y), radius=r, dxfattribs={"layer": layer})
    if label_placer is not None:
        label_placer.reserve_rect((x - r, y - r, x + r, y + r))
    add_text(msp, bubble, x, y, max(text_h * 0.45, 0.5), layer=text_layer)
    if show_number_suffix and number:
        add_text(
            msp,
            number,
            x + max(to_float(radius, 1.8), 0.4) + 0.5,
            y,
            max(text_h * 0.5, 0.5),
            layer=text_layer,
            align="MIDDLE_LEFT",
        )
