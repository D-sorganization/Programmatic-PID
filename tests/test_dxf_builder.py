"""Tests for programmatic_pid.dxf_builder — shapes, text, arrows, layers, geometry."""

from __future__ import annotations

import ezdxf
import pytest

from programmatic_pid.dxf_builder import (
    LabelPlacer,
    add_arrow,
    add_arrow_head,
    add_bin_symbol,
    add_burner_symbol,
    add_equipment,
    add_fan_symbol,
    add_hopper,
    add_instrument,
    add_poly_arrow,
    add_rotary_valve_symbol,
    add_text,
    add_text_panel,
    draw_equipment_symbol,
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
