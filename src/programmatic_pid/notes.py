"""Notes-panel rendering for P&ID sheets."""

from __future__ import annotations

import logging
from typing import Any

from programmatic_pid.dxf_builder import add_text_panel, to_float

logger = logging.getLogger(__name__)


def get_mass_balance_values(
    spec: dict[str, Any],
) -> tuple[float, float, float, float, float]:
    """Extract mass-balance parameters from *spec*.

    Raises:
        ValueError: If *spec* is ``None``.
    """
    if spec is None:
        raise ValueError("spec must not be None")

    mb = spec.get("mass_balance", {}).get("basis", {})
    if mb:
        wet_feed = to_float(mb.get("wet_feed_kg_h"), 1000)
        feed_mc = to_float(mb.get("feed_moisture_wt_frac"), 0.30)
        dried_mc = to_float(mb.get("dried_feed_target_moisture_wt_frac"), 0.20)
        char_wet = to_float(mb.get("wet_biochar_product_kg_h"), 300)
        char_mc = to_float(mb.get("product_moisture_wt_frac"), 0.02)
        return wet_feed, feed_mc, dried_mc, char_wet, char_mc

    assumptions = spec.get("assumptions", {})
    feed = assumptions.get("feed", {})
    dryer = assumptions.get("dryer", {})
    reactor = assumptions.get("reactor", {})

    wet_feed = to_float(feed.get("wet_biomass_rate_kg_h"), 1000)
    feed_mc = to_float(feed.get("moisture_wtfrac"), 0.30)
    dried_mc = to_float(dryer.get("target_moisture_wtfrac"), 0.20)
    dry_yield = to_float(reactor.get("dry_char_yield_fraction_of_dry_feed"), 0.42)
    char_mc = to_float(reactor.get("char_product_moisture_wtfrac"), 0.02)

    dry_solids = wet_feed * (1 - feed_mc)
    char_dry = dry_solids * dry_yield
    char_wet = char_dry / (1 - char_mc) if char_mc < 1.0 else 0.0
    return wet_feed, feed_mc, dried_mc, char_wet, char_mc


def add_notes(
    msp: Any,
    spec: dict[str, Any],
    text_cfg: dict[str, float],
    text_layer: str,
    notes_layer: str,
    layout_regions: dict[str, Any],
) -> None:
    """Render the control-loop, mass-balance, and design-notes panels.

    Raises:
        ValueError: If *spec* is ``None``.
    """
    if spec is None:
        raise ValueError("spec must not be None")

    panels = layout_regions["panels"]
    cfg = layout_regions["layout_cfg"]
    max_chars = cfg["panel_text_chars"]

    loops = spec.get("control_loops", [])
    loop_lines = [
        f"{loop.get('id', '')}: {loop.get('objective') or loop.get('description') or loop.get('note', '')}"
        for loop in loops
    ]
    panel = panels["control"]
    add_text_panel(
        msp,
        panel[0],
        panel[1],
        panel[2],
        panel[3],
        "Key Control Loops",
        loop_lines,
        text_cfg["small_height"],
        text_layer,
        notes_layer,
        max_chars,
    )

    wet_feed, feed_mc, dried_mc, char_wet, char_mc = get_mass_balance_values(spec)
    dry_solids = wet_feed * (1 - feed_mc)
    water_in = wet_feed * feed_mc
    water_after = dry_solids * dried_mc / (1 - dried_mc) if dried_mc < 1.0 else 0.0
    water_removed = water_in - water_after
    char_dry = char_wet * (1 - char_mc)
    dry_yield = (char_dry / dry_solids * 100) if dry_solids else 0.0
    mass_lines = [
        f"Feed water in = {water_in:.0f} kg/h",
        f"Dry biomass solids in = {dry_solids:.0f} kg/h",
        f"Water removed in dryer = {water_removed:.0f} kg/h",
        f"Biochar product = {char_wet:.0f} kg/h wet",
        f"Dry-basis char yield = {dry_yield:.1f}%",
    ]
    panel = panels["mass"]
    add_text_panel(
        msp,
        panel[0],
        panel[1],
        panel[2],
        panel[3],
        "Approximate Mass Balance",
        mass_lines,
        text_cfg["small_height"],
        text_layer,
        notes_layer,
        max_chars,
    )

    design_notes = list(spec.get("annotations", {}).get("notes_panel", {}).get("bullets", []))
    pressure = spec.get("pressure_control", {})
    if isinstance(pressure, dict):
        mode = pressure.get("mode")
        pset = pressure.get("normal_operating_pressure_psig")
        if mode:
            design_notes.insert(0, f"Pressure mode: {mode}")
        if pset is not None:
            design_notes.insert(1, f"Normal operating pressure target: {pset} psig")
        for note in pressure.get("notes", [])[:2]:
            design_notes.append(note)

    interlock_lines = [
        f"{item.get('id', '')}: {item.get('trigger', '')}" for item in spec.get("interlocks", [])[:5]
    ]
    equipment_note_lines: list[str] = []
    for eq in spec.get("equipment", []):
        notes = eq.get("notes", [])
        if notes:
            equipment_note_lines.append(f"{eq.get('id', '')}: {notes[0]}")

    right_lines: list[str] = []
    right_lines.extend(f"- {note}" for note in design_notes[:6])
    if interlock_lines:
        right_lines.append("")
        right_lines.append("Interlock Triggers:")
        right_lines.extend(interlock_lines)
    if equipment_note_lines:
        right_lines.append("")
        right_lines.append("Equipment Notes:")
        right_lines.extend(equipment_note_lines[:6])

    panel = panels["right"]
    add_text_panel(
        msp,
        panel[0],
        panel[1],
        panel[2],
        panel[3],
        "Design and Safety Notes",
        right_lines,
        text_cfg["small_height"],
        text_layer,
        notes_layer,
        max_chars,
    )
