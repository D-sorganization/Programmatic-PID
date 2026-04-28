"""Benchmark suite for core DXF builder operations.

Uses pytest-benchmark for repeatable performance measurements.
Run with: pytest tests/benchmarks/ -v --benchmark-only
"""

import pytest

from programmatic_pid.dxf_builder import DXFBuilder, add_equipment, add_instrument
from programmatic_pid.dxf_geometry import equipment_dims, equipment_center
from programmatic_pid.dxf_layer import ensure_layer, ensure_layers
from programmatic_pid.dxf_symbols import add_box, draw_equipment_symbol


@pytest.fixture
def builder():
    return DXFBuilder()


@pytest.mark.benchmark
def test_benchmark_builder_init(benchmark):
    """Benchmark DXFBuilder instantiation."""
    benchmark(DXFBuilder)


@pytest.mark.benchmark
def test_benchmark_add_box(benchmark, builder):
    """Benchmark adding a box symbol."""
    benchmark(add_box, builder.doc.modelspace(), 0, 0, 10, 10, "0")


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
def test_benchmark_ensure_layer(benchmark, builder):
    """Benchmark layer creation."""
    benchmark(ensure_layer, builder.doc, "PIPING", 7, "CONTINUOUS")


@pytest.mark.benchmark
def test_benchmark_add_equipment(benchmark, builder):
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
        add_equipment(builder.doc.modelspace(), eq, "0")

    benchmark(add_one)


@pytest.mark.benchmark
def test_benchmark_draw_equipment_symbol(benchmark, builder):
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
        draw_equipment_symbol(builder.doc.modelspace(), eq, "0")

    benchmark(draw_one)