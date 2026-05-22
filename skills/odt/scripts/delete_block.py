#!/usr/bin/env python3
"""Delete a whole block — a paragraph, heading, list, or table — from an ODT.

Selection (exactly one):
- --anchor TEXT  : delete the block whose text contains TEXT
- --paragraph N  : delete the Nth top-level block

--type narrows the selection to one block kind.
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

TYPE_TAGS = {
    "heading": q("text", "h"),
    "paragraph": q("text", "p"),
    "list": q("text", "list"),
    "table": q("table", "table"),
}
BLOCK_TAGS = set(TYPE_TAGS.values()) | {q("text", "section")}


def parent_of(root: ET.Element, target: ET.Element) -> tuple[ET.Element, int] | None:
    for parent in root.iter():
        for index, child in enumerate(parent):
            if child is target:
                return parent, index
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--type", choices=sorted(TYPE_TAGS), help="restrict to one block kind")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--anchor", help="delete the block whose text contains this")
    selection.add_argument("--paragraph", type=int, help="delete the Nth top-level block")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")

    allowed = {TYPE_TAGS[args.type]} if args.type else BLOCK_TAGS
    target: ET.Element | None = None

    if args.anchor is not None:
        for node in body.iter():
            if node.tag in allowed and args.anchor in "".join(node.itertext()):
                target = node
                break
        if target is None:
            print(f"warning: no block contains the anchor: {args.anchor!r}", file=sys.stderr)
            write_odt_with_replacements(args.input_odt, args.output, {})
            return
    else:
        candidates = [child for child in body if child.tag in allowed]
        if args.paragraph < 1 or args.paragraph > len(candidates):
            raise SystemExit(f"--paragraph out of range: {args.paragraph} (have {len(candidates)})")
        target = candidates[args.paragraph - 1]

    located = parent_of(content, target)
    if located is None:
        raise SystemExit("could not locate the block's parent")
    parent, index = located
    tail = target.tail or ""
    if tail:  # re-flow trailing whitespace so nothing is lost
        if index == 0:
            parent.text = (parent.text or "") + tail
        else:
            parent[index - 1].tail = (parent[index - 1].tail or "") + tail
    parent.remove(target)

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print(f"deleted block: {target.tag.split('}')[-1]}")


if __name__ == "__main__":
    main()
