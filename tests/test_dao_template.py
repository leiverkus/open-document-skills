"""Tests for the DAO branded template injection and end-to-end build."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import ROOT, SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def read_member(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read(name)


class DAOTemplateTests(unittest.TestCase):
    def test_dao_styles_xml_defines_branded_styles(self) -> None:
        styles = ET.fromstring((ROOT / "examples" / "dao" / "styles.xml").read_bytes())
        defined = {s.attrib.get(q("style", "name")) for s in styles.iter(q("style", "style"))}
        for required in ("DAO-Title", "DAO-Heading-1", "DAO-Heading-2", "DAO-Body", "DAO-Quote", "DAO-Caption"):
            self.assertIn(required, defined, f"missing required DAO style {required!r}")

    def test_dao_page_layout_a4_with_dfg_margins(self) -> None:
        styles = ET.fromstring((ROOT / "examples" / "dao" / "styles.xml").read_bytes())
        layouts = list(styles.iter(q("style", "page-layout")))
        self.assertEqual(len(layouts), 1)
        layout = layouts[0]
        self.assertEqual(layout.attrib.get(q("style", "name")), "DAO-A4")
        props = layout.find(q("style", "page-layout-properties"))
        assert props is not None
        self.assertEqual(props.attrib.get(q("fo", "page-width")), "21cm")
        self.assertEqual(props.attrib.get(q("fo", "page-height")), "29.7cm")
        self.assertEqual(props.attrib.get(q("fo", "margin-top")), "2.5cm")

    def test_dao_master_page_has_header_and_footer(self) -> None:
        styles = ET.fromstring((ROOT / "examples" / "dao" / "styles.xml").read_bytes())
        master = styles.find(".//style:master-page", NS)
        assert master is not None
        self.assertIsNotNone(master.find("style:header", NS))
        self.assertIsNotNone(master.find("style:footer", NS))

    def test_dao_heading_outline_numbering_three_levels(self) -> None:
        styles = ET.fromstring((ROOT / "examples" / "dao" / "styles.xml").read_bytes())
        outline = styles.find(".//text:outline-style", NS)
        assert outline is not None
        levels = outline.findall("text:outline-level-style", NS)
        self.assertGreaterEqual(len(levels), 3)

    def test_inject_styles_replaces_styles_xml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                ROOT / "examples" / "dao" / "spec.json",
                base,
            )
            # Use the lib helper in-process
            sys.path.insert(0, str(SKILLS / "odt" / "scripts"))
            from odt_common import inject_styles_from_file

            styled = tmp_path / "styled.odt"
            missing = inject_styles_from_file(base, ROOT / "examples" / "dao" / "styles.xml", styled)
            # The DAO spec uses DAO-* styles; they're all defined in dao/styles.xml.
            # Body might or might not be — but Body is defined too in our styles.xml.
            self.assertEqual(missing, [])
            # Check styles.xml content was actually replaced
            new_styles = read_member(styled, "styles.xml")
            self.assertIn(b"DAO-Heading-1", new_styles)
            self.assertIn(b"#02416C", new_styles)

    def test_dao_build_grant_proposal_uses_dao_styles(self) -> None:
        """End-to-end: the produced grant_proposal.odt uses DAO-* styles."""
        subprocess.run(
            [sys.executable, str(ROOT / "examples" / "dao" / "build_grant_proposal.py")],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        final = ROOT / "examples" / "dao" / "output" / "grant_proposal.odt"
        self.assertTrue(final.exists())
        content = ET.fromstring(read_member(final, "content.xml"))
        # Headings should reference DAO-Heading-1
        headings = [h.attrib.get(q("text", "style-name")) for h in content.iter(q("text", "h"))]
        self.assertIn("DAO-Heading-1", headings)
        # styles.xml must contain DAO styles
        styles_bytes = read_member(final, "styles.xml")
        self.assertIn(b"DAO-Heading-1", styles_bytes)
        # Logo embedded in Pictures/
        with zipfile.ZipFile(final) as archive:
            self.assertIn("Pictures/logo.png", archive.namelist())


if __name__ == "__main__":
    unittest.main()
