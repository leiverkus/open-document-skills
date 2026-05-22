#!/usr/bin/env python3
"""Record an edit in an ODT as a tracked change.

Modes:
- --insert TEXT --anchor ANCHOR   : tracked insertion after the anchor
- --delete TEXT [--anchor CTX]    : tracked deletion of a text run
- --replace OLD --with NEW        : tracked deletion of OLD + insertion of NEW

A tracked change records who changed what and when, so a human (or
resolve_changes.py) can later accept or reject it. Deletions operate on a
text run within a single paragraph; insertions work anywhere.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from odt_common import (
    NS,
    extract_text_range_from_element,
    insert_after_text_in_element,
    insert_in_paragraph,
    parse_xml_from_zip,
    q,
    update_meta_for_edit,
    write_odt_with_replacements,
    xml_bytes,
)

# text:change-id is an IDREF — it must resolve to an xml:id, so each
# changed-region carries xml:id alongside text:id (as LibreOffice does).
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def find_paragraphs(content_root: ET.Element) -> list[ET.Element]:
    body = content_root.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")
    return [n for n in body.iter() if n.tag in {q("text", "p"), q("text", "h")}]


def parent_of(root: ET.Element, target: ET.Element) -> tuple[ET.Element, int] | None:
    """Return (parent, index) of *target* within *root*, or None."""
    for parent in root.iter():
        for index, child in enumerate(parent):
            if child is target:
                return parent, index
    return None


def ensure_tracked_changes(content_root: ET.Element) -> ET.Element:
    """Return office:text's text:tracked-changes child, creating it if absent."""
    body = content_root.find(".//office:text", NS)
    if body is None:
        raise SystemExit("office:text not found")
    existing = body.find(q("text", "tracked-changes"))
    if existing is not None:
        return existing
    tracked = ET.Element(q("text", "tracked-changes"))
    body.insert(0, tracked)
    return tracked


def add_changed_region(tracked: ET.Element, kind: str, author: str, date: str) -> tuple[str, ET.Element]:
    """Append a text:changed-region of *kind* and return (change_id, type_element).

    *kind* is "insertion", "deletion", or "format-change". The returned type
    element is the text:insertion/deletion/format-change child — for a
    deletion the caller appends the deleted content to it.
    """
    used = {r.attrib.get(q("text", "id")) for r in tracked.findall(q("text", "changed-region"))}
    n = 1
    while f"ct{n}" in used:
        n += 1
    change_id = f"ct{n}"
    region = ET.SubElement(
        tracked,
        q("text", "changed-region"),
        {q("text", "id"): change_id, XML_ID: change_id},
    )
    type_el = ET.SubElement(region, q("text", kind))
    info = ET.SubElement(type_el, q("office", "change-info"))
    creator = ET.SubElement(info, q("dc", "creator"))
    creator.text = author
    date_el = ET.SubElement(info, q("dc", "date"))
    date_el.text = date
    return change_id, type_el


