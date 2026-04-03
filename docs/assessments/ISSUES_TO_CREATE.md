# Issues to Create

Generated from comprehensive code quality assessment on 2026-04-03.

---

## High Priority

### Issue 1: Enable mypy in CI pipeline
**Labels:** ci, type-safety
**Assessment refs:** G, K
**Description:** mypy is skipped in `ci-standard.yml:52` despite a strict config in `mypy.ini`. The `py.typed` marker exists but type checking is never enforced. Remove the skip and fix any mypy errors that surface.
**Files:** `.github/workflows/ci-standard.yml:52`, `mypy.ini`

### Issue 2: Break monolith sheet-generation functions into composable units
**Labels:** refactor, maintainability
**Assessment refs:** A, O
**Description:** `generate_process_sheet` (`generator.py:444-606`, 162 lines) and `generate_controls_sheet` (`generator.py:613-781`, 168 lines) each handle doc creation, layer setup, rendering, and I/O in a single function. Extract into smaller composable functions (e.g., `_create_dxf_doc`, `_render_equipment_layer`, `_save_and_export`).
**Files:** `src/programmatic_pid/generator.py`

### Issue 3: Introduce dataclasses for spec entities
**Labels:** enhancement, type-safety
**Assessment refs:** B, G, N
**Description:** All data flows through `dict[str, Any]`, requiring defensive `.get()` calls everywhere and providing no type safety. Create dataclasses (`Equipment`, `Instrument`, `Stream`, `ControlLoop`, `SpecConfig`) with typed fields. This will improve IDE support, catch errors at parse time, and simplify function signatures.
**Files:** All source files

### Issue 4: Update JSON schema to match actual YAML spec structure
**Labels:** documentation, bug
**Assessment refs:** E, O
**Description:** `pid_spec.schema.json` is missing definitions for `mass_balance`, `assumptions`, `pressure_control`, `interlocks`, and `annotations` sections that are actively consumed by the code. The schema also requires `project.title` but the validator accepts `document_title` as an alternative. Update the schema to be the authoritative spec definition.
**Files:** `schema/pid_spec.schema.json`, `src/programmatic_pid/validator.py`

### Issue 5: Extract shared utilities to resolve circular imports
**Labels:** refactor, DRY
**Assessment refs:** A, L, O
**Description:** `validator.py:17` reimplements `equipment_dims` inside a function to avoid importing from `dxf_builder.py`. `dxf_builder.py:177` imports `get_layer_config` from `generator.py` inside a function. Extract `to_float` and `equipment_dims` into a new `utils.py` module to eliminate circular dependency workarounds.
**Files:** `src/programmatic_pid/validator.py:15-19`, `src/programmatic_pid/dxf_builder.py:177`, new `src/programmatic_pid/utils.py`

---

## Medium Priority

### Issue 6: Add coverage threshold to CI
**Labels:** ci, testing
**Assessment refs:** D, K
**Description:** Tests run with `--cov` but there is no `--cov-fail-under` flag. Add a minimum coverage threshold (suggest 75%) to prevent regressions.
**Files:** `.github/workflows/ci-standard.yml`

### Issue 7: Extract test fixture to conftest.py
**Labels:** testing, DRY
**Assessment refs:** D, L
**Description:** `_minimal_spec()` is duplicated identically in `test_pid_generation.py:13-29` and `test_refactored_modules.py:47-64`. Extract to `tests/conftest.py` as a pytest fixture.
**Files:** `tests/test_pid_generation.py`, `tests/test_refactored_modules.py`, new `tests/conftest.py`

### Issue 8: Add unit tests for untested rendering functions
**Labels:** testing
**Assessment refs:** D
**Description:** The following functions lack dedicated unit tests: `export_svg_from_dxf`, `add_title_block`, `generate_controls_sheet` internals (table layout, interlock summary, instrument index), and all equipment symbol renderers (`add_hopper`, `add_fan_symbol`, `add_rotary_valve_symbol`, `add_burner_symbol`, `add_bin_symbol`).
**Files:** `tests/`

