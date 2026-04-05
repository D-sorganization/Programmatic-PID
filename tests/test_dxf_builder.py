"""Tests for programmatic_pid.dxf_builder — shapes, text, arrows, layers, geometry."""

from __future__ import annotations

import math

import ezdxf
import pytest
from ezdxf.enums import TextEntityAlignment

from programmatic_pid.dxf_builder import (
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def doc():
    """Return a fresh DXF document with standard linetypes loaded."""
    return ezdxf.new(setup=True)


@pytest.fixture()
def msp(doc):
    """Return modelspace of a fresh DXF document."""
    return doc.modelspace()


# ===================================================================
# Numeric helpers
# ===================================================================


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


# ===================================================================
# Text utilities
# ===================================================================


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


# ===================================================================
# Bounding-box helpers
# ===================================================================


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


# ===================================================================
# LabelPlacer
# ===================================================================


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


# ===================================================================
# Layer helpers
# ===================================================================


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


# ===================================================================
# DXF drawing primitives
# ===================================================================


class TestAddText:
    def test_creates_text_entity(self, msp):
        t = add_text(msp, "Hello", 10, 20, 2.0, layer="TEXT")
        assert t.dxftype() == "TEXT"
        assert t.dxf.layer == "TEXT"

    def test_height_clamped(self, msp):
        t = add_text(msp, "X", 0, 0, -5)
        assert t.dxf.height >= 0.1


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


class TestAddTextPanel:
    def test_draws_border_and_text(self, msp):
        add_text_panel(msp, 0, 0, 30, 20, "Title", ["Line 1", "Line 2"], 1.5, "TEXT", "BORDER")
        entities = list(msp)
        assert any(e.dxftype() == "LWPOLYLINE" for e in entities)
        texts = [e for e in entities if e.dxftype() == "TEXT"]
        assert len(texts) >= 2  # title + at least one body line

    def test_none_line_becomes_blank(self, msp):
        add_text_panel(msp, 0, 0, 30, 20, "T", [None, "real"], 1.5, "TEXT", "BORDER")
        # Should not raise


# ===================================================================
# Equipment shape symbols
# ===================================================================


class TestShapeSymbols:
    def test_add_hopper(self, msp):
        add_hopper(msp, 0, 0, 10, 10, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 1

    def test_add_fan_symbol(self, msp):
        add_fan_symbol(msp, 0, 0, 10, 10, "0")
        circles = [e for e in msp if e.dxftype() == "CIRCLE"]
        assert len(circles) == 1

    def test_add_rotary_valve_symbol(self, msp):
        add_rotary_valve_symbol(msp, 0, 0, 10, 10, "0")
        circles = [e for e in msp if e.dxftype() == "CIRCLE"]
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(circles) == 1
        assert len(lines) == 2

    def test_add_burner_symbol(self, msp):
        add_burner_symbol(msp, 0, 0, 10, 10, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 2  # box + flame

    def test_add_bin_symbol(self, msp):
        add_bin_symbol(msp, 0, 0, 10, 10, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(polys) == 1
        assert len(lines) == 2


class TestDrawEquipmentSymbol:
    def test_dispatches_hopper(self, msp):
        eq = {"type": "hopper", "x": 0, "y": 0, "w": 10, "h": 10}
        draw_equipment_symbol(msp, eq, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 1

    def test_dispatches_fan(self, msp):
        eq = {"type": "fan", "x": 0, "y": 0, "w": 10, "h": 10}
        draw_equipment_symbol(msp, eq, "0")
        assert any(e.dxftype() == "CIRCLE" for e in msp)

    def test_dispatches_rotary_valve(self, msp):
        eq = {"type": "rotary_valve", "x": 0, "y": 0, "w": 10, "h": 10}
        draw_equipment_symbol(msp, eq, "0")
        assert any(e.dxftype() == "CIRCLE" for e in msp)

    def test_dispatches_burner(self, msp):
        eq = {"type": "burner", "x": 0, "y": 0, "w": 10, "h": 10}
        draw_equipment_symbol(msp, eq, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 2

    def test_dispatches_bin(self, msp):
        eq = {"type": "bin", "x": 0, "y": 0, "w": 10, "h": 10}
        draw_equipment_symbol(msp, eq, "0")
        assert any(e.dxftype() == "LINE" for e in msp)

    def test_default_box(self, msp):
        eq = {"type": "generic", "x": 0, "y": 0, "w": 10, "h": 10}
        draw_equipment_symbol(msp, eq, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 1

    def test_vertical_retort_draws_zones(self, msp):
        eq = {
            "type": "vertical_retort",
            "x": 0,
            "y": 0,
            "w": 10,
            "h": 20,
            "zones": [{"name": "Z1", "y_frac": 0.5}],
        }
        draw_equipment_symbol(msp, eq, "0")
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(lines) >= 1


# ===================================================================
# Arrow primitives
# ===================================================================


class TestArrows:
    def test_add_arrow_head_creates_solid(self, msp):
        add_arrow_head(msp, (0, 0), (10, 0), "0")
        solids = [e for e in msp if e.dxftype() == "SOLID"]
        assert len(solids) == 1

    def test_add_arrow_creates_line_and_solid(self, msp):
        add_arrow(msp, (0, 0), (10, 0), "0")
        lines = [e for e in msp if e.dxftype() == "LINE"]
        solids = [e for e in msp if e.dxftype() == "SOLID"]
        assert len(lines) == 1
        assert len(solids) == 1

    def test_add_arrow_with_color(self, msp):
        add_arrow(msp, (0, 0), (10, 0), "0", color=3)
        line = [e for e in msp if e.dxftype() == "LINE"][0]
        assert line.dxf.color == 3

    def test_add_poly_arrow(self, msp):
        add_poly_arrow(msp, [(0, 0), (10, 0), (10, 10)], "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        solids = [e for e in msp if e.dxftype() == "SOLID"]
        assert len(polys) == 1
        assert len(solids) == 1

    def test_add_poly_arrow_too_few_points(self, msp):
        add_poly_arrow(msp, [(0, 0)], "0")
        assert len(list(msp)) == 0


# ===================================================================
# Equipment geometry helpers
# ===================================================================


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


# ===================================================================
# Equipment and instrument rendering
# ===================================================================


class TestAddEquipment:
    def test_draws_equipment_with_label(self, msp):
        eq = {"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10, "service": "Reactor"}
        add_equipment(msp, eq, 2.0, "TEXT", "NOTES")
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert len(texts) >= 2  # id + service

    def test_skips_zero_dim(self, msp):
        eq = {"id": "E-1", "x": 0, "y": 0, "width": 0, "height": 10}
        add_equipment(msp, eq, 2.0, "TEXT", "NOTES")
        assert len(list(msp)) == 0

    def test_id_only_label(self, msp):
        eq = {"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10}
        add_equipment(msp, eq, 2.0, "TEXT", "NOTES")
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert len(texts) == 1

    def test_inline_notes(self, msp):
        eq = {
            "id": "E-1",
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 10,
            "notes": ["Note 1", "Note 2"],
        }
        add_equipment(msp, eq, 2.0, "TEXT", "NOTES", show_inline_notes=True)
        note_texts = [e for e in msp if e.dxftype() == "TEXT" and e.dxf.layer == "NOTES"]
        assert len(note_texts) == 2

    def test_vertical_retort_zones(self, msp):
        eq = {
            "id": "VR-1",
            "type": "vertical_retort",
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 20,
            "zones": [{"name": "Drying", "y_frac": 0.3}],
        }
        add_equipment(msp, eq, 2.0, "TEXT", "NOTES")
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        zone_labels = [t for t in texts if t.dxf.text == "Drying"]
        assert len(zone_labels) == 1


class TestAddInstrument:
    def test_draws_circle_and_tag(self, msp):
        ins = {"tag": "PT-100", "x": 5, "y": 5}
        add_instrument(msp, ins, 2.0, "TEXT", "INSTRUMENTS", radius=1.8)
        circles = [e for e in msp if e.dxftype() == "CIRCLE"]
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert len(circles) == 1
        assert len(texts) >= 1

    def test_number_suffix(self, msp):
        ins = {"tag": "PT-100", "id": "PT-100", "x": 5, "y": 5}
        add_instrument(msp, ins, 2.0, "TEXT", "INSTRUMENTS", radius=1.8, show_number_suffix=True)
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert len(texts) == 2  # tag + number suffix

    def test_with_label_placer(self, msp):
        placer = LabelPlacer()
        ins = {"tag": "FT-1", "x": 10, "y": 10}
        add_instrument(msp, ins, 2.0, "TEXT", "INSTRUMENTS", radius=1.8, label_placer=placer)
        assert len(placer.occupied) == 1
