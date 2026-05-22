#!/usr/bin/env python3
"""Insert a block fragment into an existing ODT.

The fragment is a JSON ``blocks`` array — the same format create_minimal_odt
consumes (heading / paragraph / list / table). One call can insert several
blocks at once.

Position (exactly one):
- --after-anchor TEXT  : after the block containing TEXT
- --before-anchor TEXT : before the block containing TEXT
- --at-paragraph N     : after the Nth top-level block
- --at start|end       : at the document body start or end
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from create_minimal_odt import CONTENT_BLOCK_TYPES, build_block
from odt_common import (
    NS,
    parse_xml_from_zip,
    q,
    update_meta_for_edit,
    write_odt_with_replacements,
    xml_bytes,
)

BLOCK_TAGS = {
    q("text", "h"),
    q("text", "p"),
    q("text", "list"),
    q("table", "table"),
    q("text", "section"),
}


def parent_of(root: ET.Element, target: ET.Element) -> tuple[ET.Element, int] | None:
    for parent in root.iter():
        for index, child in enumerate(parent):
            if child is target:
                return parent, index
    return None


def content_blocks(body: ET.Element) -> list[ET.Element]:
    """Top-level block elements of office:text, in document order."""
    return [child for child in body if child.tag in BLOCK_TAGS]


def find_block_with_text(body: ET.Element, anchor: str) -> ET.Element | None:
    for node in body.iter():
        if node.tag in BLOCK_TAGS and anchor in "".join(node.itertext()):
            return node
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--blocks", type=Path, required=True, help='JSON file: a blocks array or {"blocks": [...]}')
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--after-anchor", help="insert after the block containing this text")
    where.add_argument("--before-anchor", help="insert before the block containing this text")
    where.add_argument("--at-paragraph", type=int, help="insert after the Nth top-level block")
    where.add_argument("--at", choices=["start", "end"], help="insert at the body start or end")
    args = parser.parse_args()

    try:
        spec = json.loads(args.blocks.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"could not read blocks file {args.blocks}: {exc}")
    blocks = spec if isinstance(spec, list) else spec.get("blocks", [])
    if not blocks:
        raise SystemExit("blocks file contains no blocks")
    for block in blocks:
        kind = block.get("type", "paragraph")
        if kind not in CONTENT_BLOCK_TYPES:
            raise SystemExit(
                f"insert_blocks supports {sorted(CONTENT_BLOCK_TYPES)} blocks; "
                f"got {kind!r} — use add_image.py / add_footnote.py for those"
            )

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")

    # Build the fragment into a throwaway container.
    fragment = ET.Element("fragment")
    for block in blocks:
        build_block(block, fragment)
    new_elements = list(fragment)

    # Resolve (parent, index) for the insertion point.
    if args.at == "end":
        parent, index = body, len(list(body))
    elif args.at == "start":
        first = content_blocks(body)
        parent, index = body, (list(body).index(first[0]) if first else len(list(body)))
    elif args.at_paragraph is not None:
        tops = content_blocks(body)
        if args.at_paragraph < 1 or args.at_paragraph > len(tops):
            raise SystemExit(f"--at-paragraph out of range: {args.at_paragraph} (have {len(tops)})")
        anchor_el = tops[args.at_paragraph - 1]
        parent, index = body, list(body).index(anchor_el) + 1
    else:
        anchor_text = args.after_anchor if args.after_anchor is not None else args.before_anchor
        block = find_block_with_text(body, anchor_text)
        if block is None:
            raise SystemExit(f"no block contains the anchor text: {anchor_text!r}")
        located = parent_of(content, block)
        if located is None:
            raise SystemExit("could not locate the anchored block's parent")
        parent, block_index = located
        index = block_index + 1 if args.after_anchor is not None else block_index

    for offset, element in enumerate(new_elements):
        parent.insert(index + offset, element)

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print(f"inserted {len(new_elements)} block(s)")


if __name__ == "__main__":
    main()
