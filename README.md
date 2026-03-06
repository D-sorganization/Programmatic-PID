# Programmatic-PID

A framework for designing, simulating, and deploying PID controllers programmatically using Python.

## Overview

This repository provides a structured environment for:

- **Designing** PID controllers with tunable gain parameters (Kp, Ki, Kd)
- **Simulating** closed-loop control systems using numerical integration
- **Visualizing** step responses, Bode plots, and phase/gain margins
- **Auto-tuning** via Ziegler-Nichols, relay feedback, and optimization-based methods
- **Deploying** controllers to embedded targets (Arduino, Raspberry Pi)

## Project Structure

```
Programmatic-PID/
├── python/
│   ├── pid/              # Core PID controller implementations
│   ├── tuning/           # Auto-tuning algorithms
│   ├── simulation/       # Plant models and simulation harness
│   └── visualization/    # Plotting and analysis utilities
├── tests/                # pytest test suite
├── docs/                 # Design documents and engineering notes
├── config/               # YAML configuration files for controllers
├── scripts/              # Utility scripts
├── data/                 # Logged data, step response recordings
└── output/               # Generated reports and plots
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run example simulation
python scripts/run_simulation.py
```

## Development Principles

- **TDD**: All new features require tests written first
- **DbC**: Design by Contract guards on all public APIs
- **DRY**: Shared utilities extracted to `python/pid/utils.py`
- **Type safety**: Full mypy strict mode compliance

## Engineering Standards

See [`AGENTS.md`](AGENTS.md) for full coding standards, Git workflow, and CI/CD requirements.