### Issue 9: Split dxf_builder.py into focused sub-modules
**Labels:** refactor
**Assessment refs:** A
**Description:** `dxf_builder.py` (650 lines) mixes six concerns: numeric helpers, text utilities, bounding-box helpers, label collision avoidance, layer management, and equipment/instrument rendering. Split into `geometry.py`, `primitives.py`, and `labels.py` (or similar decomposition).
**Files:** `src/programmatic_pid/dxf_builder.py`

### Issue 10: Create equipment renderer registry
**Labels:** enhancement, design-patterns
**Assessment refs:** B
**Description:** `draw_equipment_symbol` at `dxf_builder.py:327-357` uses a chain of if/return statements. Replace with a registry dict (`EQUIPMENT_RENDERERS: dict[str, Callable]`) to support Open-Closed Principle and simplify adding new equipment types.
**Files:** `src/programmatic_pid/dxf_builder.py:327-357`

### Issue 11: Replace `Any` type hints with specific ezdxf types
**Labels:** type-safety
**Assessment refs:** G
**Description:** `msp: Any` appears in every rendering function. Replace with `msp: ezdxf.layouts.BaseLayout` and `doc: Any` with `doc: ezdxf.document.Drawing`. This enables IDE autocompletion and catches incorrect API usage.
**Files:** All source files using `msp: Any` or `doc: Any`

---

## Low Priority

### Issue 12: Separate runtime and dev dependencies
**Labels:** dependencies
**Assessment refs:** H
**Description:** `requirements.txt` mixes runtime dependencies (ezdxf, PyYAML) with dev tools (pytest, ruff, mypy). Create `requirements-dev.txt` for testing/tooling dependencies.
**Files:** `requirements.txt`, new `requirements-dev.txt`

### Issue 13: Extract magic numbers into named constants
**Labels:** maintainability
**Assessment refs:** O
**Description:** Layout calculations in `compute_layout_regions` (`generator.py:296-308`) and equipment symbol renderers contain unexplained magic numbers (e.g., `0.58`, `56.0`, `0.72`, `0.42`). Extract into named constants with engineering rationale comments.
**Files:** `src/programmatic_pid/generator.py`, `src/programmatic_pid/dxf_builder.py`

### Issue 14: Add `__all__` exports to all modules
**Labels:** enhancement
**Assessment refs:** A
**Description:** No module defines `__all__`, making the public API implicit. Add `__all__` lists to `generator.py`, `dxf_builder.py`, `stream_router.py`, `control_loops.py`, `notes.py`, and `validator.py`.
**Files:** All source modules

### Issue 15: Standardize equipment dimension field names
**Labels:** enhancement, documentation
**Assessment refs:** F
**Description:** Equipment supports both `w`/`h` and `width`/`height` for dimensions. Standardize on `width`/`height` in documentation and schema, and deprecate `w`/`h` with a logged warning.
**Files:** `schema/pid_spec.schema.json`, `src/programmatic_pid/dxf_builder.py:432-434`

### Issue 16: Add postcondition assertions to layout computation
**Labels:** DbC
**Assessment refs:** M
**Description:** `compute_layout_regions` at `generator.py:286-326` computes panel positions but never verifies that panels don't overlap. Add postcondition assertions to catch layout bugs early.
**Files:** `src/programmatic_pid/generator.py:286-326`

### Issue 17: Narrow SVG export exception handling
**Labels:** error-handling
**Assessment refs:** C
**Description:** `export_svg_from_dxf` at `generator.py:435` catches bare `Exception`. Narrow to specific recoverable exceptions (`ImportError`, `ezdxf.DXFError`, `IOError`) so unexpected errors propagate.
**Files:** `src/programmatic_pid/generator.py:435-436`
