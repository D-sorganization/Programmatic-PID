# Assessment E: Documentation

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

### Positive

1. **Module-level docstrings:** Every source module has a descriptive docstring (`generator.py:2`, `validator.py:1`, `dxf_builder.py:1`, `stream_router.py:1`, `control_loops.py:1`, `notes.py:1`).
2. **Function docstrings:** All public functions have docstrings describing their purpose.
3. **Raises documentation:** Many docstrings document `Raises:` clauses (e.g., `generator.py:143-144`, `generator.py:237-238`, `stream_router.py:40-41`).
4. **JSON schema:** `schema/pid_spec.schema.json` (359 lines) provides a formal specification of the YAML input format with required fields and type constraints.
5. **Design review documents:** Three design review docs in `docs/design_reviews/` provide domain context.
6. **Example spec:** `examples/biochar/biochar_pid_spec.yml` (609 lines) is a comprehensive real-world example.

### Issues Found

1. **No inline comments explaining domain logic.** Complex calculations in `compute_layout_regions` (`generator.py:286-326`) and `get_mass_balance_values` (`notes.py:44-47`) lack comments explaining the engineering rationale (e.g., why `process_w * 0.58` for control panel width).
2. **No docstring for `PROFILE_PRESETS`** at `generator.py:76`. The magic numbers in presets (e.g., `gap: 9.0`, `instrument_spacing_factor: 2.6`) are unexplained.
3. **Schema does not match actual code.** The JSON schema at `schema/pid_spec.schema.json` requires `project.title` but the validator at `validator.py:38` accepts either `title` or `document_title`. The schema also lacks definitions for `mass_balance`, `assumptions`, `pressure_control`, `interlocks`, and `annotations` -- all of which are used by the code.
4. **No API documentation or usage guide.** README.md exists but was not reviewed for completeness.
5. **`py.typed` marker present** (`src/programmatic_pid/py.typed`) but mypy is skipped in CI (`ci-standard.yml:52`), making the type-safety promise hollow.

## Recommendations

1. Add inline comments to complex layout calculations explaining engineering rationale and magic numbers.
2. Document `PROFILE_PRESETS` with comments explaining when each profile is appropriate.
3. Update `pid_spec.schema.json` to match actual validator logic (accept `document_title`, add `mass_balance`, `assumptions`, `pressure_control`, `interlocks`, `annotations` sections).
4. Enable mypy in CI rather than skipping it.
5. Add a developer guide or architecture doc explaining the module relationships and data flow.
