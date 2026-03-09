# Programmatic-PID

A Python framework for generating **P&ID (Piping & Instrumentation Diagrams)** programmatically from YAML specifications — no AutoCAD required for first drafts.

## Overview

**Programmatic-PID** produces editable DXF drawings and SVG previews from a declarative YAML specification. The workflow is:

```text
YAML Spec → generate-pid → DXF (ezdxf) → LibreCAD / AutoCAD
```

## IDE Validation & Autocompletion

To get real-time validation and autocompletion for your specification files, we provide a JSON schema. Add the following comment to the top of your YAML specification files (if you are using VS Code with the RedHat YAML extension):

```yaml
# yaml-language-server: $schema=../../schema/pid_spec.schema.json
```

Key capabilities:

- **Equipment symbols** — vessels, hoppers, vertical retorts, fans, rotary valves, burners, bins
- **Process streams** — polyline routing with arrowheads, collision-avoiding label placement
- **Instruments** — bubble tags, connection leaders
- **Control loops** — signal lines from measurement to final element
- **Panels** — title block, control summary, mass balance, safety/design notes
- **Multi-sheet output** — Process view + Controls/Interlocks sheet

## Project Structure

```text
Programmatic-PID/
├── src/
│   └── programmatic_pid/     # Core P&ID generation engine
├── tests/                    # Integration and unit tests
├── schema/
│   └── pid_spec.schema.json  # Autocompletion schema for YAML specs
├── examples/                 # Example P&ID specifications
│   └── biochar/
│       └── biochar_pid_spec.yml
├── output/                   # Generated drawings (gitignored)
├── docs/                     # Engineering notes and design reviews
├── pyproject.toml            # Project and dependencies definition
└── .github/workflows/ci-standard.yml
```

## Quick Start

It is recommended to use `pip` to install the package in editable mode:

```bash
pip install -e .
```

Generate a P&ID from a YAML spec using the provided CLI tool:

```bash
# Generate a P&ID from a YAML spec
generate-pid \
  --spec examples/biochar/biochar_pid_spec.yml \
  --out output/biochar_pid.dxf \
  --svg output/biochar_pid.svg \
  --sheet-set two \
  --profile presentation
```

### Output Profiles

| Profile | Description |
| --- | --- |
| `review` | Densest annotations — loop tags, inline equipment notes |
| `presentation` | Clean default for review meetings |
| `compact` | Tighter spacing for rapid iteration |

Each `--sheet-set two` run produces:

- `output/<name>.dxf` — Process/flow view
- `output/<name>_controls.dxf` — Controls & interlocks view
- Matching `.svg` previews when `--svg` is provided

## YAML Spec Format

The spec drives everything. Make sure to reference the schema at the top for autocompletion. Key top-level keys:

```yaml
# yaml-language-server: $schema=schema/pid_spec.schema.json
project:
  id: my-project
  title: My P&ID

equipment:
  - id: V-101
    type: vessel
    x: 30.0
    y: 40.0
    w: 18.0
    h: 24.0
    label: Feed Vessel

streams:
  - id: S-101
    from: { equipment: V-101, side: right }
    to:   { equipment: P-101, side: left }

instruments:
  - id: FT-101
    type: flow_transmitter
    x: 55.0
    y: 48.0

control_loops:
  - id: FC-101
    measurement: FT-101
    final_element: FV-101
```

## Running Tests

```bash
pytest tests/ -v
```

## Development Principles

- **TDD** — Tests before features
- **DbC** — `SpecValidationError` guards all inputs
- **DRY** — Shared geometry helpers in `generate_pid.py`
- **Type safety** — mypy strict mode

See [`AGENTS.md`](AGENTS.md) for full coding standards and Git workflow.
