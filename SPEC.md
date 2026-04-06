# Programmatic-PID Specification

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
- `generator.py` loads specs, applies profiles, computes layout, and orchestrates sheet generation.
- `dxf_builder.py` provides drawing primitives, geometry helpers, and layer utilities.
- `stream_router.py` routes process streams between equipment anchors and handles labeling.
- `control_loops.py` draws control-loop relationships and reference routing.
- `notes.py` renders notes, mass balance values, and sheet annotations.

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
- Documentation should remain consistent with the real package layout and public CLI behavior.
- If a future change moves responsibility between modules, update this spec in the same change.

