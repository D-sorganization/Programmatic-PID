"""Text utilities and label placement for DXF drawings."""

from __future__ import annotations

import textwrap
from typing import Any

from ezdxf.enums import TextEntityAlignment

from programmatic_pid.dxf_math import rects_overlap, text_box, to_float

__all__ = [
    "TextEntityAlignment",
    "parse_alignment",
    "wrap_text_lines",
    "LabelPlacer",
    "add_text",
    "add_text_panel",
]


def parse_alignment(align: Any) -> TextEntityAlignment:
    """Return a :class:`TextEntityAlignment` from a string or pass-through."""
    if isinstance(align, TextEntityAlignment):
        return align
    key = str(align or "MIDDLE_CENTER").upper()
    return getattr(TextEntityAlignment, key, TextEntityAlignment.MIDDLE_CENTER)


def wrap_text_lines(text: str, width: int) -> list[str]:
    """Word-wrap *text* to *width* characters."""
    if not isinstance(text, str):
        text = str(text)
    if not isinstance(width, int) or width < 12:
        width = 12
    chunks = textwrap.wrap(
        text,
        width=max(int(width), 12),
        break_long_words=False,
        break_on_hyphens=False,
    )
    return chunks if chunks else [text]


class LabelPlacer:
    """Tracks occupied rectangles and finds non-overlapping label positions."""

    def __init__(self) -> None:
        self.occupied: list[tuple[float, float, float, float]] = []

    def reserve_rect(self, rect: tuple[float, float, float, float]) -> None:
        """Register *rect* as occupied space."""
        self.occupied.append(rect)

    def reserve_text(self, text: str, x: float, y: float, h: float, align: str = "MIDDLE_CENTER") -> None:
        """Reserve the bounding box of a text label."""
        self.reserve_rect(text_box(text, x, y, h, align=align))

    def find_position(
        self,
        text: str,
        anchor: tuple[float, float],
        h: float,
        preferred: list[tuple[float, float, str]],
    ) -> tuple[float, float, str]:
        """Find the first non-overlapping position from *preferred* offsets."""
        ax, ay = to_float(anchor[0]), to_float(anchor[1])
        for dx, dy, align in preferred:
            x = ax + dx
            y = ay + dy
            candidate = text_box(text, x, y, h, align=align)
            if not any(rects_overlap(candidate, r, pad=h * 0.20) for r in self.occupied):
                self.reserve_rect(candidate)
                return x, y, align
        fallback = preferred[0]
        x = ax + fallback[0]
        y = ay + fallback[1]
        align = fallback[2]
        self.reserve_rect(text_box(text, x, y, h, align=align))
        return x, y, align


def add_text(
    msp: Any,
    text: str,
    x: float,
    y: float,
    h: float,
    layer: str = "TEXT",
    align: str = "MIDDLE_CENTER",
) -> Any:
    """Add a text entity to *msp*."""
    t = msp.add_text(str(text), dxfattribs={"height": max(to_float(h, 1.0), 0.1), "layer": layer})
    t.set_placement((to_float(x), to_float(y)), align=parse_alignment(align))
    return t


def add_text_panel(
    msp: Any,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: list[str],
    text_h: float,
    text_layer: str,
    border_layer: str,
    max_chars: int = 42,
) -> None:
    """Draw a bordered text panel with a title and wrapped body lines."""
    from programmatic_pid.dxf_symbols import add_box

    add_box(msp, x, y, w, h, border_layer)
    inset_x = x + 1.1
    inset_top = y + h - 1.0
    add_text(msp, title, inset_x, inset_top, text_h * 1.05, layer=text_layer, align="TOP_LEFT")

    step = max(text_h * 1.16, 0.9)
    available = max(int((h - 2.6) / step), 1)
    out: list[str] = []
    for line in lines:
        if line is None:
            out.append("")
            continue
        out.extend(wrap_text_lines(line, max_chars))
    out = out[:available]

    cy = inset_top - max(text_h * 1.55, 1.1)
    for line in out:
        add_text(msp, line, inset_x, cy, text_h, layer=text_layer, align="TOP_LEFT")
        cy -= step
