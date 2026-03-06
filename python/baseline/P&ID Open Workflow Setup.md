# Biochar P&ID Open Workflow Setup

## Purpose

This repository provides a practical, scriptable workflow for generating conceptual P&ID-style drawings without needing AutoCAD for the first draft.

The stack is:

- VS Code for editing and agent workflows
- YAML as the source of truth
- Python for deterministic generation
- ezdxf for editable DXF output
- LibreCAD (or AutoCAD) for visual review

Current draft target:

- 11x17 landscape (ANSI B) plotting intent
- clean layout mode with separate process area + side/bottom note panels

## Repository layout

```text
biochar-project/
  biochar_pid_spec.yml
  scripts/
    generate_pid.py
  output/
  requirements.txt
```

## Quick start

Install dependencies:

```bash
python3 -m pip install --user -r requirements.txt
```

Generate the proof-of-concept draft:

```bash
python3 scripts/generate_pid.py \
  --spec biochar_pid_spec.yml \
  --out output/biochar_pid_clean_11x17.dxf \
  --svg output/biochar_pid_clean_11x17.svg \
  --sheet-set two \
  --profile presentation
```

Profiles:

- `review`: densest annotations, loop tags, inline equipment notes
- `presentation`: cleaner review default
- `compact`: tighter spacing for quick iteration

This now creates:

- `output/biochar_pid_clean_11x17.dxf` (Sheet 1: process view)
- `output/biochar_pid_clean_11x17_controls.dxf` (Sheet 2: controls/interlocks)
- matching SVG previews for each file when `--svg` is provided

## What the current generator renders

- Equipment symbols/blocks (including hopper and vertical retort zones)
- Process and utility stream routing with arrowheads and labels
- Automatic stream-label leader lines when labels are displaced by collision-avoidance
- Instrument bubbles and tags
- Control-loop signal lines from `measurement` to `final_element` on `line_layer` (for example `control_lines`)
- Title block plus dedicated side/bottom panels (control summary, mass balance, safety/design notes)
- Separate controls/interlocks sheet for clearer review and updates

## Validation

Run tests (contract checks + layout/routing behavior + integration generation):

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -s
```
