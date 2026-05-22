#!/usr/bin/env python3
"""Accept or reject tracked changes in an ODT.

- accept insertion : keep the inserted text, drop the markers
- reject insertion : remove the inserted text and the markers
- accept deletion  : keep the text deleted (drop the marker)
- reject deletion  : restore the deleted text

Resolved changed-regions are removed from text:tracked-changes.
"""

from __future__ import annotations

import argparse
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

KINDS = ("insertion", "deletion", "format-change")


def parent_of(root: ET.Element, target: ET.Element) -> ET.Element | None:
    for parent in root.iter():
        for child in parent:
            if child is target:
                return parent
    return None


def remove_marker(root: ET.Element, marker: ET.Element, keep_tail: bool) -> None:
    """Remove *marker* from the tree, optionally re-flowing its tail text."""
    parent = parent_of(root, marker)
    if parent is None:
        return
    index = list(parent).index(marker)
    tail = (marker.tail or "") if keep_tail else ""
    if tail:
        if index == 0:
            parent.text = (parent.text or "") + tail
        else:
            prev = parent[index - 1]
            prev.tail = (prev.tail or "") + tail
    parent.remove(marker)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--accept", action="store_true", help="accept the changes")
    action.add_argument("--reject", action="store_true", help="reject the changes")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all", action="store_true", help="resolve every tracked change")
    selection.add_argument("--id", dest="ids", action="append", help="resolve this change id (repeatable)")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    body = content.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")
    tracked = body.find(q("text", "tracked-changes"))
    if tracked is None:
        raise SystemExit("no tracked changes in this document")

    regions = {r.attrib.get(q("text", "id")): r for r in tracked.findall(q("text", "changed-region"))}
    targets = list(regions) if args.all else [cid for cid in (args.ids or []) if cid in regions]
    if not targets:
        raise SystemExit("no matching tracked changes to resolve")

    accept = args.accept
    resolved = 0
    for change_id in targets:
        region = regions[change_id]
        kind = next((k for k in KINDS if region.find(q("text", k)) is not None), None)

        markers = [
            m
            for tag in ("change", "change-start", "change-end")
            for m in content.iter(q("text", tag))
            if m.attrib.get(q("text", "change-id")) == change_id
        ]
        if kind == "deletion":
            for marker in markers:
                if not accept:
                    # Restore the deleted text in place of the marker.
                    deletion = region.find(q("text", "deletion"))
                    deleted = (
                        "".join(p.text or "" for p in deletion.findall(q("text", "p"))) if deletion is not None else ""
                    )
                    marker.tail = deleted + (marker.tail or "")
                remove_marker(content, marker, keep_tail=True)
        else:
            # Insertion (or format-change): drop both milestone markers.
            # Rejecting an insertion also drops the inserted text, which is
            # the tail of the change-start marker.
            for marker in markers:
                is_start = marker.tag == q("text", "change-start")
                keep = not (args.reject and kind == "insertion" and is_start)
                remove_marker(content, marker, keep_tail=keep)

        tracked.remove(region)
        resolved += 1

    if len(tracked) == 0:
        body.remove(tracked)

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print(f"{'accepted' if accept else 'rejected'} {resolved} change(s)")


if __name__ == "__main__":
    main()
