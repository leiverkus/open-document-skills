"""Tests for ODF ↔ OOXML format conversion via headless LibreOffice.

These tests require soffice to be present. The class is skipped when it
isn't — the module loads cleanly either way (no module-level SystemExit
the way ``test_libreoffice_integration.py`` does it, so smoke runs without
LibreOffice still work).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import FIXTURES, SKILLS, run_script

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from odf_lib.odf_common import convert_with_soffice, find_soffice  # noqa: E402

    _SOFFICE: str | None = find_soffice()
except SystemExit:
    _SOFFICE = None
    convert_with_soffice = None  # type: ignore[assignment]


def _read_text(odt: Path) -> str:
    """Concatenate paragraph text from an ODT (for round-trip equality checks)."""
    with zipfile.ZipFile(odt) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    ns_text = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    parts: list[str] = []
    for tag in (f"{{{ns_text}}}p", f"{{{ns_text}}}h"):
        for el in root.iter(tag):
            parts.append("".join(el.itertext()))
    return "\n".join(parts)


@unittest.skipUnless(_SOFFICE, "LibreOffice/soffice not available")
class ConvertHelperTests(unittest.TestCase):
    """Unit tests for the convert_with_soffice library helper."""

    def test_odt_to_docx_produces_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            output = convert_with_soffice(odt, "docx", tmp_path / "out")
            self.assertTrue(output.exists())
            self.assertEqual(output.suffix, ".docx")
            self.assertGreater(output.stat().st_size, 0)

    def test_render_to_pdf_still_works_after_refactor(self) -> None:
        # render_to_pdf is now a wrapper around convert_with_soffice.
        # This is the safety net for the refactor.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            from odf_lib.odf_common import render_to_pdf

            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            pdf = render_to_pdf(odt, tmp_path / "out")
            self.assertTrue(pdf.exists())
            self.assertEqual(pdf.suffix, ".pdf")


@unittest.skipUnless(_SOFFICE, "LibreOffice/soffice not available")
class ConvertScriptTests(unittest.TestCase):
    """Per-skill convert.py CLI integration tests."""

    def test_odt_to_docx_and_back(self) -> None:
        # Use a minimal spec without footnotes/notes — those are valid in DOCX
        # but live in separate XML parts and don't appear in body paragraphs
        # after the import. Round-trip fidelity for the simple-prose 80% case
        # is what we're verifying here.
        import json

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps(
                    {
                        "title": "Round Trip",
                        "blocks": [
                            {"type": "heading", "level": 1, "text": "Chapter One"},
                            {"type": "paragraph", "text": "First paragraph of the round-trip test."},
                            {"type": "heading", "level": 2, "text": "Subsection"},
                            {"type": "paragraph", "text": "Second paragraph with some plain text."},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", spec, odt)
            text_before = _read_text(odt)

            qa = tmp_path / "qa"
            run_script(scripts / "convert.py", odt, "--to", "docx", "--outdir", qa)
            docx = qa / "doc.docx"
            self.assertTrue(docx.exists())

            qa2 = tmp_path / "qa2"
            run_script(scripts / "convert.py", docx, "--to", "odt", "--outdir", qa2)
            roundtripped = qa2 / "doc.odt"
            self.assertTrue(roundtripped.exists())
            text_after = _read_text(roundtripped)
            for paragraph in text_before.split("\n"):
                if paragraph.strip():
                    self.assertIn(paragraph.strip(), text_after)

    def test_odt_to_legacy_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            qa = tmp_path / "qa"
            run_script(scripts / "convert.py", odt, "--to", "doc", "--outdir", qa)
            self.assertTrue((qa / "doc.doc").exists())

    def test_ods_to_xlsx_and_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            ods = tmp_path / "book.ods"
            run_script(scripts / "create_minimal_ods.py", FIXTURES / "ods_workbook.json", ods)
            qa = tmp_path / "qa"
            run_script(scripts / "convert.py", ods, "--to", "xlsx", "--outdir", qa)
            self.assertTrue((qa / "book.xlsx").exists())

            qa2 = tmp_path / "qa2"
            run_script(scripts / "convert.py", qa / "book.xlsx", "--to", "ods", "--outdir", qa2)
            self.assertTrue((qa2 / "book.ods").exists())

    def test_ods_to_legacy_xls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            ods = tmp_path / "book.ods"
            run_script(scripts / "create_minimal_ods.py", FIXTURES / "ods_workbook.json", ods)
            qa = tmp_path / "qa"
            run_script(scripts / "convert.py", ods, "--to", "xls", "--outdir", qa)
            self.assertTrue((qa / "book.xls").exists())

    def test_odp_to_pptx_and_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", FIXTURES / "odp_slides.json", odp)
            qa = tmp_path / "qa"
            run_script(scripts / "convert.py", odp, "--to", "pptx", "--outdir", qa)
            self.assertTrue((qa / "deck.pptx").exists())

            qa2 = tmp_path / "qa2"
            run_script(scripts / "convert.py", qa / "deck.pptx", "--to", "odp", "--outdir", qa2)
            self.assertTrue((qa2 / "deck.odp").exists())

    def test_odp_to_legacy_ppt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", FIXTURES / "odp_slides.json", odp)
            qa = tmp_path / "qa"
            run_script(scripts / "convert.py", odp, "--to", "ppt", "--outdir", qa)
            self.assertTrue((qa / "deck.ppt").exists())

    def test_cross_family_rejected(self) -> None:
        # ODT convert.py with an .ods input must fail with a clear message.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = tmp_path / "book.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "create_minimal_ods.py",
                FIXTURES / "ods_workbook.json",
                ods,
            )
            qa = tmp_path / "qa"
            result = run_script(
                SKILLS / "odt" / "scripts" / "convert.py",
                ods,
                "--to",
                "docx",
                "--outdir",
                qa,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a text-document format", result.stdout)

    def test_invalid_target_format_rejected(self) -> None:
        # ODT convert.py with --to xlsx (wrong family) fails via argparse.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                FIXTURES / "odt_document.json",
                odt,
            )
            qa = tmp_path / "qa"
            result = run_script(
                SKILLS / "odt" / "scripts" / "convert.py",
                odt,
                "--to",
                "xlsx",
                "--outdir",
                qa,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
