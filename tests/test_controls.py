"""Tests for programmatic_pid.controls — control loop routing and rendering."""
from __future__ import annotations

import ezdxf
import pytest

from programmatic_pid.controls import (
    add_control_loops,
    orthogonal_control_route,
    resolve_reference_point,
)
from programmatic_pid.rendering import ensure_layers


@pytest.fixture
def doc_and_msp():
    doc = ezdxf.new(setup=True)
    ensure_layers(doc, {"drawing": {}})
    return doc, doc.modelspace()


# --- orthogonal_control_route ---

class TestOrthogonalControlRoute:
    def test_basic_route(self):
        route = orthogonal_control_route((0, 0), (10, 10))
        assert len(route) >= 2
        assert route[0] == (0.0, 0.0)
        assert route[-1] == (10.0, 10.0)

    def test_with_corridor(self):
        route = orthogonal_control_route((0, 0), (10, 10), corridor_y=-5.0)
        assert len(route) >= 2
        # Should route through the corridor
        ys = [p[1] for p in route]
        assert min(ys) <= -5.0

    def test_same_point(self):
        route = orthogonal_control_route((5, 5), (5, 5))
        # Should still return at least 1 point (deduped)
        assert len(route) >= 1

    def test_route_index_offsets(self):
        r0 = orthogonal_control_route((0, 0), (10, 10), route_index=0)
        r3 = orthogonal_control_route((0, 0), (10, 10), route_index=3)
        # Different route indices should produce different routes
        assert r0 != r3


# --- resolve_reference_point ---

class TestResolveReferencePoint:
    def test_instrument_ref(self):
        result = resolve_reference_point(
            "TI-101",
            equipment_by_id={},
            instrument_by_id={"TI-101": {"x": 10, "y": 20}},
            stream_points={},
        )
        assert result == (10.0, 20.0, "instrument")

    def test_equipment_ref(self):
        result = resolve_reference_point(
            "V-101",
            equipment_by_id={"V-101": {"x": 0, "y": 0, "width": 10, "height": 10}},
            instrument_by_id={},
            stream_points={},
        )
        assert result is not None
        assert result[2] == "equipment"

    def test_stream_ref(self):
        result = resolve_reference_point(
            "S-1",
            equipment_by_id={},
            instrument_by_id={},
            stream_points={"S-1": (15.0, 25.0)},
        )
        assert result == (15.0, 25.0, "stream")

    def test_unknown_ref(self):
        result = resolve_reference_point("NOPE", {}, {}, {})
        assert result is None


# --- add_control_loops ---

class TestAddControlLoops:
    def test_draws_loop(self, doc_and_msp):
        _, msp = doc_and_msp
        spec = {
            "control_loops": [{
                "id": "CL-1",
                "measurement": "TI-101",
                "final_element": "CV-101",
            }],
            "defaults": {},
        }
        instrument_by_id = {"TI-101": {"x": 10, "y": 10}}
        equipment_by_id = {}
        stream_points = {"CV-101": (50.0, 10.0)}
        before = len(msp)
        add_control_loops(
            msp, spec, text_h=1.5, text_layer="TEXT",
            equipment_by_id=equipment_by_id,
            instrument_by_id=instrument_by_id,
            stream_points=stream_points,
        )
        assert len(msp) > before

    def test_skips_incomplete_loop(self, doc_and_msp):
        _, msp = doc_and_msp
        spec = {"control_loops": [{"id": "CL-BAD", "measurement": "", "final_element": ""}]}
        before = len(msp)
        add_control_loops(
            msp, spec, text_h=1.5, text_layer="TEXT",
            equipment_by_id={}, instrument_by_id={}, stream_points={},
        )
        assert len(msp) == before

    def test_empty_loops(self, doc_and_msp):
        _, msp = doc_and_msp
        before = len(msp)
        add_control_loops(
            msp, {"control_loops": []}, text_h=1.5, text_layer="TEXT",
            equipment_by_id={}, instrument_by_id={}, stream_points={},
        )
        assert len(msp) == before
