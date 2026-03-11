"""Contract tests for spec_loader module — SpecAccessor and config access."""
from __future__ import annotations

from programmatic_pid.spec_loader import SpecAccessor, get_layout_config, get_text_config


def _spec():
    return {
        "project": {
            "id": "P-1",
            "title": "Test",
            "drawing": {
                "text_height": 2.0,
                "layout": {
                    "gap": 10.0,
                    "stream_label_scale": 0.8,
                },
                "layers": {"EQUIPMENT": {"color": 7}},
            },
        },
        "equipment": [
            {"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10},
        ],
        "instruments": [{"id": "PT-1", "tag": "PT-1"}],
        "streams": [{"id": "S-1"}],
        "control_loops": [{"id": "PIC-1"}],
        "interlocks": [{"id": "INT-1"}],
    }


def test_accessor_project():
    acc = SpecAccessor(_spec())
    assert acc.project["id"] == "P-1"


def test_accessor_drawing():
    acc = SpecAccessor(_spec())
    assert "text_height" in acc.drawing


def test_accessor_text_config():
    acc = SpecAccessor(_spec())
    tc = acc.text_config
    assert tc.body_height == 2.0
    assert tc.title_height > tc.body_height


def test_accessor_layout_config():
    acc = SpecAccessor(_spec())
    lc = acc.layout_config
    assert lc["gap"] == 10.0
    assert lc["stream_label_scale"] == 0.8


def test_accessor_layer_config():
    acc = SpecAccessor(_spec())
    assert "EQUIPMENT" in acc.layer_config


def test_accessor_lists():
    acc = SpecAccessor(_spec())
    assert len(acc.equipment) == 1
    assert len(acc.instruments) == 1
    assert len(acc.streams) == 1
    assert len(acc.control_loops) == 1
    assert len(acc.interlocks) == 1


def test_backward_compat_get_text_config():
    """Ensure free function still works."""
    t = get_text_config(_spec())
    assert "body_height" in t
    assert t["body_height"] == 2.0


def test_backward_compat_get_layout_config():
    lc = get_layout_config(_spec())
    assert "gap" in lc
    assert lc["gap"] == 10.0
