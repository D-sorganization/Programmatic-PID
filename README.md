# Programmatic-PID

A Python framework for generating **P&ID (Piping & Instrumentation Diagrams)** programmatically from YAML specifications — no AutoCAD required for first drafts.

## Overview

**Programmatic-PID** produces editable DXF drawings and SVG previews from a declarative YAML specification. The workflow is:

```
YAML Spec → generate_pid.py → DXF (ezdxf) → LibreCAD / AutoCAD
```

Key capabilities:

- **Equipment symbols** — vessels, hoppers, vertical retorts, fans, rotary valves, burners, bins
- **Process streams** — polyline routing with arrowheads, collision-avoiding label placement
- **Instruments** — bubble tags, connection leaders
- **Control loops** — signal lines from measurement to final element
- **Panels** — title block, control summary, mass balance, safety/design notes
- **Multi-sheet output** — Process view + Controls/Interlocks sheet

## Project Structure

```
Programmatic-PID/
├── python/
│   └── baseline/             # Core P&ID generation engine
│       ├── scripts/
│       │   └── generate_pid.py   # Main generator (YAML → DXF/SVG)
│       ├── tests/
│       │   ├── test_pid_generation.py
│       │   └── test_pid_integration.py
│       ├── biochar_pid_spec.yml  # Example biochar reactor P&ID spec
│       ├── P&ID Open Workflow Setup.md
│       └── requirements.txt
├── output/                   # Generated drawings (gitignored)
├── docs/development/         # Engineering notes
├── requirements.txt          # Fleet-level dependencies
└── .github/workflows/ci-standard.yml
```

## Quick Start

```bash
pip install -r python/baseline/requirements.txt

# Generate a P&ID from a YAML spec
python python/baseline/scripts/generate_pid.py \
  --spec python/baseline/biochar_pid_spec.yml \
  --out output/biochar_pid.dxf \
  --svg output/biochar_pid.svg \
  --sheet-set two \
  --profile presentation
```

### Output Profiles

| Profile | Description |
|---|---|
| `review` | Densest annotations — loop tags, inline equipment notes |
| `presentation` | Clean default for review meetings |
| `compact` | Tighter spacing for rapid iteration |

Each `--sheet-set two` run produces:

- `output/<name>.dxf` — Process/flow view
- `output/<name>_controls.dxf` — Controls & interlocks view
- Matching `.svg` previews when `--svg` is provided

## YAML Spec Format

The spec drives everything. Key top-level keys:

```yaml
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
pytest python/baseline/tests/ -v
```

## Development Principles

- **TDD** — Tests before features
- **DbC** — `SpecValidationError` guards all inputs
- **DRY** — Shared geometry helpers in `generate_pid.py`
- **Type safety** — mypy strict mode

See [`AGENTS.md`](AGENTS.md) for full coding standards and Git workflow.
