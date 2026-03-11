"""Tests for programmatic_pid.cli — orchestration and CLI entry points."""
from __future__ import annotations

from pathlib import Path

import pytest

from programmatic_pid.cli import derive_related_path, generate


class TestDeriveRelatedPath:
    def test_adds_suffix(self):
        result = derive_related_path("output.dxf", "controls")
        assert result == Path("output_controls.dxf")

    def test_preserves_directory(self):
        result = derive_related_path("/tmp/drawings/out.dxf", "controls")
        assert result == Path("/tmp/drawings/out_controls.dxf")


class TestGenerate:
    """Integration-level test that generate() produces output files."""

    def test_generate_single_sheet(self, tmp_path):
        """Generate a single sheet from the biochar spec."""
        spec_path = Path(__file__).parent.parent / "examples" / "biochar" / "biochar_pid_spec.yml"
        if not spec_path.exists():
            pytest.skip("biochar spec not found")
        out_dxf = tmp_path / "test_process.dxf"
        generate(str(spec_path), str(out_dxf), sheet_set="single")
        assert out_dxf.exists()
        assert out_dxf.stat().st_size > 0

    def test_generate_two_sheets(self, tmp_path):
        """Generate both process and controls sheets."""
        spec_path = Path(__file__).parent.parent / "examples" / "biochar" / "biochar_pid_spec.yml"
        if not spec_path.exists():
            pytest.skip("biochar spec not found")
        out_dxf = tmp_path / "test_process.dxf"
        controls_dxf = tmp_path / "test_process_controls.dxf"
        generate(str(spec_path), str(out_dxf), sheet_set="two")
        assert out_dxf.exists()
        assert controls_dxf.exists()


class TestBackwardCompatibility:
    """Verify imports from generator.py still work."""

    def test_generator_imports(self):
        from programmatic_pid.generator import (
            add_arrow,
            add_box,
            add_control_loops,
            add_equipment,
            add_instrument,
            add_stream,
            add_text,
            compute_layout_regions,
            ensure_layer,
            generate,
            generate_controls_sheet,
            generate_process_sheet,
            LabelPlacer,
            layer_name,
            validate_spec,
        )
        # All should be callable
        assert callable(generate)
        assert callable(validate_spec)
        assert callable(add_equipment)
