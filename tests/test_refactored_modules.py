"""Comprehensive tests for the refactored P&ID modules.

Covers: validator, dxf_builder, stream_router, control_loops, notes,
and generator orchestration.
"""

from __future__ import annotations

import ezdxf
import pytest

import programmatic_pid.generator as gen
from programmatic_pid.control_loops import (
    add_control_loops,
    orthogonal_control_route,
    resolve_reference_point,
)
from programmatic_pid.dxf_builder import (
    LabelPlacer,
    add_equipment,
    add_instrument,
    ensure_layer,
    to_float,
)
from programmatic_pid.notes import add_notes, get_mass_balance_values
from programmatic_pid.sheet_layout import (
    draw_controls_header,
    prepare_controls_sheet_context,
    resolve_sheet_layers,
)
from programmatic_pid.stream_router import add_stream
from programmatic_pid.validator import SpecValidationError, validate_spec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_spec() -> dict:
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


# ===================================================================
# Issue #3 -- comprehensive tests (15+ tests)
# ===================================================================


# --- validator.py ---


class TestValidateSpec:
    def test_rejects_none(self):
        with pytest.raises(ValueError, match="must not be None"):
            validate_spec(None)

    def test_rejects_non_dict(self):
        with pytest.raises(SpecValidationError, match="YAML mapping"):
            validate_spec("not a dict")

    def test_rejects_missing_project_id(self):
        spec = _minimal_spec()
        spec["project"]["id"] = ""
        with pytest.raises(SpecValidationError, match="project.id is required"):
            validate_spec(spec)

    def test_rejects_empty_equipment(self):
        spec = _minimal_spec()
        spec["equipment"] = []
        with pytest.raises(SpecValidationError, match="equipment list cannot be empty"):
            validate_spec(spec)

    def test_rejects_duplicate_equipment(self):
        spec = _minimal_spec()
        spec["equipment"].append({"id": "E-1", "x": 0, "y": 0, "width": 5, "height": 5})
        with pytest.raises(SpecValidationError, match="duplicate equipment id: E-1"):
            validate_spec(spec)

    def test_rejects_zero_dimension_equipment(self):
        spec = _minimal_spec()
        spec["equipment"][0]["width"] = 0
        with pytest.raises(SpecValidationError, match="non-positive"):
            validate_spec(spec)

    @pytest.mark.parametrize("bad_value", ["wide", None, True, float("nan"), float("inf")])
    def test_rejects_malformed_equipment_dimensions(self, bad_value):
        spec = _minimal_spec()
        spec["equipment"][0]["width"] = bad_value
        with pytest.raises(SpecValidationError, match="equipment E-1 width"):
            validate_spec(spec)

    def test_accepts_valid_spec(self):
        validate_spec(_minimal_spec())  # should not raise


# --- dxf_builder.py ---


