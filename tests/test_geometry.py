"""Contract tests for geometry module."""
from __future__ import annotations

from programmatic_pid.geometry import (
    clamp,
    closest_point_on_rect,
    dedupe_points,
    distance,
    find_free_region,
    rects_overlap,
    text_box,
    to_float,
)
from programmatic_pid.types import BBox, Point


def test_to_float_normal():
    assert to_float(3.14) == 3.14
    assert to_float("2.5") == 2.5


def test_to_float_fallback():
    assert to_float(None, 1.0) == 1.0
    assert to_float("bad", 0.0) == 0.0


def test_clamp():
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-1.0, 0.0, 10.0) == 0.0
    assert clamp(15.0, 0.0, 10.0) == 10.0


def test_closest_point_on_rect():
    p = closest_point_on_rect((15.0, 5.0), (0.0, 0.0, 10.0, 10.0))
    assert p == Point(10.0, 5.0)


def test_rects_overlap_true():
    assert rects_overlap((0, 0, 10, 10), (5, 5, 15, 15))


def test_rects_overlap_false():
    assert not rects_overlap((0, 0, 10, 10), (20, 20, 30, 30))


def test_text_box_center_alignment():
    box = text_box("test", 5.0, 5.0, 1.0)
    x1, y1, x2, y2 = box
    assert x1 < 5.0 < x2
    assert y1 < 5.0 < y2


def test_text_box_left_alignment():
    box = text_box("test", 5.0, 5.0, 1.0, align="MIDDLE_LEFT")
    x1, y1, x2, y2 = box
    assert x1 == 5.0
    assert x2 > 5.0


def test_distance():
    assert abs(distance((0, 0), (3, 4)) - 5.0) < 1e-9


def test_dedupe_points_removes_consecutive_duplicates():
    pts = [(0, 0), (0, 0), (1, 1), (1, 1), (2, 2)]
    result = dedupe_points(pts)
    assert result == [(0, 0), (1, 1), (2, 2)]


def test_dedupe_points_preserves_non_consecutive():
    pts = [(0, 0), (1, 1), (0, 0)]
    result = dedupe_points(pts)
    assert len(result) == 3


def test_find_free_region_basic():
    occupied = [BBox(0, 0, 10, 10)]
    result = find_free_region(occupied, 5, 5, search_origin=Point(0, 0))
    assert result is not None
    assert not result.overlaps(occupied[0], pad=2.0)
