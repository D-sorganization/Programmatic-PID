"""Tests for generator orchestration and sheet layout helpers.

Split from test_refactored_modules.py to keep test files focused and under
the 500-line size budget (see issue #61).
"""

from __future__ import annotations

import ezdxf
import pytest
from ezdxf.enums import TextEntityAlignment

import programmatic_pid.generator as gen
from programmatic_pid.control_loops import add_control_loops
from programmatic_pid.dxf_builder import LabelPlacer, to_float
from programmatic_pid.dxf_builder import (
    TextEntityAlignment as DxfTextEntityAlignment,
)
from programmatic_pid.notes import add_notes
from programmatic_pid.sheet_layout import (
    draw_controls_header,
    prepare_controls_sheet_context,
    resolve_sheet_layers,
)
from programmatic_pid.stream_router import add_stream
from programmatic_pid.validator import SpecValidationError, validate_spec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_spec() -> dict:
    return {
        "project": {"id": "P-1", "title": "Test PID", "drawing": {"text_height": 2.0}},
        "equipment": [
            {"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10},
            {"id": "E-2", "x": 20, "y": 0, "width": 10, "height": 10},
        ],
        "instruments": [{"id": "PT-1", "tag": "PT-1", "x": 2, "y": 2}],
        "streams": [{"id": "S-1", "from": {"equipment": "E-1"}, "to": {"equipment": "E-2"}}],
        "control_loops": [
            {
                "id": "PIC-1",
                "measurement": "PT-1",
                "final_element": "E-2",
                "line_layer": "control_lines",
            }
        ],
    }


# --- generator.py (orchestration + config helpers) ---


class TestGeneratorHelpers:
    def test_apply_profile_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown profile"):
            gen.apply_profile(_minimal_spec(), "nonexistent")

    def test_apply_profile_none_returns_copy(self):
        spec = _minimal_spec()
        result = gen.apply_profile(spec, None)
        assert result == spec
        assert result is not spec

    def test_get_text_config(self):
        cfg = gen.get_text_config(_minimal_spec())
        assert "title_height" in cfg
        assert cfg["body_height"] > 0

    def test_compute_layout_regions_keys(self):
        regions = gen.compute_layout_regions(_minimal_spec())
        assert "layout_cfg" in regions
        assert "equipment_bbox" in regions
        assert "canvas_bbox" in regions
        assert "panels" in regions

    def test_derive_related_path(self):
        p = gen.derive_related_path("out/process.dxf", "controls")
        assert str(p).endswith("process_controls.dxf")

    def test_derive_related_path_empty_suffix_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            gen.derive_related_path("foo.dxf", "")

    def test_load_spec_empty_path_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            gen.load_spec("")

    def test_generate_process_sheet_empty_out_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            gen.generate_process_sheet("spec.yml", "")

    def test_sheet_rendering_module_exists_while_generator_keeps_back_compat(self):
        from programmatic_pid import sheet_rendering

        assert callable(sheet_rendering.render_process_sheet)
        assert callable(sheet_rendering.render_controls_sheet)
        assert callable(gen.add_title_block)
        assert callable(gen.export_svg_from_dxf)

    def test_backward_compat_imports(self):
        """All symbols previously in generator.py are still importable."""
        assert gen.SpecValidationError is SpecValidationError
        assert gen.validate_spec is validate_spec
        assert gen.add_stream is add_stream
        assert gen.add_control_loops is add_control_loops
        assert gen.add_notes is add_notes
        assert gen.LabelPlacer is LabelPlacer
        assert gen.to_float is to_float
        assert gen.TextEntityAlignment is TextEntityAlignment
        assert gen.TextEntityAlignment is DxfTextEntityAlignment


class TestSheetLayout:
    def test_resolve_sheet_layers_defaults(self):
        doc = ezdxf.new(setup=True)
        layers = resolve_sheet_layers(doc)
        assert layers["text"] == "TEXT"
        assert layers["instrument"] == "INSTRUMENTS"
        assert layers["control"] == "control_lines"

    def test_prepare_controls_sheet_context_builds_expected_canvas(self):
        spec = _minimal_spec()
        ctx = prepare_controls_sheet_context(
            spec,
            text_cfg=gen.get_text_config(spec),
            layout_cfg=gen.get_layout_config(spec),
            modelspace_extent=gen.get_modelspace_extent(spec),
        )
        assert ctx["width"] >= 200.0
        assert ctx["height"] >= 130.0
        assert "control_lines" in ctx["doc"].layers

    def test_draw_controls_header_returns_table_geometry(self):
        spec = _minimal_spec()
        ctx = prepare_controls_sheet_context(
            spec,
            text_cfg=gen.get_text_config(spec),
            layout_cfg=gen.get_layout_config(spec),
            modelspace_extent=gen.get_modelspace_extent(spec),
        )
        table = draw_controls_header(
            ctx["msp"],
            spec_name="example.yml",
            text_cfg=ctx["text_cfg"],
            text_layer=ctx["layers"]["text"],
            notes_layer=ctx["layers"]["notes"],
            x_min=ctx["x_min"],
            y_min=ctx["y_min"],
            y_max=ctx["y_max"],
            width=ctx["width"],
            height=ctx["height"],
            margin=8.0,
        )
        assert table["table_w"] > 0
        assert table["col_measure"] < table["col_ctrl"] < table["col_final"]
