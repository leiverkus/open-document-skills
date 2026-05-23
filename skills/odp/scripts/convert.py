#!/usr/bin/env python3
"""Convert between ODP and Microsoft PowerPoint formats via headless LibreOffice.

Accepted input/output combinations (this skill handles the presentation family):

- ``.odp``  → ``.pptx`` / ``.ppt`` / ``.odp`` (re-save)
- ``.pptx`` → ``.odp`` / ``.ppt``
- ``.ppt``  → ``.odp`` / ``.pptx``

Use the corresponding skill for other families: ``odt`` for text documents,
``ods`` for spreadsheets.

The conversion runs inside an isolated ``-env:UserInstallation`` temp profile
— your real LibreOffice profile is never touched.

Fidelity caveat: soffice handles text, basic shapes, images, and master pages
well. Slide layouts (the ODF ``presentation-page-layout`` introduced in v1.8)
map approximately to PowerPoint slide layouts but are not perfectly
equivalent. Animations and transitions usually round-trip; some advanced
SMIL motion paths or custom-path effects may simplify or be dropped.
Always inspect the output before relying on it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from odp_common import convert_with_soffice

ACCEPTED_INPUT_EXTS: set[str] = {".odp", ".pptx", ".ppt"}
TARGET_FORMATS: tuple[str, ...] = ("odp", "pptx", "ppt")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", type=Path)
    parser.add_argument(
        "--to",
        dest="target",
        required=True,
        choices=TARGET_FORMATS,
        help="target format identifier",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("qa"),
        help="output directory (default: %(default)s)",
    )
    args = parser.parse_args()

    if not args.input_file.exists():
        raise SystemExit(f"input file not found: {args.input_file}")
    if args.input_file.suffix.lower() not in ACCEPTED_INPUT_EXTS:
        raise SystemExit(
            f"input extension {args.input_file.suffix!r} is not a presentation format. "
            f"Use the odt skill for text documents or the ods skill for spreadsheets. "
            f"Accepted here: {sorted(ACCEPTED_INPUT_EXTS)}"
        )
    output = convert_with_soffice(args.input_file, args.target, args.outdir)
    print(output)


if __name__ == "__main__":
    main()
