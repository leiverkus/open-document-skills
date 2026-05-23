#!/usr/bin/env python3
"""Convert between ODS and Microsoft Excel formats via headless LibreOffice.

Accepted input/output combinations (this skill handles the spreadsheet family):

- ``.ods``  → ``.xlsx`` / ``.xls`` / ``.ods`` (re-save)
- ``.xlsx`` → ``.ods`` / ``.xls``
- ``.xls``  → ``.ods`` / ``.xlsx``

Use the corresponding skill for other families: ``odt`` for text documents,
``odp`` for presentations.

The conversion runs inside an isolated ``-env:UserInstallation`` temp profile
— your real LibreOffice profile is never touched.

Fidelity caveat: soffice handles cell values, basic formatting, and most
formulas well. Macros (VBA), advanced pivot-table options, conditional-
formatting graphical variants (data bars, icon sets), and some chart styles
can be lost or rendered differently on round-trip. Always inspect the
output before relying on it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ods_common import convert_with_soffice

ACCEPTED_INPUT_EXTS: set[str] = {".ods", ".xlsx", ".xls"}
TARGET_FORMATS: tuple[str, ...] = ("ods", "xlsx", "xls")


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
            f"input extension {args.input_file.suffix!r} is not a spreadsheet format. "
            f"Use the odt skill for text documents or the odp skill for presentations. "
            f"Accepted here: {sorted(ACCEPTED_INPUT_EXTS)}"
        )
    output = convert_with_soffice(args.input_file, args.target, args.outdir)
    print(output)


if __name__ == "__main__":
    main()
