#!/usr/bin/env python3
"""Render an ODS spreadsheet to PDF, per-page PNGs, or a single contact sheet.

LibreOffice paginates the sheet for printing; the contact sheet
(``--contact-sheet``) shows every printed page in one labelled grid image.
Treat rendering as a design step, not only a final check.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from ods_common import build_contact_sheet, pdf_to_pngs, render_to_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="source ODS file")
    parser.add_argument("--outdir", type=Path, default=Path("qa"))
    parser.add_argument("--png", action="store_true", help="render each printed page to a PNG")
    parser.add_argument(
        "--contact-sheet",
        action="store_true",
        help="compose all printed pages into one labelled grid image (needs Pillow)",
    )
    parser.add_argument("--dpi", type=int, default=150, help="PNG render resolution")
    parser.add_argument("--columns", type=int, default=0, help="contact-sheet columns (0 = auto)")
    args = parser.parse_args()

    pdf = render_to_pdf(args.input, args.outdir)
    print(pdf)

    if args.png:
        pages = pdf_to_pngs(pdf, args.outdir, args.dpi)
        print(f"{args.outdir / args.input.stem}-*.png ({len(pages)} pages)")

    if args.contact_sheet:
        with tempfile.TemporaryDirectory() as tmp:
            pages = pdf_to_pngs(pdf, Path(tmp), args.dpi)
            sheet = build_contact_sheet(pages, args.outdir / f"{args.input.stem}-contact.png", args.columns)
        print(sheet)


if __name__ == "__main__":
    main()
