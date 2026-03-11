"""Tests for programmatic_pid.rendering — low-level DXF drawing primitives."""
from __future__ import annotations

import ezdxf
import pytest

from programmatic_pid.rendering import (
    add_arrow,
    add_arrow_head,
    add_box,
    add_poly_arrow,
    add_text,
    add_text_panel,
    ensure_layer,
    ensure_layers,
    layer_name,
    parse_alignment,
    wrap_text_lines,
)


@pytest.fixture
def doc_and_msp():
    doc = ezdxf.new(setup=True)
    return doc, doc.modelspace()


# --- Layer management ---

class TestEnsureLayer:
    def test_creates_new_layer(self, doc_and_msp):
        doc, _ = doc_and_msp
        ensure_layer(doc, "MY_LAYER", color=3)
        assert "MY_LAYER" in doc.layers

    def test_idempotent(self, doc_and_msp):
        doc, _ = doc_and_msp
        ensure_layer(doc, "TWICE", color=1)
        ensure_layer(doc, "TWICE", color=5)  # should not raise
        assert "TWICE" in doc.layers

    def test_empty_name_is_noop(self, doc_and_msp):
        doc, _ = doc_and_msp
        layer_count = len(doc.layers)
        ensure_layer(doc, "")
        assert len(doc.layers) == layer_count


class TestEnsureLayers:
    def test_creates_standard_layers(self, doc_and_msp):
        doc, _ = doc_and_msp
        ensure_layers(doc, {"drawing": {}})
        for name in ("TEXT", "NOTES", "LEADERS", "EQUIPMENT", "INSTRUMENTS", "PROCESS"):
            assert name in doc.layers


class TestLayerName:
    def test_resolves_from_index(self):
        idx = {"text": "TEXT", "notes": "NOTES"}
        assert layer_name(idx, "TEXT") == "TEXT"

    def test_falls_back_to_default(self):
        assert layer_name({}, "MISSING", default="FALLBACK") == "FALLBACK"


# --- Text utilities ---

class TestParseAlignment:
    def test_string_to_enum(self):
        from ezdxf.enums import TextEntityAlignment
        assert parse_alignment("TOP_LEFT") == TextEntityAlignment.TOP_LEFT

    def test_none_defaults_to_middle_center(self):
        from ezdxf.enums import TextEntityAlignment
        assert parse_alignment(None) == TextEntityAlignment.MIDDLE_CENTER


class TestWrapTextLines:
    def test_short_text_single_line(self):
        assert wrap_text_lines("hello", 80) == ["hello"]

    def test_wraps_long_text(self):
        lines = wrap_text_lines("a " * 50, 20)
        assert len(lines) > 1


# --- Drawing primitives ---

class TestAddText:
    def test_adds_text_entity(self, doc_and_msp):
        _, msp = doc_and_msp
        ensure_layer(msp.doc, "TEXT")
        t = add_text(msp, "Hello", 10, 20, 2.0)
        assert t is not None


class TestAddBox:
    def test_adds_polyline(self, doc_and_msp):
        _, msp = doc_and_msp
        ensure_layer(msp.doc, "TEST")
        add_box(msp, 0, 0, 10, 5, "TEST")
        polys = msp.query("LWPOLYLINE")
        assert len(polys) >= 1


class TestAddTextPanel:
    def test_draws_panel(self, doc_and_msp):
        _, msp = doc_and_msp
        ensure_layer(msp.doc, "TEXT")
        ensure_layer(msp.doc, "NOTES")
        add_text_panel(msp, 0, 0, 40, 20, "Title", ["Line 1", "Line 2"], 1.5, "TEXT", "NOTES")
        # Should have box + title + content texts
        assert len(msp) > 2


# --- Arrow primitives ---

class TestAddArrow:
    def test_draws_line_and_head(self, doc_and_msp):
        _, msp = doc_and_msp
        ensure_layer(msp.doc, "PROCESS")
        before = len(msp)
        add_arrow(msp, (0, 0), (10, 10), "PROCESS")
        assert len(msp) > before  # line + solid arrowhead


class TestAddPolyArrow:
    def test_draws_polyline_and_head(self, doc_and_msp):
        _, msp = doc_and_msp
        ensure_layer(msp.doc, "PROCESS")
        add_poly_arrow(msp, [(0, 0), (5, 5), (10, 0)], "PROCESS")
        polys = msp.query("LWPOLYLINE")
        assert len(polys) >= 1

    def test_too_few_vertices_is_noop(self, doc_and_msp):
        _, msp = doc_and_msp
        before = len(msp)
        add_poly_arrow(msp, [(0, 0)], "PROCESS")
        assert len(msp) == before
