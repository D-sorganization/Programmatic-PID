"""Low-level DXF creation primitives: shapes, text, arrows, layers.

This module is the public interface for DXF drawing helpers.  The implementation
has been split into focused sub-modules for maintainability:

- :mod:`dxf_math`     – numeric helpers and bounding-box geometry
- :mod:`dxf_text`     – text utilities and label placement
- :mod:`dxf_layer`    – layer management
- :mod:`dxf_symbols`  – equipment shape primitives
- :mod:`dxf_geometry` – equipment geometry and endpoint resolution
- :mod:`dxf_arrows`   – arrow drawing primitives

All public names are re-exported here so existing imports remain unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

from programmatic_pid.dxf_arrows import add_arrow, add_arrow_head, add_poly_arrow
from programmatic_pid.dxf_geometry import (
    equipment_anchor,
    equipment_center,
    equipment_dims,
    equipment_side_anchors,
    get_equipment_bounds,
    nearest_equipment_anchor,
    resolve_endpoint,
    spread_instrument_positions,
)
from programmatic_pid.dxf_layer import ensure_layer, ensure_layers, layer_name
from programmatic_pid.dxf_math import (
    clamp,
    closest_point_on_rect,
    dedupe_points,
    rects_overlap,
    text_box,
    to_float,
)
from programmatic_pid.dxf_symbols import (
    add_bin_symbol,
    add_box,
    add_burner_symbol,
    add_fan_symbol,
    add_hopper,
    add_rotary_valve_symbol,
    draw_equipment_symbol,
)
from programmatic_pid.dxf_text import (
    LabelPlacer,
    TextEntityAlignment,
    add_text,
    add_text_panel,
    parse_alignment,
    wrap_text_lines,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-export everything for backward compatibility
# ---------------------------------------------------------------------------

__all__ = [
    # dxf_math
    "to_float",
    "clamp",
    "text_box",
    "rects_overlap",
    "closest_point_on_rect",
    # dxf_text
    "parse_alignment",
    "wrap_text_lines",
    "LabelPlacer",
    "TextEntityAlignment",
    "add_text",
    "add_text_panel",
    # dxf_layer
    "ensure_layer",
    "ensure_layers",
    "layer_name",
    # dxf_symbols
    "add_box",
    "add_hopper",
    "add_fan_symbol",
    "add_rotary_valve_symbol",
    "add_burner_symbol",
    "add_bin_symbol",
    "draw_equipment_symbol",
    # dxf_arrows
    "add_arrow_head",
    "add_arrow",
    "add_poly_arrow",
    # dxf_geometry
    "equipment_dims",
    "equipment_center",
    "equipment_side_anchors",
    "equipment_anchor",
    "nearest_equipment_anchor",
    "get_equipment_bounds",
    "resolve_endpoint",
    "dedupe_points",
    "spread_instrument_positions",
    # high-level renderers (defined below)
    "add_equipment",
    "add_instrument",
]


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
