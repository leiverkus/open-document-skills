"""Slide-layout library for the ODP skill.

A *layout* is a named arrangement of placeholder zones on the 28 x 15.75 cm
slide canvas — the ODF equivalent of a PowerPoint/Impress slide layout. This
module is the single source of truth: it feeds both the
``style:presentation-page-layout`` definitions written into ``styles.xml`` and
the actual ``draw:frame`` placement done by ``create_minimal_odp.py`` /
``set_layout.py``, so the two can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET

from odp_common import q


@dataclass(frozen=True)
class Placeholder:
    """One placeholder zone of a layout.

    Attributes:
        cls: The placeholder class — ``title``, ``subtitle``, or ``outline``.
            Used for both ``presentation:object`` (layout) and
            ``presentation:class`` (slide frame).
        spec_key: The JSON spec key whose content fills this zone.
        x, y, width, height: Geometry on the 28 x 15.75 cm canvas.
    """

    cls: str
    spec_key: str
    x: str
    y: str
    width: str
    height: str


# The six standard layouts. ``title-content`` keeps the geometry the generator
# used before layouts existed, so specs without a ``layout`` key are unchanged.
LAYOUTS: dict[str, list[Placeholder]] = {
    "title-content": [
        Placeholder("title", "title", "1cm", "0.8cm", "26cm", "2cm"),
        Placeholder("outline", "body", "1.4cm", "3.2cm", "25cm", "8cm"),
    ],
    "title-slide": [
        Placeholder("title", "title", "2cm", "5cm", "24cm", "3cm"),
        Placeholder("subtitle", "subtitle", "2cm", "8.5cm", "24cm", "2.5cm"),
    ],
    "two-content": [
        Placeholder("title", "title", "1cm", "0.8cm", "26cm", "2cm"),
        Placeholder("outline", "body_left", "1.4cm", "3.2cm", "12cm", "8cm"),
        Placeholder("outline", "body_right", "14.6cm", "3.2cm", "12cm", "8cm"),
    ],
    "section-header": [
        Placeholder("title", "title", "2cm", "6cm", "24cm", "3.5cm"),
    ],
    "title-only": [
        Placeholder("title", "title", "1cm", "0.8cm", "26cm", "2cm"),
    ],
    "blank": [],
}

DEFAULT_LAYOUT = "title-content"

# Layout name -> the style:presentation-page-layout style:name written in
# styles.xml. Kept stable and human-readable.
LAYOUT_STYLE_NAMES: dict[str, str] = {name: f"pl-{name}" for name in LAYOUTS}

# Placeholder class -> the graphic/paragraph style each frame uses. The graphic
# styles (gr-title, gr-body) are defined by create_minimal_odp.build_styles().
GRAPHIC_STYLE: dict[str, str] = {"title": "gr-title", "subtitle": "gr-body", "outline": "gr-body"}
PARAGRAPH_STYLE: dict[str, str] = {"title": "Title", "subtitle": "Body", "outline": "Body"}


def frame_name(spec_key: str) -> str:
    """Derive a draw:name from a spec key, e.g. 'body_left' -> 'BodyLeft'."""
    return "".join(part.capitalize() for part in spec_key.split("_"))


def build_presentation_page_layout(layout_name: str) -> ET.Element:
    """Build the style:presentation-page-layout element for *layout_name*."""
    if layout_name not in LAYOUTS:
        raise SystemExit(f"unknown layout {layout_name!r}; choose from {sorted(LAYOUTS)}")
    element = ET.Element(
        q("style", "presentation-page-layout"),
        {q("style", "name"): LAYOUT_STYLE_NAMES[layout_name]},
    )
    for zone in LAYOUTS[layout_name]:
        ET.SubElement(
            element,
            q("presentation", "placeholder"),
            {
                q("presentation", "object"): zone.cls,
                q("svg", "x"): zone.x,
                q("svg", "y"): zone.y,
                q("svg", "width"): zone.width,
                q("svg", "height"): zone.height,
            },
        )
    return element
