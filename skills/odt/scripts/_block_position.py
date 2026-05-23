"""Internal helper: resolve where to insert a block-level element in office:text.

Used by the ``add_*_index.py`` scripts and any future block-insertion entrypoint
that takes ``--anchor`` / ``--paragraph`` / ``--at start|end`` arguments.

The logic mirrors ``insert_blocks.py`` but is split out so the four index
inserters can share it without dragging in the JSON-fragment machinery.
"""

from __future__ import annotations

import sys
from xml.etree import ElementTree as ET

from odt_common import q

BLOCK_TAGS = {
    q("text", "h"),
    q("text", "p"),
    q("text", "list"),
    q("table", "table"),
    q("text", "section"),
}


def top_level_blocks(body: ET.Element) -> list[ET.Element]:
    return [child for child in body if child.tag in BLOCK_TAGS]


def find_block_with_text(body: ET.Element, anchor: str) -> ET.Element | None:
    for node in body.iter():
        if node.tag in BLOCK_TAGS and anchor in "".join(node.itertext()):
            return node
    return None


def resolve_insert_index(
    body: ET.Element,
    *,
    anchor: str | None,
    paragraph: int | None,
    at: str | None,
    kind_label: str,
) -> int | None:
    """Resolve the child-index in ``body`` where a block should be inserted.

    Exactly one of ``anchor`` / ``paragraph`` / ``at`` must be set. Returns
    ``None`` if an anchor was given but not found (caller prints a warning and
    writes the file unchanged); raises ``SystemExit`` for out-of-range
    ``--paragraph``.
    """
    children = list(body)
    if at == "end":
        return len(children)
    if at == "start":
        firsts = top_level_blocks(body)
        return children.index(firsts[0]) if firsts else len(children)
    if paragraph is not None:
        tops = top_level_blocks(body)
        if paragraph < 1 or paragraph > len(tops):
            raise SystemExit(f"--paragraph out of range: {paragraph} (have {len(tops)})")
        return children.index(tops[paragraph - 1]) + 1
    if anchor is not None:
        block = find_block_with_text(body, anchor)
        if block is None:
            print(f"warning: anchor not found, no {kind_label} inserted: {anchor!r}", file=sys.stderr)
            return None
        return children.index(block) + 1
    raise SystemExit("provide one of --anchor / --paragraph / --at")
