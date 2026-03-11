"""Spec loading, accessor utilities, and configuration extraction.

DRY: The SpecAccessor class replaces the scattered get_project / get_drawing /
get_text_config / get_layout_config / get_layer_config accessor functions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from programmatic_pid.geometry import to_float
from programmatic_pid.profiles import apply_profile
from programmatic_pid.types import SpecDict, TextConfig
from programmatic_pid.validation import validate_spec


def load_spec(path: str | Path) -> SpecDict:
    """Load a YAML specification file.

    Precondition: *path* points to a valid YAML file.
    Postcondition: returns a dict (possibly empty if YAML is blank).
    """
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def prepare_spec(spec_path: str | Path, profile: str | None) -> SpecDict:
    """Load, validate, and apply profile to a spec.

    Postcondition: returned spec has passed validation twice (pre- and post-profile).
    """
    raw = load_spec(spec_path)
    validate_spec(raw)
    prepared = apply_profile(raw, profile)
    validate_spec(prepared)
    return prepared


class SpecAccessor:
    """Unified read-only access to spec configuration with defaults.

    DRY replacement for get_project, get_drawing, get_text_config,
    get_layout_config, get_layer_config.
    """

    def __init__(self, spec: SpecDict) -> None:
        self._spec = spec

    @property
    def spec(self) -> SpecDict:
        return self._spec

    @property
    def project(self) -> dict[str, Any]:
        return self._spec.get("project", {})

    @property
    def drawing(self) -> dict[str, Any]:
        if "drawing" in self._spec and isinstance(self._spec["drawing"], dict):
            return self._spec["drawing"]
        return self.project.get("drawing", {})

    @property
    def text_config(self) -> TextConfig:
        drawing = self.drawing
        raw = drawing.get("text")
        if isinstance(raw, dict):
            return TextConfig(
                title_height=to_float(raw.get("title_height"), 3.2),
                subtitle_height=to_float(raw.get("subtitle_height"), 2.0),
                body_height=to_float(raw.get("body_height"), 1.6),
                small_height=to_float(raw.get("small_height"), 1.2),
            )
        base = to_float(drawing.get("text_height"), 2.5)
        if base <= 0:
            base = 2.5
        return TextConfig(
            title_height=base * 1.6,
            subtitle_height=base * 1.1,
            body_height=base,
            small_height=max(base * 0.75, 0.8),
        )

    @property
    def layer_config(self) -> dict[str, Any]:
        drawing = self.drawing
        layers = drawing.get("layers")
        if isinstance(layers, dict) and layers:
            return layers
        layers = self._spec.get("layers")
        if isinstance(layers, dict):
            return layers
        return {}

    @property
    def layout_config(self) -> dict[str, Any]:
        drawing = self.drawing
        layout = drawing.get("layout", {})
        if not isinstance(layout, dict):
            layout = {}
        return {
            "style": str(layout.get("style", "clean")).lower(),
            "show_inline_equipment_notes": bool(layout.get("show_inline_equipment_notes", False)),
            "show_instrument_suffix": bool(layout.get("show_instrument_suffix", False)),
            "show_control_tags_on_lines": bool(layout.get("show_control_tags_on_lines", False)),
            "gap": max(to_float(layout.get("gap"), 8.0), 2.0),
            "right_panel_width": max(to_float(layout.get("right_panel_width"), 84.0), 45.0),
            "bottom_panel_height": max(to_float(layout.get("bottom_panel_height"), 34.0), 18.0),
            "title_block_height": max(to_float(layout.get("title_block_height"), 11.0), 6.0),
            "panel_text_chars": max(int(layout.get("panel_text_chars", 42)), 24),
            "stream_label_scale": min(
                max(to_float(layout.get("stream_label_scale"), 0.76), 0.45), 1.5
            ),
            "stream_label_leaders": bool(layout.get("stream_label_leaders", True)),
            "instrument_spacing_factor": max(
                to_float(layout.get("instrument_spacing_factor"), 2.2), 1.2
            ),
            "controls_row_height_scale": max(
                to_float(layout.get("controls_row_height_scale"), 3.4), 2.0
            ),
        }

    @property
    def defaults(self) -> dict[str, Any]:
        d = self._spec.get("defaults", {})
        return d if isinstance(d, dict) else {}

    @property
    def equipment(self) -> list[dict[str, Any]]:
        return self._spec.get("equipment", [])

    @property
    def instruments(self) -> list[dict[str, Any]]:
        return self._spec.get("instruments", [])

    @property
    def streams(self) -> list[dict[str, Any]]:
        return self._spec.get("streams", [])

    @property
    def control_loops(self) -> list[dict[str, Any]]:
        return self._spec.get("control_loops", [])

    @property
    def interlocks(self) -> list[dict[str, Any]]:
        return self._spec.get("interlocks", [])


# ---------------------------------------------------------------------------
# Backward-compatible free functions that delegate to the old interface.
# These are kept so that generator.py continues to work during migration.
# ---------------------------------------------------------------------------

def get_project(spec: SpecDict) -> dict[str, Any]:
    return spec.get("project", {})


def get_drawing(spec: SpecDict) -> dict[str, Any]:
    if "drawing" in spec and isinstance(spec["drawing"], dict):
        return spec["drawing"]
    return get_project(spec).get("drawing", {})


def ensure_drawing(spec: SpecDict) -> dict[str, Any]:
    if "drawing" in spec and isinstance(spec["drawing"], dict):
        return spec["drawing"]
    project = spec.setdefault("project", {})
    drawing = project.get("drawing")
    if not isinstance(drawing, dict):
        drawing = {}
        project["drawing"] = drawing
    return drawing


def get_text_config(spec: SpecDict) -> dict[str, float]:
    tc = SpecAccessor(spec).text_config
    return {
        "title_height": tc.title_height,
        "subtitle_height": tc.subtitle_height,
        "body_height": tc.body_height,
        "small_height": tc.small_height,
    }


def get_layout_config(spec: SpecDict) -> dict[str, Any]:
    return SpecAccessor(spec).layout_config


def get_layer_config(spec: SpecDict) -> dict[str, Any]:
    return SpecAccessor(spec).layer_config
