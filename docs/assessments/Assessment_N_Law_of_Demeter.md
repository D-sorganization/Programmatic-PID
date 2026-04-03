# Assessment N: Law of Demeter (LoD) Compliance

**Date:** 2026-04-03
**Grade: 6/10**

## Findings

### Positive

1. **Config accessor functions:** `get_project`, `get_drawing`, `get_text_config`, `get_layer_config`, `get_layout_config` at `generator.py:151-230` encapsulate nested dict traversal, providing a single level of indirection rather than chaining `.get()` calls.
2. **`resolve_endpoint`** at `dxf_builder.py:494-508` encapsulates the logic for looking up equipment by ID and computing anchor points.
3. **`resolve_reference_point`** at `control_loops.py:21-43` similarly encapsulates multi-dict lookups.

### Issues Found

1. **Deep dict chaining throughout:** Despite config accessors, many functions still reach deep into nested dicts:
   - `notes.py:24`: `spec.get("mass_balance", {}).get("basis", {})`
   - `notes.py:111`: `spec.get("annotations", {}).get("notes_panel", {}).get("bullets", [])` -- three levels of `.get()` chaining.
   - `notes.py:113-114`: `pressure.get("normal_operating_pressure_psig")` after `spec.get("pressure_control", {})`.
   - `generator.py:479`: `spec.get("defaults", {}).get("arrow_size")` -- two levels.
   - `generator.py:480-482`: `spec.get("defaults", {}).get("instrument_bubble_radius")`.
2. **Rendering functions reach into spec structure:** `generate_process_sheet` at `generator.py:533` does `eq.get("id")` directly on equipment dicts, and `generator.py:544` does `ins.get("id")` on instrument dicts. These should be accessed through accessor functions or dataclass properties.
3. **Layer access pattern:** `generator.py:474` does `layer.dxf.name.lower()` -- reaching through `layer` to `dxf` to `name`. This is an ezdxf API pattern but violates LoD.
4. **`msp.doc.layers`** accessed in `stream_router.py:108` and `control_loops.py:121` -- reaching through modelspace to doc to layers.
5. **`notes.py:86`** passes `*panels["control"]` (unpacking a tuple from a dict value) which couples the caller to the internal structure of the panels dict.

## Recommendations

1. Create accessor functions for commonly chained paths (e.g., `get_defaults(spec)`, `get_annotations_bullets(spec)`, `get_mass_balance_basis(spec)`).
2. Replace raw dicts with dataclasses that expose properties directly (e.g., `spec.defaults.arrow_size` instead of `spec.get("defaults", {}).get("arrow_size")`).
3. Wrap the `msp.doc.layers` access in a helper function (e.g., `has_layer(msp, name)` and `ensure_msp_layer(msp, name, ...)`).
4. Create a `PanelLayout` dataclass instead of passing tuples from a dict.
