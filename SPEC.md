# Programmatic-PID Specification

**Version:** 0.1.1 — 2026-04-16

## Purpose

`Programmatic-PID` is a Python package for generating editable P&ID drawings from YAML specifications. It produces DXF output and optional SVG previews for review and drafting workflows.

## Public Entry Point

- CLI script: `generate-pid`
- Module entrypoint: `programmatic_pid.generator:main`
- Core orchestration module: `src/programmatic_pid/generator.py`

## Repository Layout

- `src/programmatic_pid/` contains the maintained package code.
- `tests/` contains unit and integration tests for the package.
- `schema/pid_spec.schema.json` provides YAML schema support for editor validation.
- `examples/biochar/` contains example specifications used for manual and automated verification.
- `output/` is the local generation target directory for drawings and previews.
- `docs/` holds engineering notes and related documentation.

## Runtime Responsibilities

- `validator.py` validates YAML spec structure and raises `SpecValidationError` for invalid inputs.
- `generator.py` loads specs, applies profiles, and keeps the public orchestration facade for sheet generation.
- `dxf_builder.py` is the public facade for all DXF drawing helpers; it re-exports every name from the sub-modules below and also owns the high-level `add_equipment` and `add_instrument` renderers.
- `dxf_math.py` provides numeric helpers (`to_float`, `clamp`) and bounding-box geometry (`text_box`, `rects_overlap`, `closest_point_on_rect`, `dedupe_points`).
- `dxf_text.py` provides text utilities (`parse_alignment`, `wrap_text_lines`, `LabelPlacer`) and text-drawing primitives (`add_text`, `add_text_panel`).
- `dxf_layer.py` provides layer management (`ensure_layer`, `ensure_layers`, `layer_name`).
- `dxf_symbols.py` provides equipment shape primitives (`add_box`, `add_hopper`, `add_fan_symbol`, `add_rotary_valve_symbol`, `add_burner_symbol`, `add_bin_symbol`, `draw_equipment_symbol`).
- `dxf_geometry.py` provides equipment geometry helpers and endpoint resolution (`equipment_dims`, `equipment_center`, `equipment_side_anchors`, `equipment_anchor`, `nearest_equipment_anchor`, `get_equipment_bounds`, `resolve_endpoint`, `spread_instrument_positions`).
- `dxf_arrows.py` provides arrow drawing primitives (`add_arrow_head`, `add_arrow`, `add_poly_arrow`).
- `stream_router.py` routes process streams between equipment anchors and handles labeling.
- `control_loops.py` draws control-loop relationships and reference routing.
- `notes.py` renders notes, mass balance values, and sheet annotations.
- `sheet_layout.py` owns shared layer resolution plus the controls/interlocks sheet layout and summary rendering helpers.
- `sheet_rendering.py` owns sheet-level rendering, DXF/SVG persistence, and the process-sheet drawing helpers that `generator.py` re-exports for backward compatibility.

## Configuration Model

The YAML spec is the source of truth. The common top-level sections are:

- `project`
- `equipment`
- `streams`
- `instruments`
- `control_loops`
- `interlocks`
- `defaults`
- `drawing`

The package also supports layout profiles such as `review`, `presentation`, and `compact`, which are applied as overlay configuration before drawing.

## Output Contract

- Process sheet generation writes a primary DXF file and may emit an SVG preview.
- Two-sheet generation also writes a controls/interlocks DXF and optional SVG preview.
- Generated artifacts belong in `output/` or another caller-supplied path, not in tracked source directories.

## Testing And Validation

- Unit tests cover validation, geometry helpers, routing, notes, and orchestration behavior.
- Integration tests exercise end-to-end generation from example specs.
- The repo expects packaging-compatible imports from `src/` rather than ad hoc path manipulation.

## Maintenance Notes

- Backward-compatible imports from `programmatic_pid.generator` are part of the current contract.
- All public names from the `dxf_*` sub-modules are re-exported by `dxf_builder.py`; callers should continue to import from `programmatic_pid.dxf_builder`.
- Documentation should remain consistent with the real package layout and public CLI behavior.
- If a future change moves responsibility between modules, update this spec in the same change.
