"""Sheet layout helpers for multi-sheet P&ID rendering."""

from __future__ import annotations

from typing import Any

from ezdxf import new  # type: ignore[attr-defined]

from programmatic_pid.dxf_builder import (
    add_arrow,
    add_box,
    add_text,
    add_text_panel,
    ensure_layer,
    ensure_layers,
    layer_name,
)


def resolve_sheet_layers(doc: Any) -> dict[str, str]:
    """Resolve canonical layer names for generated sheets."""
    layer_index = {layer.dxf.name.lower(): layer.dxf.name for layer in doc.layers}
    return {
        "text": layer_name(layer_index, "TEXT", "annotations", "titleblock", default="TEXT"),
        "notes": layer_name(layer_index, "NOTES", "annotations", default="TEXT"),
        "instrument": layer_name(layer_index, "INSTRUMENTS", "instruments", default="INSTRUMENTS"),
        "leader": layer_name(layer_index, "LEADERS", default="LEADERS"),
        "control": layer_name(layer_index, "control_lines", default="control_lines"),
    }


def prepare_controls_sheet_context(
    spec: dict[str, Any],
    *,
    text_cfg: dict[str, float],
    layout_cfg: dict[str, Any],
    modelspace_extent: tuple[float, float, float, float],
) -> dict[str, Any]:
    """Build the rendering context needed for the controls sheet."""
    doc = new(setup=True)
    ensure_layers(doc, spec)
    layers = resolve_sheet_layers(doc)
    if layers["control"] not in doc.layers:
        ensure_layer(doc, layers["control"], color=1, linetype="DASHDOT")

    x_min, y_min, x_max, y_max = modelspace_extent
    width = max(x_max - x_min, 200.0)
    height = max(y_max - y_min, 130.0)
    return {
        "doc": doc,
        "msp": doc.modelspace(),
        "layers": layers,
        "text_cfg": text_cfg,
        "layout_cfg": layout_cfg,
        "x_min": x_min,
        "y_min": y_min,
        "x_max": x_min + width,
        "y_max": y_min + height,
        "width": width,
        "height": height,
    }


def draw_controls_header(
    msp: Any,
    *,
    spec_name: str,
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
        f"Generated from {spec_name}",
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


def draw_controls_rows(
    msp: Any,
    loops: list[dict[str, Any]],
    *,
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


def draw_controls_panels(
    msp: Any,
    spec: dict[str, Any],
    *,
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
        f"{i.get('id', '')}: {i.get('trigger', '')} -> {i.get('action', '')}"
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
        f"{str(ins.get('tag') or ins.get('id') or '')}: {str(ins.get('service', '')).strip()}"
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
