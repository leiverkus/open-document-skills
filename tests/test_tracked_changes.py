"""Tests for ODT tracked changes — record, list, and resolve."""

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
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def content_of(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def body_text(path: Path) -> str:
    result = run_script(ODT / "extract_text.py", path)
    return result.stdout


def base_odt(tmp: Path) -> Path:
    src = tmp / "doc.md"
    src.write_text(
        "# Tracked Test\n\nThe quick brown fox jumps over the lazy dog.\n",
        encoding="utf-8",
    )
    odt = tmp / "doc.odt"
    run_script(ODT / "create_from_markdown.py", src, odt)
    return odt


class RecordTests(unittest.TestCase):
    def test_tracked_insertion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "i.odt"
            run_script(
                ODT / "track_change.py",
                base_odt(tmp_path),
                "--insert",
                " very",
                "--anchor",
                "quick",
                "--author",
                "Ed",
                "-o",
                out,
            )
            content = content_of(out)
            self.assertEqual(len(list(content.iter(q("text", "change-start")))), 1)
            self.assertEqual(len(list(content.iter(q("text", "change-end")))), 1)
            region = content.find(f".//{q('text', 'changed-region')}")
            assert region is not None
            self.assertIsNotNone(region.find(q("text", "insertion")))

    def test_tracked_deletion_moves_text_to_region(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "d.odt"
            run_script(ODT / "track_change.py", base_odt(tmp_path), "--delete", "lazy ", "--author", "Ed", "-o", out)
            content = content_of(out)
            self.assertEqual(len(list(content.iter(q("text", "change")))), 1)
            deletion = content.find(f".//{q('text', 'deletion')}")
            assert deletion is not None
            self.assertEqual(deletion.find(q("text", "p")).text, "lazy ")

    def test_tracked_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "r.odt"
            run_script(
                ODT / "track_change.py",
                base_odt(tmp_path),
                "--replace",
                "brown",
                "--with",
                "red",
                "--author",
                "Ed",
                "-o",
                out,
            )
            content = content_of(out)
            self.assertEqual(len(list(content.iter(q("text", "changed-region")))), 2)
            self.assertEqual(len(list(content.iter(q("text", "change")))), 1)
            self.assertEqual(len(list(content.iter(q("text", "change-start")))), 1)

    def test_changed_region_carries_xml_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "i.odt"
            run_script(
                ODT / "track_change.py",
                base_odt(tmp_path),
                "--insert",
                "X",
                "--anchor",
                "fox",
                "--author",
                "Ed",
                "-o",
                out,
            )
            region = content_of(out).find(f".//{q('text', 'changed-region')}")
            assert region is not None
            self.assertIn("{http://www.w3.org/XML/1998/namespace}id", region.attrib)


class ListChangesTests(unittest.TestCase):
    def test_list_changes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "d.odt"
            run_script(ODT / "track_change.py", base_odt(tmp_path), "--delete", "lazy ", "--author", "Ed", "-o", out)
            changes = json.loads(run_script(ODT / "list_changes.py", out).stdout)
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]["kind"], "deletion")
            self.assertEqual(changes[0]["author"], "Ed")
            self.assertEqual(changes[0]["text"], "lazy ")


class ResolveTests(unittest.TestCase):
    def _three_changes(self, tmp_path: Path) -> Path:
        odt = base_odt(tmp_path)
        a = tmp_path / "a.odt"
        b = tmp_path / "b.odt"
        c = tmp_path / "c.odt"
        run_script(ODT / "track_change.py", odt, "--insert", " very", "--anchor", "quick", "--author", "E", "-o", a)
        run_script(ODT / "track_change.py", a, "--delete", "lazy ", "--author", "E", "-o", b)
        run_script(ODT / "track_change.py", b, "--replace", "brown", "--with", "red", "--author", "E", "-o", c)
        return c

    def test_accept_all_applies_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            staged = self._three_changes(tmp_path)
            out = tmp_path / "accepted.odt"
            run_script(ODT / "resolve_changes.py", staged, "--accept", "--all", "-o", out)
            text = body_text(out)
            self.assertIn("quick very red fox", text)
            self.assertNotIn("lazy", text)
            self.assertEqual(len(list(content_of(out).iter(q("text", "changed-region")))), 0)

    def test_reject_all_restores_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            staged = self._three_changes(tmp_path)
            out = tmp_path / "rejected.odt"
            run_script(ODT / "resolve_changes.py", staged, "--reject", "--all", "-o", out)
            self.assertIn("The quick brown fox jumps over the lazy dog.", body_text(out))

    def test_resolve_single_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            staged = self._three_changes(tmp_path)
            out = tmp_path / "one.odt"
            run_script(ODT / "resolve_changes.py", staged, "--accept", "--id", "ct1", "-o", out)
            # One of four regions resolved; the rest remain.
            self.assertEqual(len(list(content_of(out).iter(q("text", "changed-region")))), 3)


class ValidateTrackedChangeTests(unittest.TestCase):
    def test_validate_detects_dangling_change_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "i.odt"
            run_script(
                ODT / "track_change.py",
                base_odt(tmp_path),
                "--insert",
                "X",
                "--anchor",
                "fox",
                "--author",
                "E",
                "-o",
                out,
            )
            content = content_of(out)
            start = content.find(f".//{q('text', 'change-start')}")
            assert start is not None
            start.set(q("text", "change-id"), "nonexistent")
            broken = tmp_path / "broken.odt"
            with zipfile.ZipFile(out) as src, zipfile.ZipFile(broken, "w") as dst:
                for name in src.namelist():
                    data = ET.tostring(content) if name == "content.xml" else src.read(name)
                    dst.writestr(name, data)
            result = run_script(ODT / "validate_refs.py", broken, check=False)
            self.assertIn("references missing changed-region", result.stdout)


if __name__ == "__main__":
    unittest.main()
