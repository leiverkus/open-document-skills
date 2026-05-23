#!/usr/bin/env python3
"""Insert a ``text:bibliography`` placeholder into an existing ODT.

The container holds a ``text:bibliography-source`` (configuration) and an empty
``text:index-body`` (the rendered bibliography list). LibreOffice fills the
body when ``update_indexes.py`` opens the document — until then opening it in
the GUI and pressing F9 will refresh it.

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

# ODF bibliography-type values; we configure entry templates for the common ones.
# LibreOffice falls back gracefully for unspecified types.
_BIB_TYPES = (
    "article",
    "book",
    "booklet",
    "conference",
    "incollection",
    "inproceedings",
    "manual",
    "mastersthesis",
    "misc",
    "phdthesis",
    "proceedings",
    "techreport",
    "unpublished",
)


def build_bibliography(name: str, title: str) -> ET.Element:
    """Construct a ``text:bibliography`` element with source + empty body."""
    bib = ET.Element(q("text", "bibliography"))
    bib.set(q("text", "style-name"), "Sect1")
    bib.set(q("text", "name"), name)
    bib.set(q("text", "protected"), "true")

    source = ET.SubElement(bib, q("text", "bibliography-source"))
    title_tmpl = ET.SubElement(source, q("text", "index-title-template"))
    title_tmpl.set(q("text", "style-name"), "Bibliography_20_Heading")
    title_tmpl.text = title

    for bt in _BIB_TYPES:
        ent = ET.SubElement(source, q("text", "bibliography-entry-template"))
        ent.set(q("text", "bibliography-type"), bt)
        ent.set(q("text", "style-name"), "Bibliography_20_1")
        # A minimal entry template: identifier, then author/title/year separated.
        # LibreOffice uses richer defaults; this is a sane placeholder.
        sp = ET.SubElement(ent, q("text", "index-entry-bibliography"))
        sp.set(q("text", "bibliography-data-field"), "identifier")

    body = build_index_body_placeholder(title, name, title_paragraph_style="Bibliography_20_Heading")
    bib.append(body)
    return bib


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--title", default="Bibliography", help="title text (default: %(default)r)")
    parser.add_argument("--name", default="Bibliography1", help="text:name for the bibliography (default: %(default)r)")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--anchor", help="insert after the block containing this text")
    where.add_argument("--paragraph", type=int, help="insert after the Nth top-level block (1-based)")
    where.add_argument("--at", choices=["start", "end"], help="insert at the body start or end")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")

    bib = build_bibliography(args.name, args.title)
    index = resolve_insert_index(
        body,
        anchor=args.anchor,
        paragraph=args.paragraph,
        at=args.at,
        kind_label="bibliography",
    )
    if index is None:
        write_odt_with_replacements(args.input_odt, args.output, {})
        return
    body.insert(index, bib)

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
