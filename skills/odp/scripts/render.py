#!/usr/bin/env python3
"""Render an ODP file to PDF and optionally PNG slide images."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SOFFICE_CANDIDATES = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/libreoffice",
    "/usr/local/bin/libreoffice",
    "/snap/bin/libreoffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    "/c/Program Files/LibreOffice/program/soffice.exe",
    "/mnt/c/Program Files/LibreOffice/program/soffice.exe",
]


def find_soffice() -> str:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in SOFFICE_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise SystemExit("LibreOffice/soffice not found")


def run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odp", type=Path)
    parser.add_argument("--outdir", type=Path, default=Path("qa"))
    parser.add_argument("--png", action="store_true", help="also render PDF pages to PNG with pdftoppm")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    soffice = find_soffice()
    run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(args.outdir), str(args.odp)])

    pdf = args.outdir / f"{args.odp.stem}.pdf"
    print(pdf)

    if args.png:
        pdftoppm = shutil.which("pdftoppm")
        if not pdftoppm:
            raise SystemExit("pdftoppm not found; install poppler or omit --png")
        prefix = args.outdir / args.odp.stem
        run([pdftoppm, "-png", "-r", str(args.dpi), str(pdf), str(prefix)])
        print(f"{prefix}-*.png")


if __name__ == "__main__":
    main()
