# Assessment C: Error Handling

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

### Positive

1. **Custom exception class:** `SpecValidationError` at `validator.py:11` extends `ValueError`, providing domain-specific error semantics.
2. **Precondition checks (DbC):** Functions validate inputs with clear error messages:
   - `generator.py:146`: `load_spec` checks for None/empty path.
   - `generator.py:456-457`: `generate_process_sheet` checks for empty `out_path`.
   - `control_loops.py:29`: `resolve_reference_point` checks for empty `ref_id`.
   - `stream_router.py:43`: `add_stream` checks for None stream.
   - `notes.py:21`: `get_mass_balance_values` checks for None spec.
   - `dxf_builder.py:264`: `add_box` checks for non-positive dimensions.
3. **Validation aggregation:** `validator.py:31-96` collects all errors into a list before raising, giving users a complete picture of problems rather than failing on the first one.
4. **Graceful degradation:** Stream rendering failures are caught and logged (`generator.py:575-576`) rather than aborting the entire generation.

### Issues Found

1. **Bare `except Exception` in SVG export:** `generator.py:435-436` catches all exceptions during SVG export with `except Exception as exc`. This swallows unexpected errors (e.g., disk full, permission denied) and only logs them.
2. **Silent fallback behavior:** `to_float` at `dxf_builder.py:22-27` silently returns a default on any conversion failure. While intentional, callers never know if their data was malformed.
3. **Missing precondition on `add_notes`:** The function checks `spec is None` at `notes.py:63` but does not validate that `layout_regions` contains expected keys (`panels`, `layout_cfg`), which would produce a confusing `KeyError` if malformed.
4. **No validation of stream structure:** `add_stream` at `stream_router.py:42-43` checks for None but not for non-dict types, so passing an integer would produce an opaque `AttributeError`.
5. **Inconsistent error types:** `resolve_endpoint` raises `KeyError` at `dxf_builder.py:503` for unknown equipment, while most other functions raise `ValueError`. This inconsistency complicates caller error handling.

## Recommendations

1. Narrow the SVG export `except` clause to specific recoverable exceptions (e.g., `ImportError`, `ezdxf.DXFError`).
2. Add a `warnings` or error-collection mechanism for non-fatal data quality issues (e.g., invalid float values falling back to defaults).
3. Add type guards at module boundaries (e.g., `if not isinstance(stream, dict): raise TypeError(...)`).
4. Standardize on `ValueError` for all input validation errors across modules.
