"""Tests for programmatic_pid.title_block — title block and notes panels."""
from __future__ import annotations

import ezdxf
import pytest

from programmatic_pid.rendering import ensure_layers
from programmatic_pid.title_block import add_notes, add_title_block, get_mass_balance_values


@pytest.fixture
def doc_and_msp():
    doc = ezdxf.new(setup=True)
    ensure_layers(doc, {"drawing": {}})
    return doc, doc.modelspace()


class TestAddTitleBlock:
    def test_draws_title_block(self, doc_and_msp):
        _, msp = doc_and_msp
        spec = {"project": {"title": "Test P&ID", "document_number": "PID-001"}}
        text_cfg = {"body_height": 2.0, "small_height": 1.5}
        before = len(msp)
        add_title_block(msp, spec, text_cfg, "TEXT", "NOTES", (0, 0, 100, 15))
        assert len(msp) > before

    def test_zero_dimension_is_noop(self, doc_and_msp):
        _, msp = doc_and_msp
        before = len(msp)
        add_title_block(msp, {}, {"body_height": 2.0, "small_height": 1.5},
                        "TEXT", "NOTES", (0, 0, 0, 0))
        assert len(msp) == before


class TestGetMassBalanceValues:
    def test_from_mass_balance_basis(self):
        spec = {"mass_balance": {"basis": {
            "wet_feed_kg_h": 500,
            "feed_moisture_wt_frac": 0.25,
            "dried_feed_target_moisture_wt_frac": 0.10,
            "wet_biochar_product_kg_h": 200,
            "product_moisture_wt_frac": 0.03,
        }}}
        result = get_mass_balance_values(spec)
        assert result == (500.0, 0.25, 0.10, 200.0, 0.03)

    def test_from_assumptions(self):
        spec = {"assumptions": {
            "feed": {"wet_biomass_rate_kg_h": 1000, "moisture_wtfrac": 0.30},
            "dryer": {"target_moisture_wtfrac": 0.20},
            "reactor": {"dry_char_yield_fraction_of_dry_feed": 0.42,
                        "char_product_moisture_wtfrac": 0.02},
        }}
        wet_feed, feed_mc, dried_mc, char_wet, char_mc = get_mass_balance_values(spec)
        assert wet_feed == 1000.0
        assert feed_mc == 0.30
        assert char_wet > 0

    def test_empty_spec_uses_defaults(self):
        result = get_mass_balance_values({})
        assert len(result) == 5
        assert all(isinstance(v, float) for v in result)


class TestAddNotes:
    def test_draws_panels(self, doc_and_msp):
        _, msp = doc_and_msp
        spec = {
            "control_loops": [{"id": "CL-1", "objective": "Temp control"}],
            "equipment": [],
            "interlocks": [],
            "annotations": {},
            "drawing": {},
        }
        from programmatic_pid.layout import compute_layout_regions
        # Need valid layout regions
        spec["equipment"] = [{"x": 10, "y": 20, "width": 30, "height": 20}]
        layout_regions = compute_layout_regions(spec)
        text_cfg = {"body_height": 2.0, "small_height": 1.5}
        before = len(msp)
        add_notes(msp, spec, text_cfg, "TEXT", "NOTES", layout_regions)
        assert len(msp) > before  # three panels drawn
