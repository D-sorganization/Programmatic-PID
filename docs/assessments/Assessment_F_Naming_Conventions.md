# Assessment F: Naming Conventions

**Date:** 2026-04-03
**Grade: 8/10**

## Findings

### Positive

1. **PEP 8 compliant:** All function names use `snake_case`, class names use `PascalCase` (`LabelPlacer`, `SpecValidationError`), constants use `UPPER_SNAKE_CASE` (`PROFILE_PRESETS`).
2. **Descriptive function names:** `resolve_reference_point`, `orthogonal_control_route`, `spread_instrument_positions`, `nearest_equipment_anchor` clearly convey intent.
3. **Consistent prefix convention:** DXF drawing functions use `add_` prefix (`add_box`, `add_text`, `add_arrow`, `add_equipment`, `add_instrument`, `add_stream`, `add_control_loops`, `add_notes`).
4. **Consistent getter naming:** Config accessors use `get_` prefix (`get_project`, `get_drawing`, `get_text_config`, `get_layer_config`, `get_layout_config`, `get_equipment_bounds`, `get_mass_balance_values`).
5. **Private function naming:** `_equipment_dims` in `validator.py:15` correctly uses leading underscore for internal helper.

### Issues Found

1. **Inconsistent dimension parameter names:** Equipment uses both `w`/`h` and `width`/`height` (handled by `equipment_dims` at `dxf_builder.py:433-434` which checks both). This dual naming is reflected in the schema (`pid_spec.schema.json:139-150`) and propagates confusion.
2. **Abbreviated parameter names:** `hh` at `dxf_builder.py:582` for equipment height, `t` at `generator.py:467` for text config, `r` at `dxf_builder.py:636` for radius -- these sacrifice readability.
3. **Inconsistent `spec` vs `spec_data`:** Tests use `spec_data` in some places (`test_pid_generation.py:44,99`) but the source code always uses `spec`.
4. **`msp` is never spelled out:** The modelspace parameter `msp` appears in every rendering function but is never documented as meaning "modelspace" except by DXF convention.
5. **Mixed `id` vs `tag`:** Equipment and instruments use both `id` and `tag` fields with different semantics, but the naming does not make the distinction clear.

## Recommendations

1. Standardize on `width`/`height` in the YAML spec and deprecate `w`/`h` shortcuts.
2. Replace abbreviated variable names (`hh`, `t`, `r`) with descriptive names (`eq_height`, `text_cfg`, `radius`).
3. Add a type alias or comment explaining `msp` (e.g., `# msp: ezdxf Modelspace entity`).
4. Document the `id` vs `tag` distinction in the schema and in code comments.
