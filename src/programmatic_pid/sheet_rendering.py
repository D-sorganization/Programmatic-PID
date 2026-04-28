"""Sheet rendering helpers for process and controls P&ID output."""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from ezdxf import new  # type: ignore[attr-defined]

from programmatic_pid.control_loops import add_control_loops
from programmatic_pid.dxf_builder import (
    LabelPlacer,
    add_box,
    add_equipment,
    add_instrument,
    add_text,
    ensure_layers,
    equipment_dims,
    spread_instrument_positions,
    to_float,
)
from programmatic_pid.notes import add_notes
from programmatic_pid.sheet_layout import (
    draw_controls_header,
    draw_controls_panels,
    draw_controls_rows,
    prepare_controls_sheet_context,
    resolve_sheet_layers,
)
from programmatic_pid.stream_router import add_stream

logger = logging.getLogger(__name__)


def _generator_facade() -> Any:
    from programmatic_pid import generator

    return generator


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
    project = _generator_facade().get_project(spec)
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
        from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg  # type: ignore[attr-defined]

        audit_doc, auditor = recover.readfile(dxf_path)
        ctx = RenderContext(audit_doc)
        backend = svg.SVGBackend()
        Frontend(ctx, backend).draw_layout(audit_doc.modelspace(), finalize=True)

        paper = _generator_facade().get_drawing(spec).get("paper", {})
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
    except (ImportError, OSError, ValueError, TypeError) as exc:
        logger.error("DXF created, but SVG export failed: %s", exc)


def _prepare_process_sheet_context(spec: dict[str, Any]) -> dict[str, Any]:
    """Build the rendering context needed for the process sheet."""
    generator = _generator_facade()
    doc = new(setup=True)
    ensure_layers(doc, spec)
    layout_regions = generator.compute_layout_regions(spec)
    layout_cfg = layout_regions["layout_cfg"]
    layers = resolve_sheet_layers(doc)
    text_cfg = generator.get_text_config(spec)
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
    equipment_bbox: tuple[float, float, float, float] = layout_regions["equipment_bbox"]
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

    project = _generator_facade().get_project(spec)
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


def render_process_sheet(
    spec: dict[str, Any],
    out_path: str | Path,
    svg_path: str | Path | None = None,
) -> None:
    """Render a prepared process-sheet spec to disk."""
    ctx = _prepare_process_sheet_context(spec)
    doc = ctx["doc"]
    msp = ctx["msp"]
    text_cfg = ctx["text_cfg"]
    layout_regions = ctx["layout_regions"]
    layout_cfg = ctx["layout_cfg"]
    layers = ctx["layers"]
    spec["instruments"] = spread_instrument_positions(
        spec.get("instruments", []), min_spacing=ctx["instrument_spacing"]
    )
    label_placer = _build_process_label_placer(spec, layout_regions)
    equipment_bbox = _draw_process_frame(msp, spec, text_cfg, layout_regions, layers["text"], layers["notes"])
    equipment_by_id = _draw_process_equipment(
        msp, spec, text_cfg, layout_cfg, layers["text"], layers["notes"]
    )
    instrument_by_id = _draw_process_instruments(
        msp,
        spec,
        text_cfg,
        layout_cfg,
        layers["instrument"],
        layers["text"],
        ctx["bubble_radius"],
        label_placer,
    )
    stream_points = _draw_process_streams(
        msp,
        spec,
        text_cfg,
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
        text_h=text_cfg["small_height"],
        text_layer=layers["text"],
        equipment_by_id=equipment_by_id,
        instrument_by_id=instrument_by_id,
        stream_points=stream_points,
        process_bbox=equipment_bbox,
        show_loop_tags=layout_cfg["show_control_tags_on_lines"],
    )
    add_notes(
        msp,
        spec,
        text_cfg,
        text_layer=layers["text"],
        notes_layer=layers["notes"],
        layout_regions=layout_regions,
    )
    _add_process_disclaimer(msp, text_cfg, layout_regions, layers["notes"])
    _save_sheet(doc, spec, out_path, svg_path, fallback_extent=tuple(layout_regions["canvas_bbox"]))


def render_controls_sheet(
    spec: dict[str, Any],
    spec_path: str | Path,
    out_path: str | Path,
    svg_path: str | Path | None = None,
) -> None:
    """Render a prepared controls-sheet spec to disk."""
    generator = _generator_facade()
    ctx = prepare_controls_sheet_context(
        spec,
        text_cfg=generator.get_text_config(spec),
        layout_cfg=generator.get_layout_config(spec),
        modelspace_extent=generator.get_modelspace_extent(spec),
    )
    doc = ctx["doc"]
    msp = ctx["msp"]
    text_cfg = ctx["text_cfg"]
    layout_cfg = ctx["layout_cfg"]
    layers = ctx["layers"]
    margin = 8.0
    table = draw_controls_header(
        msp,
        spec_name=Path(spec_path).name,
        text_cfg=text_cfg,
        text_layer=layers["text"],
        notes_layer=layers["notes"],
        x_min=ctx["x_min"],
        y_min=ctx["y_min"],
        y_max=ctx["y_max"],
        width=ctx["width"],
        height=ctx["height"],
        margin=margin,
    )
    loops = spec.get("control_loops", [])
    controls_bubble_radius = max(to_float(spec.get("defaults", {}).get("instrument_bubble_radius"), 1.6), 1.6)
    draw_controls_rows(
        msp,
        loops,
        text_cfg=text_cfg,
        layout_cfg=layout_cfg,
        text_layer=layers["text"],
        control_layer=layers["control"],
        table=table,
        bubble_radius=controls_bubble_radius,
    )
    draw_controls_panels(
        msp,
        spec,
        text_cfg=text_cfg,
        text_layer=layers["text"],
        notes_layer=layers["notes"],
        table=table,
        y_min=ctx["y_min"],
        margin=margin,
    )
    _save_sheet(
        doc,
        spec,
        out_path,
        svg_path,
        fallback_extent=(ctx["x_min"], ctx["y_min"], ctx["x_max"], ctx["y_max"]),
    )


def generate_process_sheet(
    spec_path: str | Path,
    out_path: str | Path,
    svg_path: str | Path | None = None,
    profile: str = "presentation",
    prepared_spec: dict[str, Any] | None = None,
) -> None:
    """Generate the main P&ID process sheet (Sheet 1)."""
    if not out_path:
        raise ValueError("out_path must not be None or empty")

    generator = _generator_facade()
    if prepared_spec is None:
        spec = generator.prepare_spec(spec_path, profile)
    else:
        spec = deepcopy(prepared_spec)
    render_process_sheet(spec, out_path, svg_path)


def generate_controls_sheet(
    spec_path: str | Path,
    out_path: str | Path,
    svg_path: str | Path | None = None,
    profile: str = "presentation",
    prepared_spec: dict[str, Any] | None = None,
) -> None:
    """Generate the controls & interlocks sheet (Sheet 2)."""
    if not out_path:
        raise ValueError("out_path must not be None or empty")

    generator = _generator_facade()
    if prepared_spec is None:
        spec = generator.prepare_spec(spec_path, profile)
    else:
        spec = deepcopy(prepared_spec)
    render_controls_sheet(spec, spec_path, out_path, svg_path)
