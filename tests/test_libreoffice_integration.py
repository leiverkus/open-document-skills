from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURES, SKILLS, run_script


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


def odg_fixture_with_image(tmp_path: Path) -> Path:
    spec = json.loads((FIXTURES / "odg_drawing.json").read_text(encoding="utf-8"))
    spec["pages"][0]["items"][-1]["path"] = str(FIXTURES / "image.svg")
    path = tmp_path / "drawing.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


@unittest.skipUnless(SOFFICE, "LibreOffice/soffice not available")
class LibreOfficeIntegrationTests(unittest.TestCase):
    def test_odt_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            run_script(scripts / "render.py", odt, "--outdir", outdir)
            pdf = outdir / "doc.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_odp_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            odp = tmp_path / "deck.odp"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odp.py", FIXTURES / "odp_slides.json", odp)
            run_script(scripts / "render.py", odp, "--outdir", outdir)
            pdf = outdir / "deck.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_odg_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            odg = tmp_path / "drawing.odg"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odg.py", odg_fixture_with_image(tmp_path), odg)
            run_script(scripts / "render.py", odg, "--outdir", outdir, "--formats", "pdf")
            pdf = outdir / "drawing.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_ods_recalc_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            ods = tmp_path / "book.ods"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_ods.py", FIXTURES / "ods_workbook.json", ods)
            run_script(scripts / "recalc.py", ods, "--outdir", outdir)
            recalced = outdir / "book.ods"
            self.assertTrue(recalced.exists())
            run_script(scripts / "validate_refs.py", recalced)


if __name__ == "__main__":
    unittest.main()
