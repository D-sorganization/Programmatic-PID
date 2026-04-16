"""Unit tests for extracted dxf_* sub-modules (issue #58).

Each sub-module gets at least one new test that exercises it directly rather
than going through the dxf_builder facade, verifying the split is clean.
"""

from __future__ import annotations

import math

import ezdxf
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def doc():
    return ezdxf.new(setup=True)


@pytest.fixture()
def msp(doc):
    return doc.modelspace()


# ===========================================================================
# dxf_math
# ===========================================================================


class TestDxfMathDirect:
    """Import directly from dxf_math — not through dxf_builder."""

    def test_to_float_string(self):
        from programmatic_pid.dxf_math import to_float

        assert to_float("2.5") == pytest.approx(2.5)

    def test_to_float_bad_input(self):
        from programmatic_pid.dxf_math import to_float

        assert to_float("not-a-number", 7.0) == 7.0

    def test_clamp_low(self):
        from programmatic_pid.dxf_math import clamp

        assert clamp(-10, 0, 5) == 0

    def test_clamp_high(self):
        from programmatic_pid.dxf_math import clamp

        assert clamp(100, 0, 5) == 5

    def test_text_box_dimensions_positive(self):
        from programmatic_pid.dxf_math import text_box

        x1, y1, x2, y2 = text_box("Hello", 0, 0, 2.0)
        assert x2 > x1
        assert y2 > y1

    def test_rects_overlap_true(self):
        from programmatic_pid.dxf_math import rects_overlap

        assert rects_overlap((0, 0, 5, 5), (3, 3, 8, 8))

    def test_rects_overlap_false(self):
        from programmatic_pid.dxf_math import rects_overlap

        assert not rects_overlap((0, 0, 2, 2), (5, 5, 9, 9))

    def test_closest_point_outside(self):
        from programmatic_pid.dxf_math import closest_point_on_rect

        assert closest_point_on_rect((15, 5), (0, 0, 10, 10)) == (10.0, 5.0)

    def test_dedupe_removes_dupes(self):
        from programmatic_pid.dxf_math import dedupe_points

        pts = [(1, 2), (1, 2), (3, 4)]
        assert dedupe_points(pts) == [(1.0, 2.0), (3.0, 4.0)]

    def test_dedupe_empty(self):
        from programmatic_pid.dxf_math import dedupe_points

        assert dedupe_points([]) == []


# ===========================================================================
# dxf_text
# ===========================================================================


class TestDxfTextDirect:
    """Import directly from dxf_text."""

    def test_parse_alignment_string(self):
        from ezdxf.enums import TextEntityAlignment

        from programmatic_pid.dxf_text import parse_alignment

        assert parse_alignment("TOP_LEFT") == TextEntityAlignment.TOP_LEFT

    def test_parse_alignment_none_defaults(self):
        from ezdxf.enums import TextEntityAlignment

        from programmatic_pid.dxf_text import parse_alignment

        assert parse_alignment(None) == TextEntityAlignment.MIDDLE_CENTER

    def test_wrap_text_lines_wraps(self):
        from programmatic_pid.dxf_text import wrap_text_lines

        lines = wrap_text_lines("the quick brown fox jumps over the lazy dog", 15)
        assert len(lines) >= 2

    def test_wrap_text_lines_short(self):
        from programmatic_pid.dxf_text import wrap_text_lines

        assert wrap_text_lines("hi", 80) == ["hi"]

    def test_label_placer_reserve_and_check(self):
        from programmatic_pid.dxf_text import LabelPlacer

        placer = LabelPlacer()
        placer.reserve_rect((0, 0, 5, 5))
        assert len(placer.occupied) == 1

    def test_label_placer_find_clear_position(self):
        from programmatic_pid.dxf_text import LabelPlacer

        placer = LabelPlacer()
        placer.reserve_rect((0, 0, 5, 5))
        preferred = [(0, 0, "MIDDLE_CENTER"), (20, 0, "MIDDLE_LEFT")]
        x, y, align = placer.find_position("T", (2, 2), 1.0, preferred)
        assert align == "MIDDLE_LEFT"

    def test_add_text_entity_type(self, msp):
        from programmatic_pid.dxf_text import add_text

        t = add_text(msp, "Test", 0, 0, 2.0, layer="TEXT")
        assert t.dxftype() == "TEXT"

    def test_add_text_panel_creates_border(self, msp):
        from programmatic_pid.dxf_text import add_text_panel

        add_text_panel(msp, 0, 0, 40, 20, "Title", ["Body line"], 1.5, "TEXT", "BORDER")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 1


# ===========================================================================
# dxf_layer
# ===========================================================================


