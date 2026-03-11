"""Contract tests for PIDDocument facade class."""
from __future__ import annotations

from pathlib import Path

from programmatic_pid.document import PIDDocument
from programmatic_pid.types import BBox, Point


def _spec():
    return {
        "project": {"id": "P-1", "title": "Test PID", "drawing": {"text_height": 2.0}},
        "equipment": [
            {"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10},
            {"id": "E-2", "x": 30, "y": 0, "width": 10, "height": 10},
        ],
        "instruments": [{"id": "PT-1", "tag": "PT-1", "x": 5, "y": 5}],
        "streams": [{"id": "S-1", "from": {"equipment": "E-1"}, "to": {"equipment": "E-2"}}],
        "control_loops": [
            {"id": "PIC-1", "measurement": "PT-1", "final_element": "E-2"}
        ],
    }


def test_construct_from_dict():
    doc = PIDDocument(_spec())
    assert doc.spec is not None


def test_construct_with_profile():
    doc = PIDDocument(_spec(), profile="compact")
    assert doc.spec.get("meta", {}).get("profile") == "compact"


def test_equipment_ids():
    doc = PIDDocument(_spec())
    assert "E-1" in doc.equipment_ids
    assert "E-2" in doc.equipment_ids


def test_instrument_ids():
    doc = PIDDocument(_spec())
    assert "PT-1" in doc.instrument_ids


def test_stream_ids():
    doc = PIDDocument(_spec())
    assert "S-1" in doc.stream_ids


def test_equipment_bbox():
    doc = PIDDocument(_spec())
    bb = doc.equipment_bbox("E-1")
    assert bb is not None
    assert bb == BBox(0.0, 0.0, 10.0, 10.0)


def test_equipment_bbox_not_found():
    doc = PIDDocument(_spec())
    assert doc.equipment_bbox("NONEXISTENT") is None


def test_equipment_position():
    doc = PIDDocument(_spec())
    pos = doc.equipment_position("E-1")
    assert pos is not None
    assert pos == Point(5.0, 5.0)


def test_process_bbox():
    doc = PIDDocument(_spec())
    bb = doc.process_bbox()
    assert bb.x_min == 0.0
    assert bb.x_max == 40.0  # E-2 at x=30 + width=10


def test_find_free_region():
    doc = PIDDocument(_spec())
    region = doc.find_free_region(5, 5)
    assert region is not None
    # Should not overlap any equipment
    for eq_id in doc.equipment_ids:
        eq_bb = doc.equipment_bbox(eq_id)
        assert not region.overlaps(eq_bb, pad=2.0)


def test_validate_json_clean():
    doc = PIDDocument(_spec())
    issues = doc.validate_json()
    assert issues == []


def test_from_partial_returns_none_on_fatal():
    bad = {"project": {}, "equipment": []}
    result = PIDDocument.from_partial(bad)
    assert result is None


def test_from_partial_returns_doc_on_valid():
    doc = PIDDocument.from_partial(_spec())
    assert doc is not None


def test_export_dxf(tmp_path):
    doc = PIDDocument(_spec())
    out = tmp_path / "test.dxf"
    doc.export_dxf(out, sheet_set="single")
    assert out.exists()
    assert out.stat().st_size > 0
