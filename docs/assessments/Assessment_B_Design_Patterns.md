# Assessment B: Design Patterns

**Date:** 2026-04-03
**Grade: 6/10**

## Findings

### Positive

1. **Strategy pattern (implicit):** `draw_equipment_symbol` at `dxf_builder.py:327-357` dispatches to type-specific renderers (hopper, fan, rotary_valve, burner, bin) based on `eq_type`. This is a valid dispatch mechanism.
2. **Facade pattern:** `generator.py` acts as a facade re-exporting all sub-module symbols, providing a single entry point.
3. **Builder-like pattern:** `LabelPlacer` class at `dxf_builder.py:118-153` accumulates state (occupied rectangles) and provides collision-free label placement.
4. **Profile/preset pattern:** `PROFILE_PRESETS` at `generator.py:76-131` and `apply_profile` at `generator.py:233-269` cleanly separate configuration presets from logic.

### Issues Found

1. **No formal Strategy or Registry pattern for equipment rendering.** The `draw_equipment_symbol` function uses a chain of `if/return` statements (`dxf_builder.py:335-351`). Adding a new equipment type requires modifying this function, violating Open-Closed Principle.
2. **No data classes or value objects.** Equipment, instruments, streams, and control loops are all passed as raw `dict[str, Any]`. This eliminates compile-time safety and requires defensive `.get()` calls throughout (over 100 instances across the codebase).
3. **No dependency injection.** Functions like `ensure_layers` at `dxf_builder.py:175` import from `generator` at runtime to avoid circular deps, rather than receiving configuration as a parameter.
4. **No observer/event pattern.** Errors during stream rendering are caught and logged inline (`generator.py:575-576`) rather than using a structured error-collection mechanism.
5. **God function anti-pattern** in `generate_process_sheet` and `generate_controls_sheet` -- these orchestrate everything procedurally rather than composing smaller units.

## Recommendations

1. Create an equipment renderer registry: `EQUIPMENT_RENDERERS: dict[str, Callable] = {"hopper": add_hopper, ...}` and look up by type string.
2. Introduce dataclasses (`Equipment`, `Instrument`, `Stream`, `ControlLoop`) to replace raw dicts and eliminate hundreds of `.get()` calls.
3. Pass `layer_config` as a parameter to `ensure_layers` instead of importing it at runtime.
4. Consider a `RenderContext` dataclass to bundle `msp`, `text_cfg`, `layout_cfg`, `label_placer`, and layer names -- reducing parameter counts on rendering functions.
