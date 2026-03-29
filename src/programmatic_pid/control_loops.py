"""Control loop rendering for P&ID generation."""
from __future__ import annotations

import logging
from typing import Any

from programmatic_pid.dxf_builder import (
    add_arrow_head,
    add_text,
    dedupe_points,
    ensure_layer,
    equipment_center,
    nearest_equipment_anchor,
    to_float,
)

logger = logging.getLogger(__name__)


def resolve_reference_point(
    ref_id: str,
    equipment_by_id: dict[str, Any],
    instrument_by_id: dict[str, Any],
    stream_points: dict[str, tuple[float, float]],
) -> tuple[float, float, str] | None:
    """Resolve a control-loop reference to ``(x, y, kind)`` or ``None``."""
    if not ref_id or not isinstance(ref_id, str):
        raise ValueError("ref_id must be a non-empty string")

    if ref_id in instrument_by_id:
        ins = instrument_by_id[ref_id]
        return to_float(ins.get("x", 0.0)), to_float(ins.get("y", 0.0)), "instrument"

    if ref_id in equipment_by_id:
        cx, cy = equipment_center(equipment_by_id[ref_id])
        return cx, cy, "equipment"

    if ref_id in stream_points:
        sx, sy = stream_points[ref_id]
        return to_float(sx), to_float(sy), "stream"

    return None


def orthogonal_control_route(
    start: tuple[float, float],
    end: tuple[float, float],
    route_index: int = 0,
    spread: float = 4.0,
    corridor_y: float | None = None,
) -> list[tuple[float, float]]:
    """Compute an orthogonal polyline route between two control points."""
    sx, sy = to_float(start[0]), to_float(start[1])
    ex, ey = to_float(end[0]), to_float(end[1])
    if corridor_y is not None:
        detour_y = to_float(corridor_y) - (route_index % 5) * max(to_float(spread), 0.5)
        return dedupe_points([(sx, sy), (sx, detour_y), (ex, detour_y), (ex, ey)])
    offset_band = (route_index % 5) - 2
    center_x = sx + (ex - sx) * 0.5 + offset_band * max(to_float(spread), 0.5)
    return dedupe_points([(sx, sy), (center_x, sy), (center_x, ey), (ex, ey)])


def add_control_loops(
    msp: Any,
    spec: dict[str, Any],
    text_h: float,
    text_layer: str,
    equipment_by_id: dict[str, Any],
    instrument_by_id: dict[str, Any],
    stream_points: dict[str, tuple[float, float]],
    process_bbox: tuple[float, float, float, float] | None = None,
    show_loop_tags: bool = False,
) -> None:
    """Draw all control-loop lines from *spec* onto *msp*.

    Raises:
        ValueError: If *spec* is ``None``.
    """
    if spec is None:
        raise ValueError("spec must not be None")

    loops = spec.get("control_loops", [])
    if not loops:
        return

    defaults = spec.get("defaults", {})
    spread = max(to_float(defaults.get("control_line_offset"), 1.5) * 2.0, 1.0)
    arrow_size = max(text_h * 0.9, 0.9)
    corridor_y: float | None = None
    if process_bbox:
        corridor_y = to_float(process_bbox[1]) - max(spread * 2.2, 3.0)

    for idx, loop in enumerate(loops):
        measurement_id = str(loop.get("measurement", "")).strip()
        final_element_id = str(loop.get("final_element", "")).strip()
        if not measurement_id or not final_element_id:
            logger.warning(
                "Skipped control loop %s: missing measurement/final_element",
                loop.get("id", "<unknown>"),
            )
            continue

        start_ref = resolve_reference_point(measurement_id, equipment_by_id, instrument_by_id, stream_points)
        end_ref = resolve_reference_point(final_element_id, equipment_by_id, instrument_by_id, stream_points)
        if start_ref is None or end_ref is None:
            logger.warning(
                "Skipped control loop %s: unresolved endpoints",
                loop.get("id", "<unknown>"),
            )
            continue

        sx, sy, start_kind = start_ref
        ex, ey, end_kind = end_ref
        if start_kind == "equipment":
            sx, sy = nearest_equipment_anchor(equipment_by_id[measurement_id], (ex, ey))
        if end_kind == "equipment":
            ex, ey = nearest_equipment_anchor(equipment_by_id[final_element_id], (sx, sy))

        layer = str(loop.get("line_layer") or "control_lines")
        if layer not in msp.doc.layers:
            ensure_layer(msp.doc, layer, color=1, linetype="DASHDOT")

        route = orthogonal_control_route(
            (sx, sy),
            (ex, ey),
            route_index=idx,
            spread=spread,
            corridor_y=corridor_y,
        )
        if len(route) < 2:
            continue

        msp.add_lwpolyline(route, dxfattribs={"layer": layer})
        add_arrow_head(msp, route[-2], route[-1], layer=layer, arrow_size=arrow_size)

        loop_tag = str(loop.get("tag") or loop.get("id") or "").strip()
        if loop_tag and show_loop_tags:
            mx = sum(p[0] for p in route) / len(route)
            my = sum(p[1] for p in route) / len(route)
            add_text(msp, loop_tag, mx, my + text_h * 0.8, text_h * 0.9, layer=text_layer)
