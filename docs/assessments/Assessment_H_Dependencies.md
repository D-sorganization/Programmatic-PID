# Assessment H: Dependencies

**Date:** 2026-04-03
**Grade: 8/10**

## Findings

### Positive

1. **Minimal runtime dependencies:** Only `ezdxf[draw]>=1.4.3` and `PyYAML>=6.0` -- both well-maintained, widely-used libraries appropriate for the domain.
2. **Version pinning with minimum bounds:** `requirements.txt` and `pyproject.toml` both specify minimum versions.
3. **Dev tools are separate:** Testing and quality tools (`pytest`, `ruff`, `mypy`) are in `requirements.txt` but not in `pyproject.toml` dependencies.
4. **CI dependency audit:** `ci-standard.yml:73-74` runs `pip-audit` to check for known vulnerabilities.
5. **Pre-commit hooks** maintain formatting and linting consistency.
6. **Tool version consistency check** in CI (`ci-standard.yml:24-37`) validates that CI tool versions match `.pre-commit-config.yaml`.

### Issues Found

1. **No upper-bound version constraints.** `ezdxf[draw]>=1.4.3` could break on a major version bump. Consider `>=1.4.3,<2.0`.
2. **`requirements.txt` mixes runtime and dev dependencies.** No separation between `requirements.txt` (runtime) and `requirements-dev.txt` (testing/tooling). The `pyproject.toml` correctly separates them, but `requirements.txt` does not.
3. **Unpinned dev tool versions in `requirements.txt`:** `ruff` and `mypy` have no version pins in `requirements.txt:11-12`, though CI pins specific versions.
4. **No lock file.** No `requirements.lock` or equivalent for reproducible builds.
5. **`types-PyYAML`** in `requirements.txt:13` is a dev dependency but is listed alongside runtime deps.

## Recommendations

1. Add upper-bound constraints to runtime deps (e.g., `ezdxf[draw]>=1.4.3,<2.0`).
2. Split `requirements.txt` into `requirements.txt` (runtime only) and `requirements-dev.txt` (testing/tooling).
3. Pin dev tool versions in `requirements-dev.txt` to match CI and pre-commit.
4. Consider adding `[project.optional-dependencies]` in `pyproject.toml` for dev dependencies.
