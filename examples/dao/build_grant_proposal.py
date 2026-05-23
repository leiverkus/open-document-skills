#!/usr/bin/env python3
"""Build a DAO-branded German-language research-grant proposal end-to-end.

This is the **localization showcase** for the v1.13 ODT template ecosystem.
The English-first generic template lives in
``skills/odt/templates/grant-proposal/``; this directory carries the German
DAO-archaeology localisation: DAO-blue (#02416C), Nunito Sans, German prose,
DAO-specific paragraph styles, DAO logo placeholder.

The pipeline:

1. Generate base ODT from spec.json.
2. Apply the localised DAO template via apply_template (one call replaces
   the v1.4 hand-rolled inject_styles + embed_pictures + validate chain).
3. Fill citations from refs.bib (pandoc-style ``[@bibkey]`` placeholders).
4. Insert a footnote.
5. Add a cross-reference (bookmark + bookmark-ref).
6. Add a figure sequence + sequence-ref.
7. Embed a LaTeX formula via MathML.
8. Optionally render to PDF.

Run from the repo root:

    python3 examples/dao/build_grant_proposal.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "odt" / "scripts"
DAO = ROOT / "examples" / "dao"
OUT = DAO / "output"
OUT.mkdir(exist_ok=True)


def run(script: str, *args: object) -> None:
    """Invoke an ODT skill script as a subprocess."""
    cmd = [sys.executable, "-B", str(SCRIPTS / script), *map(str, args)]
    print(f"  $ {' '.join(cmd[2:])}")
    subprocess.run(cmd, check=True)


def main() -> None:
    print("Step 1: Generate base ODT from spec.json")
    base = OUT / "01-base.odt"
    run("create_minimal_odt.py", DAO / "spec.json", base)

    print("Step 2: Apply the DAO localised template (German, DAO-blue)")
    # examples/dao/ IS the template directory — apply_template treats it
    # like any other directory under --template.
    styled = OUT / "02-styled.odt"
    run("apply_template.py", base, "--template", DAO, "-o", styled)

    print("Step 3: Fill citations from refs.bib")
    with_citations = OUT / "03-with-citations.odt"
    run("fill_citations.py", styled, "--source", DAO / "refs.bib", "-o", with_citations)

    print("Step 4: Add a footnote on the methodology")
    with_footnote = OUT / "04-with-footnote.odt"
    run(
        "add_footnote.py",
        with_citations,
        "--anchor",
        "dreistufigen Vorgehen",
        "--body",
        "Detaillierte Beschreibung in Arbeitspaket 1.",
        "-o",
        with_footnote,
    )

    print("Step 5: Bookmark + reference for cross-linking")
    with_bookmark = OUT / "05-with-bookmark.odt"
    run("add_bookmark.py", with_footnote, "--name", "Methodik", "--anchor", "3. Methodik", "-o", with_bookmark)
    with_ref = OUT / "06-with-ref.odt"
    run(
        "add_reference.py",
        with_bookmark,
        "--ref-to",
        "Methodik",
        "--kind",
        "bookmark",
        "--anchor",
        "Methodik",
        "--display",
        "chapter",
        "-o",
        with_ref,
    )

    print("Step 6: Add a figure sequence + sequence-ref")
    with_seq = OUT / "07-with-sequence.odt"
    run(
        "add_sequence.py",
        with_ref,
        "--sequence",
        "Figure",
        "--name",
        "fig:gebiet",
        "--anchor",
        "Abbildung zeigt",
        "-o",
        with_seq,
    )
    with_seq_ref = OUT / "08-with-sequence-ref.odt"
    run(
        "add_sequence.py",
        with_seq,
        "--ref-to",
        "fig:gebiet",
        "--anchor",
        "siehe Abbildung",
        "-o",
        with_seq_ref,
    )

    print("Step 7: Embed a Carbon-14 formula via LaTeX")
    with_math = OUT / "09-with-math.odt"
    pandoc = shutil.which("pandoc")
    if pandoc:
        run(
            "add_math.py",
            with_seq_ref,
            "--latex",
            r"N(t) = N_0 e^{-\lambda t}",
            "--anchor",
            "Datierungsformel",
            "-o",
            with_math,
        )
    else:
        print("  (pandoc not found — skipping LaTeX math step)")
        shutil.copy(with_seq_ref, with_math)

    final = OUT / "grant_proposal.odt"
    shutil.copy(with_math, final)
    print(f"\nFinal ODT: {final}")

    soffice = (
        shutil.which("soffice")
        or shutil.which("libreoffice")
        or (
            "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            if Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").exists()
            else None
        )
    )
    if soffice:
        print(f"\nRendering PDF via {soffice}...")
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(final)],
            check=True,
            capture_output=True,
        )
        pdf = OUT / "grant_proposal.pdf"
        if pdf.exists():
            print(f"PDF: {pdf} ({pdf.stat().st_size} bytes)")
    else:
        print("\nLibreOffice not found — skipping PDF render.")


if __name__ == "__main__":
    main()
