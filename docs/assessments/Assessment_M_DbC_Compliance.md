# Assessment M: Design by Contract (DbC) Compliance

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

### Positive

1. **Preconditions documented and enforced:** Key public functions have explicit precondition checks with descriptive error messages:
   - `load_spec`: path must not be None/empty (`generator.py:145-146`)
   - `generate_process_sheet`: out_path must not be None/empty (`generator.py:456-457`)
   - `generate_controls_sheet`: out_path must not be None/empty (`generator.py:624-625`)
   - `apply_profile`: profile must be a recognized preset (`generator.py:242-244`)
   - `derive_related_path`: suffix must be non-empty string (`generator.py:791-792`)
   - `resolve_reference_point`: ref_id must be non-empty string (`control_loops.py:28-29`)
   - `add_stream`: stream must not be None (`stream_router.py:42-43`)
   - `add_control_loops`: spec must not be None (`control_loops.py:80-81`)
   - `add_notes`: spec must not be None (`notes.py:62-63`)
   - `get_mass_balance_values`: spec must not be None (`notes.py:20-21`)
   - `add_box`: dimensions must be positive (`dxf_builder.py:263-264`)
   - `validate_spec`: spec must not be None (`validator.py:29-30`)
2. **Postconditions implicit but verifiable:** `validate_spec` at `validator.py:22-96` acts as a comprehensive postcondition check on spec structure, verifying referential integrity between equipment, instruments, streams, and control loops.
3. **All preconditions have corresponding test coverage.**

### Issues Found

1. **No postcondition assertions.** No function verifies its return value before returning. For example, `compute_layout_regions` could assert that panel positions don't overlap.
2. **No class invariants.** `LabelPlacer` has no invariant checks (e.g., that `occupied` contains only valid rectangles where x1 < x2 and y1 < y2).
3. **Inconsistent precondition depth:** `add_equipment` at `dxf_builder.py:571-616` silently returns on zero-dimension equipment (`dxf_builder.py:583-584`) rather than raising, while `add_box` raises on the same condition. Contract inconsistency.
4. **Missing preconditions on several public functions:**
   - `add_text` at `dxf_builder.py:211`: no check that `text` is not None.
   - `equipment_anchor` at `dxf_builder.py:458`: no check that `eq` dict has required keys.
   - `get_text_config` at `generator.py:175`: no check that `spec` is not None.
   - `get_layout_config` at `generator.py:210`: no check that `spec` is not None.
5. **`to_float` intentionally violates DbC** by silently converting invalid inputs rather than rejecting them. This is a design choice for robustness but makes debugging harder.

## Recommendations

1. Add postcondition assertions to `compute_layout_regions` verifying panels don't overlap with each other or the equipment bbox.
2. Make `add_equipment` raise on zero-dimension equipment (like `add_box` does) instead of silently returning.
3. Add precondition checks to `get_text_config`, `get_layout_config`, and `add_text` for None inputs.
4. Consider adding a `strict` mode to `to_float` that raises on invalid input instead of falling back to defaults.