class TestDxfBuilder:
    def test_ensure_layer_creates_layer(self):
        doc = ezdxf.new()
        ensure_layer(doc, "MY_LAYER", color=3)
        assert "MY_LAYER" in doc.layers

    def test_ensure_layer_invalid_linetype_falls_back(self, monkeypatch):
        doc = ezdxf.new()
        original_new = doc.layers.new
        calls = {"count": 0}

        def flaky_new(name, dxfattribs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise ezdxf.DXFValueError("bad linetype")
            return original_new(name=name, dxfattribs=dxfattribs)

        monkeypatch.setattr(doc.layers, "new", flaky_new)
        ensure_layer(doc, "SAFE_LAYER", color=3, linetype="NOT_A_REAL_LTYPE")
        assert doc.layers.get("SAFE_LAYER").dxf.linetype == "CONTINUOUS"

    def test_add_equipment_inline_notes_and_add_instrument_suffix(self):
        doc = ezdxf.new(setup=True)
        ensure_layer(doc, "EQUIPMENT")
        ensure_layer(doc, "TEXT")
        ensure_layer(doc, "NOTES")
        msp = doc.modelspace()
        placer = LabelPlacer()

        add_equipment(
            msp,
            {
                "id": "EQ-1",
                "type": "vertical_retort",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 12,
                "service": "Dryer",
                "notes": ["First note", "Second note"],
                "zones": [{"name": "Zone 1", "y_frac": 0.5}],
            },
            text_h=1.2,
            text_layer="TEXT",
            notes_layer="NOTES",
            show_inline_notes=True,
        )
        add_instrument(
            msp,
            {"id": "PT-101", "tag": "PT", "x": 2, "y": 2},
            text_h=1.0,
            text_layer="TEXT",
            default_layer="INSTRUMENTS",
            radius=1.2,
            show_number_suffix=True,
            label_placer=placer,
        )

        assert any(entity.dxftype() == "TEXT" and entity.dxf.text == "EQ-1" for entity in msp)
        assert any(entity.dxftype() == "TEXT" and entity.dxf.text == "- First note" for entity in msp)
        assert any(entity.dxftype() == "TEXT" and entity.dxf.text == "101" for entity in msp)
        assert placer.occupied

    def test_add_equipment_zero_dimensions_is_noop(self):
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()
        add_equipment(msp, {"id": "EQ-0", "x": 0, "y": 0, "width": 0, "height": 5}, 1.0, "TEXT", "NOTES")
        assert list(msp) == []


# --- stream_router.py ---


class TestStreamRouter:
    def test_add_stream_vertices_requires_two_points(self):
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()
        stream = {"vertices": [(0, 0)], "label": "S1"}
        assert add_stream(msp, stream, 1.5, "TEXT", {}, 1.0) is None

    def test_add_stream_with_vertices(self):
        doc = ezdxf.new(setup=True)
        ensure_layer(doc, "PROCESS", color=5)
        ensure_layer(doc, "TEXT", color=7)
        msp = doc.modelspace()
        stream = {"vertices": [(0, 0), (10, 0), (10, 10)], "label": "S1", "layer": "PROCESS"}
        result = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert result is not None

    def test_add_stream_start_end(self):
        doc = ezdxf.new(setup=True)
        ensure_layer(doc, "PROCESS", color=5)
        ensure_layer(doc, "TEXT", color=7)
        msp = doc.modelspace()
        stream = {"start": [0, 0], "end": [20, 0], "layer": "PROCESS"}
        result = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert result is not None

    def test_add_stream_none_raises(self):
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()
        with pytest.raises(ValueError, match="must not be None"):
            add_stream(msp, None, 1.5, "TEXT", {}, 1.0)

    def test_add_stream_empty_returns_none(self):
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()
        result = add_stream(msp, {}, 1.5, "TEXT", {}, 1.0)
        assert result is None

    def test_add_stream_uses_name_when_label_blank(self):
        doc = ezdxf.new(setup=True)
        ensure_layer(doc, "PROCESS", color=5)
        ensure_layer(doc, "TEXT", color=7)
        msp = doc.modelspace()
        stream = {"start": [0, 0], "end": [10, 0], "label": "", "name": "Feed", "layer": "PROCESS"}
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert any(entity.dxftype() == "TEXT" and entity.dxf.text == "Feed" for entity in msp)

    def test_add_stream_label_dict_creates_missing_leader_layer(self):
        doc = ezdxf.new(setup=True)
        ensure_layer(doc, "PROCESS", color=5)
        ensure_layer(doc, "TEXT", color=7)
        msp = doc.modelspace()
        placer = LabelPlacer()
        placer.reserve_rect((4.0, 3.0, 8.0, 6.0))
        stream = {
            "from": {"point": [0, 0]},
            "to": {"point": [10, 0]},
            "waypoints": [[5, 5]],
            "label": {"text": "Stream A", "x": 6, "y": 4},
            "layer": "PROCESS",
        }

        add_stream(
            msp,
            stream,
            text_h=1.5,
            text_layer="TEXT",
            equipment_by_id={},
            arrow_size=1.0,
            label_placer=placer,
            draw_label_leader=True,
        )

        assert "LEADERS" in doc.layers
        assert any(entity.dxftype() == "LINE" and entity.dxf.layer == "LEADERS" for entity in msp)


# --- control_loops.py ---


class TestControlLoops:
    def test_orthogonal_route_basic(self):
        route = orthogonal_control_route((0, 0), (10, 10))
        assert len(route) >= 2
        assert route[0] == (0.0, 0.0)
        assert route[-1] == (10.0, 10.0)

    def test_orthogonal_route_with_corridor(self):
        route = orthogonal_control_route((10, 30), (40, 45), route_index=0, corridor_y=15.0)
        y_vals = [p[1] for p in route]
        assert min(y_vals) <= 15.0

    def test_resolve_reference_point_instrument(self):
        ins_map = {"PT-1": {"x": 5, "y": 10}}
        result = resolve_reference_point("PT-1", {}, ins_map, {})
        assert result == (5.0, 10.0, "instrument")

    def test_resolve_reference_point_equipment(self):
        eq_map = {"E-1": {"x": 0, "y": 0, "width": 10, "height": 10}}
        result = resolve_reference_point("E-1", eq_map, {}, {})
        assert result == (5.0, 5.0, "equipment")

    def test_resolve_reference_point_not_found(self):
        result = resolve_reference_point("NOPE", {}, {}, {})
        assert result is None

    def test_resolve_reference_point_empty_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            resolve_reference_point("", {}, {}, {})

    def test_add_control_loops_none_spec_raises(self):
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()
        with pytest.raises(ValueError, match="must not be None"):
            add_control_loops(msp, None, 1.5, "TEXT", {}, {}, {})

    def test_add_control_loops_draws_lines(self):
        spec = _minimal_spec()
        doc = ezdxf.new(setup=True)
        ensure_layer(doc, "TEXT")
        ensure_layer(doc, "control_lines", color=1, linetype="CONTINUOUS")
        msp = doc.modelspace()
        eq_map = {"E-1": spec["equipment"][0], "E-2": spec["equipment"][1]}
        ins_map = {"PT-1": {"x": 2, "y": 2}}
        add_control_loops(msp, spec, 1.5, "TEXT", eq_map, ins_map, {})
        entities = list(msp)
        assert len(entities) > 0


# --- notes.py ---


class TestNotes:
    def test_get_mass_balance_defaults(self):
        spec = _minimal_spec()
        wet, fmc, dmc, cw, cmc = get_mass_balance_values(spec)
        assert wet > 0
        assert 0 < fmc < 1

    def test_get_mass_balance_none_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            get_mass_balance_values(None)

    def test_add_notes_none_raises(self):
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()
        with pytest.raises(ValueError, match="must not be None"):
            add_notes(msp, None, {"small_height": 1.0}, "TEXT", "NOTES", {})


# --- generator.py (orchestration + config helpers) ---


class TestGeneratorHelpers:
    def test_apply_profile_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown profile"):
            gen.apply_profile(_minimal_spec(), "nonexistent")

    def test_apply_profile_none_returns_copy(self):
        spec = _minimal_spec()
        result = gen.apply_profile(spec, None)
        assert result == spec
        assert result is not spec

    def test_get_text_config(self):
        cfg = gen.get_text_config(_minimal_spec())
        assert "title_height" in cfg
        assert cfg["body_height"] > 0

    def test_compute_layout_regions_keys(self):
        regions = gen.compute_layout_regions(_minimal_spec())
        assert "layout_cfg" in regions
        assert "equipment_bbox" in regions
        assert "canvas_bbox" in regions
        assert "panels" in regions

    def test_derive_related_path(self):
        p = gen.derive_related_path("out/process.dxf", "controls")
        assert str(p).endswith("process_controls.dxf")

    def test_derive_related_path_empty_suffix_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            gen.derive_related_path("foo.dxf", "")

    def test_load_spec_empty_path_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            gen.load_spec("")

    def test_generate_process_sheet_empty_out_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            gen.generate_process_sheet("spec.yml", "")

    def test_sheet_rendering_module_exists_while_generator_keeps_back_compat(self):
        from programmatic_pid import sheet_rendering

        assert callable(sheet_rendering.render_process_sheet)
        assert callable(sheet_rendering.render_controls_sheet)
        assert callable(gen.add_title_block)
        assert callable(gen.export_svg_from_dxf)

    def test_backward_compat_imports(self):
        """All symbols previously in generator.py are still importable."""
        assert gen.SpecValidationError is SpecValidationError
        assert gen.validate_spec is validate_spec
        assert gen.add_stream is add_stream
        assert gen.add_control_loops is add_control_loops
        assert gen.add_notes is add_notes
        assert gen.LabelPlacer is LabelPlacer
        assert gen.to_float is to_float


class TestSheetLayout:
    def test_resolve_sheet_layers_defaults(self):
        doc = ezdxf.new(setup=True)
        layers = resolve_sheet_layers(doc)
        assert layers["text"] == "TEXT"
        assert layers["instrument"] == "INSTRUMENTS"
        assert layers["control"] == "control_lines"

    def test_prepare_controls_sheet_context_builds_expected_canvas(self):
        spec = _minimal_spec()
        ctx = prepare_controls_sheet_context(
            spec,
            text_cfg=gen.get_text_config(spec),
            layout_cfg=gen.get_layout_config(spec),
            modelspace_extent=gen.get_modelspace_extent(spec),
        )
        assert ctx["width"] >= 200.0
        assert ctx["height"] >= 130.0
        assert "control_lines" in ctx["doc"].layers

    def test_draw_controls_header_returns_table_geometry(self):
        spec = _minimal_spec()
        ctx = prepare_controls_sheet_context(
            spec,
            text_cfg=gen.get_text_config(spec),
            layout_cfg=gen.get_layout_config(spec),
            modelspace_extent=gen.get_modelspace_extent(spec),
        )
        table = draw_controls_header(
            ctx["msp"],
            spec_name="example.yml",
            text_cfg=ctx["text_cfg"],
            text_layer=ctx["layers"]["text"],
            notes_layer=ctx["layers"]["notes"],
            x_min=ctx["x_min"],
            y_min=ctx["y_min"],
            y_max=ctx["y_max"],
            width=ctx["width"],
            height=ctx["height"],
            margin=8.0,
        )
        assert table["table_w"] > 0
        assert table["col_measure"] < table["col_ctrl"] < table["col_final"]
