#!/usr/bin/env python3
"""Create a minimal ODP file from a JSON slide specification."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from odp_common import ODP_MIMETYPE, ensure_manifest_entry, media_type_for, pack_dir_as_odp, q, unique_picture_name
from odp_layouts import (
    DEFAULT_LAYOUT,
    GRAPHIC_STYLE,
    LAYOUT_STYLE_NAMES,
    LAYOUTS,
    PARAGRAPH_STYLE,
    build_presentation_page_layout,
    frame_name,
)

# Content spec keys that fill layout placeholder zones.
SLOT_KEYS = {"title", "subtitle", "body", "body_left", "body_right"}


def text_frame(
    parent: ET.Element,
    name: str,
    x: str,
    y: str,
    width: str,
    height: str,
    style: str,
    lines: list[str],
    frame_style: str,
    presentation_class: str | None = None,
) -> None:
    """Add a draw:frame with draw:text-box containing styled paragraphs.

    *frame_style* names a ``style:family="graphic"`` style — without it the
    frame inherits LibreOffice's default fill and renders as a blue box.
    *presentation_class*, when given, tags the frame as a layout placeholder
    (``presentation:class``).
    """
    attribs = {
        q("draw", "name"): name,
        q("draw", "style-name"): frame_style,
        q("draw", "layer"): "layout",
        q("svg", "x"): x,
        q("svg", "y"): y,
        q("svg", "width"): width,
        q("svg", "height"): height,
    }
    if presentation_class:
        attribs[q("presentation", "class")] = presentation_class
    frame = ET.SubElement(parent, q("draw", "frame"), attribs)
    box = ET.SubElement(frame, q("draw", "text-box"))
    for line in lines:
        paragraph = ET.SubElement(box, q("text", "p"), {q("text", "style-name"): style})
        paragraph.text = line


def image_frame(
    parent: ET.Element,
    href: str,
    x: str,
    y: str,
    width: str,
    height: str,
) -> None:
    """Add a draw:frame with embedded draw:image at the given position."""
    frame = ET.SubElement(
        parent,
        q("draw", "frame"),
        {
            q("draw", "name"): "Image",
            q("svg", "x"): x,
            q("svg", "y"): y,
            q("svg", "width"): width,
            q("svg", "height"): height,
        },
    )
    frame.set(q("draw", "style-name"), "gr-image")
    frame.set(q("draw", "layer"), "layout")
    ET.SubElement(
        frame,
        q("draw", "image"),
        {
            q("xlink", "href"): href,
            q("xlink", "type"): "simple",
            q("xlink", "show"): "embed",
            q("xlink", "actuate"): "onLoad",
        },
    )


# Default presentation theme — light background, accent-blue title, dark body.
BACKGROUND_COLOR = "#FFFFFF"
TITLE_COLOR = "#02416C"
BODY_COLOR = "#1A1A1A"
NOTES_COLOR = "#000000"


def _graphic_style(
    styles: ET.Element,
    name: str,
    vertical_align: str,
    size: str | None = None,
    weight: str | None = None,
    color: str | None = None,
) -> ET.Element:
    """Append a no-fill, no-stroke graphic style and return it.

    A styleless draw:frame inherits LibreOffice's default ``standard`` graphic
    style (a solid #729fcf fill) and renders as a blue box. Every generated
    frame references one of these instead.

    The graphic style also carries the ``style:text-properties`` that style the
    text inside the frame — slide text is styled through the frame's graphic
    style, not through a paragraph ``text:style-name``.
    """
    style = ET.SubElement(
        styles,
        q("style", "style"),
        {q("style", "name"): name, q("style", "family"): "graphic"},
    )
    ET.SubElement(
        style,
        q("style", "graphic-properties"),
        {
            q("draw", "fill"): "none",
            q("draw", "stroke"): "none",
            q("draw", "textarea-vertical-align"): vertical_align,
            q("draw", "auto-grow-height"): "false",
            q("draw", "auto-grow-width"): "false",
        },
    )
    if size or color:
        text_props: dict[str, str] = {}
        if size:
            text_props[q("fo", "font-size")] = size
        if weight:
            text_props[q("fo", "font-weight")] = weight
        if color:
            text_props[q("fo", "color")] = color
        ET.SubElement(style, q("style", "text-properties"), text_props)
    return style


def _paragraph_style(styles: ET.Element, name: str, size: str, weight: str, color: str) -> None:
    """Append a paragraph style carrying an explicit text colour."""
    style = ET.SubElement(styles, q("style", "style"), {q("style", "name"): name, q("style", "family"): "paragraph"})
    if name == "Body":
        ET.SubElement(style, q("style", "paragraph-properties"), {q("fo", "margin-bottom"): "0.35cm"})
    ET.SubElement(
        style,
        q("style", "text-properties"),
        {q("fo", "font-size"): size, q("fo", "font-weight"): weight, q("fo", "color"): color},
    )


def build_styles(masters: list[dict[str, Any]] | None = None) -> ET.Element:
    """Build office:document-styles with a designed default presentation theme.

    Emits a ``drawing-page`` background style (referenced by the master page),
    ``graphic`` frame styles that suppress the default fill, the paragraph
    styles Title/Body/Notes, and a ``style:presentation-page-layout`` per named
    layout. Names stay stable so injected branded styles and customize_master
    keep working.

    *masters* is an optional list of extra master pages, each a dict with a
    ``name`` and optional ``background_color``. The built-in ``Default`` master
    is always present.
    """
    root = ET.Element(q("office", "document-styles"), {q("office", "version"): "1.3"})

    # office:styles — common named styles.
    styles = ET.SubElement(root, q("office", "styles"))

    # Graphic styles — no blue box; the title block is vertically centred.
    # Their text-properties style the text inside each frame.
    _graphic_style(styles, "gr-title", "middle", "40pt", "bold", TITLE_COLOR)
    _graphic_style(styles, "gr-body", "top", "20pt", "normal", BODY_COLOR)
    _graphic_style(styles, "gr-notes", "top", "12pt", "normal", NOTES_COLOR)
    _graphic_style(styles, "gr-image", "middle")

    # Paragraph styles — colours double as a second guarantee of text colour.
    _paragraph_style(styles, "Title", "40pt", "bold", TITLE_COLOR)
    _paragraph_style(styles, "Body", "20pt", "normal", BODY_COLOR)
    _paragraph_style(styles, "Notes", "12pt", "normal", NOTES_COLOR)

    # Slide layouts — one style:presentation-page-layout per named layout.
    for layout_name in LAYOUTS:
        styles.append(build_presentation_page_layout(layout_name))

    # office:automatic-styles — page layout + the drawing-page background
    # style. A master page's drawing-page style must live here (not in
    # office:styles) for LibreOffice to render the slide background.
    automatic = ET.SubElement(root, q("office", "automatic-styles"))
    layout = ET.SubElement(automatic, q("style", "page-layout"), {q("style", "name"): "Screen"})
    ET.SubElement(
        layout,
        q("style", "page-layout-properties"),
        {
            q("fo", "page-width"): "28cm",
            q("fo", "page-height"): "15.75cm",
            q("style", "print-orientation"): "landscape",
        },
    )

    def drawing_page_style(name: str, color: str) -> None:
        style = ET.SubElement(
            automatic,
            q("style", "style"),
            {q("style", "name"): name, q("style", "family"): "drawing-page"},
        )
        ET.SubElement(
            style,
            q("style", "drawing-page-properties"),
            {q("draw", "fill"): "solid", q("draw", "fill-color"): color},
        )

    drawing_page_style("dp-default", BACKGROUND_COLOR)
    for spec in masters or []:
        name = spec.get("name")
        if not name or name == "Default":
            raise SystemExit(f"master {name!r}: each extra master needs a unique name other than 'Default'")
        drawing_page_style(f"dp-{name}", spec.get("background_color", BACKGROUND_COLOR))

    # office:master-styles — each master page references its background style.
    master_styles = ET.SubElement(root, q("office", "master-styles"))

    def master_page(name: str, drawing_page: str) -> None:
        ET.SubElement(
            master_styles,
            q("style", "master-page"),
            {
                q("style", "name"): name,
                q("style", "page-layout-name"): "Screen",
                q("draw", "style-name"): drawing_page,
            },
        )

    master_page("Default", "dp-default")
    for spec in masters or []:
        master_page(spec["name"], f"dp-{spec['name']}")
    return root


def build_manifest(entries: list[tuple[str, str]]) -> ET.Element:
    """Build manifest:manifest with root mimetype entry and one file-entry per *entries*."""
    root = ET.Element(q("manifest", "manifest"), {q("manifest", "version"): "1.3"})
    ensure_manifest_entry(root, "/", ODP_MIMETYPE)
    for full_path, media_type in entries:
        ensure_manifest_entry(root, full_path, media_type)
    return root


def build_meta(title: str | None) -> ET.Element:
    """Build office:document-meta with optional dc:title and current UTC creation-date."""
    root = ET.Element(q("office", "document-meta"), {q("office", "version"): "1.3"})
    meta = ET.SubElement(root, q("office", "meta"))
    if title:
        title_el = ET.SubElement(meta, q("dc", "title"))
        title_el.text = title
    created = ET.SubElement(meta, q("meta", "creation-date"))
    created.text = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return root


def build_settings() -> ET.Element:
    """Build office:document-settings with an empty office:settings element."""
    root = ET.Element(q("office", "document-settings"), {q("office", "version"): "1.3"})
    ET.SubElement(root, q("office", "settings"))
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="JSON spec with a slides array")
    parser.add_argument("output_odp", type=Path)
    args = parser.parse_args()

    if not args.spec.exists():
        raise SystemExit(f"Spec file not found: {args.spec}")
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {args.spec}: {exc}")
    slides = spec.get("slides", [])
    if not slides:
        raise SystemExit("Spec must contain a non-empty slides array")
    masters = spec.get("masters", [])
    known_masters = {"Default"} | {m.get("name") for m in masters}
    for index, slide in enumerate(slides, start=1):
        ref = slide.get("master") or slide.get("master_page", "Default")
        if ref not in known_masters:
            raise SystemExit(f"slide {index}: unknown master {ref!r}; defined masters: {sorted(known_masters)}")

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        (root_dir / "META-INF").mkdir()
        (root_dir / "Pictures").mkdir()
        (root_dir / "mimetype").write_text(ODP_MIMETYPE)

        content = ET.Element(q("office", "document-content"), {q("office", "version"): "1.3"})
        body = ET.SubElement(content, q("office", "body"))
        presentation = ET.SubElement(body, q("office", "presentation"))
        manifest_entries = [
            ("content.xml", "text/xml"),
            ("styles.xml", "text/xml"),
            ("meta.xml", "text/xml"),
            ("settings.xml", "text/xml"),
        ]
        existing_media: set[str] = set()

        for index, slide in enumerate(slides, start=1):
            layout_name = slide.get("layout", DEFAULT_LAYOUT)
            if layout_name not in LAYOUTS:
                raise SystemExit(f"slide {index}: unknown layout {layout_name!r}; choose from {sorted(LAYOUTS)}")
            page = ET.SubElement(
                presentation,
                q("draw", "page"),
                {
                    q("draw", "name"): slide.get("name", f"Slide {index}"),
                    q("draw", "master-page-name"): slide.get("master") or slide.get("master_page", "Default"),
                    q("presentation", "presentation-page-layout-name"): LAYOUT_STYLE_NAMES[layout_name],
                },
            )
            zones = LAYOUTS[layout_name]
            for zone in zones:
                value = slide.get(zone.spec_key)
                if value is None:
                    continue
                lines = [value] if isinstance(value, str) else list(value)
                if not lines:
                    continue
                text_frame(
                    page,
                    frame_name(zone.spec_key),
                    zone.x,
                    zone.y,
                    zone.width,
                    zone.height,
                    PARAGRAPH_STYLE[zone.cls],
                    [str(line) for line in lines],
                    GRAPHIC_STYLE[zone.cls],
                    presentation_class=zone.cls,
                )
            for key in sorted(SLOT_KEYS - {z.spec_key for z in zones}):
                if slide.get(key):
                    print(
                        f"warning: slide {index} layout {layout_name!r} has no zone for {key!r} — content dropped",
                        file=sys.stderr,
                    )
            image = slide.get("image")
            if image:
                source = Path(image)
                package_path = unique_picture_name(existing_media, source)
                existing_media.add(package_path)
                target = root_dir / package_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                manifest_entries.append((package_path, media_type_for(source)))
                image_frame(
                    page,
                    package_path,
                    slide.get("image_x", "15cm"),
                    slide.get("image_y", "3cm"),
                    slide.get("image_width", "11cm"),
                    slide.get("image_height", "8cm"),
                )
            notes = slide.get("notes", [])
            if isinstance(notes, str):
                notes = [notes]
            if notes:
                notes_el = ET.SubElement(page, q("presentation", "notes"))
                text_frame(
                    notes_el,
                    "Notes",
                    "1cm",
                    "1cm",
                    "24cm",
                    "10cm",
                    "Notes",
                    [str(line) for line in notes],
                    "gr-notes",
                )

        ET.ElementTree(content).write(root_dir / "content.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_styles(masters)).write(root_dir / "styles.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_meta(spec.get("title"))).write(
            root_dir / "meta.xml", encoding="utf-8", xml_declaration=True
        )
        ET.ElementTree(build_settings()).write(root_dir / "settings.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_manifest(manifest_entries)).write(
            root_dir / "META-INF" / "manifest.xml", encoding="utf-8", xml_declaration=True
        )
        pack_dir_as_odp(root_dir, args.output_odp)
    print(args.output_odp)


if __name__ == "__main__":
    main()
