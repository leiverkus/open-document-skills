"""Tests for the ODP template ecosystem: inspect, extract, apply.

The full bridge (extract from .pptx) and rendering live in
``test_libreoffice_integration.py``; these tests are stdlib-only and cover
the structural pieces.
"""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import FIXTURES, SKILLS, run_script

TEMPLATES_DIR = SKILLS / "odp" / "templates"
TEMPLATE_NAMES = ("academic-blue", "dao-conference", "minimalist-mono")

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
                result = json.loads(run_script(SKILLS / "odp" / "scripts" / "inspect_template.py", styles_xml).stdout)
                self.assertIn("master_pages", result)
                self.assertIn("presentation_page_layouts", result)
                self.assertGreaterEqual(len(result["master_pages"]), 1)
                # Every shipped template ships at least the v1.8 6 standard layouts.
                self.assertGreaterEqual(len(result["presentation_page_layouts"]), 6)
                # And at least Title, Body, Notes named paragraph styles.
                paragraph_names = {p.get("name") for p in result["paragraph_styles"]}
                self.assertIn("Title", paragraph_names)
                self.assertIn("Body", paragraph_names)

    def test_inspect_odp_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp = tmp_path / "deck.odp"
            run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", FIXTURES / "odp_slides.json", odp)
            result = json.loads(run_script(SKILLS / "odp" / "scripts" / "inspect_template.py", odp).stdout)
            self.assertGreaterEqual(len(result["master_pages"]), 1)

    def test_inspect_extracted_master_background_resolved(self) -> None:
        # dao-conference has a solid background; the inspector should resolve it
        # via the drawing-page-style indirection.
        styles_xml = TEMPLATES_DIR / "dao-conference" / "styles.xml"
        result = json.loads(run_script(SKILLS / "odp" / "scripts" / "inspect_template.py", styles_xml).stdout)
        master = result["master_pages"][0]
        self.assertEqual(master["background"], "#02416C")


class ExtractTemplateTests(unittest.TestCase):
    def test_extract_from_corpus_filters_auto_styles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_script(
                SKILLS / "odp" / "scripts" / "extract_template.py",
                FIXTURES / "corpus" / "odp-minimal.odp",
                "--name",
                "corpus-extracted",
                "--outdir",
                tmp_path,
            )
            extracted = tmp_path / "corpus-extracted"
            self.assertTrue((extracted / "styles.xml").exists())
            self.assertTrue((extracted / "LICENSE.txt").exists())
            self.assertTrue((extracted / "PROVENANCE.md").exists())
            self.assertTrue((extracted / "README.md").exists())

            # Auto-styles filter should leave fewer auto-styles than the original.
            with zipfile.ZipFile(FIXTURES / "corpus" / "odp-minimal.odp") as archive:
                original_root = ET.fromstring(archive.read("styles.xml"))
            original_count = len(original_root.findall(".//office:automatic-styles/style:style", NS))

            extracted_root = ET.parse(extracted / "styles.xml").getroot()
            extracted_count = len(extracted_root.findall(".//office:automatic-styles/style:style", NS))

            self.assertLess(extracted_count, original_count, "extract did not filter any auto-styles")

    def test_extract_from_generated_odp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp = tmp_path / "deck.odp"
            run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", FIXTURES / "odp_slides.json", odp)
            run_script(
                SKILLS / "odp" / "scripts" / "extract_template.py",
                odp,
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
                SKILLS / "odp" / "scripts" / "extract_template.py",
                FIXTURES / "corpus" / "odp-minimal.odp",
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
                    base = tmp_path / "base.odp"
                    out = tmp_path / "branded.odp"
                    run_script(
                        SKILLS / "odp" / "scripts" / "create_minimal_odp.py",
                        FIXTURES / "odp_slides.json",
                        base,
                    )
                    result = json.loads(
                        run_script(
                            SKILLS / "odp" / "scripts" / "apply_template.py",
                            base,
                            "--template-name",
                            name,
                            "-o",
                            out,
                        ).stdout
                    )
                    self.assertEqual(result["status"], "ok", msg=str(result))
                    self.assertTrue(out.exists())
                    # The output styles.xml should contain a string from the template.
                    with zipfile.ZipFile(out) as archive:
                        styles = archive.read("styles.xml").decode("utf-8")
                    self.assertIn("dp-default", styles)

    def test_apply_with_explicit_template_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.odp"
            out = tmp_path / "branded.odp"
            run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", FIXTURES / "odp_slides.json", base)
            json.loads(
                run_script(
                    SKILLS / "odp" / "scripts" / "apply_template.py",
                    base,
                    "--template",
                    TEMPLATES_DIR / "dao-conference",
                    "-o",
                    out,
                ).stdout
            )
            # dao-conference ships a logo; it must be embedded in the output.
            with zipfile.ZipFile(out) as archive:
                self.assertIn("Pictures/logo.png", archive.namelist())

    def test_apply_rejects_unknown_template_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.odp"
            out = tmp_path / "branded.odp"
            run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", FIXTURES / "odp_slides.json", base)
            result = run_script(
                SKILLS / "odp" / "scripts" / "apply_template.py",
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
    """The three v1.12 templates must exist with their required files."""

    def test_all_three_templates_present_and_complete(self) -> None:
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
