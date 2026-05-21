#!/usr/bin/env python3
"""Create a minimal ODP file from a JSON slide specification."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from odp_common import ODP_MIMETYPE, ensure_manifest_entry, media_type_for, pack_dir_as_odp, q, unique_picture_name


def text_frame(
    parent: ET.Element, name: str, x: str, y: str,
    width: str, height: str, style: str, lines: list[str],
) -> None:
    """Add a draw:frame with draw:text-box containing styled paragraphs."""
    frame = ET.SubElement(
        parent,
        q("draw", "frame"),
        {
            q("draw", "name"): name,
            q("svg", "x"): x,
            q("svg", "y"): y,
            q("svg", "width"): width,
            q("svg", "height"): height,
        },
    )
    box = ET.SubElement(frame, q("draw", "text-box"))
    for line in lines:
        paragraph = ET.SubElement(box, q("text", "p"), {q("text", "style-name"): style})
        paragraph.text = line


def image_frame(
    parent: ET.Element, href: str, x: str, y: str,
    width: str, height: str,
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


def build_styles() -> ET.Element:
    """Build office:document-styles with Title/Body/Notes styles and Screen page layout."""
    root = ET.Element(q("office", "document-styles"), {q("office", "version"): "1.3"})
    styles = ET.SubElement(root, q("office", "styles"))
    for name, size, weight in [("Title", "32pt", "bold"), ("Body", "18pt", "normal"), ("Notes", "12pt", "normal")]:
        style = ET.SubElement(styles, q("style", "style"), {q("style", "name"): name, q("style", "family"): "paragraph"})
        ET.SubElement(style, q("style", "text-properties"), {q("fo", "font-size"): size, q("fo", "font-weight"): weight})
    master_styles = ET.SubElement(root, q("office", "master-styles"))
    ET.SubElement(master_styles, q("style", "master-page"), {q("style", "name"): "Default", q("style", "page-layout-name"): "Screen"})
    automatic = ET.SubElement(root, q("office", "automatic-styles"))
    layout = ET.SubElement(automatic, q("style", "page-layout"), {q("style", "name"): "Screen"})
    ET.SubElement(layout, q("style", "page-layout-properties"), {q("fo", "page-width"): "28cm", q("fo", "page-height"): "15.75cm", q("style", "print-orientation"): "landscape"})
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
            page = ET.SubElement(
                presentation,
                q("draw", "page"),
                {
                    q("draw", "name"): slide.get("name", f"Slide {index}"),
                    q("draw", "master-page-name"): slide.get("master_page", "Default"),
                },
            )
            title = slide.get("title")
            if title:
                text_frame(page, "Title", "1cm", "0.8cm", "26cm", "2cm", "Title", [str(title)])
            body_lines = slide.get("body", [])
            if isinstance(body_lines, str):
                body_lines = [body_lines]
            if body_lines:
                text_frame(page, "Body", "1.4cm", "3.2cm", "25cm", "8cm", "Body", [str(line) for line in body_lines])
            image = slide.get("image")
            if image:
                source = Path(image)
                package_path = unique_picture_name(existing_media, source)
                existing_media.add(package_path)
                target = root_dir / package_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                manifest_entries.append((package_path, media_type_for(source)))
                image_frame(page, package_path, slide.get("image_x", "15cm"), slide.get("image_y", "3cm"), slide.get("image_width", "11cm"), slide.get("image_height", "8cm"))
            notes = slide.get("notes", [])
            if isinstance(notes, str):
                notes = [notes]
            if notes:
                notes_el = ET.SubElement(page, q("presentation", "notes"))
                text_frame(notes_el, "Notes", "1cm", "1cm", "24cm", "10cm", "Notes", [str(line) for line in notes])

        ET.ElementTree(content).write(root_dir / "content.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_styles()).write(root_dir / "styles.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_meta(spec.get("title"))).write(root_dir / "meta.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_settings()).write(root_dir / "settings.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_manifest(manifest_entries)).write(root_dir / "META-INF" / "manifest.xml", encoding="utf-8", xml_declaration=True)
        pack_dir_as_odp(root_dir, args.output_odp)
    print(args.output_odp)


if __name__ == "__main__":
    main()
