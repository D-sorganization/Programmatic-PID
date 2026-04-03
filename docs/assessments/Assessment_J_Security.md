# Assessment J: Security

**Date:** 2026-04-03
**Grade: 8/10**

## Findings

### Positive

1. **`yaml.safe_load`** used at `generator.py:148` -- prevents arbitrary code execution from YAML deserialization.
2. **Bandit security scan** in CI at `ci-standard.yml:58` with `-ll -ii` flags.
3. **`pip-audit`** dependency vulnerability scanning in CI at `ci-standard.yml:74`.
4. **No network operations.** The tool is entirely offline -- reads YAML, writes DXF/SVG files.
5. **No user authentication or secrets handling.**
6. **No `eval()` or `exec()` usage anywhere in the codebase.**

### Issues Found

1. **No path traversal protection:** `load_spec` at `generator.py:147` opens any path passed to it. If used in a web service context, this could allow reading arbitrary files. Currently mitigated by being a CLI tool.
2. **No file size limits:** Large YAML specs could consume excessive memory during `yaml.safe_load`.
3. **`open()` without explicit mode:** `generator.py:147` opens for reading (default), which is correct, but the encoding is explicitly set to `utf-8`, which is good.
4. **SVG output contains no sanitization:** If equipment names or labels contain HTML/SVG injection payloads, they would be written directly into the SVG output via ezdxf's SVG backend. This is low risk since the SVG is generated from trusted YAML input.

## Recommendations

1. Add file size validation before loading YAML specs (e.g., reject files > 10MB).
2. If the tool is ever exposed as a web service, add path canonicalization and restrict input paths to a configured directory.
3. Sanitize text content before SVG export if the input source becomes untrusted.
