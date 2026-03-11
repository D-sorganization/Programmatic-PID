"""Contract tests for profiles module."""
from __future__ import annotations

import pytest

from programmatic_pid.profiles import PROFILE_PRESETS, apply_profile


def _spec():
    return {
        "project": {"id": "P-1", "title": "Test", "drawing": {"text_height": 2.0}},
        "equipment": [{"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10}],
    }


def test_all_profiles_present():
    assert set(PROFILE_PRESETS.keys()) == {"review", "presentation", "compact"}


def test_apply_profile_none_returns_deep_copy():
    spec = _spec()
    result = apply_profile(spec, None)
    assert result == spec
    assert result is not spec  # must be a copy


def test_apply_profile_compact_reduces_panel_size():
    from programmatic_pid.spec_loader import get_layout_config

    spec = _spec()
    compact = apply_profile(spec, "compact")
    lc = get_layout_config(compact)
    default_lc = get_layout_config(spec)
    assert lc["bottom_panel_height"] < default_lc["bottom_panel_height"]


def test_apply_profile_sets_meta():
    result = apply_profile(_spec(), "review")
    assert result["meta"]["profile"] == "review"


def test_apply_profile_invalid_raises():
    with pytest.raises(ValueError, match="Unknown profile"):
        apply_profile(_spec(), "nonexistent")
