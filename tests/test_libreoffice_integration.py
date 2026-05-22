from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURES, ROOT, SKILLS, run_script

# Import shared find_soffice from lib
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from odf_lib.odf_common import find_soffice  # noqa: E402

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

    def test_branded_odp_deck_renders_to_pdf(self) -> None:
        """A base ODP with the branded deck styles.xml injected + logo embedded
        must render to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            sys.path.insert(0, str(scripts))
            from odp_common import embed_pictures, inject_styles_from_file

            deck = ROOT / "examples" / "deck"
            base = tmp_path / "base.odp"
            run_script(scripts / "create_minimal_odp.py", deck / "spec.json", base)
            styled = tmp_path / "styled.odp"
            inject_styles_from_file(base, deck / "styles.xml", styled)
            final = tmp_path / "deck.odp"
            embed_pictures(styled, {"Pictures/logo.png": deck / "logo-placeholder.png"}, final)
            run_script(scripts / "validate_refs.py", final)

            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", final, "--outdir", outdir)
            pdf = outdir / "deck.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_ods_render_to_pdf(self) -> None:
        """The new ODS render.py must produce a PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            ods = tmp_path / "book.ods"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_ods.py", FIXTURES / "ods_workbook.json", ods)
            run_script(scripts / "render.py", ods, "--outdir", outdir)
            pdf = outdir / "book.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_contact_sheet_render(self) -> None:
        """render.py --contact-sheet must compose all pages into one PNG."""
        import shutil

        if not shutil.which("pdftoppm"):
            self.skipTest("pdftoppm (Poppler) not available")
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = tmp_path / "deck.json"
            spec.write_text(
                json.dumps({"slides": [{"name": f"S{i}", "title": f"Slide {i}"} for i in range(1, 4)]}),
                encoding="utf-8",
            )
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", odp, "--outdir", outdir, "--contact-sheet")
            sheet = outdir / "deck-contact.png"
            self.assertTrue(sheet.exists())
            self.assertGreater(sheet.stat().st_size, 0)

    def test_tracked_changes_and_comments_render_to_pdf(self) -> None:
        """An ODT with tracked changes and a comment must render to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            src = tmp_path / "doc.md"
            src.write_text(
                "# Review\n\nThe quick brown fox jumps over the lazy dog.\n",
                encoding="utf-8",
            )
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_from_markdown.py", src, odt)
            commented = tmp_path / "commented.odt"
            run_script(
                scripts / "add_comment.py", odt, "--anchor", "fox", "--author", "Rev", "--text", "Note", "-o", commented
            )
            tracked = tmp_path / "tracked.odt"
            run_script(
                scripts / "track_change.py",
                commented,
                "--replace",
                "brown",
                "--with",
                "red",
                "--author",
                "Rev",
                "-o",
                tracked,
            )
            run_script(scripts / "validate_refs.py", tracked, "--strict")
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", tracked, "--outdir", outdir)
            pdf = outdir / "tracked.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_markdown_to_odt_renders_to_pdf(self) -> None:
        """An ODT built from Markdown must render to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            src = tmp_path / "doc.md"
            src.write_text(
                "# Title\n\nText with **bold** and a [link](https://x.io).\n\n"
                "- one\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n",
                encoding="utf-8",
            )
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_from_markdown.py", src, odt)
            run_script(scripts / "validate_refs.py", odt, "--strict")
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", odt, "--outdir", outdir)
            pdf = outdir / "doc.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_branded_odg_diagram_renders_to_pdf(self) -> None:
        """A base ODG with the branded diagram styles.xml injected must render
        to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            sys.path.insert(0, str(scripts))
            from odg_common import inject_styles_from_file

            diagram = ROOT / "examples" / "diagram"
            base = tmp_path / "base.odg"
            run_script(scripts / "create_minimal_odg.py", diagram / "spec.json", base)
            final = tmp_path / "diagram.odg"
            inject_styles_from_file(base, diagram / "styles.xml", final)
            run_script(scripts / "validate_refs.py", final)

            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", final, "--outdir", outdir, "--formats", "pdf")
            pdf = outdir / "diagram.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_libreoffice_opens_flat_fodt(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            fodt = tmp_path / "doc.fodt"
            run_script(scripts / "pack_fodt.py", odt, "-o", fodt)
            outdir = tmp_path / "qa"
            outdir.mkdir()
            subprocess.run(
                [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(fodt)],
                check=True,
                capture_output=True,
            )
            pdf = outdir / "doc.pdf"
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
