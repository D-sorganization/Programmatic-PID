#!/usr/bin/env python3
"""P&ID generation entry-point — delegates to focused sub-modules.

This module is the public API surface.  It re-exports every symbol that
previously lived here so that existing ``import programmatic_pid.generator as mod``
continues to work without changes.
"""

from __future__ import annotations

import argparse
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import ezdxf
import yaml

# Re-export everything that used to live in this single file so the public
# interface is unchanged.
from programmatic_pid.control_loops import (  # noqa: F401
    add_control_loops,
    orthogonal_control_route,
    resolve_reference_point,
)
from programmatic_pid.dxf_builder import (  # noqa: F401
    LabelPlacer,
    add_arrow,
    add_arrow_head,
    add_bin_symbol,
    add_box,
    add_burner_symbol,
    add_equipment,
    add_fan_symbol,
    add_hopper,
    add_instrument,
    add_poly_arrow,
    add_rotary_valve_symbol,
    add_text,
    add_text_panel,
    clamp,
    closest_point_on_rect,
    dedupe_points,
    draw_equipment_symbol,
    ensure_layer,
    ensure_layers,
    equipment_anchor,
    equipment_center,
    equipment_dims,
    equipment_side_anchors,
    get_equipment_bounds,
    layer_name,
    nearest_equipment_anchor,
    parse_alignment,
    rects_overlap,
    resolve_endpoint,
    spread_instrument_positions,
    text_box,
    to_float,
    wrap_text_lines,
)
from programmatic_pid.notes import (  # noqa: F401
    add_notes,
    get_mass_balance_values,
)
from programmatic_pid.stream_router import add_stream  # noqa: F401
from programmatic_pid.validator import SpecValidationError, validate_spec  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profile presets
# ---------------------------------------------------------------------------

PROFILE_PRESETS: dict[str, dict[str, Any]] = {
    "review": {
        "layout": {
            "show_inline_equipment_notes": True,
            "show_instrument_suffix": True,
            "show_control_tags_on_lines": True,
            "gap": 9.0,
            "right_panel_width": 96.0,
            "bottom_panel_height": 40.0,
            "title_block_height": 12.0,
            "panel_text_chars": 52,
            "stream_label_scale": 0.82,
            "stream_label_leaders": True,
            "instrument_spacing_factor": 2.6,
            "controls_row_height_scale": 4.0,
        },
        "defaults": {
            "instrument_bubble_radius": 1.8,
        },
    },
    "presentation": {
        "layout": {
            "show_inline_equipment_notes": False,
            "show_instrument_suffix": False,
            "show_control_tags_on_lines": False,
            "gap": 8.0,
            "right_panel_width": 90.0,
            "bottom_panel_height": 36.0,
            "title_block_height": 11.0,
            "panel_text_chars": 44,
            "stream_label_scale": 0.76,
            "stream_label_leaders": True,
            "instrument_spacing_factor": 2.2,
            "controls_row_height_scale": 3.4,
        }
    },
    "compact": {
        "layout": {
            "show_inline_equipment_notes": False,
            "show_instrument_suffix": False,
            "show_control_tags_on_lines": False,
            "gap": 6.0,
            "right_panel_width": 74.0,
            "bottom_panel_height": 28.0,
            "title_block_height": 9.0,
            "panel_text_chars": 34,
            "stream_label_scale": 0.64,
            "stream_label_leaders": True,
            "instrument_spacing_factor": 1.8,
            "controls_row_height_scale": 2.8,
        },
        "defaults": {
            "instrument_bubble_radius": 1.4,
        },
    },
}


# ---------------------------------------------------------------------------
# Spec loading / config helpers
# ---------------------------------------------------------------------------


