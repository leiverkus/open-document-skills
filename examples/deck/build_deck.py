#!/usr/bin/env python3
"""Build a branded presentation deck end-to-end via the v1.12 template stack.

Demonstrates the ODP presentation-styling pipeline:

1. Generate a base ODP from ``spec.json``.
2. Apply the ``dao-conference`` template (deep-blue theme + light typography
   + logo placeholder) in one call.
3. Optionally render to PDF via LibreOffice.

The ``dao-conference`` template is the v1.12 home of what used to live in
this directory's ``styles.xml`` and ``logo-placeholder.png`` — they were
migrated into ``skills/odp/templates/dao-conference/`` so any user gets the
same branding via ``apply_template.py --template-name dao-conference``.

Run from the repo root:

    python3 examples/deck/build_deck.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "odp" / "scripts"
DECK = ROOT / "examples" / "deck"
OUT = DECK / "output"
OUT.mkdir(exist_ok=True)


def run(script: str, *args: object) -> None:
    cmd = [sys.executable, "-B", str(SCRIPTS / script), *map(str, args)]
    print(f"  $ {' '.join(cmd[2:])}")
    subprocess.run(cmd, check=True)


def main() -> None:
    print("Step 1: Generate base ODP from spec.json")
    base = OUT / "01-base.odp"
    run("create_minimal_odp.py", DECK / "spec.json", base)

    print("Step 2: Apply the dao-conference template")
    final = OUT / "deck.odp"
    run("apply_template.py", base, "--template-name", "dao-conference", "-o", final)

    print(f"\nFinal ODP: {final}")
    print("\nStep 3: Render to PDF (if soffice available)")
    run("render.py", final, "--outdir", OUT)
    pdf = OUT / "deck.pdf"
    if pdf.exists():
        print(f"PDF: {pdf} ({pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
