#!/usr/bin/env python3
"""List office:annotation comments in an ODT as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from odt_common import NS, parse_xml_from_zip, q


def paragraph_text(paragraph: ET.Element) -> str:
    """Visible text of a paragraph, excluding any office:annotation bodies."""
    parts: list[str] = []

    def walk(node: ET.Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            # Skip the annotation's comment body, but keep its tail —
            # the tail is real document text after the comment marker.
            if child.tag != q("office", "annotation"):
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(paragraph)
    return " ".join("".join(parts).split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("--json", action="store_true", help="emit JSON (default)")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")
    paragraphs = [n for n in body.iter() if n.tag in {q("text", "p"), q("text", "h")}]

    # A comment is a range if a matching office:annotation-end exists.
    range_names = {e.attrib.get(q("office", "name")) for e in content.iter(q("office", "annotation-end"))}

    comments: list[dict[str, object]] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        for annotation in paragraph.iter(q("office", "annotation")):
            name = annotation.attrib.get(q("office", "name"), "")
            creator = annotation.find(q("dc", "creator"))
            date = annotation.find(q("dc", "date"))
            text = "\n".join((p.text or "") for p in annotation.findall(q("text", "p")))
            comments.append(
                {
                    "name": name,
                    "kind": "range" if name in range_names else "point",
                    "author": creator.text if creator is not None else None,
                    "date": date.text if date is not None else None,
                    "text": text,
                    "paragraph_index": index,
                    "context": paragraph_text(paragraph),
                }
            )

    print(json.dumps(comments, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
