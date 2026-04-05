"""Tests for programmatic_pid.stream_router — stream drawing and label placement."""

from __future__ import annotations

import ezdxf
import pytest

from programmatic_pid.dxf_builder import LabelPlacer, ensure_layer
from programmatic_pid.stream_router import add_stream

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def doc():
    """Return a fresh DXF document with standard linetypes loaded."""
    d = ezdxf.new(setup=True)
    ensure_layer(d, "PROCESS", color=5)
    ensure_layer(d, "TEXT", color=7)
    ensure_layer(d, "LEADERS", color=8, linetype="DASHED")
    return d


@pytest.fixture()
def msp(doc):
    """Return modelspace of a prepared DXF document."""
    return doc.modelspace()


def _eq_map():
    """Standard equipment map for from/to tests."""
    return {
        "E-1": {"x": 0, "y": 0, "width": 10, "height": 10},
        "E-2": {"x": 30, "y": 0, "width": 10, "height": 10},
    }


# ===================================================================
# Basic stream routing
# ===================================================================


class TestAddStreamVertices:
    def test_draws_poly_arrow(self, msp):
        stream = {"vertices": [(0, 0), (10, 0), (10, 10)], "layer": "PROCESS"}
        result = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert result is not None
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) == 1

    def test_too_few_vertices_returns_none(self, msp):
        stream = {"vertices": [(0, 0)], "layer": "PROCESS"}
        result = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert result is None

    def test_label_midpoint(self, msp):
        stream = {"vertices": [(0, 0), (10, 0), (10, 10)], "label": "S1", "layer": "PROCESS"}
        lx, ly = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert lx == pytest.approx(20.0 / 3)
        assert ly == pytest.approx(10.0 / 3)


class TestAddStreamStartEnd:
    def test_draws_arrow(self, msp):
        stream = {"start": [0, 0], "end": [20, 0], "layer": "PROCESS"}
        result = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert result is not None
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(lines) >= 1

    def test_midpoint(self, msp):
        stream = {"start": [0, 0], "end": [20, 10], "layer": "PROCESS"}
        lx, ly = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert lx == pytest.approx(10.0)
        assert ly == pytest.approx(5.0)


class TestAddStreamFromTo:
    def test_simple_from_to(self, msp):
        stream = {
            "from": {"equipment": "E-1", "side": "right"},
            "to": {"equipment": "E-2", "side": "left"},
            "layer": "PROCESS",
        }
        result = add_stream(msp, stream, 1.5, "TEXT", _eq_map(), 1.0)
        assert result is not None

    def test_with_waypoints(self, msp):
        stream = {
            "from": {"equipment": "E-1", "side": "right"},
            "to": {"equipment": "E-2", "side": "left"},
            "waypoints": [(15, 5), (25, 5)],
            "layer": "PROCESS",
        }
        result = add_stream(msp, stream, 1.5, "TEXT", _eq_map(), 1.0)
        assert result is not None
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) >= 1

    def test_from_to_no_waypoints_arrow(self, msp):
        stream = {
            "from": {"equipment": "E-1", "side": "right"},
            "to": {"equipment": "E-2", "side": "left"},
            "layer": "PROCESS",
        }
        add_stream(msp, stream, 1.5, "TEXT", _eq_map(), 1.0)
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(lines) >= 1


# ===================================================================
# Edge cases
# ===================================================================


class TestAddStreamEdgeCases:
    def test_none_raises(self, msp):
        with pytest.raises(ValueError, match="must not be None"):
            add_stream(msp, None, 1.5, "TEXT", {}, 1.0)

    def test_empty_dict_returns_none(self, msp):
        result = add_stream(msp, {}, 1.5, "TEXT", {}, 1.0)
        assert result is None

    def test_no_routing_keys_returns_none(self, msp):
        stream = {"label": "orphan", "layer": "PROCESS"}
        result = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert result is None


# ===================================================================
# Label handling
# ===================================================================


class TestStreamLabels:
    def test_string_label(self, msp):
        stream = {"start": [0, 0], "end": [20, 0], "label": "S-100", "layer": "PROCESS"}
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert any(t.dxf.text == "S-100" for t in texts)

    def test_dict_label(self, msp):
        stream = {
            "start": [0, 0],
            "end": [20, 0],
            "label": {"text": "Stream A", "x": 15, "y": 5},
            "layer": "PROCESS",
        }
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert any(t.dxf.text == "Stream A" for t in texts)

    def test_name_fallback_label(self, msp):
        stream = {"start": [0, 0], "end": [20, 0], "name": "Process Gas", "layer": "PROCESS"}
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert any(t.dxf.text == "Process Gas" for t in texts)

    def test_no_label(self, msp):
        stream = {"start": [0, 0], "end": [20, 0], "layer": "PROCESS"}
        result = add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        assert result is not None
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert len(texts) == 0

    def test_empty_label_string(self, msp):
        stream = {"start": [0, 0], "end": [20, 0], "label": "  ", "layer": "PROCESS"}
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert len(texts) == 0


# ===================================================================
# Label placer integration
# ===================================================================


class TestStreamLabelPlacer:
    def test_with_label_placer(self, msp):
        placer = LabelPlacer()
        stream = {"start": [0, 0], "end": [20, 0], "label": "S-1", "layer": "PROCESS"}
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0, label_placer=placer)
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert any(t.dxf.text == "S-1" for t in texts)

    def test_leader_line_when_displaced(self, msp):
        placer = LabelPlacer()
        # Reserve the default label area to force displacement
        placer.reserve_rect((9.0, 0.0, 13.0, 3.0))
        stream = {
            "start": [0, 0],
            "end": [20, 0],
            "label": "Displaced Label",
            "layer": "PROCESS",
        }
        add_stream(
            msp,
            stream,
            1.5,
            "TEXT",
            {},
            1.0,
            label_placer=placer,
            draw_label_leader=True,
            leader_layer="LEADERS",
        )
        leader_lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "LEADERS"]
        assert len(leader_lines) >= 1

    def test_no_leader_when_leader_disabled(self, msp):
        placer = LabelPlacer()
        stream = {"start": [0, 0], "end": [20, 0], "label": "S-1", "layer": "PROCESS"}
        add_stream(
            msp,
            stream,
            1.5,
            "TEXT",
            {},
            1.0,
            label_placer=placer,
            draw_label_leader=False,
            leader_layer="LEADERS",
        )
        leader_lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "LEADERS"]
        assert len(leader_lines) == 0


# ===================================================================
# Stream color and layer
# ===================================================================


class TestStreamColor:
    def test_custom_color(self, msp):
        stream = {"start": [0, 0], "end": [20, 0], "layer": "PROCESS", "color": 3}
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert any(e.dxf.color == 3 for e in lines)

    def test_default_layer(self, msp):
        stream = {"start": [0, 0], "end": [20, 0]}
        add_stream(msp, stream, 1.5, "TEXT", {}, 1.0)
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert all(e.dxf.layer == "PROCESS" for e in lines)
