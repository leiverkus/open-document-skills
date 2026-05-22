#!/usr/bin/env python3
"""List tracked changes in an ODT as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from odt_common import NS, parse_xml_from_zip, q

KINDS = ("insertion", "deletion", "format-change")


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

    # Map each change-id to the paragraph index of its first body marker.
    para_of: dict[str, int] = {}
    for index, paragraph in enumerate(paragraphs, start=1):
        for marker_tag in ("change", "change-start", "change-end"):
            for marker in paragraph.iter(q("text", marker_tag)):
                cid = marker.attrib.get(q("text", "change-id"))
                if cid and cid not in para_of:
                    para_of[cid] = index

    # Inserted text lives as the tail of each change-start marker.
    inserted_text: dict[str, str] = {}
    for marker in content.iter(q("text", "change-start")):
        cid = marker.attrib.get(q("text", "change-id"))
        if cid:
            inserted_text[cid] = (marker.tail or "").strip()

    changes: list[dict[str, object]] = []
    for region in content.iter(q("text", "changed-region")):
        change_id = region.attrib.get(q("text", "id"), "")
        kind = next((k for k in KINDS if region.find(q("text", k)) is not None), "unknown")
        type_el = region.find(q("text", kind)) if kind != "unknown" else None
        author = date = None
        text = ""
        if type_el is not None:
            info = type_el.find(q("office", "change-info"))
            if info is not None:
                creator = info.find(q("dc", "creator"))
                when = info.find(q("dc", "date"))
                author = creator.text if creator is not None else None
                date = when.text if when is not None else None
            if kind == "deletion":
                text = "\n".join((p.text or "") for p in type_el.findall(q("text", "p")))
        if kind == "insertion":
            text = inserted_text.get(change_id, "")
        changes.append(
            {
                "id": change_id,
                "kind": kind,
                "author": author,
                "date": date,
                "text": text,
                "paragraph_index": para_of.get(change_id),
            }
        )

    print(json.dumps(changes, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
