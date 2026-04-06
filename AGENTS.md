# Programmatic-PID Agent Notes

## Scope

This repository generates P&ID drawings from YAML specifications. The maintained code lives under `src/programmatic_pid`, with tests in `tests/`, schemas in `schema/`, examples in `examples/`, and generated drawings in `output/`.

## Working Rules

- Keep changes aligned with the current package layout and public CLI entrypoint `generate-pid`.
- Prefer small, targeted edits. Do not widen a docs task into implementation refactors unless the documentation is wrong without them.
- Preserve backward-compatible imports from `programmatic_pid.generator` unless a task explicitly says otherwise.
- Treat generated files, caches, and build artifacts as disposable unless a specific task says to promote them to fixtures.
- Do not edit unrelated files or revert user changes.

## Validation

- Use the repo-standard test and lint commands for code changes: `pytest`, `ruff`, `black`, and `mypy` when relevant to the task.
- For documentation-only changes, run a lightweight repo sanity check and confirm the docs still match the current layout.

## Documentation

- Keep `SPEC.md` truthful. If the implementation changes, update the spec in the same workstream.
- Keep the README, spec, and repo layout consistent enough that another engineer can find the CLI, schema, tests, and generated outputs quickly.

