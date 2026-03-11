"""Contract tests for types module."""
from __future__ import annotations

from programmatic_pid.types import BBox, Point, SpecValidationError, ValidationIssue


def test_bbox_width_and_height():
    bb = BBox(10.0, 20.0, 30.0, 50.0)
    assert bb.width == 20.0
    assert bb.height == 30.0


def test_bbox_center():
    bb = BBox(0.0, 0.0, 10.0, 10.0)
    c = bb.center
    assert c == Point(5.0, 5.0)


def test_bbox_contains_point():
    bb = BBox(0.0, 0.0, 10.0, 10.0)
    assert bb.contains_point(Point(5.0, 5.0))
    assert not bb.contains_point(Point(15.0, 5.0))


def test_bbox_overlaps():
    a = BBox(0.0, 0.0, 10.0, 10.0)
    b = BBox(5.0, 5.0, 15.0, 15.0)
    c = BBox(20.0, 20.0, 30.0, 30.0)
    assert a.overlaps(b)
    assert not a.overlaps(c)


def test_bbox_overlaps_with_padding():
    a = BBox(0.0, 0.0, 10.0, 10.0)
    b = BBox(11.0, 0.0, 20.0, 10.0)
    assert not a.overlaps(b, pad=0.0)
    assert a.overlaps(b, pad=2.0)


def test_bbox_union():
    a = BBox(0.0, 0.0, 5.0, 5.0)
    b = BBox(3.0, 3.0, 10.0, 10.0)
    u = a.union(b)
    assert u == BBox(0.0, 0.0, 10.0, 10.0)


def test_bbox_expanded():
    bb = BBox(5.0, 5.0, 10.0, 10.0)
    e = bb.expanded(2.0)
    assert e == BBox(3.0, 3.0, 12.0, 12.0)


def test_validation_issue_to_dict():
    issue = ValidationIssue("equipment[0].id", "duplicate id: E-1")
    d = issue.to_dict()
    assert d["path"] == "equipment[0].id"
    assert d["severity"] == "error"


def test_spec_validation_error_is_value_error():
    assert issubclass(SpecValidationError, ValueError)
