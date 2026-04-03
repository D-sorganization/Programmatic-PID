# Assessment I: Performance

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

### Positive

1. **Fast test suite:** 62 tests complete in 2.53 seconds, including full DXF generation.
2. **Minimal memory overhead:** `deepcopy` is used sparingly (only in `apply_profile` at `generator.py:246` and sheet generation functions).
3. **Efficient label collision:** `LabelPlacer.find_position` at `dxf_builder.py:132-153` uses a simple linear scan which is adequate for the expected number of labels (typically < 100).
4. **Lazy SVG import:** SVG export dependencies are imported inside `export_svg_from_dxf` at `generator.py:413-414`, avoiding import overhead when SVG is not needed.

### Issues Found

1. **O(n^2) instrument spreading:** `spread_instrument_positions` at `dxf_builder.py:526-563` checks each new instrument against all previously placed instruments, with a nested loop over 9 ring positions and 4 radius values. For n instruments, worst case is O(n * 36 * n) = O(36n^2). With the biochar spec's 19 instruments this is negligible, but would not scale to hundreds.
2. **O(n^2) label collision:** `LabelPlacer.find_position` at `dxf_builder.py:145` checks candidates against all occupied rectangles. Combined with the preferred-position list, this is O(preferences * occupied).
3. **Redundant spec validation:** `prepare_spec` at `generator.py:272-278` calls `validate_spec` twice -- once before and once after profile application. The second call is defensive but may be unnecessary overhead for large specs.
4. **No benchmark tests.** The `benchmark` marker is defined in `pyproject.toml:29` but no benchmark tests exist.
5. **Full `deepcopy` of spec** at `generator.py:462` even when `prepared_spec` is provided, copying potentially large YAML structures unnecessarily.

## Recommendations

1. For large diagrams, consider a spatial index (e.g., grid-based) for `LabelPlacer` and `spread_instrument_positions` to reduce collision checks from O(n) to O(1) amortized.
2. Add benchmark tests for the full generation pipeline to catch performance regressions.
3. Consider making the second `validate_spec` call optional or only in debug mode.
4. Document the expected scale limits (e.g., "designed for diagrams with < 200 equipment items").
