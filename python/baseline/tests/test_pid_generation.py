from __future__ import annotations

import importlib.util
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pid.py"

spec = importlib.util.spec_from_file_location("generate_pid", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def minimal_spec() -> dict:
    return {
        "project": {"id": "P-1", "title": "Test PID", "drawing": {"text_height": 2.0}},
        "equipment": [
            {"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10},
            {"id": "E-2", "x": 20, "y": 0, "width": 10, "height": 10},
        ],
        "instruments": [{"id": "PT-1", "tag": "PT-1", "x": 2, "y": 2}],
        "streams": [{"id": "S-1", "from": {"equipment": "E-1"}, "to": {"equipment": "E-2"}}],
        "control_loops": [
            {
                "id": "PIC-1",
                "measurement": "PT-1",
                "final_element": "E-2",
                "line_layer": "control_lines",
            }
        ],
    }


def test_validate_spec_rejects_duplicate_equipment_ids():
    bad = minimal_spec()
    bad["equipment"].append({"id": "E-1", "x": 40, "y": 0, "width": 10, "height": 10})
    try:
        mod.validate_spec(bad)
    except mod.SpecValidationError as exc:
        assert "duplicate equipment id: E-1" in str(exc)
    else:
        raise AssertionError("Expected SpecValidationError for duplicate equipment IDs")


def test_compute_layout_regions_puts_panels_outside_process_bbox():
    spec_data = minimal_spec()
    regions = mod.compute_layout_regions(spec_data)
    eq_min_x, eq_min_y, eq_max_x, eq_max_y = regions["equipment_bbox"]

    control = regions["panels"]["control"]
    right = regions["panels"]["right"]
    title = regions["panels"]["title"]

    assert control[1] + control[3] <= eq_min_y
    assert right[0] >= eq_max_x
    assert title[1] + title[3] <= eq_min_y


def test_label_placer_finds_non_overlapping_position():
    placer = mod.LabelPlacer()
    placer.reserve_rect((0.0, 0.0, 10.0, 10.0))
    x, y, align = placer.find_position(
        "Label",
        anchor=(5.0, 5.0),
        h=1.0,
        preferred=[(0.0, 0.0, "MIDDLE_CENTER"), (6.0, 0.0, "MIDDLE_LEFT")],
    )
    assert align == "MIDDLE_LEFT"
    assert x > 10.0


def test_spread_instrument_positions_separates_points():
    instruments = [
        {"id": "I-1", "x": 10.0, "y": 10.0},
        {"id": "I-2", "x": 10.0, "y": 10.0},
        {"id": "I-3", "x": 10.0, "y": 10.0},
    ]
    out = mod.spread_instrument_positions(instruments, min_spacing=2.0)
    points = {(round(i["x"], 3), round(i["y"], 3)) for i in out}
    assert len(points) == len(out)


def test_orthogonal_control_route_uses_corridor_y():
    route = mod.orthogonal_control_route(
        (10.0, 30.0), (40.0, 45.0), route_index=1, spread=3.0, corridor_y=15.0
    )
    y_values = [p[1] for p in route]
    assert min(y_values) <= 15.0
    assert route[0] == (10.0, 30.0)
    assert route[-1] == (40.0, 45.0)


def test_derive_related_path_suffix():
    path = Path("out/process.dxf")
    new_path = mod.derive_related_path(path, "controls")
    assert str(new_path).endswith("process_controls.dxf")


def test_apply_profile_overrides_layout_and_defaults():
    spec_data = minimal_spec()
    prof = mod.apply_profile(spec_data, "compact")
    layout = mod.get_layout_config(prof)
    assert layout["bottom_panel_height"] < mod.get_layout_config(spec_data)["bottom_panel_height"]
    assert layout["stream_label_scale"] < 0.76


def test_add_stream_draws_leader_line_when_displaced():
    doc = ezdxf.new(setup=True)
    mod.ensure_layer(doc, "process_lines", color=5)
    mod.ensure_layer(doc, "TEXT", color=7)
    mod.ensure_layer(doc, "LEADERS", color=8, linetype="DASHED")
    msp = doc.modelspace()

    placer = mod.LabelPlacer()
    # Reserve around the default placement so the placer must move the label.
    placer.reserve_rect((9.0, 0.2, 13.0, 2.4))

    stream = {"start": [0.0, 0.0], "end": [20.0, 0.0], "label": "Long stream label", "layer": "process_lines"}
    mod.add_stream(
        msp,
        stream,
        text_h=1.5,
        text_layer="TEXT",
        equipment_by_id={},
        arrow_size=1.0,
        label_scale=0.8,
        label_placer=placer,
        draw_label_leader=True,
        leader_layer="LEADERS",
    )

    leader_lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "LEADERS"]
    assert leader_lines, "Expected displaced label leader line on LEADERS layer"
