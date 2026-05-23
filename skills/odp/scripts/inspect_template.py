#!/usr/bin/env python3
"""Inspect an ODP template and report its master pages, slide layouts,
named styles, and font declarations as JSON.

Accepts either:

- an ODP/OTP package (``.odp`` / ``.otp``): the template payload is read
  from the package's ``styles.xml`` member.
- a standalone ``styles.xml`` file: a curated template that lives alongside
  its assets in ``skills/odp/templates/<name>/styles.xml``.

The output is the inventory an agent needs to decide, per slide, which
layout/master to assign and which named styles to reference — without
re-reading the raw XML.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from odp_common import inspect_styles_xml, load_styles_xml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="path to an .odp/.otp package or a styles.xml file")
    parser.add_argument("--json", action="store_true", help="output JSON (the default and only format)")
    args = parser.parse_args()

    if not args.path.exists():
        raise SystemExit(f"input not found: {args.path}")
    styles_root = load_styles_xml(args.path)
    inventory = inspect_styles_xml(styles_root)
    print(json.dumps(inventory, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
