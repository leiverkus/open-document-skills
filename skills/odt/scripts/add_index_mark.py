#!/usr/bin/env python3
"""Insert a ``text:alphabetical-index-mark`` point marker into an ODT.

Marks a position in the document text as an entry for the alphabetical index
(``add_alphabetical_index.py``). Each call sets one mark at the first anchor
match; call repeatedly for multiple entries.

Modes:
- ``--anchor TEXT``     — insert after the first occurrence of TEXT
- ``--paragraph N``     — insert at the end of the Nth paragraph
"""

from __future__ import annotations

import argparse
import sys
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
    write_odt_with_replacements,
    xml_bytes,
)


def find_paragraphs(content_root: ET.Element) -> list[ET.Element]:
    body = content_root.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")
    return [n for n in body.iter() if n.tag in {q("text", "p"), q("text", "h")}]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--key1", required=True, help="primary heading under which the entry appears")
    parser.add_argument("--key2", help="optional secondary heading nested under --key1")
    parser.add_argument("--string-value", help="text shown in the index (default: --key1)")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--anchor", help="text substring; insert after first match")
    where.add_argument("--paragraph", type=int, help="1-based paragraph index to insert into")
    parser.add_argument(
        "--position", choices=["start", "end"], default="end", help="position within --paragraph (default: end)"
    )
    args = parser.parse_args()

    string_value = args.string_value or args.key1

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    paragraphs = find_paragraphs(content)

    mark_attrs: dict[str, str] = {
        q("text", "key1"): args.key1,
        q("text", "string-value"): string_value,
    }
    if args.key2:
        mark_attrs[q("text", "key2")] = args.key2

    inserted = False
    if args.anchor is not None:
        for paragraph in paragraphs:
            if find_text_position_in_element(paragraph, args.anchor) is None:
                continue
            mark = ET.Element(q("text", "alphabetical-index-mark"), mark_attrs)
            if insert_after_text_in_element(paragraph, args.anchor, mark):
                inserted = True
                break
    else:
        idx = args.paragraph
        if idx is None or idx < 1 or idx > len(paragraphs):
            raise SystemExit(f"paragraph index out of range: {idx} (have {len(paragraphs)})")
        mark = ET.Element(q("text", "alphabetical-index-mark"), mark_attrs)
        insert_in_paragraph(paragraphs[idx - 1], args.position, mark)
        inserted = True

    if not inserted:
        print(f"warning: anchor not found, no index mark inserted: {args.anchor!r}", file=sys.stderr)
        write_odt_with_replacements(args.input_odt, args.output, {})
        return

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print(args.key1)


if __name__ == "__main__":
    main()