class TestDxfLayerDirect:
    """Import directly from dxf_layer."""

    def test_ensure_layer_creates(self, doc):
        from programmatic_pid.dxf_layer import ensure_layer

        ensure_layer(doc, "NEW_LAYER", color=4)
        assert "NEW_LAYER" in doc.layers

    def test_ensure_layer_idempotent(self, doc):
        from programmatic_pid.dxf_layer import ensure_layer

        ensure_layer(doc, "DUP", color=1)
        ensure_layer(doc, "DUP", color=2)
        assert "DUP" in doc.layers

    def test_ensure_layer_empty_name_noop(self, doc):
        from programmatic_pid.dxf_layer import ensure_layer

        count_before = len(list(doc.layers))
        ensure_layer(doc, "")
        assert len(list(doc.layers)) == count_before

    def test_ensure_layer_bad_linetype_fallback(self, doc):
        from programmatic_pid.dxf_layer import ensure_layer

        ensure_layer(doc, "BAD_LT", linetype="DOES_NOT_EXIST")
        assert "BAD_LT" in doc.layers

    def test_layer_name_resolves(self):
        from programmatic_pid.dxf_layer import layer_name

        idx = {"process": "PROCESS_LAYER"}
        assert layer_name(idx, "process") == "PROCESS_LAYER"

    def test_layer_name_default(self):
        from programmatic_pid.dxf_layer import layer_name

        assert layer_name({}, "missing") == "0"

    def test_layer_name_skips_empty(self):
        from programmatic_pid.dxf_layer import layer_name

        idx = {"text": "TEXT_LAYER"}
        assert layer_name(idx, "", None, "text") == "TEXT_LAYER"


# ===========================================================================
# dxf_symbols
# ===========================================================================


