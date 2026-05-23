#!/usr/bin/env python3
"""Convert between ODT and Microsoft Word formats via headless LibreOffice.

Accepted input/output combinations (this skill handles the text-document family):

- ``.odt``  → ``.docx`` / ``.doc`` / ``.odt`` (re-save)
- ``.docx`` → ``.odt`` / ``.doc``
- ``.doc``  → ``.odt`` / ``.docx``

Use the corresponding skill for other families: ``ods`` for spreadsheets,
``odp`` for presentations.

The conversion runs inside an isolated ``-env:UserInstallation`` temp profile
— your real LibreOffice profile is never touched. Mirrors the pattern of
``render.py``, ``recalc.py``, and ``update_indexes.py``.

Fidelity caveat: soffice does the conversion well for the 80% case (prose,
simple tables, footnotes, basic styles). Round-tripping documents with
complex master pages, embedded MathML objects, advanced bibliography
features, or heavy custom formatting can lose detail. Always inspect the
output of a round-trip before relying on it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from odt_common import convert_with_soffice

ACCEPTED_INPUT_EXTS: set[str] = {".odt", ".docx", ".doc"}
TARGET_FORMATS: tuple[str, ...] = ("odt", "docx", "doc")


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
            f"input extension {args.input_file.suffix!r} is not a text-document format. "
            f"Use the ods skill for spreadsheets or the odp skill for presentations. "
            f"Accepted here: {sorted(ACCEPTED_INPUT_EXTS)}"
        )
    output = convert_with_soffice(args.input_file, args.target, args.outdir)
    print(output)


if __name__ == "__main__":
    main()
