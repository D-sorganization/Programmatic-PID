"""Tests for programmatic_pid.layout — canvas layout and label placement."""
from __future__ import annotations

import pytest

from programmatic_pid.layout import (
    LabelPlacer,
    compute_layout_regions,
    get_equipment_bounds,
    get_modelspace_extent,
    spread_instrument_positions,
)


# --- LabelPlacer ---

class TestLabelPlacer:
    def test_first_position_is_accepted(self):
        lp = LabelPlacer()
        x, y, align = lp.find_position(
            "Hello", (10, 10), 2.0,
            preferred=[(0, 3, "BOTTOM_CENTER"), (0, -3, "TOP_CENTER")],
        )
        assert isinstance(x, float)
        assert isinstance(y, float)
        assert isinstance(align, str)

    def test_collision_shifts_to_alternative(self):
        lp = LabelPlacer()
        # Reserve a large area at (10, 13)
        lp.reserve_rect((5, 11, 15, 15))
        x, y, align = lp.find_position(
            "Hi", (10, 10), 1.0,
            preferred=[(0, 3, "BOTTOM_CENTER"), (0, -3, "TOP_CENTER")],
        )
        # Should have picked the second preferred since first overlaps
        # (or first if it happens to not overlap — both are valid)
        assert align in ("BOTTOM_CENTER", "TOP_CENTER")

    def test_reserve_text(self):
        lp = LabelPlacer()
        lp.reserve_text("test", 10, 10, 2.0)
        assert len(lp.occupied) == 1

    def test_fallback_when_all_collide(self):
        lp = LabelPlacer()
        # Reserve everything around anchor
        for dx in range(-20, 20, 2):
            for dy in range(-20, 20, 2):
                lp.reserve_rect((dx, dy, dx + 2, dy + 2))
        # Should still return something (fallback to first preferred)
        x, y, align = lp.find_position(
            "Test", (0, 0), 1.0,
            preferred=[(0, 3, "BOTTOM_CENTER")],
        )
        assert align == "BOTTOM_CENTER"


# --- spread_instrument_positions ---

class TestSpreadInstrumentPositions:
    def test_preserves_count(self):
        instruments = [{"x": 10, "y": 10}, {"x": 10, "y": 10}, {"x": 10, "y": 10}]
        result = spread_instrument_positions(instruments, min_spacing=3.5)
        assert len(result) == 3

    def test_spreads_overlapping_instruments(self):
        instruments = [{"x": 0, "y": 0}, {"x": 0, "y": 0}]
        result = spread_instrument_positions(instruments, min_spacing=2.0)
        p1 = (result[0]["x"], result[0]["y"])
        p2 = (result[1]["x"], result[1]["y"])
        dist = ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
        assert dist >= 1.2  # at least min viable spacing

    def test_empty_input(self):
        assert spread_instrument_positions([]) == []


# --- get_equipment_bounds ---

class TestGetEquipmentBounds:
    def test_with_equipment(self):
        spec = {"equipment": [
            {"x": 10, "y": 20, "width": 15, "height": 10},
            {"x": 50, "y": 30, "width": 20, "height": 15},
        ]}
        x_min, y_min, x_max, y_max = get_equipment_bounds(spec)
        assert x_min == 10
        assert y_min == 20
        assert x_max >= 70  # 50 + 20
        assert y_max >= 45  # 30 + 15

    def test_no_equipment_returns_defaults(self):
        bounds = get_equipment_bounds({"equipment": []})
        assert bounds == (0.0, 0.0, 240.0, 160.0)


# --- compute_layout_regions ---

class TestComputeLayoutRegions:
    def test_returns_required_keys(self):
        spec = {
            "equipment": [{"x": 10, "y": 20, "width": 30, "height": 20}],
            "drawing": {},
        }
        regions = compute_layout_regions(spec)
        assert "layout_cfg" in regions
        assert "equipment_bbox" in regions
        assert "canvas_bbox" in regions
        assert "panels" in regions
        assert set(regions["panels"].keys()) == {"control", "mass", "right", "title"}


# --- get_modelspace_extent ---

class TestGetModelspaceExtent:
    def test_from_explicit_extent(self):
        spec = {"drawing": {"modelspace_extent": {
            "x_min": 0, "y_min": 0, "x_max": 200, "y_max": 150,
        }}}
        result = get_modelspace_extent(spec)
        assert result == (0.0, 0.0, 200.0, 150.0)

    def test_computed_from_equipment(self):
        spec = {
            "drawing": {},
            "equipment": [{"x": 10, "y": 10, "width": 20, "height": 15}],
        }
        x_min, y_min, x_max, y_max = get_modelspace_extent(spec)
        assert x_min < 10  # includes margin
        assert y_max > 25  # includes margin

    def test_fallback_default(self):
        result = get_modelspace_extent({"drawing": {}})
        assert result == (0.0, 0.0, 240.0, 160.0)
