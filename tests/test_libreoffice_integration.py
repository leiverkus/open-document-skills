from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "/usr/local/bin/libreoffice",
        "/snap/bin/libreoffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        "/c/Program Files/LibreOffice/program/soffice.exe",
        "/mnt/c/Program Files/LibreOffice/program/soffice.exe",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


SOFFICE = find_soffice()


def run_script(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *map(str, args)],
        cwd=script.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_svg(path: Path, label: str) -> Path:
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="100">'
        f'<rect width="160" height="100" fill="#eef0ff"/>'
        f'<text x="20" y="55" font-size="22">{label}</text></svg>',
        encoding="utf-8",
    )
    return path


@unittest.skipUnless(SOFFICE, "LibreOffice/soffice not available")
class LibreOfficeIntegrationTests(unittest.TestCase):
    def test_odt_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            spec = write_json(tmp_path / "doc.json", {"title": "Render ODT", "blocks": [{"type": "paragraph", "text": "Hello PDF"}]})
            odt = tmp_path / "doc.odt"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odt.py", spec, odt)
            run_script(scripts / "render.py", odt, "--outdir", outdir)
            pdf = outdir / "doc.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_odp_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = write_json(tmp_path / "slides.json", {"slides": [{"name": "Intro", "title": "Render ODP", "body": ["Hello PDF"]}]})
            odp = tmp_path / "deck.odp"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            run_script(scripts / "render.py", odp, "--outdir", outdir)
            pdf = outdir / "deck.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_odg_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            image = write_svg(tmp_path / "image.svg", "ODG")
            spec = write_json(
                tmp_path / "drawing.json",
                {"pages": [{"name": "Diagram", "items": [{"type": "text", "text": "Render ODG"}, {"type": "image", "path": str(image)}]}]},
            )
            odg = tmp_path / "drawing.odg"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odg.py", spec, odg)
            run_script(scripts / "render.py", odg, "--outdir", outdir, "--formats", "pdf")
            pdf = outdir / "drawing.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_ods_recalc_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            spec = write_json(
                tmp_path / "workbook.json",
                {"sheets": [{"name": "Data", "rows": [["Value"], [10]], "cells": {"B2": {"formula": "of:=[.A2]*2"}}}]},
            )
            ods = tmp_path / "book.ods"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_ods.py", spec, ods)
            run_script(scripts / "recalc.py", ods, "--outdir", outdir)
            recalced = outdir / "book.ods"
            self.assertTrue(recalced.exists())
            run_script(scripts / "validate_refs.py", recalced)


if __name__ == "__main__":
    unittest.main()
