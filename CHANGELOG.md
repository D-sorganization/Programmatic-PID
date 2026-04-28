# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Separate `dev-requirements.txt` for development dependencies.
- `requirements-lock.txt` for fully reproducible installs.
- SECURITY.md with vulnerability disclosure policy.
- `spec-check` CI workflow to validate SPEC.md on every PR.
- CONTRIBUTING.md with DCO enforcement for external contributors.

### Changed
- CI workflow now runs `mypy` type checks on every pull request.
- Split oversized DXF builder test files by responsibility.

### Fixed
- MyPy type errors in `dxf_text` module.
- MyPy function signature errors across core modules.
- Duplicate `TextEntityAlignment` import in DXF builder.
- Missing `TextEntityAlignment` re-export from `dxf_builder` facade.
- Spec numeric dimensions are now validated strictly.

## [0.2.0] - 2026-04-11

### Added
- Stream-backed control loop validation tests.
- Consolidated fleet remediation workflow for cross-repo alignment.
- Pre-commit hooks for code quality enforcement.

### Changed
- Refactored `dxf_builder.py` into focused sub-modules for maintainability.
- Updated CI to support optional Codecov integration.

### Fixed
- xvfb plugin disabled in CI test jobs to prevent spurious failures.

## [0.1.0] - 2026-04-01

### Added
- Initial release of Programmatic-PID.
- DXF generation engine with text, circle, and polyline entities.
- PID controller integration for automated sheet layout.
- CLI entry point for batch DXF creation.
- Unit test suite with pytest.