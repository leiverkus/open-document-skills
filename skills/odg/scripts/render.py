#!/usr/bin/env python3
"""Render/export an ODG drawing to PDF, SVG, PNG, or a contact sheet.

``--formats`` exports via LibreOffice (PDF/SVG/PNG). ``--contact-sheet``
composes every page into one labelled grid image — render an early draft,
look at it, and iterate. Treat rendering as a design step, not only a final
check.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from odg_common import build_contact_sheet, find_soffice, pdf_to_pngs, render_to_pdf


def run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="source ODG file")
    parser.add_argument("--outdir", type=Path, default=Path("qa"))
    parser.add_argument("--formats", default="pdf", help="comma-separated export formats: pdf,svg,png")
    parser.add_argument("--png", action="store_true", help="shortcut to include png")
    parser.add_argument(
        "--contact-sheet",
        action="store_true",
        help="compose all pages into one labelled grid image (needs Pillow)",
    )
    parser.add_argument("--dpi", type=int, default=150, help="contact-sheet render resolution")
    parser.add_argument("--columns", type=int, default=0, help="contact-sheet columns (0 = auto)")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    formats = [fmt.strip() for fmt in args.formats.split(",") if fmt.strip()]
    if args.png and "png" not in formats:
        formats.append("png")
    soffice = find_soffice()
    for fmt in formats:
        profile = tempfile.mkdtemp(prefix="odf-soffice-")
        try:
            run(
                [
                    soffice,
                    f"-env:UserInstallation=file://{profile}",
                    "--headless",
                    "--convert-to",
                    fmt,
                    "--outdir",
                    str(args.outdir),
                    str(args.input),
                ]
            )
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        print(args.outdir / f"{args.input.stem}.{fmt}")

    if args.contact_sheet:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = render_to_pdf(args.input, Path(tmp))
            pages = pdf_to_pngs(pdf, Path(tmp), args.dpi)
            sheet = build_contact_sheet(pages, args.outdir / f"{args.input.stem}-contact.png", args.columns)
        print(sheet)


if __name__ == "__main__":
    main()
