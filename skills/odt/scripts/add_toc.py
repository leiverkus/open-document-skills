#!/usr/bin/env python3
"""Insert a ``text:table-of-content`` placeholder into an existing ODT.

The element ships in two halves:

- ``text:table-of-content-source`` — configuration (max outline level, entry
  templates, title style). LibreOffice reads this when refreshing.
- ``text:index-body`` — the *rendered* TOC. We insert a placeholder containing
  only the title paragraph; the entries are filled in by LibreOffice when
  ``update_indexes.py`` opens the document and dispatches an index refresh
  (or when the user presses F9 in the GUI).

Position (exactly one):
- ``--anchor TEXT``     — after the block containing TEXT
- ``--paragraph N``     — after the Nth top-level block
- ``--at start|end``    — at the body start or end (start = before any block)
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


def build_toc(name: str, title: str, outline_level: int) -> ET.Element:
    """Construct a ``text:table-of-content`` element with source + empty body."""
    toc = ET.Element(q("text", "table-of-content"))
    toc.set(q("text", "style-name"), "Sect1")
    toc.set(q("text", "name"), name)
    toc.set(q("text", "protected"), "true")

    source = ET.SubElement(toc, q("text", "table-of-content-source"))
    source.set(q("text", "outline-level"), str(outline_level))
    source.set(q("text", "use-outline-level"), "true")

    title_tmpl = ET.SubElement(source, q("text", "index-title-template"))
    title_tmpl.set(q("text", "style-name"), "Contents_20_Heading")
    title_tmpl.text = title

    for lvl in range(1, outline_level + 1):
        ent = ET.SubElement(source, q("text", "table-of-content-entry-template"))
        ent.set(q("text", "outline-level"), str(lvl))
        ent.set(q("text", "style-name"), f"Contents_20_{lvl}")
        ET.SubElement(ent, q("text", "index-entry-chapter"))
        ET.SubElement(ent, q("text", "index-entry-text"))
        tab = ET.SubElement(ent, q("text", "index-entry-tab-stop"))
        tab.set(q("style", "type"), "right")
        tab.set(q("style", "leader-char"), ".")
        ET.SubElement(ent, q("text", "index-entry-page-number"))

    body = build_index_body_placeholder(title, name)
    toc.append(body)
    return toc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--title", default="Table of Contents", help="title text (default: %(default)r)")
    parser.add_argument("--levels", type=int, default=3, help="max outline level included (default: 3)")
    parser.add_argument("--name", default="Table of Contents1", help="text:name for the TOC (default: %(default)r)")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--anchor", help="insert after the block containing this text")
    where.add_argument("--paragraph", type=int, help="insert after the Nth top-level block (1-based)")
    where.add_argument("--at", choices=["start", "end"], help="insert at the body start or end")
    args = parser.parse_args()

    if args.levels < 1 or args.levels > 10:
        raise SystemExit("--levels must be between 1 and 10")

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")

    toc = build_toc(args.name, args.title, args.levels)

    index = resolve_insert_index(
        body,
        anchor=args.anchor,
        paragraph=args.paragraph,
        at=args.at,
        kind_label="TOC",
    )
    if index is None:
        write_odt_with_replacements(args.input_odt, args.output, {})
        return
    body.insert(index, toc)

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
