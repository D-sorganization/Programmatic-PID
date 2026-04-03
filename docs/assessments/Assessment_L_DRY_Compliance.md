# Assessment L: DRY Compliance

**Date:** 2026-04-03
**Grade: 6/10**

## Findings

### Positive

1. **Shared utilities:** `to_float`, `clamp`, `equipment_dims`, `equipment_center` are defined once in `dxf_builder.py` and imported by all modules.
2. **`add_text_panel`** at `dxf_builder.py:226-258` encapsulates the repeated pattern of bordered panel with title and wrapped text lines.
3. **`add_text`** at `dxf_builder.py:211-223` is a single function used for all text placement.
4. **Profile preset application** at `generator.py:233-269` avoids duplicating layout overrides for each profile.

### Issues Found

1. **`_minimal_spec()` duplicated verbatim** in `test_pid_generation.py:13-29` and `test_refactored_modules.py:47-64`. Identical 17-line function in two files.
2. **`_equipment_dims` duplicated** in `validator.py:15-19` -- reimplements `equipment_dims` from `dxf_builder.py:432-434` to avoid a circular import. Same logic, different module.
3. **Layer setup repeated:** Both `generate_process_sheet` (`generator.py:474-478`) and `generate_controls_sheet` (`generator.py:644-649`) repeat the same `layer_index` + `layer_name` pattern for TEXT, NOTES, and other layers.
4. **Sheet generation boilerplate:** Both `generate_process_sheet` and `generate_controls_sheet` share identical patterns for:
   - Spec preparation (`generator.py:459-462` vs `generator.py:628-631`)
   - Doc creation and layer setup (`generator.py:464-466` vs `generator.py:632-634`)
   - File saving and SVG export (`generator.py:603-610` vs `generator.py:775-781`)
5. **Equipment rendering zone-drawing duplicated:** `draw_equipment_symbol` at `dxf_builder.py:353-356` draws zones, and `add_equipment` at `dxf_builder.py:600-603` draws zone labels. Both iterate `eq.get("zones", [])` independently with similar y-fraction logic.
6. **Config accessor pattern repeated:** `get_drawing`, `get_text_config`, `get_layer_config`, `get_layout_config` all follow a similar "get from drawing, fall back" pattern but each reimplements it.

## Recommendations

1. Extract `_minimal_spec()` to `tests/conftest.py` as a pytest fixture.
2. Resolve the `_equipment_dims` duplication by extracting `to_float` and `equipment_dims` to a `utils.py` module that both `validator.py` and `dxf_builder.py` can import without circular dependency.
3. Extract shared sheet-generation boilerplate into helper functions (e.g., `_create_doc(spec)`, `_save_and_export(doc, spec, out_path, svg_path)`).
4. Extract the layer-index-and-resolve pattern into a reusable `LayerResolver` or helper function.
