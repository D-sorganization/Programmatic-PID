# Assessment O: Maintainability

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

### Positive

1. **Recent refactoring shows active maintenance.** Commit 11023b3 broke a monolith into focused modules, added tests, type hints, logging, and DbC -- demonstrating commitment to quality.
2. **Consistent code style.** Black formatter (line-length 110) and Ruff linter enforced via pre-commit hooks and CI.
3. **Good module decomposition.** Each sub-module (validator, dxf_builder, stream_router, control_loops, notes) handles a distinct concern.
4. **Backward compatibility maintained.** The `generator.py` re-exports at lines 22-68 ensure existing code continues to work after the refactor.
5. **Logging infrastructure.** Every module creates a `logger = logging.getLogger(__name__)` and uses it for warnings and info messages.
6. **CI placeholder check.** `ci-standard.yml:60-63` rejects TODO/FIXME comments, enforcing a policy of tracking work in issues rather than code comments.

### Issues Found

1. **Two monolith functions remain.** `generate_process_sheet` (162 lines, `generator.py:444-606`) and `generate_controls_sheet` (168 lines, `generator.py:613-781`) are difficult to understand, test, and modify in isolation.
2. **High coupling to dict structure.** All modules depend on the raw dict shape of the YAML spec. A change to a key name (e.g., renaming `final_element` to `actuator`) would require changes across validator.py, control_loops.py, generator.py, and all tests.
3. **Magic numbers scattered throughout:**
   - `generator.py:296-299`: `60.0`, `50.0`, `0.75`, `4.0`, `1.35`, `10.0`
   - `generator.py:306-308`: `0.58`, `56.0`, `38.0`
   - `dxf_builder.py:279`: `0.72` (hopper bottom width ratio)
   - `dxf_builder.py:289`: `0.42` (fan radius ratio)
   - `dxf_builder.py:299`: `0.35` (rotary valve radius ratio)
4. **No changelog or version history** beyond git commits.
5. **Schema drift:** `pid_spec.schema.json` does not fully describe the actual YAML structure used by the code (missing sections for mass_balance, assumptions, pressure_control, interlocks, annotations).
6. **Circular import workarounds** in `validator.py:17` and `dxf_builder.py:177` are fragile and make the dependency graph harder to reason about.

## Recommendations

1. Break `generate_process_sheet` and `generate_controls_sheet` into smaller functions (< 50 lines each).
2. Extract magic numbers into named constants with comments explaining their engineering rationale.
3. Introduce dataclasses for the spec structure to centralize the data model and reduce coupling to raw dict keys.
4. Resolve circular imports by extracting shared utilities to a `utils.py` module.
5. Update `pid_spec.schema.json` to be the single source of truth for the YAML spec structure.
6. Add a CHANGELOG.md to track breaking changes and improvements.
