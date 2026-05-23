#!/usr/bin/env python3
"""Render an ODP deck to PDF, per-slide PNGs, or a single contact sheet.

The contact sheet (``--contact-sheet``) shows every slide in one labelled
grid image — ideal for judging cross-slide consistency at a glance. Treat
rendering as a design step, not only a final check.

Speaker-notes export:

- ``--notes``: include speaker-notes pages interleaved with slides
  (output: ``<stem>-with-notes.pdf``).
- ``--notes-only``: export only the notes pages (output:
  ``<stem>-notes.pdf``).

The flags are mutually exclusive. Both produce additional files alongside
the default ``<stem>.pdf`` so slide-only and notes views can be compared
side by side.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from odp_common import build_contact_sheet, pdf_to_pngs, render_impress_to_pdf, render_to_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="source ODP file")
    parser.add_argument("--outdir", type=Path, default=Path("qa"))
    parser.add_argument("--png", action="store_true", help="render each slide to a PNG")
    parser.add_argument(
        "--contact-sheet",
        action="store_true",
        help="compose all slides into one labelled grid image (needs Pillow)",
    )
    parser.add_argument("--dpi", type=int, default=150, help="PNG render resolution")
    parser.add_argument("--columns", type=int, default=0, help="contact-sheet columns (0 = auto)")
    notes_group = parser.add_mutually_exclusive_group()
    notes_group.add_argument(
        "--notes",
        action="store_true",
        help="also export a slides+notes PDF (<stem>-with-notes.pdf)",
    )
    notes_group.add_argument(
        "--notes-only",
        action="store_true",
        help="also export a notes-only PDF (<stem>-notes.pdf)",
    )
    args = parser.parse_args()

    pdf = render_to_pdf(args.input, args.outdir)
    print(pdf)

    if args.notes:
        notes_pdf = render_impress_to_pdf(args.input, args.outdir, notes=True)
        print(notes_pdf)
    elif args.notes_only:
        notes_pdf = render_impress_to_pdf(args.input, args.outdir, notes_only=True)
        print(notes_pdf)

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
