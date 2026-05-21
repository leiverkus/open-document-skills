#!/usr/bin/env python3
"""Customize an ODP master page: background, header, footer, page numbers, logo.

Operates on styles.xml's <style:master-page> elements. Two modes:
- Mutate in place: pass --master NAME with one or more property flags.
- Clone first: pass --clone-to NEW_NAME plus the property flags; the
  cloned master is then customized.
"""

from __future__ import annotations

import argparse
import copy
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from odp_common import (
    copy_into_package,
    ensure_manifest_entry,
    parse_xml_from_zip,
    q,
    unique_picture_name,
    update_meta_for_edit,
    write_odp_with_replacements,
    xml_bytes,
)


def find_master(styles_root: ET.Element, name: str) -> ET.Element | None:
    for master in styles_root.iter(q("style", "master-page")):
        if master.attrib.get(q("style", "name")) == name:
            return master
    return None


def find_or_create_drawing_page_properties(master: ET.Element) -> ET.Element:
    """Resolve the master's drawing-page-properties via its page-layout."""
    # ODF master-page's background is normally set on its style:page-layout's
    # style:drawing-page-properties. For simplicity, attach properties directly
    # under the master and let LibreOffice honour them.
    props = master.find(q("style", "drawing-page-properties"))
    if props is None:
        props = ET.SubElement(master, q("style", "drawing-page-properties"))
    return props


def apply_background(props: ET.Element, color: str | None, image_path: str | None, fill: str) -> None:
    if color:
        props.set(q("draw", "fill"), "solid")
        props.set(q("draw", "fill-color"), color)
    if image_path:
        props.set(q("draw", "fill"), "bitmap")
        props.set(q("draw", "fill-image-name"), image_path)
        props.set(q("style", "repeat"), fill)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odp", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--master", required=True, help="master-page name to customize")
    parser.add_argument("--clone-to", help="if set, clone the master under this new name first")
    parser.add_argument("--background-color", help="hex color, e.g. #02416C")
    parser.add_argument("--background-image", type=Path, help="local image path to embed")
    parser.add_argument("--background-fill", choices=["bitmap", "tile", "stretch"], default="stretch")
    parser.add_argument("--header", help="header text")
    parser.add_argument("--footer-text", help="footer text")
    parser.add_argument("--page-numbers", choices=["true", "false"], help="visibility of page numbers")
    parser.add_argument("--logo", type=Path, help="logo image path (embedded into Pictures/)")
    args = parser.parse_args()

    styles = parse_xml_from_zip(args.input_odp, "styles.xml")
    master_styles = styles.find(q("office", "master-styles"))
    if master_styles is None:
        raise SystemExit("office:master-styles not found in styles.xml")

    master = find_master(styles, args.master)
    if master is None:
        raise SystemExit(f"master-page {args.master!r} not found")

    if args.clone_to:
        clone = copy.deepcopy(master)
        clone.set(q("style", "name"), args.clone_to)
        master_styles.append(clone)
        target = clone
    else:
        target = master

    # Embed background image / logo into Pictures/ if provided
    new_picture_path: str | None = None
    new_logo_path: str | None = None
    embed_source: Path | None = None
    if args.background_image:
        with zipfile.ZipFile(args.input_odp) as archive:
            existing = set(archive.namelist())
        new_picture_path = unique_picture_name(existing, args.background_image)
        embed_source = args.background_image
    if args.logo:
        with zipfile.ZipFile(args.input_odp) as archive:
            existing = set(archive.namelist())
        new_logo_path = unique_picture_name(existing, args.logo)

    # Apply background
    if args.background_color or new_picture_path:
        props = find_or_create_drawing_page_properties(target)
        apply_background(props, args.background_color, new_picture_path, args.background_fill)

    # Header / footer / page numbers / logo as draw:frame children of master
    if args.header:
        frame = ET.SubElement(
            target,
            q("draw", "frame"),
            {q("presentation", "class"): "header", q("draw", "name"): "Header"},
        )
        text_box = ET.SubElement(frame, q("draw", "text-box"))
        p = ET.SubElement(text_box, q("text", "p"))
        p.text = args.header
    if args.footer_text:
        frame = ET.SubElement(
            target,
            q("draw", "frame"),
            {q("presentation", "class"): "footer", q("draw", "name"): "Footer"},
        )
        text_box = ET.SubElement(frame, q("draw", "text-box"))
        p = ET.SubElement(text_box, q("text", "p"))
        p.text = args.footer_text
    if args.page_numbers == "true":
        frame = ET.SubElement(
            target,
            q("draw", "frame"),
            {q("presentation", "class"): "page-number", q("draw", "name"): "PageNumber"},
        )
        text_box = ET.SubElement(frame, q("draw", "text-box"))
        p = ET.SubElement(text_box, q("text", "p"))
        ET.SubElement(p, q("text", "page-number"))
    if new_logo_path:
        frame = ET.SubElement(
            target,
            q("draw", "frame"),
            {
                q("draw", "name"): "Logo",
                q("svg", "width"): "3cm",
                q("svg", "height"): "1.2cm",
                q("svg", "x"): "0.5cm",
                q("svg", "y"): "0.5cm",
            },
        )
        ET.SubElement(
            frame,
            q("draw", "image"),
            {
                q("xlink", "href"): new_logo_path,
                q("xlink", "type"): "simple",
                q("xlink", "show"): "embed",
                q("xlink", "actuate"): "onLoad",
            },
        )

    manifest = parse_xml_from_zip(args.input_odp, "META-INF/manifest.xml")
    if new_picture_path:
        ensure_manifest_entry(manifest, new_picture_path, "image/png")
    if new_logo_path:
        ensure_manifest_entry(manifest, new_logo_path, "image/png")

    meta = parse_xml_from_zip(args.input_odp, "meta.xml")
    update_meta_for_edit(meta)

    replacements = {
        "styles.xml": xml_bytes(styles),
        "meta.xml": xml_bytes(meta),
        "META-INF/manifest.xml": xml_bytes(manifest),
    }

    if new_picture_path and embed_source:
        copy_into_package(args.input_odp, args.output, new_picture_path, embed_source, replacements)
    elif new_logo_path and args.logo:
        copy_into_package(args.input_odp, args.output, new_logo_path, args.logo, replacements)
    else:
        write_odp_with_replacements(args.input_odp, args.output, replacements)

    print(args.clone_to or args.master)


if __name__ == "__main__":
    main()
