"""Specification validation for P&ID YAML specs."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SpecValidationError(ValueError):
    """Raised when a P&ID specification fails validation."""


def _equipment_dims(eq: dict[str, Any]) -> tuple[float, float]:
    """Return (width, height) for an equipment entry, avoiding circular import."""
    from programmatic_pid.dxf_builder import to_float

    return to_float(eq.get("w", eq.get("width", 0.0))), to_float(eq.get("h", eq.get("height", 0.0)))


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

        w, h = _equipment_dims(eq)
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
