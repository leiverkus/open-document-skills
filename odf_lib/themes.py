"""Curated theme registry — palettes and font pairings for the generators.

A *theme* is format-agnostic data: a colour palette plus a heading/body font
pairing. The four ``create_minimal_*`` generators and ``create_from_markdown``
apply a theme through their ``--theme`` flag. This module is pure data — it
holds no XML; each generator turns the values into its own styles.

Fonts are given as CSS-style stacks ending in a generic family
(``sans-serif``/``serif``/``monospace``). The first name is a metric-compatible
font that ships with LibreOffice, so themed documents render deterministically
even on a bare renderer; :func:`theme_font_faces` derives the ODF
``style:font-family-generic`` from the trailing generic keyword.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """A named colour palette and font pairing.

    Attributes:
        background: Page/slide background colour.
        accent: Headings, titles, shape strokes — the brand colour.
        text: Body text colour.
        muted: Secondary text (speaker notes, captions).
        shape_fill: Filled-shape colour (ODG); table-header fill (ODS).
        heading_font: CSS-style font stack for headings/titles.
        body_font: CSS-style font stack for body text.
    """

    background: str
    accent: str
    text: str
    muted: str
    shape_fill: str
    heading_font: str
    body_font: str


# Five curated themes. ``corporate-blue`` reproduces the palette the ODP/ODG
# generators used before themes existed, now also available to ODT and ODS.
THEMES: dict[str, Theme] = {
    "corporate-blue": Theme(
        background="#FFFFFF",
        accent="#02416C",
        text="#1A1A1A",
        muted="#5A6B7B",
        shape_fill="#DCE6F0",
        heading_font="'Carlito', 'Liberation Sans', sans-serif",
        body_font="'Liberation Sans', sans-serif",
    ),
    "warm-editorial": Theme(
        background="#FBF7F0",
        accent="#7A3B2E",
        text="#2B2420",
        muted="#8A7B6B",
        shape_fill="#EFE3D4",
        heading_font="'Caladea', 'Liberation Serif', serif",
        body_font="'Caladea', 'Liberation Serif', serif",
    ),
    "high-contrast": Theme(
        background="#FFFFFF",
        accent="#000000",
        text="#000000",
        muted="#333333",
        shape_fill="#E0E0E0",
        heading_font="'Liberation Sans', sans-serif",
        body_font="'Liberation Sans', sans-serif",
    ),
    "slate-mono": Theme(
        background="#F4F5F7",
        accent="#2F3E4E",
        text="#1C2530",
        muted="#6B7785",
        shape_fill="#DDE2E8",
        heading_font="'Liberation Mono', monospace",
        body_font="'Liberation Sans', sans-serif",
    ),
    "forest": Theme(
        background="#F7F9F5",
        accent="#1F5130",
        text="#1E2A20",
        muted="#5E6F60",
        shape_fill="#DCE8DC",
        heading_font="'Carlito', 'Liberation Sans', sans-serif",
        body_font="'Caladea', 'Liberation Serif', serif",
    ),
}

# The ODF style:font-name values a themed document references.
HEADING_FACE = "theme-heading"
BODY_FACE = "theme-body"

_GENERIC = {"sans-serif": "swiss", "serif": "roman", "monospace": "modern"}


def get_theme(name: str) -> Theme:
    """Return the named theme, or exit with the list of valid names."""
    theme = THEMES.get(name)
    if theme is None:
        raise SystemExit(f"unknown theme {name!r}; choose from {sorted(THEMES)}")
    return theme


def _generic(font_stack: str) -> str:
    """Derive the ODF style:font-family-generic from a CSS font stack."""
    last = font_stack.rsplit(",", 1)[-1].strip().strip("'\"").lower()
    return _GENERIC.get(last, "swiss")


def theme_font_faces(theme: Theme) -> list[tuple[str, str, str]]:
    """Return the font faces a themed document declares.

    Each entry is ``(face_name, font_family, family_generic)`` — the inputs for
    one ODF ``style:font-face`` element. Generators build the element with their
    own ``q``; this keeps the module XML-free.
    """
    return [
        (HEADING_FACE, theme.heading_font, _generic(theme.heading_font)),
        (BODY_FACE, theme.body_font, _generic(theme.body_font)),
    ]
