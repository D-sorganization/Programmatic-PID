#!/usr/bin/env python3
"""P&ID generation entry-point — delegates to focused sub-modules.

This module is the public API surface.  It re-exports every symbol that
previously lived here so that existing ``import programmatic_pid.generator as mod``
continues to work without changes.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

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
    TextEntityAlignment,
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
from programmatic_pid.sheet_rendering import (  # noqa: F401
    add_title_block,
    export_svg_from_dxf,
    generate_controls_sheet,
    generate_process_sheet,
)
from programmatic_pid.stream_router import add_stream  # noqa: F401
from programmatic_pid.validator import SpecValidationError, validate_spec  # noqa: F401

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
# Top-level orchestration
# ---------------------------------------------------------------------------


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
