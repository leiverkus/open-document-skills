#!/usr/bin/env python3
"""Bulk-restyle paragraphs and headings in an ODT.

Sets text:style-name to a new style on every text:p / text:h matching the
selectors. With no selector, every paragraph and heading is restyled.

Selectors (combine freely — all must match):
- --current-style OLD : only elements currently styled OLD
- --headings          : only text:h
- --paragraphs        : only text:p
- --level N           : only headings with outline-level N
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from odt_common import (
    NS,
    parse_xml_from_zip,
    q,
    update_meta_for_edit,
    write_odt_with_replacements,
    xml_bytes,
)


def defined_styles(content: ET.Element, styles: ET.Element | None) -> set[str]:
    names: set[str] = set()
    for root in (content, styles):
        if root is None:
            continue
        for tag in ("style:style", "text:list-style", "text:outline-style"):
            for style_el in root.findall(f".//{tag}", NS):
                name = style_el.attrib.get(q("style", "name"))
                if name:
                    names.add(name)
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--style", required=True, help="the new style name to apply")
    parser.add_argument("--current-style", help="only restyle elements currently styled this way")
    parser.add_argument("--level", type=int, help="only restyle headings of this outline level")
    kind = parser.add_mutually_exclusive_group()
    kind.add_argument("--headings", action="store_true", help="only restyle text:h")
    kind.add_argument("--paragraphs", action="store_true", help="only restyle text:p")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")

    style_attr = q("text", "style-name")
    level_attr = q("text", "outline-level")
    count = 0
    for node in body.iter():
        is_heading = node.tag == q("text", "h")
        is_paragraph = node.tag == q("text", "p")
        if not (is_heading or is_paragraph):
            continue
        if args.headings and not is_heading:
            continue
        if args.paragraphs and not is_paragraph:
            continue
        if args.level is not None:
            if not is_heading or node.attrib.get(level_attr) != str(args.level):
                continue
        if args.current_style is not None and node.attrib.get(style_attr) != args.current_style:
            continue
        node.set(style_attr, args.style)
        count += 1

    if count == 0:
        print("warning: no matching paragraphs or headings — nothing restyled", file=sys.stderr)
        write_odt_with_replacements(args.input_odt, args.output, {})
        return

    styles = parse_xml_from_zip(args.input_odt, "styles.xml")
    if args.style not in defined_styles(content, styles):
        print(
            f"warning: style {args.style!r} is not defined in styles.xml or content.xml",
            file=sys.stderr,
        )

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print(f"restyled: {count}")


if __name__ == "__main__":
    main()
