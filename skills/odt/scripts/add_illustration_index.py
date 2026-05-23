#!/usr/bin/env python3
"""Insert a ``text:illustration-index`` (or table-index) placeholder.

``--sequence Figure`` produces an Abbildungsverzeichnis (illustration index).
``--sequence Table`` produces a table index. Other sequence names are also
accepted — the script wraps the right element either way:

- ``Figure`` / ``Illustration``  → ``text:illustration-index``
- ``Table``                      → ``text:table-index``
- anything else                  → ``text:illustration-index`` (with the given
  caption-sequence-name)

LibreOffice fills the index body during refresh based on ``text:sequence``
elements whose ``text:name`` matches the caption-sequence-name. Until then
the body holds only a title placeholder.

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


def _container_tag(sequence: str) -> str:
    if sequence.lower() in {"table"}:
        return q("text", "table-index")
    return q("text", "illustration-index")


def _source_tag(container_tag: str) -> str:
    return (
        q("text", "table-index-source")
        if container_tag == q("text", "table-index")
        else q("text", "illustration-index-source")
    )


def build_illustration_index(name: str, title: str, sequence: str) -> ET.Element:
    container_tag = _container_tag(sequence)
    source_tag = _source_tag(container_tag)

    elem = ET.Element(container_tag)
    elem.set(q("text", "style-name"), "Sect1")
    elem.set(q("text", "name"), name)
    elem.set(q("text", "protected"), "true")

    source = ET.SubElement(elem, source_tag)
    source.set(q("text", "caption-sequence-name"), sequence)
    source.set(q("text", "caption-sequence-format"), "category-and-value")

    title_tmpl = ET.SubElement(source, q("text", "index-title-template"))
    title_tmpl.set(q("text", "style-name"), "Illustration_20_Index_20_Heading")
    title_tmpl.text = title

    entry_tag = (
        q("text", "table-index-entry-template")
        if container_tag == q("text", "table-index")
        else q("text", "illustration-index-entry-template")
    )
    ent = ET.SubElement(source, entry_tag)
    ent.set(q("text", "style-name"), "Illustration_20_Index_20_1")
    ET.SubElement(ent, q("text", "index-entry-text"))
    tab = ET.SubElement(ent, q("text", "index-entry-tab-stop"))
    tab.set(q("style", "type"), "right")
    tab.set(q("style", "leader-char"), ".")
    ET.SubElement(ent, q("text", "index-entry-page-number"))

    body = build_index_body_placeholder(title, name, title_paragraph_style="Illustration_20_Index_20_Heading")
    elem.append(body)
    return elem


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--sequence",
        default="Figure",
        help="caption-sequence-name to index (Figure, Table, Equation, …; default: %(default)r)",
    )
    parser.add_argument("--title", help="title text (default depends on --sequence)")
    parser.add_argument("--name", help="text:name (default: derived from --sequence)")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--anchor", help="insert after the block containing this text")
    where.add_argument("--paragraph", type=int, help="insert after the Nth top-level block (1-based)")
    where.add_argument("--at", choices=["start", "end"], help="insert at the body start or end")
    args = parser.parse_args()

    default_titles = {
        "Figure": "List of Figures",
        "Illustration": "List of Illustrations",
        "Table": "List of Tables",
        "Equation": "List of Equations",
    }
    title = args.title or default_titles.get(args.sequence, f"List of {args.sequence}s")
    name = args.name or f"{args.sequence} Index1"

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")

    elem = build_illustration_index(name, title, args.sequence)
    index = resolve_insert_index(
        body,
        anchor=args.anchor,
        paragraph=args.paragraph,
        at=args.at,
        kind_label="illustration index",
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
    print(name)


if __name__ == "__main__":
    main()
