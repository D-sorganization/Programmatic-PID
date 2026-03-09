#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import textwrap
from copy import deepcopy
from pathlib import Path

import ezdxf
import yaml
from ezdxf.enums import TextEntityAlignment


class SpecValidationError(ValueError):
    pass


PROFILE_PRESETS = {
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


def load_spec(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def get_project(spec):
    return spec.get("project", {})


def get_drawing(spec):
    if "drawing" in spec and isinstance(spec["drawing"], dict):
        return spec["drawing"]
    return get_project(spec).get("drawing", {})


def ensure_drawing(spec):
    if "drawing" in spec and isinstance(spec["drawing"], dict):
        return spec["drawing"]
    project = spec.setdefault("project", {})
    drawing = project.get("drawing")
    if not isinstance(drawing, dict):
        drawing = {}
        project["drawing"] = drawing
    return drawing


def get_text_config(spec):
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


def get_layer_config(spec):
    drawing = get_drawing(spec)
    layers = drawing.get("layers")
    if isinstance(layers, dict) and layers:
        return layers
    layers = spec.get("layers")
    if isinstance(layers, dict):
        return layers
    return {}


def get_layout_config(spec):
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


def apply_profile(spec, profile):
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


def prepare_spec(spec_path, profile):
    raw = load_spec(spec_path)
    validate_spec(raw)
    prepared = apply_profile(raw, profile)
    validate_spec(prepared)
    return prepared


def validate_spec(spec):
    errors = []
    if not isinstance(spec, dict):
        raise SpecValidationError("Specification must be a YAML mapping.")

    project = get_project(spec)
    if not project.get("id"):
        errors.append("project.id is required")
    if not (project.get("title") or project.get("document_title")):
        errors.append("project.title or project.document_title is required")

    equipment = spec.get("equipment", [])
    if not equipment:
        errors.append("equipment list cannot be empty")

    equipment_ids = set()
    for eq in equipment:
        eq_id = eq.get("id")
        if not eq_id:
            errors.append("equipment entry missing id")
            continue
        if eq_id in equipment_ids:
            errors.append(f"duplicate equipment id: {eq_id}")
        equipment_ids.add(eq_id)

        w, h = equipment_dims(eq)
        if w <= 0 or h <= 0:
            errors.append(f"equipment {eq_id} has non-positive width/height")

    instrument_ids = set()
    for ins in spec.get("instruments", []):
        ins_id = ins.get("id")
        if not ins_id:
            errors.append("instrument entry missing id")
            continue
        if ins_id in instrument_ids:
            errors.append(f"duplicate instrument id: {ins_id}")
        instrument_ids.add(ins_id)

    for stream in spec.get("streams", []):
        sid = stream.get("id", "<unknown>")
        if "from" in stream:
            fr = stream.get("from", {})
            eq = fr.get("equipment")
            if eq and eq not in equipment_ids:
                errors.append(f"stream {sid} references unknown from equipment: {eq}")
        if "to" in stream:
            to = stream.get("to", {})
            eq = to.get("equipment")
            if eq and eq not in equipment_ids:
                errors.append(f"stream {sid} references unknown to equipment: {eq}")

    references = equipment_ids | instrument_ids
    for loop in spec.get("control_loops", []):
        lid = loop.get("id", "<unknown>")
        meas = loop.get("measurement")
        final = loop.get("final_element")
        if not meas or not final:
            errors.append(f"control loop {lid} missing measurement/final_element")
            continue
        if meas not in references:
            errors.append(f"control loop {lid} unknown measurement reference: {meas}")
        if final not in references:
            errors.append(f"control loop {lid} unknown final element reference: {final}")

    if errors:
        raise SpecValidationError("Invalid spec:\n- " + "\n- ".join(errors))


def ensure_layer(doc, name, color=7, linetype="CONTINUOUS"):
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


def ensure_layers(doc, spec):
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


def layer_name(layer_index, *candidates, default="0"):
    for candidate in candidates:
        if not candidate:
            continue
        actual = layer_index.get(str(candidate).lower())
        if actual:
            return actual
    return default


def parse_alignment(align):
    if isinstance(align, TextEntityAlignment):
        return align
    key = str(align or "MIDDLE_CENTER").upper()
    return getattr(TextEntityAlignment, key, TextEntityAlignment.MIDDLE_CENTER)


def wrap_text_lines(text, width):
    chunks = textwrap.wrap(
        str(text),
        width=max(int(width), 12),
        break_long_words=False,
        break_on_hyphens=False,
    )
    return chunks if chunks else [str(text)]


def rects_overlap(a, b, pad=0.0):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 + pad <= bx1 or bx2 + pad <= ax1 or ay2 + pad <= by1 or by2 + pad <= ay1)


def text_box(text, x, y, h, align="MIDDLE_CENTER"):
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


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def closest_point_on_rect(point, rect):
    px, py = to_float(point[0]), to_float(point[1])
    x1, y1, x2, y2 = rect
    return clamp(px, x1, x2), clamp(py, y1, y2)


class LabelPlacer:
    def __init__(self):
        self.occupied = []

    def reserve_rect(self, rect):
        self.occupied.append(rect)

    def reserve_text(self, text, x, y, h, align="MIDDLE_CENTER"):
        self.reserve_rect(text_box(text, x, y, h, align=align))

    def find_position(self, text, anchor, h, preferred):
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


def spread_instrument_positions(instruments, min_spacing=3.5):
    placed = []
    output = []
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


def add_text(msp, text, x, y, h, layer="TEXT", align="MIDDLE_CENTER"):
    t = msp.add_text(str(text), dxfattribs={"height": max(to_float(h, 1.0), 0.1), "layer": layer})
    t.set_placement((to_float(x), to_float(y)), align=parse_alignment(align))
    return t


def add_text_panel(
    msp,
    x,
    y,
    w,
    h,
    title,
    lines,
    text_h,
    text_layer,
    border_layer,
    max_chars=42,
):
    add_box(msp, x, y, w, h, border_layer)
    inset_x = x + 1.1
    inset_top = y + h - 1.0
    add_text(msp, title, inset_x, inset_top, text_h * 1.05, layer=text_layer, align="TOP_LEFT")

    step = max(text_h * 1.16, 0.9)
    available = max(int((h - 2.6) / step), 1)
    out = []
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


def add_box(msp, x, y, w, h, layer):
    x = to_float(x)
    y = to_float(y)
    w = to_float(w)
    h = to_float(h)
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


def add_hopper(msp, x, y, w, h, layer):
    x = to_float(x)
    y = to_float(y)
    w = to_float(w)
    h = to_float(h)
    bot_w = w * 0.72
    cx = x + w / 2
    pts = [(x, y + h), (x + w, y + h), (cx + bot_w / 2, y), (cx - bot_w / 2, y)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


def add_fan_symbol(msp, x, y, w, h, layer):
    cx = x + w / 2
    cy = y + h / 2
    r = max(min(w, h) * 0.42, 0.5)
    msp.add_circle((cx, cy), radius=r, dxfattribs={"layer": layer})
    blade = [(cx - r * 0.25, cy), (cx + r * 0.45, cy + r * 0.20), (cx + r * 0.45, cy - r * 0.20)]
    msp.add_lwpolyline(blade, close=True, dxfattribs={"layer": layer})


def add_rotary_valve_symbol(msp, x, y, w, h, layer):
    cx = x + w / 2
    cy = y + h / 2
    r = max(min(w, h) * 0.35, 0.5)
    msp.add_circle((cx, cy), radius=r, dxfattribs={"layer": layer})
    msp.add_line((cx - r * 0.85, cy - r * 0.85), (cx + r * 0.85, cy + r * 0.85), dxfattribs={"layer": layer})
    msp.add_line((cx - r * 0.85, cy + r * 0.85), (cx + r * 0.85, cy - r * 0.85), dxfattribs={"layer": layer})


def add_burner_symbol(msp, x, y, w, h, layer):
    add_box(msp, x, y, w, h, layer)
    cx = x + w / 2
    flame = [
        (cx, y + h * 0.76),
        (cx + w * 0.10, y + h * 0.48),
        (cx, y + h * 0.22),
        (cx - w * 0.10, y + h * 0.48),
    ]
    msp.add_lwpolyline(flame, close=True, dxfattribs={"layer": layer})


def add_bin_symbol(msp, x, y, w, h, layer):
    add_box(msp, x, y, w, h, layer)
    msp.add_line((x, y + h), (x + w, y + h), dxfattribs={"layer": layer})
    msp.add_line(
        (x + w * 0.1, y + h + h * 0.12), (x + w * 0.9, y + h + h * 0.12), dxfattribs={"layer": layer}
    )


def draw_equipment_symbol(msp, eq, layer):
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


def add_arrow_head(msp, s, e, layer, color=None, arrow_size=1.6):
    sx, sy = to_float(s[0]), to_float(s[1])
    ex, ey = to_float(e[0]), to_float(e[1])
    attrs = {"layer": layer}
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


def add_arrow(msp, s, e, layer, color=None, arrow_size=1.6):
    sx, sy = to_float(s[0]), to_float(s[1])
    ex, ey = to_float(e[0]), to_float(e[1])
    attrs = {"layer": layer}
    if color is not None:
        attrs["color"] = int(color)

    msp.add_line((sx, sy), (ex, ey), dxfattribs=attrs)
    add_arrow_head(msp, (sx, sy), (ex, ey), layer=layer, color=color, arrow_size=arrow_size)


def add_poly_arrow(msp, verts, layer, color=None, arrow_size=1.6):
    points = [(to_float(v[0]), to_float(v[1])) for v in verts if len(v) >= 2]
    if len(points) < 2:
        return

    attrs = {"layer": layer}
    if color is not None:
        attrs["color"] = int(color)
    msp.add_lwpolyline(points, dxfattribs=attrs)
    add_arrow_head(msp, points[-2], points[-1], layer, color=color, arrow_size=arrow_size)


def equipment_dims(eq):
    return to_float(eq.get("w", eq.get("width", 0.0))), to_float(eq.get("h", eq.get("height", 0.0)))


def get_equipment_bounds(spec):
    equipment = spec.get("equipment", [])
    if not equipment:
        return 0.0, 0.0, 240.0, 160.0
    x_min = min(to_float(eq.get("x", 0.0)) for eq in equipment)
    y_min = min(to_float(eq.get("y", 0.0)) for eq in equipment)
    x_max = max(to_float(eq.get("x", 0.0)) + equipment_dims(eq)[0] for eq in equipment)
    y_max = max(to_float(eq.get("y", 0.0)) + equipment_dims(eq)[1] for eq in equipment)
    return x_min, y_min, x_max, y_max


def compute_layout_regions(spec):
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


def equipment_center(eq):
    x = to_float(eq.get("x", 0.0))
    y = to_float(eq.get("y", 0.0))
    w, h = equipment_dims(eq)
    return x + w / 2, y + h / 2


def equipment_side_anchors(eq):
    x = to_float(eq.get("x", 0.0))
    y = to_float(eq.get("y", 0.0))
    w, h = equipment_dims(eq)
    return {
        "left": (x, y + h / 2),
        "right": (x + w, y + h / 2),
        "top": (x + w / 2, y + h),
        "bottom": (x + w / 2, y),
    }


def equipment_anchor(eq, side, offset=0.0):
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


def nearest_equipment_anchor(eq, source):
    sx, sy = to_float(source[0]), to_float(source[1])
    anchors = equipment_side_anchors(eq).values()
    return min(anchors, key=lambda p: (p[0] - sx) ** 2 + (p[1] - sy) ** 2)


def resolve_endpoint(endpoint, equipment_by_id):
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


def dedupe_points(points):
    cleaned = []
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


def orthogonal_control_route(start, end, route_index=0, spread=4.0, corridor_y=None):
    sx, sy = to_float(start[0]), to_float(start[1])
    ex, ey = to_float(end[0]), to_float(end[1])
    if corridor_y is not None:
        detour_y = to_float(corridor_y) - (route_index % 5) * max(to_float(spread), 0.5)
        return dedupe_points([(sx, sy), (sx, detour_y), (ex, detour_y), (ex, ey)])
    offset_band = (route_index % 5) - 2
    center_x = sx + (ex - sx) * 0.5 + offset_band * max(to_float(spread), 0.5)
    return dedupe_points([(sx, sy), (center_x, sy), (center_x, ey), (ex, ey)])


def resolve_reference_point(ref_id, equipment_by_id, instrument_by_id, stream_points):
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


def add_control_loops(
    msp,
    spec,
    text_h,
    text_layer,
    equipment_by_id,
    instrument_by_id,
    stream_points,
    process_bbox=None,
    show_loop_tags=False,
):
    loops = spec.get("control_loops", [])
    if not loops:
        return

    defaults = spec.get("defaults", {})
    spread = max(to_float(defaults.get("control_line_offset"), 1.5) * 2.0, 1.0)
    arrow_size = max(text_h * 0.9, 0.9)
    corridor_y = None
    if process_bbox:
        corridor_y = to_float(process_bbox[1]) - max(spread * 2.2, 3.0)

    for idx, loop in enumerate(loops):
        measurement_id = str(loop.get("measurement", "")).strip()
        final_element_id = str(loop.get("final_element", "")).strip()
        if not measurement_id or not final_element_id:
            print(f'Skipped control loop {loop.get("id", "<unknown>")}: missing measurement/final_element')
            continue

        start_ref = resolve_reference_point(measurement_id, equipment_by_id, instrument_by_id, stream_points)
        end_ref = resolve_reference_point(final_element_id, equipment_by_id, instrument_by_id, stream_points)
        if start_ref is None or end_ref is None:
            print(f'Skipped control loop {loop.get("id", "<unknown>")}: unresolved endpoints')
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


def get_modelspace_extent(spec):
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


def add_equipment(msp, eq, text_h, text_layer, notes_layer, show_inline_notes=False):
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
    msp,
    instrument,
    text_h,
    text_layer,
    default_layer,
    radius,
    show_number_suffix=False,
    label_placer=None,
):
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


def add_stream(
    msp,
    stream,
    text_h,
    text_layer,
    equipment_by_id,
    arrow_size,
    label_scale=0.82,
    label_placer=None,
    draw_label_leader=False,
    leader_layer="LEADERS",
):
    layer = stream.get("layer", "PROCESS")
    color = stream.get("color")
    lx = 0.0
    ly = 0.0

    if "vertices" in stream:
        verts = [tuple(v) for v in stream.get("vertices", [])]
        if len(verts) < 2:
            return None
        add_poly_arrow(msp, verts, layer, color=color, arrow_size=arrow_size)
        lx = sum(v[0] for v in verts) / len(verts)
        ly = sum(v[1] for v in verts) / len(verts)
    elif "start" in stream and "end" in stream:
        start = tuple(stream["start"])
        end = tuple(stream["end"])
        add_arrow(msp, start, end, layer, color=color, arrow_size=arrow_size)
        lx = (to_float(start[0]) + to_float(end[0])) / 2
        ly = (to_float(start[1]) + to_float(end[1])) / 2
    elif "from" in stream and "to" in stream:
        start = resolve_endpoint(stream.get("from"), equipment_by_id)
        end = resolve_endpoint(stream.get("to"), equipment_by_id)
        waypoints = [tuple(wp) for wp in stream.get("waypoints", [])]
        verts = [start, *waypoints, end]
        if len(verts) > 2:
            add_poly_arrow(msp, verts, layer, color=color, arrow_size=arrow_size)
            lx = sum(to_float(v[0]) for v in verts) / len(verts)
            ly = sum(to_float(v[1]) for v in verts) / len(verts)
        else:
            add_arrow(msp, start, end, layer, color=color, arrow_size=arrow_size)
            lx = (start[0] + end[0]) / 2
            ly = (start[1] + end[1]) / 2
    else:
        return None

    label = stream.get("label", "")
    if isinstance(label, dict):
        text = str(label.get("text", "")).strip()
        lx = to_float(label.get("x", lx))
        ly = to_float(label.get("y", ly))
    else:
        text = str(label).strip()

    if not text and stream.get("name"):
        text = str(stream["name"])
    if text:
        h = max(text_h * label_scale, 0.5)
        default_x = lx
        default_y = ly + text_h * 0.72
        if label_placer is not None:
            x, y, align = label_placer.find_position(
                text,
                (lx, ly),
                h,
                preferred=[
                    (0.0, text_h * 1.1, "BOTTOM_CENTER"),
                    (0.0, -text_h * 1.1, "TOP_CENTER"),
                    (text_h * 1.5, text_h * 0.6, "BOTTOM_LEFT"),
                    (-text_h * 1.5, text_h * 0.6, "BOTTOM_RIGHT"),
                ],
            )
            add_text(msp, text, x, y, h, layer=text_layer, align=align)
            displaced = abs(x - default_x) > h * 0.35 or abs(y - default_y) > h * 0.35
            if draw_label_leader and displaced:
                if leader_layer not in msp.doc.layers:
                    ensure_layer(msp.doc, leader_layer, color=8, linetype="DASHED")
                target = closest_point_on_rect((lx, ly), text_box(text, x, y, h, align=align))
                msp.add_line((lx, ly), target, dxfattribs={"layer": leader_layer})
        else:
            add_text(msp, text, default_x, default_y, h, layer=text_layer)
    return to_float(lx), to_float(ly)


def add_title_block(msp, spec, text_cfg, text_layer, notes_layer, title_box):
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


def get_mass_balance_values(spec):
    mb = spec.get("mass_balance", {}).get("basis", {})
    if mb:
        wet_feed = to_float(mb.get("wet_feed_kg_h"), 1000)
        feed_mc = to_float(mb.get("feed_moisture_wt_frac"), 0.30)
        dried_mc = to_float(mb.get("dried_feed_target_moisture_wt_frac"), 0.20)
        char_wet = to_float(mb.get("wet_biochar_product_kg_h"), 300)
        char_mc = to_float(mb.get("product_moisture_wt_frac"), 0.02)
        return wet_feed, feed_mc, dried_mc, char_wet, char_mc

    assumptions = spec.get("assumptions", {})
    feed = assumptions.get("feed", {})
    dryer = assumptions.get("dryer", {})
    reactor = assumptions.get("reactor", {})

    wet_feed = to_float(feed.get("wet_biomass_rate_kg_h"), 1000)
    feed_mc = to_float(feed.get("moisture_wtfrac"), 0.30)
    dried_mc = to_float(dryer.get("target_moisture_wtfrac"), 0.20)
    dry_yield = to_float(reactor.get("dry_char_yield_fraction_of_dry_feed"), 0.42)
    char_mc = to_float(reactor.get("char_product_moisture_wtfrac"), 0.02)

    dry_solids = wet_feed * (1 - feed_mc)
    char_dry = dry_solids * dry_yield
    char_wet = char_dry / (1 - char_mc) if char_mc < 1.0 else 0.0
    return wet_feed, feed_mc, dried_mc, char_wet, char_mc


def add_notes(msp, spec, text_cfg, text_layer, notes_layer, layout_regions):
    panels = layout_regions["panels"]
    cfg = layout_regions["layout_cfg"]
    max_chars = cfg["panel_text_chars"]

    loops = spec.get("control_loops", [])
    loop_lines = [
        f'{loop.get("id", "")}: {loop.get("objective") or loop.get("description") or loop.get("note", "")}'
        for loop in loops
    ]
    add_text_panel(
        msp,
        *panels["control"],
        title="Key Control Loops",
        lines=loop_lines,
        text_h=text_cfg["small_height"],
        text_layer=text_layer,
        border_layer=notes_layer,
        max_chars=max_chars,
    )

    wet_feed, feed_mc, dried_mc, char_wet, char_mc = get_mass_balance_values(spec)
    dry_solids = wet_feed * (1 - feed_mc)
    water_in = wet_feed * feed_mc
    water_after = dry_solids * dried_mc / (1 - dried_mc) if dried_mc < 1.0 else 0.0
    water_removed = water_in - water_after
    char_dry = char_wet * (1 - char_mc)
    dry_yield = (char_dry / dry_solids * 100) if dry_solids else 0.0
    mass_lines = [
        f"Feed water in = {water_in:.0f} kg/h",
        f"Dry biomass solids in = {dry_solids:.0f} kg/h",
        f"Water removed in dryer = {water_removed:.0f} kg/h",
        f"Biochar product = {char_wet:.0f} kg/h wet",
        f"Dry-basis char yield = {dry_yield:.1f}%",
    ]
    add_text_panel(
        msp,
        *panels["mass"],
        title="Approximate Mass Balance",
        lines=mass_lines,
        text_h=text_cfg["small_height"],
        text_layer=text_layer,
        border_layer=notes_layer,
        max_chars=max_chars,
    )

    design_notes = list(spec.get("annotations", {}).get("notes_panel", {}).get("bullets", []))
    pressure = spec.get("pressure_control", {})
    if isinstance(pressure, dict):
        mode = pressure.get("mode")
        pset = pressure.get("normal_operating_pressure_psig")
        if mode:
            design_notes.insert(0, f"Pressure mode: {mode}")
        if pset is not None:
            design_notes.insert(1, f"Normal operating pressure target: {pset} psig")
        for note in pressure.get("notes", [])[:2]:
            design_notes.append(note)

    interlock_lines = [
        f'{item.get("id", "")}: {item.get("trigger", "")}' for item in spec.get("interlocks", [])[:5]
    ]
    equipment_note_lines = []
    for eq in spec.get("equipment", []):
        notes = eq.get("notes", [])
        if notes:
            equipment_note_lines.append(f'{eq.get("id", "")}: {notes[0]}')

    right_lines = []
    right_lines.extend(f"- {note}" for note in design_notes[:6])
    if interlock_lines:
        right_lines.append("")
        right_lines.append("Interlock Triggers:")
        right_lines.extend(interlock_lines)
    if equipment_note_lines:
        right_lines.append("")
        right_lines.append("Equipment Notes:")
        right_lines.extend(equipment_note_lines[:6])

    add_text_panel(
        msp,
        *panels["right"],
        title="Design and Safety Notes",
        lines=right_lines,
        text_h=text_cfg["small_height"],
        text_layer=text_layer,
        border_layer=notes_layer,
        max_chars=max_chars,
    )


def export_svg_from_dxf(spec, dxf_path, svg_path, fallback_extent):
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
        print(f"DXF created, but SVG export failed: {exc}")


def generate_process_sheet(spec_path, out_path, svg_path=None, profile="presentation", prepared_spec=None):
    if prepared_spec is None:
        spec = prepare_spec(spec_path, profile)
    else:
        spec = deepcopy(prepared_spec)

    doc = ezdxf.new(setup=True)
    ensure_layers(doc, spec)
    msp = doc.modelspace()
    t = get_text_config(spec)
    layout_regions = compute_layout_regions(spec)
    layout_cfg = layout_regions["layout_cfg"]
    equipment_bbox = layout_regions["equipment_bbox"]
    x_min, y_min, x_max, y_max = layout_regions["canvas_bbox"]
    eq_min_x, eq_min_y, eq_max_x, eq_max_y = equipment_bbox

    layer_index = {layer.dxf.name.lower(): layer.dxf.name for layer in doc.layers}
    text_layer = layer_name(layer_index, "TEXT", "annotations", "titleblock", default="TEXT")
    notes_layer = layer_name(layer_index, "NOTES", "annotations", default=text_layer)
    instrument_layer = layer_name(layer_index, "INSTRUMENTS", "instruments", default="INSTRUMENTS")
    leader_layer = layer_name(layer_index, "LEADERS", default="LEADERS")
    arrow_size = to_float(spec.get("defaults", {}).get("arrow_size"), max(t["small_height"] * 1.2, 1.2))
    bubble_radius = to_float(
        spec.get("defaults", {}).get("instrument_bubble_radius"), max(t["small_height"] * 0.9, 1.0)
    )
    stream_label_scale = layout_cfg["stream_label_scale"]
    stream_label_leaders = layout_cfg["stream_label_leaders"]
    instrument_spacing = bubble_radius * layout_cfg["instrument_spacing_factor"]

    spec["instruments"] = spread_instrument_positions(
        spec.get("instruments", []), min_spacing=instrument_spacing
    )

    label_placer = LabelPlacer()
    for eq in spec.get("equipment", []):
        x = to_float(eq.get("x", 0.0))
        y = to_float(eq.get("y", 0.0))
        w, h = equipment_dims(eq)
        label_placer.reserve_rect((x, y, x + w, y + h))
    for _, panel in layout_regions["panels"].items():
        px, py, pw, ph = panel
        label_placer.reserve_rect((px, py, px + pw, py + ph))

    add_box(msp, x_min, y_min, x_max - x_min, y_max - y_min, notes_layer)
    add_box(
        msp,
        eq_min_x - 2.0,
        eq_min_y - 2.0,
        (eq_max_x - eq_min_x) + 4.0,
        (eq_max_y - eq_min_y) + 4.0,
        notes_layer,
    )

    add_title_block(msp, spec, t, text_layer, notes_layer, layout_regions["panels"]["title"])

    project = get_project(spec)
    doc_title = project.get("document_title") or project.get("title") or "Process and Instrumentation Diagram"
    subtitle = project.get("subtitle") or "Conceptual process arrangement"
    add_text(
        msp,
        doc_title,
        (eq_min_x + eq_max_x) / 2,
        eq_max_y + max(t["title_height"] * 0.9, 3.0),
        t["title_height"],
        layer=text_layer,
    )
    add_text(
        msp,
        subtitle,
        (eq_min_x + eq_max_x) / 2,
        eq_max_y + max(t["title_height"] * 0.1, 1.3),
        max(t["subtitle_height"] * 0.95, 1.2),
        layer=text_layer,
    )

    equipment_by_id = {eq.get("id"): eq for eq in spec.get("equipment", []) if eq.get("id")}
    for eq in spec.get("equipment", []):
        add_equipment(
            msp,
            eq,
            t["body_height"],
            text_layer=text_layer,
            notes_layer=notes_layer,
            show_inline_notes=layout_cfg["show_inline_equipment_notes"],
        )

    instrument_by_id = {ins.get("id"): ins for ins in spec.get("instruments", []) if ins.get("id")}
    for ins in spec.get("instruments", []):
        add_instrument(
            msp,
            ins,
            text_h=t["small_height"],
            text_layer=text_layer,
            default_layer=instrument_layer,
            radius=bubble_radius,
            show_number_suffix=layout_cfg["show_instrument_suffix"],
            label_placer=label_placer,
        )

    stream_points = {}
    for stream in spec.get("streams", []):
        try:
            stream_point = add_stream(
                msp,
                stream,
                text_h=t["small_height"],
                text_layer=text_layer,
                equipment_by_id=equipment_by_id,
                arrow_size=arrow_size,
                label_scale=stream_label_scale,
                label_placer=label_placer,
                draw_label_leader=stream_label_leaders,
                leader_layer=leader_layer,
            )
            stream_id = stream.get("id")
            if stream_id and stream_point:
                stream_points[stream_id] = stream_point
        except Exception as exc:
            print(f'Skipped stream {stream.get("id", "<unknown>")}: {exc}')

    add_control_loops(
        msp,
        spec,
        text_h=t["small_height"],
        text_layer=text_layer,
        equipment_by_id=equipment_by_id,
        instrument_by_id=instrument_by_id,
        stream_points=stream_points,
        process_bbox=equipment_bbox,
        show_loop_tags=layout_cfg["show_control_tags_on_lines"],
    )

    add_notes(msp, spec, t, text_layer=text_layer, notes_layer=notes_layer, layout_regions=layout_regions)
    add_text(
        msp,
        "Conceptual draft generated from YAML. Validate controls and safety details before design issue.",
        layout_regions["panels"]["title"][0] + 1.1,
        layout_regions["panels"]["title"][1]
        + layout_regions["panels"]["title"][3]
        - max(t["small_height"] * 3.0, 3.0),
        max(t["small_height"] * 0.95, 1.0),
        layer=notes_layer,
        align="TOP_LEFT",
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out_path)
    export_svg_from_dxf(spec, out_path, svg_path, fallback_extent=(x_min, y_min, x_max, y_max))

    print(f"Created: {out_path}")
    if svg_path:
        print(f"Attempted SVG: {svg_path}")


def generate_controls_sheet(spec_path, out_path, svg_path=None, profile="presentation", prepared_spec=None):
    if prepared_spec is None:
        spec = prepare_spec(spec_path, profile)
    else:
        spec = deepcopy(prepared_spec)
    doc = ezdxf.new(setup=True)
    ensure_layers(doc, spec)
    msp = doc.modelspace()

    t = get_text_config(spec)
    layout_cfg = get_layout_config(spec)
    x_min, y_min, x_max, y_max = get_modelspace_extent(spec)
    width = max(x_max - x_min, 200.0)
    height = max(y_max - y_min, 130.0)
    x_max = x_min + width
    y_max = y_min + height

    layer_index = {layer.dxf.name.lower(): layer.dxf.name for layer in doc.layers}
    text_layer = layer_name(layer_index, "TEXT", "annotations", "titleblock", default="TEXT")
    notes_layer = layer_name(layer_index, "NOTES", "annotations", default=text_layer)
    control_layer = layer_name(layer_index, "control_lines", default="control_lines")
    if control_layer not in doc.layers:
        ensure_layer(doc, control_layer, color=1, linetype="DASHDOT")

    margin = 8.0
    add_box(msp, x_min, y_min, width, height, notes_layer)
    add_text(
        msp,
        "Sheet 2 - Controls and Interlocks",
        x_min + margin,
        y_max - margin * 0.6,
        t["title_height"],
        layer=text_layer,
        align="TOP_LEFT",
    )
    add_text(
        msp,
        f"Generated from {Path(spec_path).name}",
        x_min + margin,
        y_max - margin * 1.7,
        t["subtitle_height"],
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
        msp, "Measurement", col_measure, table_top - 1.3, t["body_height"], layer=text_layer, align="TOP_LEFT"
    )
    add_text(
        msp,
        "Controller/Logic",
        col_ctrl,
        table_top - 1.3,
        t["body_height"],
        layer=text_layer,
        align="TOP_LEFT",
    )
    add_text(
        msp, "Final Element", col_final, table_top - 1.3, t["body_height"], layer=text_layer, align="TOP_LEFT"
    )
    msp.add_line((col_ctrl - 2.0, table_y), (col_ctrl - 2.0, table_top), dxfattribs={"layer": notes_layer})
    msp.add_line((col_final - 2.0, table_y), (col_final - 2.0, table_top), dxfattribs={"layer": notes_layer})

    loops = spec.get("control_loops", [])
    row_h = max(t["small_height"] * layout_cfg["controls_row_height_scale"], 8.0)
    usable_rows = max(int((table_h - 4.0) / row_h), 1)
    bubble_r = max(to_float(spec.get("defaults", {}).get("instrument_bubble_radius"), 1.6) * 0.42, 0.7)
    for i, loop in enumerate(loops[:usable_rows]):
        y = table_top - 3.2 - i * row_h
        measurement = str(loop.get("measurement", ""))
        final = str(loop.get("final_element", ""))
        loop_tag = str(loop.get("tag") or loop.get("id") or "")
        desc = str(loop.get("description") or loop.get("note") or "")

        msp.add_circle((col_measure - 1.5, y - 0.4), radius=bubble_r, dxfattribs={"layer": "instruments"})
        add_text(msp, measurement, col_measure, y, t["small_height"], layer=text_layer, align="TOP_LEFT")
        add_text(msp, loop_tag, col_ctrl, y, t["small_height"], layer=text_layer, align="TOP_LEFT")
        add_text(msp, final, col_final, y, t["small_height"], layer=text_layer, align="TOP_LEFT")
        if desc:
            add_text(
                msp, desc, col_ctrl, y - 1.9, t["small_height"] * 0.9, layer=text_layer, align="TOP_LEFT"
            )

        add_arrow(msp, (col_measure + 8.5, y - 0.5), (col_ctrl - 3.2, y - 0.5), control_layer, arrow_size=1.0)
        add_arrow(msp, (col_ctrl + 9.2, y - 0.5), (col_final - 3.2, y - 0.5), control_layer, arrow_size=1.0)

    if len(loops) > usable_rows:
        add_text(
            msp,
            f"... {len(loops) - usable_rows} additional loops truncated",
            table_x + 1.0,
            table_y + 1.0,
            t["small_height"],
            layer=text_layer,
            align="BOTTOM_LEFT",
        )

    interlocks = spec.get("interlocks", [])
    lower_y = y_min + margin
    lower_h = table_y - lower_y - margin
    left_w = table_w * 0.58
    right_w = table_w - left_w - margin
    interlock_lines = [
        f'{i.get("id", "")}: {i.get("trigger", "")} -> {i.get("action", "")}' for i in interlocks
    ]
    add_text_panel(
        msp,
        table_x,
        lower_y,
        left_w,
        lower_h,
        "Interlock Summary",
        interlock_lines,
        t["small_height"],
        text_layer,
        notes_layer,
        max_chars=72,
    )

    inst_lines = []
    for ins in spec.get("instruments", []):
        tag = str(ins.get("tag") or ins.get("id") or "")
        service = str(ins.get("service", "")).strip()
        inst_lines.append(f"{tag}: {service}")
    add_text_panel(
        msp,
        table_x + left_w + margin,
        lower_y,
        right_w,
        lower_h,
        "Instrument Index",
        inst_lines,
        t["small_height"],
        text_layer,
        notes_layer,
        max_chars=38,
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out_path)
    export_svg_from_dxf(spec, out_path, svg_path, fallback_extent=(x_min, y_min, x_max, y_max))
    print(f"Created: {out_path}")
    if svg_path:
        print(f"Attempted SVG: {svg_path}")


def derive_related_path(path, suffix):
    p = Path(path)
    return p.with_name(f"{p.stem}_{suffix}{p.suffix}")


def generate(
    spec_path,
    out_path,
    svg_path=None,
    sheet_set="two",
    controls_out=None,
    controls_svg=None,
    profile="presentation",
):
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


def main():
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
