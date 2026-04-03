# Assessment A: Code Structure

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

The codebase follows a well-decomposed module structure with clear single-responsibility separation:

- **generator.py** (845 lines) -- orchestrator and public API surface. Re-exports all symbols for backward compatibility. Contains config helpers, layout computation, title block rendering, SVG export, sheet generation, and CLI. This file is the largest and approaches monolith territory.
- **dxf_builder.py** (650 lines) -- low-level DXF primitives, equipment geometry, label collision avoidance. Also borderline monolith; mixes numeric helpers, text utilities, bounding-box logic, layer management, drawing primitives, and equipment rendering in a single file.
- **control_loops.py** (141 lines) -- focused module for control loop rendering.
- **stream_router.py** (114 lines) -- focused module for stream routing and drawing.
- **notes.py** (152 lines) -- notes-panel rendering.
- **validator.py** (96 lines) -- spec validation logic.

### Positive

1. The recent refactor (commit 11023b3) successfully broke a single monolithic file into focused sub-modules.
2. Backward compatibility is maintained via re-exports in `generator.py:22-68`.
3. Each sub-module has a clear docstring declaring its purpose.
4. The `__init__.py` is intentionally empty, keeping the package namespace clean.

### Issues Found

1. **generator.py:444-606** (`generate_process_sheet`) is a 162-line function that performs DXF doc creation, layer setup, layout computation, equipment rendering, stream drawing, control loops, notes, title block, and file I/O all in one function. This is a monolith function.
2. **generator.py:613-781** (`generate_controls_sheet`) is similarly a 168-line monolith function.
3. **dxf_builder.py** mixes six distinct concerns (numeric helpers, text utilities, bounding-box helpers, label collision, layer management, equipment/instrument rendering) in a single 650-line file.
4. No `__all__` exports defined in any module, making the public API implicit.
5. Circular import workaround in `validator.py:17` (`from programmatic_pid.dxf_builder import to_float` inside a function) and `dxf_builder.py:177` (`from programmatic_pid.generator import get_layer_config` inside a function).

## Recommendations

1. Extract `generate_process_sheet` and `generate_controls_sheet` body logic into smaller composable functions (e.g., `_setup_doc`, `_render_equipment`, `_render_streams`).
2. Split `dxf_builder.py` into `geometry.py` (equipment dims, anchors, bounds), `primitives.py` (add_box, add_arrow, add_text), and `labels.py` (LabelPlacer, text_box, collision).
3. Add `__all__` to each module to formalize the public API.
4. Resolve circular imports by extracting shared utilities (e.g., `to_float`) into a `utils.py` module.
