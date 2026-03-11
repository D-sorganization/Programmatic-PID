"""Tests for programmatic_pid.streams — stream/pipe rendering."""
from __future__ import annotations

import ezdxf
import pytest

from programmatic_pid.rendering import ensure_layer, ensure_layers
from programmatic_pid.streams import add_stream, resolve_endpoint


@pytest.fixture
def doc_and_msp():
    doc = ezdxf.new(setup=True)
    ensure_layers(doc, {"drawing": {}})
    return doc, doc.modelspace()


# --- resolve_endpoint ---

class TestResolveEndpoint:
    def test_point_endpoint(self):
        ep = {"point": [10.0, 20.0]}
        x, y = resolve_endpoint(ep, {})
        assert (x, y) == (10.0, 20.0)

    def test_equipment_endpoint(self):
        eq = {"id": "V-101", "x": 10, "y": 20, "width": 15, "height": 10}
        x, y = resolve_endpoint(
            {"equipment": "V-101", "side": "right", "offset": 0.0},
            {"V-101": eq},
        )
        assert x >= 25  # right side of equipment

    def test_missing_equipment_raises(self):
        with pytest.raises(KeyError, match="Unknown equipment"):
            resolve_endpoint({"equipment": "NOPE"}, {})

    def test_none_endpoint_raises(self):
        with pytest.raises(KeyError):
            resolve_endpoint(None, {})


# --- add_stream ---

class TestAddStream:
    def test_vertices_stream(self, doc_and_msp):
        _, msp = doc_and_msp
        result = add_stream(
            msp,
            {"vertices": [[0, 0], [10, 10], [20, 0]], "label": "S-1"},
            text_h=1.5, text_layer="TEXT",
            equipment_by_id={}, arrow_size=1.2,
        )
        assert result is not None
        assert len(result) == 2

    def test_start_end_stream(self, doc_and_msp):
        _, msp = doc_and_msp
        result = add_stream(
            msp,
            {"start": [0, 0], "end": [20, 20]},
            text_h=1.5, text_layer="TEXT",
            equipment_by_id={}, arrow_size=1.2,
        )
        assert result is not None

    def test_from_to_stream(self, doc_and_msp):
        _, msp = doc_and_msp
        eq = {"id": "V-101", "x": 0, "y": 0, "width": 10, "height": 10}
        eq2 = {"id": "V-102", "x": 30, "y": 0, "width": 10, "height": 10}
        result = add_stream(
            msp,
            {"from": {"equipment": "V-101", "side": "right"},
             "to": {"equipment": "V-102", "side": "left"}},
            text_h=1.5, text_layer="TEXT",
            equipment_by_id={"V-101": eq, "V-102": eq2},
            arrow_size=1.2,
        )
        assert result is not None

    def test_empty_stream_returns_none(self, doc_and_msp):
        _, msp = doc_and_msp
        result = add_stream(
            msp, {}, text_h=1.5, text_layer="TEXT",
            equipment_by_id={}, arrow_size=1.2,
        )
        assert result is None

    def test_too_few_vertices_returns_none(self, doc_and_msp):
        _, msp = doc_and_msp
        result = add_stream(
            msp, {"vertices": [[0, 0]]},
            text_h=1.5, text_layer="TEXT",
            equipment_by_id={}, arrow_size=1.2,
        )
        assert result is None

    def test_dict_label(self, doc_and_msp):
        _, msp = doc_and_msp
        result = add_stream(
            msp,
            {"vertices": [[0, 0], [10, 10]],
             "label": {"text": "S-1", "x": 5, "y": 8}},
            text_h=1.5, text_layer="TEXT",
            equipment_by_id={}, arrow_size=1.2,
        )
        assert result is not None
