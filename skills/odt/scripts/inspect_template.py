#!/usr/bin/env python3
"""Inspect an ODT template and report its page layouts, master pages,
outline-styles, named paragraph/text/list styles, and font declarations
as JSON.

Accepts either:

- an ODT/OTT package (``.odt`` / ``.ott``): the template payload is read
  from the package's ``styles.xml`` member.
- a standalone ``styles.xml`` file: a curated template that lives alongside
  its assets in ``skills/odt/templates/<name>/styles.xml``.

The output is the inventory an agent needs to decide, per block, which
named style to reference and which outline-numbering scheme to expect —
without re-reading the raw XML.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from odt_common import inspect_styles_xml, load_styles_xml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="path to an .odt/.ott package or a styles.xml file")
    parser.add_argument("--json", action="store_true", help="output JSON (the default and only format)")
    args = parser.parse_args()

    if not args.path.exists():
        raise SystemExit(f"input not found: {args.path}")
    styles_root = load_styles_xml(args.path)
    inventory = inspect_styles_xml(styles_root)
    print(json.dumps(inventory, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