def tracked_insert(paragraph: ET.Element, anchor: str | None, position: str, text: str, change_id: str) -> bool:
    """Insert *text* wrapped in change-start/change-end markers for *change_id*."""
    start = ET.Element(q("text", "change-start"), {q("text", "change-id"): change_id})
    end = ET.Element(q("text", "change-end"), {q("text", "change-id"): change_id})
    if anchor is not None:
        if not insert_after_text_in_element(paragraph, anchor, start):
            return False
    else:
        insert_in_paragraph(paragraph, position, start)
    located = parent_of(paragraph, start)
    if located is None:
        return False
    parent, index = located
    remainder = start.tail
    start.tail = text
    parent.insert(index + 1, end)
    end.tail = remainder
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--author", required=True, help="change author (dc:creator)")
    parser.add_argument("--date", help="ISO date (default: now, UTC)")
    parser.add_argument("--insert", dest="insert_text", help="text to insert as a tracked change")
    parser.add_argument("--delete", dest="delete_text", help="text run to delete as a tracked change")
    parser.add_argument("--replace", dest="replace_old", help="text run to replace as a tracked change")
    parser.add_argument("--with", dest="replace_new", help="(with --replace) the replacement text")
    parser.add_argument("--anchor", help="(with --insert/--delete) locate the edit")
    parser.add_argument("--paragraph", type=int, help="(with --insert) 1-based paragraph index")
    parser.add_argument("--position", choices=["start", "end"], default="end")
    args = parser.parse_args()

    modes = sum([args.insert_text is not None, args.delete_text is not None, args.replace_old is not None])
    if modes != 1:
        raise SystemExit("provide exactly one of: --insert / --delete / --replace")
    if args.replace_old is not None and args.replace_new is None:
        raise SystemExit("--replace requires --with")
    if args.insert_text is not None and args.anchor is None and args.paragraph is None:
        raise SystemExit("--insert requires --anchor or --paragraph")

    date = args.date or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    content = parse_xml_from_zip(args.input_odt, "content.xml")
    paragraphs = find_paragraphs(content)
    tracked = ensure_tracked_changes(content)
    done = False

    if args.insert_text is not None:
        change_id, _ = add_changed_region(tracked, "insertion", args.author, date)
        if args.anchor is not None:
            for paragraph in paragraphs:
                if tracked_insert(paragraph, args.anchor, args.position, args.insert_text, change_id):
                    done = True
                    break
        else:
            idx = args.paragraph
            if idx is None or idx < 1 or idx > len(paragraphs):
                raise SystemExit(f"paragraph index out of range: {idx}")
            done = tracked_insert(paragraphs[idx - 1], None, args.position, args.insert_text, change_id)
        if not done:
            tracked.remove(tracked[-1])  # roll back the unused region

    elif args.delete_text is not None:
        change_id, type_el = add_changed_region(tracked, "deletion", args.author, date)
        for paragraph in paragraphs:
            if args.anchor is not None and args.anchor not in "".join(paragraph.itertext()):
                continue
            marker = ET.Element(q("text", "change"), {q("text", "change-id"): change_id})
            removed = extract_text_range_from_element(paragraph, args.delete_text, marker)
            if removed is not None:
                deleted_p = ET.SubElement(type_el, q("text", "p"))
                deleted_p.text = removed
                done = True
                break
        if not done:
            tracked.remove(tracked[-1])

    else:  # --replace
        del_id, del_type = add_changed_region(tracked, "deletion", args.author, date)
        for paragraph in paragraphs:
            marker = ET.Element(q("text", "change"), {q("text", "change-id"): del_id})
            removed = extract_text_range_from_element(paragraph, args.replace_old, marker)
            if removed is None:
                continue
            deleted_p = ET.SubElement(del_type, q("text", "p"))
            deleted_p.text = removed
            # Insert the replacement right after the deletion marker.
            located = parent_of(paragraph, marker)
            if located is None:
                break
            parent, index = located
            ins_id, _ = add_changed_region(tracked, "insertion", args.author, date)
            start = ET.Element(q("text", "change-start"), {q("text", "change-id"): ins_id})
            end = ET.Element(q("text", "change-end"), {q("text", "change-id"): ins_id})
            remainder = marker.tail
            marker.tail = None
            parent.insert(index + 1, start)
            start.tail = args.replace_new
            parent.insert(index + 2, end)
            end.tail = remainder
            done = True
            break
        if not done:
            tracked.remove(tracked[-1])  # roll back the unused deletion region

    if not done:
        print("warning: edit target not found, no tracked change recorded", file=sys.stderr)
        if len(tracked) == 0:
            body = content.find(".//office:text", NS)
            if body is not None:
                body.remove(tracked)
        write_odt_with_replacements(args.input_odt, args.output, {})
        return

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print("tracked change recorded")


if __name__ == "__main__":
    main()