def load_spec(path: str | Path) -> dict[str, Any]:
    """Load a YAML specification file.

    Raises:
        ValueError: If *path* is ``None`` or empty.
    """
    if not path:
        raise ValueError("path must not be None or empty")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_project(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the ``project`` section of *spec*."""
    return spec.get("project", {})


def get_drawing(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the ``drawing`` configuration from *spec*."""
    if "drawing" in spec and isinstance(spec["drawing"], dict):
        return spec["drawing"]
    return get_project(spec).get("drawing", {})


def ensure_drawing(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the ``drawing`` dict, creating it in-place if absent."""
    if "drawing" in spec and isinstance(spec["drawing"], dict):
        return spec["drawing"]
    project = spec.setdefault("project", {})
    drawing = project.get("drawing")
    if not isinstance(drawing, dict):
        drawing = {}
        project["drawing"] = drawing
    return drawing


def get_text_config(spec: dict[str, Any]) -> dict[str, float]:
    """Derive text-height configuration from *spec*."""
    drawing = get_drawing(spec)
    raw = drawing.get("text")
    if isinstance(raw, dict):
        return {
            "title_height": to_float(raw.get("title_height"), 3.2),
            "subtitle_height": to_float(raw.get("subtitle_height"), 2.0),
            "body_height": to_float(raw.get("body_height"), 1.6),
            "small_height": to_float(raw.get("small_height"), 1.2),
        }

    base = to_float(drawing.get("text_height"), 2.5)
    if base <= 0:
        base = 2.5
    return {
        "title_height": base * 1.6,
        "subtitle_height": base * 1.1,
        "body_height": base,
        "small_height": max(base * 0.75, 0.8),
    }


def get_layer_config(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the layer configuration from *spec*."""
    drawing = get_drawing(spec)
    layers = drawing.get("layers")
    if isinstance(layers, dict) and layers:
        return layers
    layers = spec.get("layers")
    if isinstance(layers, dict):
        return layers
    return {}


def get_layout_config(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the resolved layout configuration from *spec*."""
    drawing = get_drawing(spec)
    layout = drawing.get("layout", {})
    if not isinstance(layout, dict):
        layout = {}
    return {
        "style": str(layout.get("style", "clean")).lower(),
        "show_inline_equipment_notes": bool(layout.get("show_inline_equipment_notes", False)),
        "show_instrument_suffix": bool(layout.get("show_instrument_suffix", False)),
        "show_control_tags_on_lines": bool(layout.get("show_control_tags_on_lines", False)),
        "gap": max(to_float(layout.get("gap"), 8.0), 2.0),
        "right_panel_width": max(to_float(layout.get("right_panel_width"), 84.0), 45.0),
        "bottom_panel_height": max(to_float(layout.get("bottom_panel_height"), 34.0), 18.0),
        "title_block_height": max(to_float(layout.get("title_block_height"), 11.0), 6.0),
        "panel_text_chars": max(int(layout.get("panel_text_chars", 42)), 24),
        "stream_label_scale": min(max(to_float(layout.get("stream_label_scale"), 0.76), 0.45), 1.5),
        "stream_label_leaders": bool(layout.get("stream_label_leaders", True)),
        "instrument_spacing_factor": max(to_float(layout.get("instrument_spacing_factor"), 2.2), 1.2),
        "controls_row_height_scale": max(to_float(layout.get("controls_row_height_scale"), 3.4), 2.0),
    }


def apply_profile(spec: dict[str, Any], profile: str | None) -> dict[str, Any]:
    """Return a deep copy of *spec* with *profile* overrides applied.

    Raises:
        ValueError: If *profile* is not a recognised preset name.
    """
    if profile is None:
        return deepcopy(spec)
    key = str(profile).strip().lower()
    if key not in PROFILE_PRESETS:
        valid = ", ".join(sorted(PROFILE_PRESETS))
        raise ValueError(f"Unknown profile '{profile}'. Expected one of: {valid}")

    updated = deepcopy(spec)
    preset = PROFILE_PRESETS[key]
    drawing = ensure_drawing(updated)
    layout = drawing.get("layout")
    if not isinstance(layout, dict):
        layout = {}
        drawing["layout"] = layout

    for k, v in preset.get("layout", {}).items():
        layout[k] = v

    defaults = updated.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
        updated["defaults"] = defaults
    for k, v in preset.get("defaults", {}).items():
        defaults[k] = v

    meta = updated.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        updated["meta"] = meta
    meta["profile"] = key
    return updated


def prepare_spec(spec_path: str | Path, profile: str | None) -> dict[str, Any]:
    """Load, validate, and apply *profile* to the spec at *spec_path*."""
    raw = load_spec(spec_path)
    validate_spec(raw)
    prepared = apply_profile(raw, profile)
    validate_spec(prepared)
    return prepared


# ---------------------------------------------------------------------------
# Layout computation
# ---------------------------------------------------------------------------


def compute_layout_regions(spec: dict[str, Any]) -> dict[str, Any]:
    """Compute canvas, equipment-bbox, and panel positions."""
    layout_cfg = get_layout_config(spec)
    eq_min_x, eq_min_y, eq_max_x, eq_max_y = get_equipment_bounds(spec)

    gap = layout_cfg["gap"]
    right_w = layout_cfg["right_panel_width"]
    bottom_h = layout_cfg["bottom_panel_height"]
    title_h = layout_cfg["title_block_height"]

    process_w = max(eq_max_x - eq_min_x, 60.0)
    process_h = max(eq_max_y - eq_min_y, 50.0)
    left_pad = max(gap * 0.75, 4.0)
    top_pad = max(gap * 1.35, 10.0)

    canvas_x_min = eq_min_x - left_pad
    canvas_x_max = eq_max_x + gap + right_w + left_pad
    canvas_y_min = eq_min_y - (bottom_h + title_h + gap * 2.0)
    canvas_y_max = eq_max_y + top_pad

    control_w = max(process_w * 0.58, 56.0)
    mass_w = max(process_w - control_w - gap, 38.0)
    if control_w + mass_w + gap > process_w:
        scale = process_w / (control_w + mass_w + gap)
        control_w *= scale
        mass_w *= scale

    bottom_y = eq_min_y - (bottom_h + gap)
    panels = {
        "control": (eq_min_x, bottom_y, control_w, bottom_h),
        "mass": (eq_min_x + control_w + gap, bottom_y, mass_w, bottom_h),
        "right": (eq_max_x + gap, eq_min_y, right_w, process_h + top_pad * 0.85),
        "title": (canvas_x_min, canvas_y_min, canvas_x_max - canvas_x_min, title_h),
    }

    return {
        "layout_cfg": layout_cfg,
        "equipment_bbox": (eq_min_x, eq_min_y, eq_max_x, eq_max_y),
        "canvas_bbox": (canvas_x_min, canvas_y_min, canvas_x_max, canvas_y_max),
        "panels": panels,
    }


def get_modelspace_extent(spec: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return the modelspace extent for a controls sheet."""
    drawing = get_drawing(spec)
    extent = drawing.get("modelspace_extent", {})
    if all(k in extent for k in ("x_min", "y_min", "x_max", "y_max")):
        return (
            to_float(extent["x_min"]),
            to_float(extent["y_min"]),
            to_float(extent["x_max"]),
            to_float(extent["y_max"]),
        )

    equipment = spec.get("equipment", [])
    if equipment:
        x_min = min(to_float(eq.get("x", 0.0)) for eq in equipment)
        y_min = min(to_float(eq.get("y", 0.0)) for eq in equipment)
        x_max = max(to_float(eq.get("x", 0.0)) + equipment_dims(eq)[0] for eq in equipment)
        y_max = max(to_float(eq.get("y", 0.0)) + equipment_dims(eq)[1] for eq in equipment)
        margin = max((x_max - x_min) * 0.08, 5.0)
        return x_min - margin, y_min - margin, x_max + margin, y_max + margin

    return 0.0, 0.0, 240.0, 160.0


# ---------------------------------------------------------------------------
# Title block
# ---------------------------------------------------------------------------


def add_title_block(
    msp: Any,
    spec: dict[str, Any],
    text_cfg: dict[str, float],
    text_layer: str,
    notes_layer: str,
    title_box: tuple[float, float, float, float],
) -> None:
    """Draw the title-block panel at the bottom of the canvas."""
    x, y, w, h = title_box
    if w <= 0 or h <= 0:
        return

    add_box(msp, x, y, w, h, notes_layer)
    project = get_project(spec)
    title = project.get("document_title") or project.get("title") or "Process and Instrumentation Diagram"
    subtitle = project.get("subtitle", "")
    doc_no = project.get("document_number") or project.get("id", "")
    revision = project.get("revision", "")
    company = project.get("company", "")
    author = project.get("author", "")
    date = project.get("date", "")

    add_text(msp, title, x + 1.1, y + h - 0.9, text_cfg["body_height"], layer=text_layer, align="TOP_LEFT")
    if subtitle:
        add_text(
            msp,
            subtitle,
            x + 1.1,
            y + h - max(text_cfg["body_height"] * 1.35, 2.0),
            text_cfg["small_height"],
            layer=text_layer,
            align="TOP_LEFT",
        )

    meta = f"Doc: {doc_no}   Rev: {revision}   Date: {date}   Author: {author}   Company: {company}".strip()
    add_text(msp, meta, x + 1.1, y + 0.9, text_cfg["small_height"], layer=text_layer, align="BOTTOM_LEFT")


# ---------------------------------------------------------------------------
# SVG export
# ---------------------------------------------------------------------------


def export_svg_from_dxf(
    spec: dict[str, Any],
    dxf_path: str | Path,
    svg_path: str | Path | None,
    fallback_extent: tuple[float, float, float, float],
) -> None:
    """Attempt to convert a DXF file to SVG using ezdxf's drawing add-on."""
    if not svg_path:
        return
    x_min, y_min, x_max, y_max = fallback_extent
    try:
        from ezdxf import recover
        from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg

        audit_doc, auditor = recover.readfile(dxf_path)
        ctx = RenderContext(audit_doc)
        backend = svg.SVGBackend()
        Frontend(ctx, backend).draw_layout(audit_doc.modelspace(), finalize=True)

        paper = get_drawing(spec).get("paper", {})
        page_width = to_float(paper.get("width"), max(x_max - x_min, 100.0))
        page_height = to_float(paper.get("height"), max(y_max - y_min, 100.0))
        unit_name = str(paper.get("units", "mm")).lower()
        unit_map = {
            "mm": layout.Units.mm,
            "cm": layout.Units.cm,
            "inch": layout.Units.inch,
            "in": layout.Units.inch,
            "pt": layout.Units.pt,
            "px": layout.Units.px,
        }
        page = layout.Page(page_width, page_height, units=unit_map.get(unit_name, layout.Units.mm))
        Path(svg_path).write_text(backend.get_string(page), encoding="utf-8")
    except Exception as exc:
        logger.error("DXF created, but SVG export failed: %s", exc)


# ---------------------------------------------------------------------------
# Sheet generation
# ---------------------------------------------------------------------------


def _resolve_sheet_layers(doc: Any) -> dict[str, str]:
    """Resolve canonical layer names for generated sheets."""
    layer_index = {layer.dxf.name.lower(): layer.dxf.name for layer in doc.layers}
    return {
        "text": layer_name(layer_index, "TEXT", "annotations", "titleblock", default="TEXT"),
        "notes": layer_name(layer_index, "NOTES", "annotations", default="TEXT"),
        "instrument": layer_name(layer_index, "INSTRUMENTS", "instruments", default="INSTRUMENTS"),
        "leader": layer_name(layer_index, "LEADERS", default="LEADERS"),
        "control": layer_name(layer_index, "control_lines", default="control_lines"),
    }


def _prepare_process_sheet_context(spec: dict[str, Any]) -> dict[str, Any]:
    """Build the rendering context needed for the process sheet."""
    doc = ezdxf.new(setup=True)
    ensure_layers(doc, spec)
    layout_regions = compute_layout_regions(spec)
    layout_cfg = layout_regions["layout_cfg"]
    layers = _resolve_sheet_layers(doc)
    text_cfg = get_text_config(spec)
    arrow_size = to_float(
        spec.get("defaults", {}).get("arrow_size"), max(text_cfg["small_height"] * 1.2, 1.2)
    )
    bubble_radius = to_float(
        spec.get("defaults", {}).get("instrument_bubble_radius"), max(text_cfg["small_height"] * 0.9, 1.0)
    )
    return {
        "doc": doc,
        "msp": doc.modelspace(),
        "layout_regions": layout_regions,
        "layout_cfg": layout_cfg,
        "layers": layers,
        "text_cfg": text_cfg,
        "arrow_size": arrow_size,
        "bubble_radius": bubble_radius,
        "instrument_spacing": bubble_radius * layout_cfg["instrument_spacing_factor"],
    }


def _build_process_label_placer(spec: dict[str, Any], layout_regions: dict[str, Any]) -> LabelPlacer:
    """Reserve occupied regions so label placement can avoid collisions."""
    label_placer = LabelPlacer()
    for eq in spec.get("equipment", []):
        x = to_float(eq.get("x", 0.0))
        y = to_float(eq.get("y", 0.0))
        w, h = equipment_dims(eq)
        label_placer.reserve_rect((x, y, x + w, y + h))
    for panel in layout_regions["panels"].values():
        px, py, pw, ph = panel
        label_placer.reserve_rect((px, py, px + pw, py + ph))
    return label_placer


def _draw_process_frame(
    msp: Any,
    spec: dict[str, Any],
    text_cfg: dict[str, float],
    layout_regions: dict[str, Any],
    text_layer: str,
    notes_layer: str,
) -> tuple[float, float, float, float]:
    """Draw the process-sheet page frame, title block, and main title."""
    equipment_bbox = layout_regions["equipment_bbox"]
    x_min, y_min, x_max, y_max = layout_regions["canvas_bbox"]
    eq_min_x, eq_min_y, eq_max_x, eq_max_y = equipment_bbox

    add_box(msp, x_min, y_min, x_max - x_min, y_max - y_min, notes_layer)
    add_box(
        msp,
        eq_min_x - 2.0,
        eq_min_y - 2.0,
        (eq_max_x - eq_min_x) + 4.0,
        (eq_max_y - eq_min_y) + 4.0,
        notes_layer,
    )
    add_title_block(msp, spec, text_cfg, text_layer, notes_layer, layout_regions["panels"]["title"])

    project = get_project(spec)
    doc_title = project.get("document_title") or project.get("title") or "Process and Instrumentation Diagram"
    subtitle = project.get("subtitle") or "Conceptual process arrangement"
    add_text(
        msp,
        doc_title,
        (eq_min_x + eq_max_x) / 2,
        eq_max_y + max(text_cfg["title_height"] * 0.9, 3.0),
        text_cfg["title_height"],
        layer=text_layer,
    )
    add_text(
        msp,
        subtitle,
        (eq_min_x + eq_max_x) / 2,
        eq_max_y + max(text_cfg["title_height"] * 0.1, 1.3),
        max(text_cfg["subtitle_height"] * 0.95, 1.2),
        layer=text_layer,
    )
    return equipment_bbox


def _draw_process_equipment(
    msp: Any,
    spec: dict[str, Any],
    text_cfg: dict[str, float],
    layout_cfg: dict[str, Any],
    text_layer: str,
    notes_layer: str,
) -> dict[str, Any]:
    """Draw process equipment and return an index keyed by equipment id."""
    equipment_by_id = {eq.get("id"): eq for eq in spec.get("equipment", []) if eq.get("id")}
    for eq in spec.get("equipment", []):
        add_equipment(
            msp,
            eq,
            text_cfg["body_height"],
            text_layer=text_layer,
            notes_layer=notes_layer,
            show_inline_notes=layout_cfg["show_inline_equipment_notes"],
        )
    return equipment_by_id


def _draw_process_instruments(
    msp: Any,
    spec: dict[str, Any],
    text_cfg: dict[str, float],
    layout_cfg: dict[str, Any],
    instrument_layer: str,
    text_layer: str,
    bubble_radius: float,
    label_placer: LabelPlacer,
) -> dict[str, Any]:
    """Draw instruments and return an index keyed by instrument id."""
    instrument_by_id = {ins.get("id"): ins for ins in spec.get("instruments", []) if ins.get("id")}
    for ins in spec.get("instruments", []):
        add_instrument(
            msp,
            ins,
            text_h=text_cfg["small_height"],
            text_layer=text_layer,
            default_layer=instrument_layer,
            radius=bubble_radius,
            show_number_suffix=layout_cfg["show_instrument_suffix"],
            label_placer=label_placer,
        )
    return instrument_by_id


def _draw_process_streams(
    msp: Any,
    spec: dict[str, Any],
    text_cfg: dict[str, float],
    layout_cfg: dict[str, Any],
    text_layer: str,
    leader_layer: str,
    equipment_by_id: dict[str, Any],
    arrow_size: float,
    label_placer: LabelPlacer,
) -> dict[str, tuple[float, float]]:
    """Draw process streams and return resolved stream label anchor points."""
    stream_points: dict[str, tuple[float, float]] = {}
    for stream in spec.get("streams", []):
        try:
            stream_point = add_stream(
                msp,
                stream,
                text_h=text_cfg["small_height"],
                text_layer=text_layer,
                equipment_by_id=equipment_by_id,
                arrow_size=arrow_size,
                label_scale=layout_cfg["stream_label_scale"],
                label_placer=label_placer,
                draw_label_leader=layout_cfg["stream_label_leaders"],
                leader_layer=leader_layer,
            )
            stream_id = stream.get("id")
            if stream_id and stream_point:
                stream_points[stream_id] = stream_point
        except Exception as exc:
            logger.warning("Skipped stream %s: %s", stream.get("id", "<unknown>"), exc)
    return stream_points


def _add_process_disclaimer(
    msp: Any,
    text_cfg: dict[str, float],
    layout_regions: dict[str, Any],
    notes_layer: str,
) -> None:
    """Add the standard process-sheet disclaimer above the title block."""
    title_panel = layout_regions["panels"]["title"]
    add_text(
        msp,
        "Conceptual draft generated from YAML. Validate controls and safety details before design issue.",
        title_panel[0] + 1.1,
        title_panel[1] + title_panel[3] - max(text_cfg["small_height"] * 3.0, 3.0),
        max(text_cfg["small_height"] * 0.95, 1.0),
        layer=notes_layer,
        align="TOP_LEFT",
    )


def _prepare_controls_sheet_context(spec: dict[str, Any]) -> dict[str, Any]:
    """Build the rendering context needed for the controls sheet."""
    doc = ezdxf.new(setup=True)
    ensure_layers(doc, spec)
    layers = _resolve_sheet_layers(doc)
    if layers["control"] not in doc.layers:
        ensure_layer(doc, layers["control"], color=1, linetype="DASHDOT")

    x_min, y_min, x_max, y_max = get_modelspace_extent(spec)
    width = max(x_max - x_min, 200.0)
    height = max(y_max - y_min, 130.0)
    return {
        "doc": doc,
        "msp": doc.modelspace(),
        "layers": layers,
        "text_cfg": get_text_config(spec),
        "layout_cfg": get_layout_config(spec),
        "x_min": x_min,
        "y_min": y_min,
        "x_max": x_min + width,
        "y_max": y_min + height,
        "width": width,
        "height": height,
    }


def _draw_controls_header(
    msp: Any,
    spec_path: str | Path,
    text_cfg: dict[str, float],
    text_layer: str,
    notes_layer: str,
    x_min: float,
    y_min: float,
    y_max: float,
    width: float,
    height: float,
    margin: float,
) -> dict[str, float]:
    """Draw the controls-sheet border, heading, and table frame."""
    add_box(msp, x_min, y_min, width, height, notes_layer)
    add_text(
        msp,
        "Sheet 2 - Controls and Interlocks",
        x_min + margin,
        y_max - margin * 0.6,
        text_cfg["title_height"],
        layer=text_layer,
        align="TOP_LEFT",
    )
    add_text(
        msp,
        f"Generated from {Path(spec_path).name}",
        x_min + margin,
        y_max - margin * 1.7,
        text_cfg["subtitle_height"],
        layer=text_layer,
        align="TOP_LEFT",
    )

    table_x = x_min + margin
    table_w = width - 2 * margin
    table_top = y_max - margin * 3.4
    table_h = height * 0.52
    table_y = table_top - table_h
    add_box(msp, table_x, table_y, table_w, table_h, notes_layer)

    col_measure = table_x + table_w * 0.06
    col_ctrl = table_x + table_w * 0.44
    col_final = table_x + table_w * 0.72
    add_text(
        msp,
        "Measurement",
        col_measure,
        table_top - 1.3,
        text_cfg["body_height"],
        layer=text_layer,
        align="TOP_LEFT",
    )
    add_text(
        msp,
        "Controller/Logic",
        col_ctrl,
        table_top - 1.3,
        text_cfg["body_height"],
        layer=text_layer,
        align="TOP_LEFT",
    )
    add_text(
        msp,
        "Final Element",
        col_final,
        table_top - 1.3,
        text_cfg["body_height"],
        layer=text_layer,
        align="TOP_LEFT",
    )
    msp.add_line((col_ctrl - 2.0, table_y), (col_ctrl - 2.0, table_top), dxfattribs={"layer": notes_layer})
    msp.add_line((col_final - 2.0, table_y), (col_final - 2.0, table_top), dxfattribs={"layer": notes_layer})
    return {
        "table_x": table_x,
        "table_y": table_y,
        "table_w": table_w,
        "table_h": table_h,
        "table_top": table_top,
        "col_measure": col_measure,
        "col_ctrl": col_ctrl,
        "col_final": col_final,
    }


def _draw_controls_rows(
    msp: Any,
    loops: list[dict[str, Any]],
    text_cfg: dict[str, float],
    layout_cfg: dict[str, Any],
    text_layer: str,
    control_layer: str,
    table: dict[str, float],
    bubble_radius: float,
) -> None:
    """Render the control-loop summary rows."""
    row_h = max(text_cfg["small_height"] * layout_cfg["controls_row_height_scale"], 8.0)
    usable_rows = max(int((table["table_h"] - 4.0) / row_h), 1)
    bubble_r = max(bubble_radius * 0.42, 0.7)
    for i, loop in enumerate(loops[:usable_rows]):
        y = table["table_top"] - 3.2 - i * row_h
        measurement = str(loop.get("measurement", ""))
        final = str(loop.get("final_element", ""))
        loop_tag = str(loop.get("tag") or loop.get("id") or "")
        desc = str(loop.get("description") or loop.get("note") or "")

        msp.add_circle(
            (table["col_measure"] - 1.5, y - 0.4), radius=bubble_r, dxfattribs={"layer": "instruments"}
        )
        add_text(
            msp,
            measurement,
            table["col_measure"],
            y,
            text_cfg["small_height"],
            layer=text_layer,
            align="TOP_LEFT",
        )
        add_text(
            msp, loop_tag, table["col_ctrl"], y, text_cfg["small_height"], layer=text_layer, align="TOP_LEFT"
        )
        add_text(
            msp, final, table["col_final"], y, text_cfg["small_height"], layer=text_layer, align="TOP_LEFT"
        )
        if desc:
            add_text(
                msp,
                desc,
                table["col_ctrl"],
                y - 1.9,
                text_cfg["small_height"] * 0.9,
                layer=text_layer,
                align="TOP_LEFT",
            )

        add_arrow(
            msp,
            (table["col_measure"] + 8.5, y - 0.5),
            (table["col_ctrl"] - 3.2, y - 0.5),
            control_layer,
            arrow_size=1.0,
        )
        add_arrow(
            msp,
            (table["col_ctrl"] + 9.2, y - 0.5),
            (table["col_final"] - 3.2, y - 0.5),
            control_layer,
            arrow_size=1.0,
        )

    if len(loops) > usable_rows:
        add_text(
            msp,
            f"... {len(loops) - usable_rows} additional loops truncated",
            table["table_x"] + 1.0,
            table["table_y"] + 1.0,
            text_cfg["small_height"],
            layer=text_layer,
            align="BOTTOM_LEFT",
        )


def _draw_controls_panels(
    msp: Any,
    spec: dict[str, Any],
    text_cfg: dict[str, float],
    text_layer: str,
    notes_layer: str,
    table: dict[str, float],
    y_min: float,
    margin: float,
) -> None:
    """Render the interlock summary and instrument index panels."""
    lower_y = y_min + margin
    lower_h = table["table_y"] - lower_y - margin
    left_w = table["table_w"] * 0.58
    right_w = table["table_w"] - left_w - margin
    interlock_lines = [
        f'{i.get("id", "")}: {i.get("trigger", "")} -> {i.get("action", "")}'
        for i in spec.get("interlocks", [])
    ]
    add_text_panel(
        msp,
        table["table_x"],
        lower_y,
        left_w,
        lower_h,
        "Interlock Summary",
        interlock_lines,
        text_cfg["small_height"],
        text_layer,
        notes_layer,
        max_chars=72,
    )

    inst_lines = [
        f'{str(ins.get("tag") or ins.get("id") or "")}: {str(ins.get("service", "")).strip()}'
        for ins in spec.get("instruments", [])
    ]
    add_text_panel(
        msp,
        table["table_x"] + left_w + margin,
        lower_y,
        right_w,
        lower_h,
        "Instrument Index",
        inst_lines,
        text_cfg["small_height"],
        text_layer,
        notes_layer,
        max_chars=38,
    )


def _save_sheet(
    doc: Any,
    spec: dict[str, Any],
    out_path: str | Path,
    svg_path: str | Path | None,
    fallback_extent: tuple[float, float, float, float],
) -> None:
    """Persist a generated sheet and attempt SVG export."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out_path)
    export_svg_from_dxf(spec, out_path, svg_path, fallback_extent=fallback_extent)
    logger.info("Created: %s", out_path)
    if svg_path:
        logger.info("Attempted SVG: %s", svg_path)


def generate_process_sheet(
    spec_path: str | Path,
    out_path: str | Path,
    svg_path: str | Path | None = None,
    profile: str = "presentation",
    prepared_spec: dict[str, Any] | None = None,
) -> None:
    """Generate the main P&ID process sheet (Sheet 1).

    Raises:
        ValueError: If *out_path* is ``None`` or empty.
    """
    if not out_path:
        raise ValueError("out_path must not be None or empty")

    if prepared_spec is None:
        spec = prepare_spec(spec_path, profile)
    else:
        spec = deepcopy(prepared_spec)

    ctx = _prepare_process_sheet_context(spec)
    doc = ctx["doc"]
    msp = ctx["msp"]
    t = ctx["text_cfg"]
    layout_regions = ctx["layout_regions"]
    layout_cfg = ctx["layout_cfg"]
    layers = ctx["layers"]
    spec["instruments"] = spread_instrument_positions(
        spec.get("instruments", []), min_spacing=ctx["instrument_spacing"]
    )
    label_placer = _build_process_label_placer(spec, layout_regions)
    equipment_bbox = _draw_process_frame(msp, spec, t, layout_regions, layers["text"], layers["notes"])
    equipment_by_id = _draw_process_equipment(msp, spec, t, layout_cfg, layers["text"], layers["notes"])
    instrument_by_id = _draw_process_instruments(
        msp,
        spec,
        t,
        layout_cfg,
        layers["instrument"],
        layers["text"],
        ctx["bubble_radius"],
        label_placer,
    )
    stream_points = _draw_process_streams(
        msp,
        spec,
        t,
        layout_cfg,
        layers["text"],
        layers["leader"],
        equipment_by_id,
        ctx["arrow_size"],
        label_placer,
    )
    add_control_loops(
        msp,
        spec,
        text_h=t["small_height"],
        text_layer=layers["text"],
        equipment_by_id=equipment_by_id,
        instrument_by_id=instrument_by_id,
        stream_points=stream_points,
        process_bbox=equipment_bbox,
        show_loop_tags=layout_cfg["show_control_tags_on_lines"],
    )
    add_notes(
        msp, spec, t, text_layer=layers["text"], notes_layer=layers["notes"], layout_regions=layout_regions
    )
    _add_process_disclaimer(msp, t, layout_regions, layers["notes"])
    _save_sheet(doc, spec, out_path, svg_path, fallback_extent=tuple(layout_regions["canvas_bbox"]))


def generate_controls_sheet(
    spec_path: str | Path,
    out_path: str | Path,
    svg_path: str | Path | None = None,
    profile: str = "presentation",
    prepared_spec: dict[str, Any] | None = None,
) -> None:
    """Generate the controls & interlocks sheet (Sheet 2).

    Raises:
        ValueError: If *out_path* is ``None`` or empty.
    """
    if not out_path:
        raise ValueError("out_path must not be None or empty")

    if prepared_spec is None:
        spec = prepare_spec(spec_path, profile)
    else:
        spec = deepcopy(prepared_spec)
    ctx = _prepare_controls_sheet_context(spec)
    doc = ctx["doc"]
    msp = ctx["msp"]
    t = ctx["text_cfg"]
    layout_cfg = ctx["layout_cfg"]
    layers = ctx["layers"]
    margin = 8.0
    table = _draw_controls_header(
        msp,
        spec_path,
        t,
        layers["text"],
        layers["notes"],
        ctx["x_min"],
        ctx["y_min"],
        ctx["y_max"],
        ctx["width"],
        ctx["height"],
        margin,
    )
    loops = spec.get("control_loops", [])
    controls_bubble_radius = max(to_float(spec.get("defaults", {}).get("instrument_bubble_radius"), 1.6), 1.6)
    _draw_controls_rows(
        msp,
        loops,
        t,
        layout_cfg,
        layers["text"],
        layers["control"],
        table,
        controls_bubble_radius,
    )
    _draw_controls_panels(msp, spec, t, layers["text"], layers["notes"], table, ctx["y_min"], margin)
    _save_sheet(
        doc,
        spec,
        out_path,
        svg_path,
        fallback_extent=(ctx["x_min"], ctx["y_min"], ctx["x_max"], ctx["y_max"]),
    )


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def derive_related_path(path: str | Path, suffix: str) -> Path:
    """Derive a sibling path with *suffix* appended before the extension."""
    if not suffix or not isinstance(suffix, str):
        raise ValueError("suffix must be a non-empty string")
    p = Path(path)
    return p.with_name(f"{p.stem}_{suffix}{p.suffix}")


def generate(
    spec_path: str | Path,
    out_path: str | Path,
    svg_path: str | Path | None = None,
    sheet_set: str = "two",
    controls_out: str | Path | None = None,
    controls_svg: str | Path | None = None,
    profile: str = "presentation",
) -> None:
    """Generate one or two P&ID sheets from a YAML specification."""
    prepared_spec = prepare_spec(spec_path, profile)
    generate_process_sheet(spec_path, out_path, svg_path, profile=profile, prepared_spec=prepared_spec)
    if sheet_set == "two":
        controls_out = controls_out or derive_related_path(out_path, "controls")
        if controls_svg:
            target_svg = controls_svg
        elif svg_path:
            target_svg = derive_related_path(svg_path, "controls")
        else:
            target_svg = None
        generate_controls_sheet(
            spec_path, controls_out, target_svg, profile=profile, prepared_spec=prepared_spec
        )


def main() -> None:
    """CLI entry-point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--svg")
    ap.add_argument("--sheet-set", choices=["single", "two"], default="two")
    ap.add_argument("--profile", choices=sorted(PROFILE_PRESETS), default="presentation")
    ap.add_argument("--controls-out")
    ap.add_argument("--controls-svg")
    args = ap.parse_args()
    generate(
        args.spec,
        args.out,
        args.svg,
        args.sheet_set,
        args.controls_out,
        args.controls_svg,
        args.profile,
    )


if __name__ == "__main__":
    main()
