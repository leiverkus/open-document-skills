"""Tests for the ODT template ecosystem: inspect, extract, apply.

Parallel to ``tests/test_templates.py`` (which covers ODP). Stdlib-only;
LibreOffice integration lives in ``test_libreoffice_integration.py``.
"""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import FIXTURES, SKILLS, run_script

TEMPLATES_DIR = SKILLS / "odt" / "templates"
TEMPLATE_NAMES = ("grant-proposal", "academic-paper", "letterhead", "cv", "dissertation")

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


class InspectTemplateTests(unittest.TestCase):
    def test_inspect_standalone_styles_xml(self) -> None:
        for name in TEMPLATE_NAMES:
            with self.subTest(template=name):
                styles_xml = TEMPLATES_DIR / name / "styles.xml"
                result = json.loads(run_script(SKILLS / "odt" / "scripts" / "inspect_template.py", styles_xml).stdout)
                # Each ODT template defines a page layout + master page + the
                # standard Title/Heading1/Body named paragraph styles.
                self.assertGreaterEqual(len(result["page_layouts"]), 1)
                self.assertGreaterEqual(len(result["master_pages"]), 1)
                para_names = {p.get("name") for p in result["paragraph_styles"]}
                for required in ("Title", "Heading1", "Body"):
                    self.assertIn(required, para_names, f"{name}: missing {required}")

    def test_inspect_odt_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            result = json.loads(run_script(SKILLS / "odt" / "scripts" / "inspect_template.py", odt).stdout)
            self.assertGreaterEqual(len(result["master_pages"]), 1)
            self.assertGreaterEqual(len(result["page_layouts"]), 1)

    def test_inspect_grant_proposal_outline_levels(self) -> None:
        # grant-proposal ships a 4-level outline numbering scheme.
        styles_xml = TEMPLATES_DIR / "grant-proposal" / "styles.xml"
        result = json.loads(run_script(SKILLS / "odt" / "scripts" / "inspect_template.py", styles_xml).stdout)
        self.assertGreaterEqual(len(result["outline_styles"]), 1)
        outline = result["outline_styles"][0]
        self.assertEqual(outline["name"], "Outline")
        self.assertEqual(len(outline["levels"]), 4)

    def test_inspect_dissertation_five_outline_levels(self) -> None:
        styles_xml = TEMPLATES_DIR / "dissertation" / "styles.xml"
        result = json.loads(run_script(SKILLS / "odt" / "scripts" / "inspect_template.py", styles_xml).stdout)
        outline = result["outline_styles"][0]
        self.assertEqual(len(outline["levels"]), 5)


class ExtractTemplateTests(unittest.TestCase):
    def test_extract_from_corpus_filters_auto_styles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_script(
                SKILLS / "odt" / "scripts" / "extract_template.py",
                FIXTURES / "corpus" / "odt-minimal.odt",
                "--name",
                "corpus-extracted",
                "--outdir",
                tmp_path,
            )
            extracted = tmp_path / "corpus-extracted"
            self.assertTrue((extracted / "styles.xml").exists())
            for required in ("LICENSE.txt", "PROVENANCE.md", "README.md"):
                self.assertTrue((extracted / required).exists())

    def test_extract_from_generated_odt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            run_script(
                SKILLS / "odt" / "scripts" / "extract_template.py",
                odt,
                "--name",
                "generated",
                "--outdir",
                tmp_path,
            )
            self.assertTrue((tmp_path / "generated" / "styles.xml").exists())

    def test_extract_with_license_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_script(
                SKILLS / "odt" / "scripts" / "extract_template.py",
                FIXTURES / "corpus" / "odt-minimal.odt",
                "--name",
                "with-license",
                "--outdir",
                tmp_path,
                "--license",
                "CC-BY-4.0",
                "--source",
                "https://example.com/template",
            )
            license_text = (tmp_path / "with-license" / "LICENSE.txt").read_text(encoding="utf-8")
            self.assertIn("CC-BY-4.0", license_text)
            provenance_text = (tmp_path / "with-license" / "PROVENANCE.md").read_text(encoding="utf-8")
            self.assertIn("https://example.com/template", provenance_text)


class ApplyTemplateTests(unittest.TestCase):
    def test_apply_each_shipped_template(self) -> None:
        for name in TEMPLATE_NAMES:
            with self.subTest(template=name):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    base = tmp_path / "base.odt"
                    out = tmp_path / "branded.odt"
                    run_script(
                        SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                        FIXTURES / "odt_document.json",
                        base,
                    )
                    result = json.loads(
                        run_script(
                            SKILLS / "odt" / "scripts" / "apply_template.py",
                            base,
                            "--template-name",
                            name,
                            "-o",
                            out,
                        ).stdout
                    )
                    self.assertEqual(result["status"], "ok", msg=str(result))
                    self.assertTrue(out.exists())
                    # The output styles.xml should contain at least the
                    # standard named paragraph styles defined by the template.
                    with zipfile.ZipFile(out) as archive:
                        styles = archive.read("styles.xml").decode("utf-8")
                    self.assertIn('style:name="Body"', styles)
                    self.assertIn('style:name="Heading1"', styles)

    def test_apply_with_explicit_template_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.odt"
            out = tmp_path / "branded.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", FIXTURES / "odt_document.json", base)
            json.loads(
                run_script(
                    SKILLS / "odt" / "scripts" / "apply_template.py",
                    base,
                    "--template",
                    TEMPLATES_DIR / "grant-proposal",
                    "-o",
                    out,
                ).stdout
            )
            self.assertTrue(out.exists())

    def test_apply_examples_dao_localisation(self) -> None:
        """The German DAO localisation (examples/dao/) is itself a valid template."""

        # Find repo root via the existing helpers convention.
        from helpers import ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.odt"
            out = tmp_path / "branded.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", FIXTURES / "odt_document.json", base)
            result = json.loads(
                run_script(
                    SKILLS / "odt" / "scripts" / "apply_template.py",
                    base,
                    "--template",
                    ROOT / "examples" / "dao",
                    "-o",
                    out,
                ).stdout
            )
            self.assertEqual(result["status"], "ok", msg=str(result))
            with zipfile.ZipFile(out) as archive:
                self.assertIn("Pictures/logo.png", archive.namelist())

    def test_apply_rejects_unknown_template_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.odt"
            out = tmp_path / "branded.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", FIXTURES / "odt_document.json", base)
            result = run_script(
                SKILLS / "odt" / "scripts" / "apply_template.py",
                base,
                "--template-name",
                "does-not-exist",
                "-o",
                out,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not found", result.stdout)


class TemplatesShippedTests(unittest.TestCase):
    """The five v1.13 templates must exist with their required files."""

    def test_all_five_templates_present_and_complete(self) -> None:
        for name in TEMPLATE_NAMES:
            with self.subTest(template=name):
                template_dir = TEMPLATES_DIR / name
                self.assertTrue(template_dir.is_dir(), f"missing template dir: {template_dir}")
                for required in ("styles.xml", "LICENSE.txt", "PROVENANCE.md", "README.md"):
                    self.assertTrue(
                        (template_dir / required).is_file(),
                        f"template {name} missing {required}",
                    )


if __name__ == "__main__":
    unittest.main()
