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
    add_box,
    clamp,
    closest_point_on_rect,
    dedupe_points,
    ensure_layer,
    equipment_anchor,
    equipment_center,
    equipment_dims,
    equipment_side_anchors,
    nearest_equipment_anchor,
    parse_alignment,
    rects_overlap,
    resolve_endpoint,
    spread_instrument_positions,
    text_box,
    to_float,
    wrap_text_lines,
)
from programmatic_pid.notes import add_notes, get_mass_balance_values
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

    def test_accepts_valid_spec(self):
        validate_spec(_minimal_spec())  # should not raise


# --- dxf_builder.py ---


class TestDxfBuilder:
    def test_to_float_normal(self):
        assert to_float("3.14") == pytest.approx(3.14)

    def test_to_float_fallback(self):
        assert to_float("abc", 42.0) == 42.0

    def test_to_float_none(self):
        assert to_float(None) == 0.0

    def test_clamp(self):
        assert clamp(5, 0, 10) == 5
        assert clamp(-1, 0, 10) == 0
        assert clamp(20, 0, 10) == 10

    def test_wrap_text_lines(self):
        lines = wrap_text_lines("hello world this is a long line", 15)
        assert len(lines) >= 2
        assert all(isinstance(item, str) for item in lines)

    def test_text_box_centered(self):
        x1, y1, x2, y2 = text_box("ABC", 10, 10, 2.0, "MIDDLE_CENTER")
        assert x1 < 10 < x2
        assert y1 < 10 < y2

    def test_rects_overlap_true(self):
        assert rects_overlap((0, 0, 10, 10), (5, 5, 15, 15))

    def test_rects_overlap_false(self):
        assert not rects_overlap((0, 0, 5, 5), (10, 10, 15, 15))

    def test_closest_point_on_rect(self):
        pt = closest_point_on_rect((20, 5), (0, 0, 10, 10))
        assert pt == (10.0, 5.0)

    def test_equipment_dims(self):
        assert equipment_dims({"width": 8, "height": 4}) == (8.0, 4.0)
        assert equipment_dims({"w": 3, "h": 7}) == (3.0, 7.0)

    def test_equipment_center(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        assert equipment_center(eq) == (5.0, 5.0)

    def test_equipment_side_anchors(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        anchors = equipment_side_anchors(eq)
        assert anchors["left"] == (0.0, 5.0)
        assert anchors["right"] == (10.0, 5.0)
        assert anchors["top"] == (5.0, 10.0)
        assert anchors["bottom"] == (5.0, 0.0)

    def test_equipment_anchor_sides(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        assert equipment_anchor(eq, "left") == (0.0, 5.0)
        assert equipment_anchor(eq, "right") == (10.0, 5.0)
        assert equipment_anchor(eq, "top") == (5.0, 10.0)
        assert equipment_anchor(eq, "bottom") == (5.0, 0.0)

    def test_nearest_equipment_anchor(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        assert nearest_equipment_anchor(eq, (20, 5)) == (10.0, 5.0)

    def test_resolve_endpoint_with_point(self):
        ep = {"point": [42, 99]}
        assert resolve_endpoint(ep, {}) == (42.0, 99.0)

    def test_resolve_endpoint_unknown_equipment(self):
        with pytest.raises(KeyError, match="Unknown equipment"):
            resolve_endpoint({"equipment": "X-99"}, {})

    def test_dedupe_points(self):
        pts = [(0, 0), (0, 0), (1, 1), (1, 1), (2, 2)]
        assert dedupe_points(pts) == [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]

    def test_spread_instrument_positions_no_collision(self):
        instruments = [
            {"id": "I-1", "x": 10, "y": 10},
            {"id": "I-2", "x": 10, "y": 10},
        ]
        out = spread_instrument_positions(instruments, min_spacing=2.0)
        assert len(out) == 2
        p1 = (out[0]["x"], out[0]["y"])
        p2 = (out[1]["x"], out[1]["y"])
        dist_sq = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
        assert dist_sq >= 2.0**2 - 0.01

    def test_parse_alignment_string(self):
        from ezdxf.enums import TextEntityAlignment

        assert parse_alignment("MIDDLE_CENTER") == TextEntityAlignment.MIDDLE_CENTER
        assert parse_alignment("TOP_LEFT") == TextEntityAlignment.TOP_LEFT

    def test_add_box_negative_dims_raises(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        with pytest.raises(ValueError, match="positive"):
            add_box(msp, 0, 0, -1, 5, "0")

    def test_label_placer_finds_position(self):
        placer = LabelPlacer()
        placer.reserve_rect((0, 0, 10, 10))
        x, y, align = placer.find_position(
            "Label",
            (5, 5),
            1.0,
            [(0, 0, "MIDDLE_CENTER"), (12, 0, "MIDDLE_LEFT")],
        )
        # First position overlaps, second should be chosen
        assert align == "MIDDLE_LEFT"

    def test_ensure_layer_creates_layer(self):
        doc = ezdxf.new()
        ensure_layer(doc, "MY_LAYER", color=3)
        assert "MY_LAYER" in doc.layers


# --- stream_router.py ---


class TestStreamRouter:
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

    def test_backward_compat_imports(self):
        """All symbols previously in generator.py are still importable."""
        assert gen.SpecValidationError is SpecValidationError
        assert gen.validate_spec is validate_spec
        assert gen.add_stream is add_stream
        assert gen.add_control_loops is add_control_loops
        assert gen.add_notes is add_notes
        assert gen.LabelPlacer is LabelPlacer
        assert gen.to_float is to_float
