"""Tests for ODT comments — office:annotation point and range insertion."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

ODT = SKILLS / "odt" / "scripts"
NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def content_of(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def base_odt(tmp: Path) -> Path:
    src = tmp / "doc.md"
    src.write_text(
        "# Comment Test\n\nThe quick brown fox jumps over the lazy dog.\n",
        encoding="utf-8",
    )
    odt = tmp / "doc.odt"
    run_script(ODT / "create_from_markdown.py", src, odt)
    return odt


class PointCommentTests(unittest.TestCase):
    def test_point_comment_inserted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = base_odt(tmp_path)
            out = tmp_path / "c.odt"
            run_script(
                ODT / "add_comment.py", odt, "--anchor", "quick", "--author", "Rev", "--text", "Check.", "-o", out
            )
            annotations = list(content_of(out).iter(q("office", "annotation")))
            self.assertEqual(len(annotations), 1)
            creator = annotations[0].find(q("dc", "creator"))
            assert creator is not None
            self.assertEqual(creator.text, "Rev")
            self.assertEqual(annotations[0].find(q("text", "p")).text, "Check.")

    def test_auto_named_and_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = base_odt(tmp_path)
            one = tmp_path / "c1.odt"
            two = tmp_path / "c2.odt"
            run_script(ODT / "add_comment.py", odt, "--anchor", "quick", "--author", "A", "--text", "x", "-o", one)
            run_script(ODT / "add_comment.py", one, "--anchor", "lazy", "--author", "B", "--text", "y", "-o", two)
            names = sorted(a.attrib.get(q("office", "name")) for a in content_of(two).iter(q("office", "annotation")))
            self.assertEqual(names, ["cmt1", "cmt2"])


class RangeCommentTests(unittest.TestCase):
    def test_range_comment_inserts_matched_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = base_odt(tmp_path)
            out = tmp_path / "c.odt"
            run_script(
                ODT / "add_comment.py",
                odt,
                "--start-anchor",
                "quick",
                "--end-anchor",
                "fox",
                "--author",
                "Rev",
                "--text",
                "Range note.",
                "-o",
                out,
            )
            content = content_of(out)
            starts = list(content.iter(q("office", "annotation")))
            ends = list(content.iter(q("office", "annotation-end")))
            self.assertEqual(len(starts), 1)
            self.assertEqual(len(ends), 1)
            self.assertEqual(starts[0].attrib.get(q("office", "name")), ends[0].attrib.get(q("office", "name")))


class ListCommentsTests(unittest.TestCase):
    def test_list_comments_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = base_odt(tmp_path)
            out = tmp_path / "c.odt"
            run_script(ODT / "add_comment.py", odt, "--anchor", "fox", "--author", "Rev", "--text", "Note.", "-o", out)
            result = run_script(ODT / "list_comments.py", out)
            comments = json.loads(result.stdout)
            self.assertEqual(len(comments), 1)
            self.assertEqual(comments[0]["author"], "Rev")
            self.assertEqual(comments[0]["kind"], "point")
            self.assertEqual(comments[0]["text"], "Note.")


class ValidateCommentTests(unittest.TestCase):
    def test_validate_detects_duplicate_annotation_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = base_odt(tmp_path)
            out = tmp_path / "c.odt"
            run_script(
                ODT / "add_comment.py",
                odt,
                "--anchor",
                "quick",
                "--author",
                "A",
                "--text",
                "x",
                "--name",
                "dup",
                "-o",
                out,
            )
            # Inject a second annotation with the same name.
            content = content_of(out)
            paragraph = next(p for p in content.iter(q("text", "p")) if p.text)
            ET.SubElement(paragraph, q("office", "annotation"), {q("office", "name"): "dup"})
            broken = tmp_path / "broken.odt"
            with zipfile.ZipFile(out) as src, zipfile.ZipFile(broken, "w") as dst:
                for name in src.namelist():
                    data = ET.tostring(content) if name == "content.xml" else src.read(name)
                    dst.writestr(name, data)
            result = run_script(ODT / "validate_refs.py", broken, check=False)
            self.assertIn("Duplicate office:annotation name", result.stdout)


if __name__ == "__main__":
    unittest.main()
