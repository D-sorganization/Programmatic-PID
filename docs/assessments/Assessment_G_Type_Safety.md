# Assessment G: Type Safety

**Date:** 2026-04-03
**Grade: 6/10**

## Findings

### Positive

1. **`from __future__ import annotations`** is used in all source files, enabling modern type hint syntax.
2. **Return type annotations** on all public functions (e.g., `generator.py:139`, `dxf_builder.py:22`, `validator.py:22`).
3. **Parameter type annotations** on all function signatures.
4. **`py.typed` marker** present, declaring the package as typed.
5. **Strict mypy config** in `mypy.ini:1-27` with `strict = True`, `disallow_untyped_defs = True`.

### Issues Found

1. **mypy is skipped in CI:** `ci-standard.yml:52` reads `echo "mypy skipped - baseline scripts not yet typed"`. The strict mypy config exists but is never enforced.
2. **Pervasive `Any` usage:** 47 occurrences of `Any` type across source files. Key offenders:
   - `msp: Any` in every rendering function (could be `ezdxf.layouts.Modelspace`).
   - `doc: Any` in layer functions (could be `ezdxf.document.Drawing`).
   - `spec: dict[str, Any]` everywhere (could be a TypedDict or dataclass).
3. **No TypedDict for spec structure.** The spec dict is typed as `dict[str, Any]` in all 20+ functions that accept it, providing zero compile-time safety for key access.
4. **No runtime type checking** beyond `isinstance` checks in `validate_spec`. Functions like `add_stream` accept `stream: dict[str, Any]` but don't verify the dict has the expected keys.
5. **`to_float(value: Any, ...)` accepts `Any`** at `dxf_builder.py:22`, which is correct for its purpose but means callers get no type feedback on what they're passing.

## Recommendations

1. Enable mypy in CI immediately -- the config is already strict.
2. Replace `msp: Any` with `msp: ezdxf.layouts.BaseLayout` and `doc: Any` with `doc: ezdxf.document.Drawing` across all modules.
3. Create a `TypedDict` (or dataclass) for the spec structure to catch key-access errors at type-check time.
4. Create a `TextConfig` TypedDict for the text configuration dict returned by `get_text_config`.
5. Add `overload` signatures where functions accept multiple input shapes (e.g., `add_stream` with vertices vs. start/end vs. from/to).