class TestDxfSymbolsDirect:
    """Import directly from dxf_symbols."""

    def test_add_box_creates_polyline(self, msp):
        from programmatic_pid.dxf_symbols import add_box

        add_box(msp, 0, 0, 10, 5, "0")
        assert any(e.dxftype() == "LWPOLYLINE" for e in msp)

    def test_add_box_negative_raises(self, msp):
        from programmatic_pid.dxf_symbols import add_box

        with pytest.raises(ValueError):
            add_box(msp, 0, 0, -1, 5, "0")

    def test_add_hopper_closed_poly(self, msp):
        from programmatic_pid.dxf_symbols import add_hopper

        add_hopper(msp, 0, 0, 10, 10, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 1

    def test_add_fan_symbol_has_circle(self, msp):
        from programmatic_pid.dxf_symbols import add_fan_symbol

        add_fan_symbol(msp, 0, 0, 10, 10, "0")
        assert any(e.dxftype() == "CIRCLE" for e in msp)

    def test_add_rotary_valve_cross_lines(self, msp):
        from programmatic_pid.dxf_symbols import add_rotary_valve_symbol

        add_rotary_valve_symbol(msp, 0, 0, 10, 10, "0")
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(lines) == 2

    def test_add_burner_box_and_flame(self, msp):
        from programmatic_pid.dxf_symbols import add_burner_symbol

        add_burner_symbol(msp, 0, 0, 10, 10, "0")
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 2

    def test_add_bin_lines(self, msp):
        from programmatic_pid.dxf_symbols import add_bin_symbol

        add_bin_symbol(msp, 0, 0, 10, 10, "0")
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(lines) == 2

    def test_draw_equipment_symbol_hopper(self, msp):
        from programmatic_pid.dxf_symbols import draw_equipment_symbol

        eq = {"type": "hopper", "x": 0, "y": 0, "w": 10, "h": 10}
        draw_equipment_symbol(msp, eq, "0")
        assert any(e.dxftype() == "LWPOLYLINE" for e in msp)

    def test_draw_equipment_symbol_default_box(self, msp):
        from programmatic_pid.dxf_symbols import draw_equipment_symbol

        eq = {"type": "unknown", "x": 0, "y": 0, "w": 8, "h": 6}
        draw_equipment_symbol(msp, eq, "0")
        assert any(e.dxftype() == "LWPOLYLINE" for e in msp)

    def test_draw_equipment_symbol_vertical_retort_zones(self, msp):
        from programmatic_pid.dxf_symbols import draw_equipment_symbol

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


# ===========================================================================
# dxf_geometry
# ===========================================================================


class TestDxfGeometryDirect:
    """Import directly from dxf_geometry."""

    def test_equipment_dims_wh(self):
        from programmatic_pid.dxf_geometry import equipment_dims

        assert equipment_dims({"w": 5, "h": 3}) == (5.0, 3.0)

    def test_equipment_dims_width_height(self):
        from programmatic_pid.dxf_geometry import equipment_dims

        assert equipment_dims({"width": 8, "height": 4}) == (8.0, 4.0)

    def test_equipment_center(self):
        from programmatic_pid.dxf_geometry import equipment_center

        eq = {"x": 0, "y": 0, "w": 10, "h": 6}
        assert equipment_center(eq) == (5.0, 3.0)

    def test_equipment_side_anchors_keys(self):
        from programmatic_pid.dxf_geometry import equipment_side_anchors

        eq = {"x": 0, "y": 0, "w": 10, "h": 10}
        anchors = equipment_side_anchors(eq)
        assert set(anchors) == {"left", "right", "top", "bottom"}

    def test_equipment_anchor_left(self):
        from programmatic_pid.dxf_geometry import equipment_anchor

        eq = {"x": 0, "y": 0, "w": 10, "h": 10}
        assert equipment_anchor(eq, "left") == (0.0, 5.0)

    def test_equipment_anchor_bottom(self):
        from programmatic_pid.dxf_geometry import equipment_anchor

        eq = {"x": 0, "y": 0, "w": 10, "h": 10}
        assert equipment_anchor(eq, "bottom") == (5.0, 0.0)

    def test_nearest_equipment_anchor(self):
        from programmatic_pid.dxf_geometry import nearest_equipment_anchor

        eq = {"x": 0, "y": 0, "w": 10, "h": 10}
        assert nearest_equipment_anchor(eq, (15, 5)) == (10.0, 5.0)

    def test_get_equipment_bounds_with_items(self):
        from programmatic_pid.dxf_geometry import get_equipment_bounds

        spec = {"equipment": [{"x": 5, "y": 10, "w": 3, "h": 4}]}
        x_min, y_min, x_max, y_max = get_equipment_bounds(spec)
        assert x_min == 5.0
        assert y_min == 10.0
        assert x_max == 8.0
        assert y_max == 14.0

    def test_get_equipment_bounds_empty_defaults(self):
        from programmatic_pid.dxf_geometry import get_equipment_bounds

        assert get_equipment_bounds({}) == (0.0, 0.0, 240.0, 160.0)

    def test_resolve_endpoint_point(self):
        from programmatic_pid.dxf_geometry import resolve_endpoint

        assert resolve_endpoint({"point": [3, 7]}, {}) == (3.0, 7.0)

    def test_resolve_endpoint_equipment(self):
        from programmatic_pid.dxf_geometry import resolve_endpoint

        eq_map = {"V-1": {"x": 0, "y": 0, "w": 10, "h": 10}}
        result = resolve_endpoint({"equipment": "V-1", "side": "right"}, eq_map)
        assert result == (10.0, 5.0)

    def test_resolve_endpoint_unknown_raises(self):
        from programmatic_pid.dxf_geometry import resolve_endpoint

        with pytest.raises(KeyError, match="Unknown equipment"):
            resolve_endpoint({"equipment": "GHOST"}, {})

    def test_spread_instrument_positions_separates(self):
        from programmatic_pid.dxf_geometry import spread_instrument_positions

        instruments = [{"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 0, "y": 0}]
        out = spread_instrument_positions(instruments, min_spacing=2.0)
        a, b = (out[0]["x"], out[0]["y"]), (out[1]["x"], out[1]["y"])
        dist = math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
        assert dist >= 2.0 - 0.01


# ===========================================================================
# dxf_arrows
# ===========================================================================


class TestDxfArrowsDirect:
    """Import directly from dxf_arrows."""

    def test_add_arrow_head_solid(self, msp):
        from programmatic_pid.dxf_arrows import add_arrow_head

        add_arrow_head(msp, (0, 0), (10, 0), "0")
        solids = [e for e in msp if e.dxftype() == "SOLID"]
        assert len(solids) == 1

    def test_add_arrow_line_and_solid(self, msp):
        from programmatic_pid.dxf_arrows import add_arrow

        add_arrow(msp, (0, 0), (10, 0), "0")
        assert any(e.dxftype() == "LINE" for e in msp)
        assert any(e.dxftype() == "SOLID" for e in msp)

    def test_add_arrow_with_color(self, msp):
        from programmatic_pid.dxf_arrows import add_arrow

        add_arrow(msp, (0, 0), (5, 0), "0", color=2)
        line = next(e for e in msp if e.dxftype() == "LINE")
        assert line.dxf.color == 2

    def test_add_poly_arrow_polyline_and_solid(self, msp):
        from programmatic_pid.dxf_arrows import add_poly_arrow

        add_poly_arrow(msp, [(0, 0), (5, 0), (5, 5)], "0")
        assert any(e.dxftype() == "LWPOLYLINE" for e in msp)
        assert any(e.dxftype() == "SOLID" for e in msp)

    def test_add_poly_arrow_too_few_points_noop(self, msp):
        from programmatic_pid.dxf_arrows import add_poly_arrow

        add_poly_arrow(msp, [(0, 0)], "0")
        assert len(list(msp)) == 0

    def test_add_arrow_head_diagonal(self, msp):
        from programmatic_pid.dxf_arrows import add_arrow_head

        add_arrow_head(msp, (0, 0), (3, 4), "0", arrow_size=2.0)
        solids = [e for e in msp if e.dxftype() == "SOLID"]
        assert len(solids) == 1
