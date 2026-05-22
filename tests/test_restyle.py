"""Tests for restyle.py — bulk paragraph/heading restyling."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

ODT = SKILLS / "odt" / "scripts"
NS = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def content_of(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def base_odt(tmp: Path) -> Path:
    spec = tmp / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "title": "T",
                "blocks": [
                    {"type": "heading", "level": 1, "text": "One"},
                    {"type": "paragraph", "text": "Body para."},
                    {"type": "heading", "level": 2, "text": "Two"},
                ],
            }
        ),
        encoding="utf-8",
    )
    odt = tmp / "doc.odt"
    run_script(ODT / "create_minimal_odt.py", spec, odt)
    return odt


def styles_of(path: Path, tag: str) -> list[str | None]:
    return [n.attrib.get(q("text", "style-name")) for n in content_of(path).iter(q("text", tag))]


class RestyleTests(unittest.TestCase):
    def test_restyle_headings_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "r.odt"
            result = run_script(ODT / "restyle.py", base_odt(tmp_path), "--headings", "--style", "Fancy", "-o", out)
            self.assertIn("restyled: 3", result.stdout)
            self.assertEqual(set(styles_of(out, "h")), {"Fancy"})
            # Paragraphs untouched.
            self.assertNotIn("Fancy", styles_of(out, "p"))

    def test_restyle_by_current_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "r.odt"
            run_script(ODT / "restyle.py", base_odt(tmp_path), "--current-style", "Body", "--style", "New", "-o", out)
            self.assertIn("New", styles_of(out, "p"))

    def test_restyle_by_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "r.odt"
            result = run_script(ODT / "restyle.py", base_odt(tmp_path), "--level", "2", "--style", "H2", "-o", out)
            self.assertIn("restyled: 1", result.stdout)

    def test_unknown_style_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "r.odt"
            result = run_script(
                ODT / "restyle.py", base_odt(tmp_path), "--headings", "--style", "Nonexistent", "-o", out
            )
            self.assertIn("not defined", result.stdout)


if __name__ == "__main__":
    unittest.main()
