# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial CHANGELOG.md to track project changes.
- LICENSE file (MIT).

## [0.1.0] - 2026-04-11

### Added
- Python framework for generating P&ID diagrams from YAML specifications.
- Core drawing engine powered by `ezdxf[draw]>=1.4.3`.
- YAML spec parsing with `PyYAML>=6.0`.
- CLI entry point: `generate-pid`.
- Unit test suite using pytest.
- Pre-commit hooks with ruff and mypy.
- AGENTS.md, README.md, and SPEC.md for contributor and architecture documentation.