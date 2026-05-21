#!/usr/bin/env python3
"""Replace text in ODP slides, optionally scoped to a slide and/or notes."""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

from odp_common import NS, clear_children, parse_xml_from_zip, select_slide, write_odp_with_replacements, xml_bytes


def paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return "".join(parts)


def set_plain_text(paragraph: ET.Element, value: str) -> None:
    attrs = dict(paragraph.attrib)
    clear_children(paragraph)
    paragraph.attrib.clear()
    paragraph.attrib.update(attrs)
    paragraph.text = value


def iter_target_paragraphs(root: ET.Element, slide: str | None, include_notes: bool, notes_only: bool):
    pages = [select_slide(root, slide)] if slide else root.findall(".//draw:page", NS)
    for page in pages:
        notes = page.find("presentation:notes", NS)
        if not notes_only:
            page_copy = ET.fromstring(ET.tostring(page))
            for copied_notes in page_copy.findall("presentation:notes", NS):
                page_copy.remove(copied_notes)
            # Match paragraphs by position in the original visible subtree.
            visible_count = len(page_copy.findall(".//text:p", NS))
            yield from page.findall(".//text:p", NS)[:visible_count]
        if include_notes or notes_only:
            if notes is not None:
                yield from notes.findall(".//text:p", NS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odp", type=Path)
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--slide", help="slide index (1-based) or draw:name")
    parser.add_argument("--include-notes", action="store_true", help="also replace inside speaker notes")
    parser.add_argument("--notes-only", action="store_true", help="replace only inside speaker notes")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odp, "content.xml")
    count = 0
    for paragraph in iter_target_paragraphs(content, args.slide, args.include_notes, args.notes_only):
        current = paragraph_text(paragraph)
        if args.old in current:
            set_plain_text(paragraph, current.replace(args.old, args.new))
            count += 1

    write_odp_with_replacements(args.input_odp, args.output, {"content.xml": xml_bytes(content)})
    print(f"replacements: {count}")


if __name__ == "__main__":
    main()
