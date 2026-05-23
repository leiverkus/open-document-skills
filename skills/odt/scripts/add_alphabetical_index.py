#!/usr/bin/env python3
"""Insert a ``text:alphabetical-index`` placeholder into an existing ODT.

Pairs with ``add_index_mark.py``: this script wraps the container + source
configuration + an empty ``text:index-body``. The index entries come from
``text:alphabetical-index-mark`` markers scattered through the document body —
LibreOffice scans them when refreshing the index.

Position (exactly one):
- ``--anchor TEXT``     — after the block containing TEXT
- ``--paragraph N``     — after the Nth top-level block
- ``--at start|end``    — at the body start or end
"""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

from _block_position import resolve_insert_index
from odt_common import (
    NS,
    build_index_body_placeholder,
    parse_xml_from_zip,
    q,
    update_meta_for_edit,
    write_odt_with_replacements,
    xml_bytes,
)


def build_alphabetical_index(name: str, title: str) -> ET.Element:
    """Construct a ``text:alphabetical-index`` element with source + empty body."""
    elem = ET.Element(q("text", "alphabetical-index"))
    elem.set(q("text", "style-name"), "Sect1")
    elem.set(q("text", "name"), name)
    elem.set(q("text", "protected"), "true")

    source = ET.SubElement(elem, q("text", "alphabetical-index-source"))
    title_tmpl = ET.SubElement(source, q("text", "index-title-template"))
    title_tmpl.set(q("text", "style-name"), "Index_20_Heading")
    title_tmpl.text = title

    ent = ET.SubElement(source, q("text", "alphabetical-index-entry-template"))
    ent.set(q("text", "outline-level"), "1")
    ent.set(q("text", "style-name"), "Index_20_1")
    ET.SubElement(ent, q("text", "index-entry-text"))
    tab = ET.SubElement(ent, q("text", "index-entry-tab-stop"))
    tab.set(q("style", "type"), "right")
    tab.set(q("style", "leader-char"), ".")
    ET.SubElement(ent, q("text", "index-entry-page-number"))

    body = build_index_body_placeholder(title, name, title_paragraph_style="Index_20_Heading")
    elem.append(body)
    return elem


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--title", default="Index", help="title text (default: %(default)r)")
    parser.add_argument("--name", default="Alphabetical Index1", help="text:name (default: %(default)r)")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--anchor", help="insert after the block containing this text")
    where.add_argument("--paragraph", type=int, help="insert after the Nth top-level block (1-based)")
    where.add_argument("--at", choices=["start", "end"], help="insert at the body start or end")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")

    elem = build_alphabetical_index(args.name, args.title)
    index = resolve_insert_index(
        body,
        anchor=args.anchor,
        paragraph=args.paragraph,
        at=args.at,
        kind_label="alphabetical index",
    )
    if index is None:
        write_odt_with_replacements(args.input_odt, args.output, {})
        return
    body.insert(index, elem)

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print(args.name)


if __name__ == "__main__":
    main()
