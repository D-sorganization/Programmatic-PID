"""DXF layer management utilities."""

from __future__ import annotations

from typing import Any

from ezdxf import DXFValueError  # type: ignore[attr-defined]


def ensure_layer(doc: Any, name: str, color: int = 7, linetype: str = "CONTINUOUS") -> None:
    """Create a DXF layer if it does not already exist."""
    if not name:
        return
    if name in doc.layers:
        return
    attrs = {"color": int(color), "linetype": str(linetype)}
    try:
        doc.layers.new(name=name, dxfattribs=attrs)
    except DXFValueError:
        attrs["linetype"] = "CONTINUOUS"
        doc.layers.new(name=name, dxfattribs=attrs)


def ensure_layers(doc: Any, spec: dict[str, Any]) -> None:
    """Create all layers referenced in *spec* plus sensible defaults."""
    from programmatic_pid.generator import get_layer_config

    for name, cfg in get_layer_config(spec).items():
        cfg = cfg or {}
        ensure_layer(doc, name, color=cfg.get("color", 7), linetype=cfg.get("linetype", "CONTINUOUS"))

    for name, color in (
        ("TEXT", 7),
        ("NOTES", 3),
        ("LEADERS", 8),
        ("EQUIPMENT", 7),
        ("INSTRUMENTS", 2),
        ("PROCESS", 5),
    ):
        ltype = "DASHED" if name == "LEADERS" else "CONTINUOUS"
        ensure_layer(doc, name, color=color, linetype=ltype)


def layer_name(layer_index: dict[str, str], *candidates: str, default: str = "0") -> str:
    """Resolve the first matching layer name from *candidates*."""
    for candidate in candidates:
        if not candidate:
            continue
        actual = layer_index.get(str(candidate).lower())
        if actual:
            return actual
    return default
