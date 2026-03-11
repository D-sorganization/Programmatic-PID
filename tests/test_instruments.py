"""Tests for programmatic_pid.instruments — instrument bubble rendering."""
from __future__ import annotations

import ezdxf
import pytest

from programmatic_pid.instruments import add_instrument
from programmatic_pid.rendering import ensure_layers


@pytest.fixture
def doc_and_msp():
    doc = ezdxf.new(setup=True)
    ensure_layers(doc, {"drawing": {}})
    return doc, doc.modelspace()


class TestAddInstrument:
    def test_draws_circle_and_text(self, doc_and_msp):
        _, msp = doc_and_msp
        add_instrument(
            msp,
            {"id": "TI-101", "tag": "TI-101", "x": 10, "y": 20},
            text_h=1.5, text_layer="TEXT",
            default_layer="INSTRUMENTS", radius=1.8,
        )
        circles = msp.query("CIRCLE")
        assert len(circles) >= 1

    def test_with_number_suffix(self, doc_and_msp):
        _, msp = doc_and_msp
        before = len(msp)
        add_instrument(
            msp,
            {"id": "TI-101", "tag": "TI-101", "x": 10, "y": 20},
            text_h=1.5, text_layer="TEXT",
            default_layer="INSTRUMENTS", radius=1.8,
            show_number_suffix=True,
        )
        # Should have circle + main text + suffix text
        assert len(msp) > before + 1

    def test_with_label_placer(self, doc_and_msp):
        from programmatic_pid.layout import LabelPlacer
        _, msp = doc_and_msp
        lp = LabelPlacer()
        add_instrument(
            msp,
            {"id": "PI-201", "x": 5, "y": 5},
            text_h=1.5, text_layer="TEXT",
            default_layer="INSTRUMENTS", radius=1.8,
            label_placer=lp,
        )
        assert len(lp.occupied) == 1  # bubble rect reserved

    def test_missing_tag_uses_id(self, doc_and_msp):
        _, msp = doc_and_msp
        # No tag, only id — should still render
        add_instrument(
            msp,
            {"id": "FI-300", "x": 0, "y": 0},
            text_h=1.5, text_layer="TEXT",
            default_layer="INSTRUMENTS", radius=1.8,
        )
        texts = msp.query("TEXT")
        assert len(texts) >= 1
