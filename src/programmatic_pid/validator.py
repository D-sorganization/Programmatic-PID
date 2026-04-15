"""Specification validation for P&ID YAML specs."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class SpecValidationError(ValueError):
    """Raised when a P&ID specification fails validation."""


def _equipment_dims(eq: dict[str, Any]) -> tuple[float, float]:
    """Return (width, height) for an equipment entry using strict spec parsing."""

    eq_id = str(eq.get("id", "<unknown>"))
    width = _strict_float(eq.get("w", eq.get("width")), f"equipment {eq_id} width")
    height = _strict_float(eq.get("h", eq.get("height")), f"equipment {eq_id} height")
    return width, height


def _strict_float(value: Any, field_name: str) -> float:
    """Parse a spec-authored number without falling back to plausible defaults."""
    if isinstance(value, bool):
        raise SpecValidationError(f"{field_name} must be numeric, got bool")
    if value is None:
        raise SpecValidationError(f"{field_name} is required")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise SpecValidationError(f"{field_name} must be numeric, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise SpecValidationError(f"{field_name} must be finite, got {value!r}")
    return parsed


def validate_spec(spec: Any) -> None:
    """Validate a P&ID specification dict, raising *SpecValidationError* on problems.

    Raises:
        ValueError: If *spec* is ``None``.
        SpecValidationError: If *spec* is not a dict or contains semantic errors.
    """
    if spec is None:
        raise ValueError("spec must not be None")
    errors: list[str] = []
    if not isinstance(spec, dict):
        raise SpecValidationError("Specification must be a YAML mapping.")

    project = spec.get("project", {})
    if not project.get("id"):
        errors.append("project.id is required")
    if not (project.get("title") or project.get("document_title")):
        errors.append("project.title or project.document_title is required")

    equipment = spec.get("equipment", [])
    if not equipment:
        errors.append("equipment list cannot be empty")

    equipment_ids: set[str] = set()
    for eq in equipment:
        eq_id = eq.get("id")
        if not eq_id:
            errors.append("equipment entry missing id")
            continue
        if eq_id in equipment_ids:
            errors.append(f"duplicate equipment id: {eq_id}")
        equipment_ids.add(eq_id)

        try:
            w, h = _equipment_dims(eq)
        except SpecValidationError as exc:
            errors.append(str(exc))
        else:
            if w <= 0 or h <= 0:
                errors.append(f"equipment {eq_id} has non-positive width/height")

    instrument_ids: set[str] = set()
    for ins in spec.get("instruments", []):
        ins_id = ins.get("id")
        if not ins_id:
            errors.append("instrument entry missing id")
            continue
        if ins_id in instrument_ids:
            errors.append(f"duplicate instrument id: {ins_id}")
        instrument_ids.add(ins_id)

    for stream in spec.get("streams", []):
        sid = stream.get("id", "<unknown>")
        if "from" in stream:
            fr = stream.get("from", {})
            eq = fr.get("equipment")
            if eq and eq not in equipment_ids:
                errors.append(f"stream {sid} references unknown from equipment: {eq}")
        if "to" in stream:
            to = stream.get("to", {})
            eq = to.get("equipment")
            if eq and eq not in equipment_ids:
                errors.append(f"stream {sid} references unknown to equipment: {eq}")

    references = equipment_ids | instrument_ids
    for loop in spec.get("control_loops", []):
        lid = loop.get("id", "<unknown>")
        meas = loop.get("measurement")
        final = loop.get("final_element")
        if not meas or not final:
            errors.append(f"control loop {lid} missing measurement/final_element")
            continue
        if meas not in references:
            errors.append(f"control loop {lid} unknown measurement reference: {meas}")
        if final not in references:
            errors.append(f"control loop {lid} unknown final element reference: {final}")

    if errors:
        raise SpecValidationError("Invalid spec:\n- " + "\n- ".join(errors))
