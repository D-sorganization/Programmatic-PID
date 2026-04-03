# Assessment K: CI/CD

**Date:** 2026-04-03
**Grade: 7/10**

## Findings

### Positive

1. **Comprehensive quality gate:** `ci-standard.yml` runs Ruff linting, Black formatting checks, Bandit security scan, and placeholder verification.
2. **Multi-version testing:** Tests run on Python 3.11 and 3.12 (`ci-standard.yml:82-83`).
3. **Dependency vulnerability scanning:** `pip-audit` in a separate `security-scan` job.
4. **Tool version consistency:** CI verifies that tool versions match `.pre-commit-config.yaml` (`ci-standard.yml:24-37`).
5. **Coverage reporting:** `pytest-cov` generates XML and terminal output, with optional Codecov upload.
6. **Concurrency control:** `ci-standard.yml:7-9` cancels in-progress runs for the same branch.
7. **Pre-commit hooks** configured for Black, isort, Ruff, mypy, and Prettier.

### Issues Found

1. **mypy skipped in CI:** `ci-standard.yml:52` explicitly skips type checking with a comment "planned improvement." This undermines the strict mypy config in `mypy.ini`.
2. **No coverage threshold.** Tests run with `--cov` but there is no `--cov-fail-under` flag to enforce minimum coverage.
3. **No integration test separation.** The `integration` marker is defined but integration tests are not run separately or gated differently from unit tests.
4. **No artifact publishing.** Generated DXF/SVG outputs from integration tests are not saved as CI artifacts for review.
5. **Codecov token is optional:** `ci-standard.yml:93-98` gracefully handles missing Codecov token, but this means coverage tracking may silently not work.
6. **No release/packaging pipeline.** No CI job builds or publishes the Python package.

## Recommendations

1. Enable mypy in CI immediately.
2. Add `--cov-fail-under=75` (or appropriate threshold) to the pytest command.
3. Save DXF/SVG artifacts from integration tests using `actions/upload-artifact`.
4. Add a release job that builds and optionally publishes the package on tagged commits.
5. Consider running integration tests as a separate job to allow faster feedback on unit tests.
