#!/usr/bin/env python3
"""Build a branded presentation deck end-to-end.

Demonstrates the ODP presentation-styling stack:
1. Generate a base ODP from spec.json.
2. Inject a curated branded styles.xml (deep-blue theme, light typography).
3. Embed the logo placeholder referenced by the branded master page.
4. Validate references.
5. Optionally render to PDF via LibreOffice.

The branded styles.xml redefines the same named styles the generator
emits (dp-default, gr-title, gr-body, gr-image, Title, Body, master
"Default", layout "Screen") so the injection swaps the whole theme
without touching content.xml.

Run from the repo root:

    python3 examples/deck/build_deck.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "odp" / "scripts"
DECK = ROOT / "examples" / "deck"
OUT = DECK / "output"
OUT.mkdir(exist_ok=True)


def run(script: str, *args: object) -> None:
    """Invoke an ODP skill script as a subprocess."""
    cmd = [sys.executable, "-B", str(SCRIPTS / script), *map(str, args)]
    print(f"  $ {' '.join(cmd[2:])}")
    subprocess.run(cmd, check=True)


def inject_branded_styles_and_logo(input_odp: Path, output_odp: Path) -> None:
    """Replace styles.xml with the branded theme and embed the logo."""
    sys.path.insert(0, str(SCRIPTS))
    from odp_common import embed_pictures, inject_styles_from_file  # noqa: E402

    intermediate = OUT / "_styled.tmp.odp"
    missing = inject_styles_from_file(input_odp, DECK / "styles.xml", intermediate)
    if missing:
        print(f"  ! style refs in content not defined in new styles.xml: {missing}", file=sys.stderr)
    embed_pictures(intermediate, {"Pictures/logo.png": DECK / "logo-placeholder.png"}, output_odp)
    intermediate.unlink(missing_ok=True)


def find_soffice() -> str | None:
    """Locate a LibreOffice binary, including the macOS app bundle."""
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    return mac if Path(mac).exists() else None


def main() -> None:
    print("Step 1: Generate base ODP from spec.json")
    base = OUT / "01-base.odp"
    run("create_minimal_odp.py", DECK / "spec.json", base)

    print("Step 2: Inject branded styles + logo placeholder")
    final = OUT / "deck.odp"
    inject_branded_styles_and_logo(base, final)

    print(f"\nFinal ODP: {final}")
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
        pdf = OUT / "deck.pdf"
        if pdf.exists():
            print(f"PDF: {pdf} ({pdf.stat().st_size} bytes)")
    else:
        print("\nLibreOffice not found — skipping PDF render.")


if __name__ == "__main__":
    main()
