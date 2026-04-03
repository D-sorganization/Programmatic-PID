# Assessment D: Testing

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

### Test Suite Summary

- **62 tests, all passing** (2.53s runtime)
- Three test files: `test_pid_generation.py` (131 lines, 8 tests), `test_pid_integration.py` (20 lines, 1 test), `test_refactored_modules.py` (389 lines, 53 tests)
- CI runs tests on Python 3.11 and 3.12 with coverage reporting

### Positive

1. **Good coverage of the refactored modules:** `test_refactored_modules.py` systematically tests validator, dxf_builder, stream_router, control_loops, notes, and generator helpers with 53 focused tests.
2. **DbC precondition tests:** Every `raise ValueError` / `raise SpecValidationError` precondition has a corresponding test (e.g., `test_rejects_none`, `test_resolve_reference_point_empty_raises`, `test_add_stream_none_raises`).
3. **Integration test:** `test_pid_integration.py:11-19` tests the full two-sheet generation pipeline from YAML spec to DXF+SVG output.
4. **Test markers defined:** `pyproject.toml:26-29` defines `slow`, `integration`, and `benchmark` markers.
5. **Shared test helper:** `_minimal_spec()` provides a reusable valid spec fixture.

### Issues Found

1. **No TDD evidence in commit history.** Tests were added in a single batch commit (11023b3) alongside the refactor, not before the implementation changes.
2. **No coverage for SVG export path:** `export_svg_from_dxf` at `generator.py:402-436` has no dedicated test. The integration test indirectly exercises it but does not verify SVG content.
3. **No coverage for `add_title_block`:** `generator.py:358-394` is only tested indirectly via integration.
4. **No coverage for controls sheet rendering details:** `generate_controls_sheet` logic at `generator.py:613-781` (table layout, interlock summary, instrument index) has no unit tests.
5. **No edge-case tests for `get_mass_balance_values`:** The `mass_balance.basis` path (`notes.py:25-31`) is never tested; only the `assumptions` fallback path is exercised.
6. **No parametrized tests:** Equipment symbol renderers (`add_hopper`, `add_fan_symbol`, `add_rotary_valve_symbol`, `add_burner_symbol`, `add_bin_symbol`) each lack dedicated tests.
7. **`_minimal_spec()` is duplicated** identically in both `test_pid_generation.py:13-29` and `test_refactored_modules.py:47-64`.
8. **No negative test for `apply_profile` with valid profiles** verifying that specific layout values are correctly applied.

## Recommendations

1. Add unit tests for `export_svg_from_dxf`, `add_title_block`, and `generate_controls_sheet` internals.
2. Add parametrized tests for all equipment symbol renderers.
3. Extract `_minimal_spec()` to a shared `conftest.py` fixture to eliminate duplication.
4. Add edge-case tests for the `mass_balance.basis` path in `get_mass_balance_values`.
5. Add property-based tests for numeric helpers (`to_float`, `clamp`, `equipment_dims`).
6. Target explicit coverage metrics in CI (e.g., `--cov-fail-under=80`).
