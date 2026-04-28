"""Benchmark suite for core DXF builder operations.

Uses pytest-benchmark for repeatable performance measurements.
Run with: pytest tests/benchmarks/ -v --benchmark-only
"""

import ezdxf
import pytest

from programmatic_pid.dxf_builder import add_equipment
from programmatic_pid.dxf_geometry import equipment_center, equipment_dims
from programmatic_pid.dxf_layer import ensure_layer
from programmatic_pid.dxf_symbols import add_box, draw_equipment_symbol
from programmatic_pid.sheet_rendering import generate_process_sheet


@pytest.fixture
def doc():
    return ezdxf.new()


@pytest.mark.benchmark
def test_benchmark_document_init(benchmark):
    """Benchmark DXF document creation."""
    benchmark(ezdxf.new)


@pytest.mark.benchmark
def test_benchmark_add_box(benchmark, doc):
    """Benchmark adding a box symbol."""
    benchmark(add_box, doc.modelspace(), 0, 0, 10, 10, "0")


@pytest.mark.benchmark
def test_benchmark_equipment_dims(benchmark):
    """Benchmark equipment dimension calculation."""
    eq = {"width": 5.0, "height": 3.0}
    benchmark(equipment_dims, eq)


@pytest.mark.benchmark
def test_benchmark_equipment_center(benchmark):
    """Benchmark equipment center calculation."""
    eq = {"x": 10.0, "y": 20.0, "width": 5.0, "height": 3.0}
    benchmark(equipment_center, eq)


@pytest.mark.benchmark
def test_benchmark_ensure_layer(benchmark, doc):
    """Benchmark layer creation."""
    benchmark(ensure_layer, doc, "PIPING", 7, "CONTINUOUS")


@pytest.mark.benchmark
def test_benchmark_add_equipment(benchmark, doc):
    """Benchmark adding equipment to the drawing."""

    def add_one():
        eq = {
            "id": "E-101",
            "x": 10.0,
            "y": 20.0,
            "width": 5.0,
            "height": 3.0,
            "type": "vessel",
        }
        add_equipment(doc.modelspace(), eq, 2.0, "TEXT", "NOTES")

    benchmark(add_one)


@pytest.mark.benchmark
def test_benchmark_draw_equipment_symbol(benchmark, doc):
    """Benchmark drawing an equipment symbol."""

    def draw_one():
        eq = {
            "id": "E-101",
            "x": 10.0,
            "y": 20.0,
            "width": 5.0,
            "height": 3.0,
            "type": "vessel",
        }
        draw_equipment_symbol(doc.modelspace(), eq, "0")

    benchmark(draw_one)


@pytest.mark.benchmark
def test_benchmark_biochar_process_sheet_render(benchmark, tmp_path):
    """Benchmark a full process-sheet render from the biochar example spec."""
    spec_path = "examples/biochar/biochar_pid_spec.yml"
    out_path = tmp_path / "biochar_pid.dxf"

    def render_sheet():
        generate_process_sheet(spec_path, out_path, svg_path=None)

    benchmark(render_sheet)
