#!/usr/bin/env python3
"""Build a branded flowchart end-to-end.

Demonstrates the ODG drawing-styling stack:
1. Generate a base ODG from spec.json — per-shape fill/stroke/text colours.
2. Connect the nodes with draw:connector elements.
3. Inject a curated branded styles.xml (white cards on a light-grey page).
4. Validate references.
5. Optionally render to PDF via LibreOffice.

The branded styles.xml redefines the same named styles the generator
emits (standard, gr-shape, gr-text, gr-line, gr-image, dp-default,
master "Default", layout "Screen"), so the injection re-themes every
default-styled shape while per-shape overrides from the spec stay intact.

Run from the repo root:

    python3 examples/diagram/build_diagram.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "odg" / "scripts"
DIAGRAM = ROOT / "examples" / "diagram"
OUT = DIAGRAM / "output"
OUT.mkdir(exist_ok=True)

# Flowchart edges — connected in order with connect_shapes.py.
EDGES = [("Draft", "Review"), ("Review", "Revise"), ("Revise", "Approve"), ("Approve", "Publish")]


def run(script: str, *args: object) -> None:
    """Invoke an ODG skill script as a subprocess."""
    cmd = [sys.executable, "-B", str(SCRIPTS / script), *map(str, args)]
    print(f"  $ {' '.join(cmd[2:])}")
    subprocess.run(cmd, check=True)


def find_soffice() -> str | None:
    """Locate a LibreOffice binary, including the macOS app bundle."""
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    return mac if Path(mac).exists() else None


def main() -> None:
    print("Step 1: Generate base ODG from spec.json")
    current = OUT / "01-base.odg"
    run("create_minimal_odg.py", DIAGRAM / "spec.json", current)

    print("Step 2: Connect the flowchart nodes")
    for index, (src, dst) in enumerate(EDGES, start=1):
        nxt = OUT / f"02-connected-{index}.odg"
        run("connect_shapes.py", current, "--from", src, "--to", dst, "-o", nxt)
        current = nxt

    print("Step 3: Inject the branded drawing theme")
    sys.path.insert(0, str(SCRIPTS))
    from odg_common import inject_styles_from_file  # noqa: E402

    final = OUT / "diagram.odg"
    missing = inject_styles_from_file(current, DIAGRAM / "styles.xml", final)
    if missing:
        print(f"  ! style refs in content not defined in new styles.xml: {missing}", file=sys.stderr)

    print(f"\nFinal ODG: {final}")
    print("\nValidating references...")
    run("validate_refs.py", final)

    soffice = find_soffice()
    if soffice:
        print(f"\nRendering PDF via {soffice}...")
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(final)],
            check=True,
            capture_output=True,
        )
        pdf = OUT / "diagram.pdf"
        if pdf.exists():
            print(f"PDF: {pdf} ({pdf.stat().st_size} bytes)")
    else:
        print("\nLibreOffice not found — skipping PDF render.")


if __name__ == "__main__":
    main()
