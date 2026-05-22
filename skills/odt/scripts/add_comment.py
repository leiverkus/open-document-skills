#!/usr/bin/env python3
"""Insert an office:annotation (comment) into an ODT.

Modes:
- Point:  --anchor TEXT  (or --paragraph N) — a single office:annotation.
- Range:  --start-anchor START --end-anchor END — a matched
          office:annotation / office:annotation-end pair.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from odt_common import (
    NS,
    find_text_position_in_element,
    insert_after_text_in_element,
    insert_in_paragraph,
    parse_xml_from_zip,
    q,
    update_meta_for_edit,
    wrap_text_across_elements,
    wrap_text_with_pair_in_element,
    write_odt_with_replacements,
    xml_bytes,
)


def find_paragraphs(content_root: ET.Element) -> list[ET.Element]:
    body = content_root.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")
    return [n for n in body.iter() if n.tag in {q("text", "p"), q("text", "h")}]


def unique_comment_name(content_root: ET.Element) -> str:
    """Return cmt1/cmt2/... not already used by an office:annotation."""
    used = {a.attrib.get(q("office", "name")) for a in content_root.iter(q("office", "annotation"))}
    n = 1
    while f"cmt{n}" in used:
        n += 1
    return f"cmt{n}"


def build_annotation(name: str, author: str, date: str, text: str) -> ET.Element:
    """Build an office:annotation with creator, date, and a text body."""
    annotation = ET.Element(q("office", "annotation"), {q("office", "name"): name})
    creator = ET.SubElement(annotation, q("dc", "creator"))
    creator.text = author
    date_el = ET.SubElement(annotation, q("dc", "date"))
    date_el.text = date
    for line in text.split("\n"):
        paragraph = ET.SubElement(annotation, q("text", "p"))
        paragraph.text = line
    return annotation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--author", required=True, help="comment author (dc:creator)")
    parser.add_argument("--text", required=True, help="comment body (\\n splits paragraphs)")
    parser.add_argument("--date", help="ISO date (default: now, UTC)")
    parser.add_argument("--name", help="annotation name (default: auto cmtN)")
    parser.add_argument("--anchor", help="text substring; point comment after first match")
    parser.add_argument("--paragraph", type=int, help="1-based paragraph index for a point comment")
    parser.add_argument(
        "--position", choices=["start", "end"], default="end", help="position within --paragraph (default: end)"
    )
    parser.add_argument("--start-anchor", help="(with --end-anchor) range start substring")
    parser.add_argument("--end-anchor", help="(with --start-anchor) range end substring")
    args = parser.parse_args()

    if (args.start_anchor is None) != (args.end_anchor is None):
        raise SystemExit("--start-anchor and --end-anchor must be given together")
    modes = sum([args.start_anchor is not None, args.anchor is not None, args.paragraph is not None])
    if modes != 1:
        raise SystemExit("provide exactly one of: --anchor / --paragraph / (--start-anchor + --end-anchor)")

    date = args.date or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    content = parse_xml_from_zip(args.input_odt, "content.xml")
    paragraphs = find_paragraphs(content)
    name = args.name or unique_comment_name(content)

    inserted = False

    if args.start_anchor is not None:
        for paragraph in paragraphs:
            start = build_annotation(name, args.author, date, args.text)
            end = ET.Element(q("office", "annotation-end"), {q("office", "name"): name})
            if wrap_text_with_pair_in_element(paragraph, args.start_anchor, args.end_anchor, start, end):
                inserted = True
                break
        if not inserted:
            start = build_annotation(name, args.author, date, args.text)
            end = ET.Element(q("office", "annotation-end"), {q("office", "name"): name})
            if wrap_text_across_elements(paragraphs, args.start_anchor, args.end_anchor, start, end):
                inserted = True
    elif args.anchor is not None:
        for paragraph in paragraphs:
            if find_text_position_in_element(paragraph, args.anchor) is None:
                continue
            if insert_after_text_in_element(
                paragraph, args.anchor, build_annotation(name, args.author, date, args.text)
            ):
                inserted = True
                break
    else:
        idx = args.paragraph
        if idx < 1 or idx > len(paragraphs):
            raise SystemExit(f"paragraph index out of range: {idx} (have {len(paragraphs)})")
        insert_in_paragraph(paragraphs[idx - 1], args.position, build_annotation(name, args.author, date, args.text))
        inserted = True

    if not inserted:
        print("warning: anchor not found, no comment inserted", file=sys.stderr)
        write_odt_with_replacements(args.input_odt, args.output, {})
        return

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
