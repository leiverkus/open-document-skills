"""Tests for ODT MathML embedding via add_math.py."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import FIXTURES, SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "math": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def read_manifest(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("META-INF/manifest.xml"))


HAVE_PANDOC = shutil.which("pandoc") is not None


class MathTests(unittest.TestCase):
    def _make_odt(self, tmp_path: Path, blocks: list[dict]) -> Path:
        spec = write_json(tmp_path / "spec.json", {"title": "T", "blocks": blocks})
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, odt)
        return odt

    def test_add_math_mathml_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Pythagoras"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_math.py",
                odt,
                "--mathml",
                FIXTURES / "sample_formula.mml",
                "--anchor",
                "Pythagoras",
                "-o",
                out,
            )
            # Object 1/ structure
            with zipfile.ZipFile(out) as archive:
                names = archive.namelist()
                self.assertIn("Object 1/content.xml", names)
                obj_content = archive.read("Object 1/content.xml")
            self.assertIn(b"http://www.w3.org/1998/Math/MathML", obj_content)
            self.assertIn(b"<math", obj_content)

    def test_add_math_mathml_inline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Inline math"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_math.py",
                odt,
                "--mathml-inline",
                '<math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi></math>',
                "--paragraph",
                "1",
                "-o",
                out,
            )
            content = read_content(out)
            objects = [o for o in content.iter() if o.tag == q("draw", "object")]
            self.assertEqual(len(objects), 1)
            self.assertEqual(objects[0].attrib.get(q("xlink", "href")), "./Object 1/")

    @unittest.skipUnless(HAVE_PANDOC, "pandoc not installed")
    def test_add_math_latex_via_pandoc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Einstein"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_math.py",
                odt,
                "--latex",
                "E = mc^2",
                "--anchor",
                "Einstein",
                "-o",
                out,
            )
            with zipfile.ZipFile(out) as archive:
                obj_content = archive.read("Object 1/content.xml")
            # Pandoc emits <math display="inline">…</math> with MathML inside.
            self.assertIn(b"<math", obj_content)
            self.assertIn(b"mc", obj_content)  # Some part of the formula

    def test_add_math_creates_two_manifest_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "P"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_math.py",
                odt,
                "--mathml",
                FIXTURES / "sample_formula.mml",
                "--paragraph",
                "1",
                "-o",
                out,
            )
            manifest = read_manifest(out)
            entries = {
                e.attrib.get(q("manifest", "full-path")): e.attrib.get(q("manifest", "media-type"))
                for e in manifest.findall("manifest:file-entry", NS)
            }
            self.assertEqual(entries.get("Object 1/"), "application/vnd.oasis.opendocument.formula")
            self.assertEqual(entries.get("Object 1/content.xml"), "text/xml")

    def test_add_math_two_consecutive_uses_object_1_and_object_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "First"},
                    {"type": "paragraph", "text": "Second"},
                ],
            )
            first = tmp_path / "first.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_math.py",
                odt,
                "--mathml",
                FIXTURES / "sample_formula.mml",
                "--anchor",
                "First",
                "-o",
                first,
            )
            second = tmp_path / "second.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_math.py",
                first,
                "--mathml",
                FIXTURES / "sample_formula.mml",
                "--anchor",
                "Second",
                "-o",
                second,
            )
            with zipfile.ZipFile(second) as archive:
                names = archive.namelist()
                self.assertIn("Object 1/content.xml", names)
                self.assertIn("Object 2/content.xml", names)

    def test_validate_refs_passes_with_math(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Eq"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_math.py",
                odt,
                "--mathml",
                FIXTURES / "sample_formula.mml",
                "--anchor",
                "Eq",
                "-o",
                out,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", out)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
