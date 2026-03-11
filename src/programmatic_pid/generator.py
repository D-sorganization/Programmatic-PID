"""P&ID generator — backward-compatible shim module.

This module preserves the original public API by re-exporting from the
decomposed submodules.  New code should import from the specific modules
(``rendering``, ``layout``, ``streams``, etc.) or use the ``PIDDocument``
facade class.

.. deprecated:: 0.3.0
    Import from specific submodules instead of ``generator``.
"""
from __future__ import annotations

# Re-export everything for backward compatibility --------------------------
# Types & geometry
from programmatic_pid.types import SpecValidationError  # noqa: F401
from programmatic_pid.geometry import (  # noqa: F401
    to_float,
    clamp,
    closest_point_on_rect,
    rects_overlap,
    text_box,
    dedupe_points,
)

# Profiles
from programmatic_pid.profiles import PROFILE_PRESETS, apply_profile  # noqa: F401

# Spec loading
from programmatic_pid.spec_loader import (  # noqa: F401
    load_spec,
    prepare_spec,
    get_project,
    get_drawing,
    ensure_drawing,
    get_text_config,
    get_layout_config,
    get_layer_config,
)

# Validation
from programmatic_pid.validation import validate_spec  # noqa: F401

# Equipment
from programmatic_pid.equipment import (  # noqa: F401
    equipment_dims,
    equipment_center,
    equipment_side_anchors,
    equipment_anchor,
    nearest_equipment_anchor,
    draw_equipment_symbol,
    EQUIPMENT_RENDERERS,
    register_equipment,
)

# Rendering primitives
from programmatic_pid.rendering import (  # noqa: F401
    ensure_layer,
    ensure_layers,
    layer_name,
    parse_alignment,
    wrap_text_lines,
    add_text,
    add_text_panel,
    add_box,
    add_arrow_head,
    add_arrow,
    add_poly_arrow,
    export_svg_from_dxf,
)

# Layout
from programmatic_pid.layout import (  # noqa: F401
    LabelPlacer,
    spread_instrument_positions,
    get_equipment_bounds,
    compute_layout_regions,
    get_modelspace_extent,
)

# Streams
from programmatic_pid.streams import resolve_endpoint, add_stream  # noqa: F401

# Instruments
from programmatic_pid.instruments import add_instrument  # noqa: F401

# Controls
from programmatic_pid.controls import (  # noqa: F401
    orthogonal_control_route,
    resolve_reference_point,
    add_control_loops,
)

# Title block & notes
from programmatic_pid.title_block import (  # noqa: F401
    add_title_block,
    get_mass_balance_values,
    add_notes,
)

# CLI / orchestration
from programmatic_pid.cli import (  # noqa: F401
    add_equipment,
    generate_process_sheet,
    generate_controls_sheet,
    derive_related_path,
    generate,
    main,
)
