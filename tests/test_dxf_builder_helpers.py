"""Focused tests for programmatic_pid.dxf_builder helper functions."""

from __future__ import annotations

import math

import ezdxf
import pytest
from ezdxf.enums import TextEntityAlignment

from programmatic_pid.dxf_builder import (
    LabelPlacer,
    add_box,
    clamp,
    closest_point_on_rect,
    dedupe_points,
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


@pytest.fixture()
def doc():
    """Return a fresh DXF document with standard linetypes loaded."""
    return ezdxf.new(setup=True)


@pytest.fixture()
def msp(doc):
    """Return modelspace of a fresh DXF document."""
    return doc.modelspace()


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


class TestToFloat:
    def test_int(self):
        assert to_float(7) == 7.0

    def test_string(self):
        assert to_float("3.14") == pytest.approx(3.14)

    def test_none_returns_default(self):
        assert to_float(None) == 0.0

    def test_garbage_returns_default(self):
        assert to_float("abc", 99.0) == 99.0

    def test_bool_converts(self):
        assert to_float(True) == 1.0


class TestClamp:
    def test_within_range(self):
        assert clamp(5, 0, 10) == 5

    def test_below(self):
        assert clamp(-5, 0, 10) == 0

    def test_above(self):
        assert clamp(15, 0, 10) == 10

    def test_boundary(self):
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10


class TestParseAlignment:
    def test_string(self):
        assert parse_alignment("TOP_LEFT") == TextEntityAlignment.TOP_LEFT

    def test_pass_through_enum(self):
        assert parse_alignment(TextEntityAlignment.BOTTOM_RIGHT) == TextEntityAlignment.BOTTOM_RIGHT

    def test_none_defaults(self):
        assert parse_alignment(None) == TextEntityAlignment.MIDDLE_CENTER

    def test_unknown_string_defaults(self):
        assert parse_alignment("BOGUS") == TextEntityAlignment.MIDDLE_CENTER


class TestWrapTextLines:
    def test_short_text_unchanged(self):
        lines = wrap_text_lines("hi", 80)
        assert lines == ["hi"]

    def test_long_text_wraps(self):
        lines = wrap_text_lines("hello world this is a long sentence", 15)
        assert len(lines) >= 2

    def test_non_string_coerced(self):
        lines = wrap_text_lines(12345, 80)
        assert lines == ["12345"]

    def test_width_below_minimum_clamped(self):
        # width < 12 is clamped to 12; textwrap won't break a single long word
        lines = wrap_text_lines("a" * 50, 3)
        assert len(lines) >= 1
        assert all(isinstance(ln, str) for ln in lines)

    def test_empty_string(self):
        lines = wrap_text_lines("", 20)
        assert lines == [""]


class TestTextBox:
    def test_middle_center(self):
        x1, y1, x2, y2 = text_box("ABC", 10, 10, 2.0, "MIDDLE_CENTER")
        assert x1 < 10 < x2
        assert y1 < 10 < y2

    def test_top_left(self):
        x1, y1, x2, y2 = text_box("ABC", 0, 10, 2.0, "TOP_LEFT")
        assert x1 == pytest.approx(0.0)
        assert y2 == pytest.approx(10.0)

    def test_bottom_right(self):
        x1, y1, x2, y2 = text_box("ABC", 10, 0, 2.0, "BOTTOM_RIGHT")
        assert x2 == pytest.approx(10.0)
        assert y1 == pytest.approx(0.0)

    def test_height_clamped(self):
        x1, y1, x2, y2 = text_box("A", 0, 0, -5)
        # height should be clamped to 0.1
        assert y2 - y1 > 0


class TestRectsOverlap:
    def test_overlap(self):
        assert rects_overlap((0, 0, 10, 10), (5, 5, 15, 15))

    def test_no_overlap(self):
        assert not rects_overlap((0, 0, 5, 5), (10, 10, 15, 15))

    def test_touching_edge_no_pad(self):
        # Touching exactly at boundary: ax2 == bx1, so ax2 + 0 <= bx1 is True
        assert not rects_overlap((0, 0, 5, 5), (5, 0, 10, 5))

    def test_touching_with_pad(self):
        assert not rects_overlap((0, 0, 5, 5), (6, 0, 10, 5), pad=0.5)


class TestClosestPointOnRect:
    def test_outside_right(self):
        assert closest_point_on_rect((20, 5), (0, 0, 10, 10)) == (10.0, 5.0)

    def test_inside(self):
        assert closest_point_on_rect((5, 5), (0, 0, 10, 10)) == (5.0, 5.0)

    def test_corner(self):
        assert closest_point_on_rect((-5, -5), (0, 0, 10, 10)) == (0.0, 0.0)


class TestLabelPlacer:
    def test_finds_non_overlapping_position(self):
        placer = LabelPlacer()
        placer.reserve_rect((0, 0, 10, 10))
        x, y, align = placer.find_position(
            "Label", (5, 5), 1.0, [(0, 0, "MIDDLE_CENTER"), (12, 0, "MIDDLE_LEFT")]
        )
        assert align == "MIDDLE_LEFT"

    def test_falls_back_to_first_preferred(self):
        placer = LabelPlacer()
        # Reserve everywhere so nothing is free
        for i in range(-50, 50, 5):
            for j in range(-50, 50, 5):
                placer.reserve_rect((i, j, i + 5, j + 5))
        x, y, align = placer.find_position(
            "Label", (0, 0), 1.0, [(0, 0, "MIDDLE_CENTER"), (5, 0, "MIDDLE_LEFT")]
        )
        # Falls back to first preferred
        assert align == "MIDDLE_CENTER"

    def test_reserve_text(self):
        placer = LabelPlacer()
        placer.reserve_text("hello", 10, 10, 2.0)
        assert len(placer.occupied) == 1


class TestEnsureLayer:
    def test_creates_layer(self, doc):
        ensure_layer(doc, "MY_LAYER", color=3)
        assert "MY_LAYER" in doc.layers

    def test_no_duplicate(self, doc):
        ensure_layer(doc, "L1", color=1)
        ensure_layer(doc, "L1", color=2)
        assert "L1" in doc.layers

    def test_empty_name_skipped(self, doc):
        layer_count = len(list(doc.layers))
        ensure_layer(doc, "", color=1)
        assert len(list(doc.layers)) == layer_count

    def test_invalid_linetype_falls_back(self, doc):
        ensure_layer(doc, "BAD_LT", color=1, linetype="NONEXISTENT")
        assert "BAD_LT" in doc.layers

    def test_ensure_layers_and_layer_name_default(self):
        doc = ezdxf.new(setup=True)
        spec = _minimal_spec()
        ensure_layers(doc, spec)
        assert "TEXT" in doc.layers
        assert "PROCESS" in doc.layers
        assert layer_name({"process": "PROCESS"}, None, "", default="0") == "0"

    def test_invalid_linetype_falls_back_after_retry(self, doc, monkeypatch):
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


class TestLayerName:
    def test_resolves_first_match(self):
        index = {"process": "PROCESS_LAYER", "text": "TEXT_LAYER"}
        assert layer_name(index, "process", "text") == "PROCESS_LAYER"

    def test_skips_empty_candidates(self):
        index = {"text": "TEXT_LAYER"}
        assert layer_name(index, "", None, "text") == "TEXT_LAYER"

    def test_returns_default(self):
        assert layer_name({}, "missing") == "0"

    def test_custom_default(self):
        assert layer_name({}, "missing", default="FALLBACK") == "FALLBACK"


class TestAddBox:
    def test_creates_polyline(self, msp):
        add_box(msp, 0, 0, 10, 5, "0")
        entities = list(msp)
        polys = [e for e in entities if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 1

    def test_negative_width_raises(self, msp):
        with pytest.raises(ValueError, match="positive"):
            add_box(msp, 0, 0, -1, 5, "0")

    def test_zero_height_raises(self, msp):
        with pytest.raises(ValueError, match="positive"):
            add_box(msp, 0, 0, 5, 0, "0")


class TestEquipmentGeometry:
    def test_dims_width_height_keys(self):
        assert equipment_dims({"width": 8, "height": 4}) == (8.0, 4.0)

    def test_dims_w_h_keys(self):
        assert equipment_dims({"w": 3, "h": 7}) == (3.0, 7.0)

    def test_center(self):
        eq = {"x": 10, "y": 20, "width": 6, "height": 4}
        assert equipment_center(eq) == (13.0, 22.0)

    def test_side_anchors(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        a = equipment_side_anchors(eq)
        assert a["left"] == (0.0, 5.0)
        assert a["right"] == (10.0, 5.0)
        assert a["top"] == (5.0, 10.0)
        assert a["bottom"] == (5.0, 0.0)

    def test_anchor_with_offset(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        assert equipment_anchor(eq, "right", offset=2.0) == (10.0, 7.0)
        assert equipment_anchor(eq, "top", offset=1.0) == (6.0, 10.0)

    def test_anchor_default_is_right(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        assert equipment_anchor(eq, None) == (10.0, 5.0)

    def test_nearest_anchor(self):
        eq = {"x": 0, "y": 0, "width": 10, "height": 10}
        assert nearest_equipment_anchor(eq, (-5, 5)) == (0.0, 5.0)  # left side


class TestGetEquipmentBounds:
    def test_with_equipment(self):
        spec = {
            "equipment": [
                {"x": 10, "y": 20, "width": 5, "height": 3},
                {"x": 30, "y": 40, "w": 8, "h": 6},
            ]
        }
        x_min, y_min, x_max, y_max = get_equipment_bounds(spec)
        assert x_min == 10.0
        assert y_min == 20.0
        assert x_max == 38.0
        assert y_max == 46.0

    def test_empty_equipment_defaults(self):
        assert get_equipment_bounds({"equipment": []}) == (0.0, 0.0, 240.0, 160.0)

    def test_no_key_defaults(self):
        assert get_equipment_bounds({}) == (0.0, 0.0, 240.0, 160.0)


class TestResolveEndpoint:
    def test_point(self):
        assert resolve_endpoint({"point": [5, 10]}, {}) == (5.0, 10.0)

    def test_equipment(self):
        eq_map = {"E-1": {"x": 0, "y": 0, "width": 10, "height": 10}}
        result = resolve_endpoint({"equipment": "E-1", "side": "top"}, eq_map)
        assert result == (5.0, 10.0)

    def test_unknown_equipment_raises(self):
        with pytest.raises(KeyError, match="Unknown equipment"):
            resolve_endpoint({"equipment": "X-99"}, {})

    def test_none_returns_point_error(self):
        # None endpoint defaults to empty dict, missing equipment raises
        with pytest.raises(KeyError):
            resolve_endpoint(None, {})


class TestDedupePoints:
    def test_removes_consecutive_dupes(self):
        pts = [(0, 0), (0, 0), (1, 1), (1, 1), (2, 2)]
        assert dedupe_points(pts) == [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]

    def test_empty(self):
        assert dedupe_points([]) == []

    def test_single_point(self):
        assert dedupe_points([(5, 5)]) == [(5.0, 5.0)]


class TestSpreadInstrumentPositions:
    def test_separates_overlapping(self):
        instruments = [
            {"id": "I-1", "x": 10, "y": 10},
            {"id": "I-2", "x": 10, "y": 10},
            {"id": "I-3", "x": 10, "y": 10},
        ]
        out = spread_instrument_positions(instruments, min_spacing=2.0)
        points = [(o["x"], o["y"]) for o in out]
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                dx = points[i][0] - points[j][0]
                dy = points[i][1] - points[j][1]
                assert math.sqrt(dx**2 + dy**2) >= 2.0 - 0.01

    def test_already_separated(self):
        instruments = [
            {"id": "I-1", "x": 0, "y": 0},
            {"id": "I-2", "x": 100, "y": 100},
        ]
        out = spread_instrument_positions(instruments, min_spacing=2.0)
        assert out[0]["x"] == pytest.approx(0.0)
        assert out[1]["x"] == pytest.approx(100.0)
