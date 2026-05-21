"""Tests for ODT cross-references: bookmarks, reference-marks, sequences, refs."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


class CrossRefTests(unittest.TestCase):
    def _make_odt(self, tmp_path: Path, blocks: list[dict]) -> Path:
        spec = write_json(tmp_path / "spec.json", {"title": "T", "blocks": blocks})
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, odt)
        return odt

    def test_add_point_bookmark_with_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello world"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_bookmark.py", odt, "--name", "K1", "--anchor", "Hello", "-o", out
            )
            content = read_content(out)
            marks = [b for b in content.iter() if b.tag == q("text", "bookmark")]
            self.assertEqual(len(marks), 1)
            self.assertEqual(marks[0].attrib.get(q("text", "name")), "K1")

    def test_add_range_bookmark_intra_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "before START middle END after"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_bookmark.py",
                odt,
                "--name",
                "RangeB",
                "--start-anchor",
                "START",
                "--end-anchor",
                "END",
                "-o",
                out,
            )
            content = read_content(out)
            starts = [b for b in content.iter() if b.tag == q("text", "bookmark-start")]
            ends = [b for b in content.iter() if b.tag == q("text", "bookmark-end")]
            self.assertEqual(len(starts), 1)
            self.assertEqual(len(ends), 1)
            self.assertEqual(starts[0].attrib.get(q("text", "name")), "RangeB")
            self.assertEqual(ends[0].attrib.get(q("text", "name")), "RangeB")

    def test_add_reference_mark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello world"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_reference.py", odt, "--mark", "thm1", "--anchor", "Hello", "-o", out
            )
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "reference-mark")]
            self.assertEqual(len(marks), 1)
            self.assertEqual(marks[0].attrib.get(q("text", "name")), "thm1")

    def test_add_bookmark_ref_with_chapter_display(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "Chapter target"},
                    {"type": "paragraph", "text": "see chapter"},
                ],
            )
            bookmarked = tmp_path / "bm.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_bookmark.py",
                odt,
                "--name",
                "C1",
                "--anchor",
                "Chapter target",
                "-o",
                bookmarked,
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_reference.py",
                bookmarked,
                "--ref-to",
                "C1",
                "--kind",
                "bookmark",
                "--anchor",
                "see chapter",
                "--display",
                "chapter",
                "-o",
                out,
            )
            content = read_content(out)
            refs = [r for r in content.iter() if r.tag == q("text", "bookmark-ref")]
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].attrib.get(q("text", "ref-name")), "C1")
            self.assertEqual(refs[0].attrib.get(q("text", "reference-format")), "chapter")

    def test_add_sequence_creates_decls_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Figure label"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_sequence.py",
                odt,
                "--sequence",
                "Figure",
                "--name",
                "fig:karte",
                "--anchor",
                "Figure label",
                "-o",
                out,
            )
            content = read_content(out)
            decls = content.find(".//office:text/text:sequence-decls", NS)
            assert decls is not None
            decls_list = decls.findall("text:sequence-decl", NS)
            self.assertEqual(len(decls_list), 1)
            self.assertEqual(decls_list[0].attrib.get(q("text", "name")), "Figure")
            seq = content.find(".//text:sequence", NS)
            assert seq is not None
            self.assertEqual(seq.attrib.get(q("text", "ref-name")), "fig:karte")

    def test_add_sequence_reuses_existing_decls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "Figure one"},
                    {"type": "paragraph", "text": "Figure two"},
                ],
            )
            first = tmp_path / "first.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_sequence.py",
                odt,
                "--sequence",
                "Figure",
                "--name",
                "f1",
                "--anchor",
                "Figure one",
                "-o",
                first,
            )
            second = tmp_path / "second.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_sequence.py",
                first,
                "--sequence",
                "Figure",
                "--name",
                "f2",
                "--anchor",
                "Figure two",
                "-o",
                second,
            )
            content = read_content(second)
            decls_list = content.findall(".//office:text/text:sequence-decls/text:sequence-decl", NS)
            self.assertEqual(len(decls_list), 1, "Figure decl should not be duplicated")
            sequences = content.findall(".//text:sequence", NS)
            self.assertEqual(len(sequences), 2)

    def test_add_sequence_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "Figure 1: example"},
                    {"type": "paragraph", "text": "see figure"},
                ],
            )
            with_seq = tmp_path / "with_seq.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_sequence.py",
                odt,
                "--sequence",
                "Figure",
                "--name",
                "f1",
                "--anchor",
                "Figure 1:",
                "-o",
                with_seq,
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_sequence.py",
                with_seq,
                "--ref-to",
                "f1",
                "--anchor",
                "see figure",
                "-o",
                out,
            )
            content = read_content(out)
            refs = [r for r in content.iter() if r.tag == q("text", "sequence-ref")]
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].attrib.get(q("text", "ref-name")), "f1")

    def test_list_refs_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "Hello world"},
                    {"type": "paragraph", "text": "see Hello"},
                ],
            )
            bm = tmp_path / "bm.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_bookmark.py", odt, "--name", "K", "--anchor", "Hello", "-o", bm
            )
            ref = tmp_path / "ref.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_reference.py",
                bm,
                "--ref-to",
                "K",
                "--kind",
                "bookmark",
                "--anchor",
                "see Hello",
                "-o",
                ref,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "list_refs.py", ref, "--json").stdout
            data = json.loads(result)
            self.assertEqual(len(data["bookmarks"]), 1)
            self.assertEqual(data["bookmarks"][0]["name"], "K")
            self.assertEqual(len(data["references"]), 1)
            self.assertEqual(data["references"][0]["ref_name"], "K")

    def test_validate_refs_detects_dangling_bookmark_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "see X"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_reference.py",
                odt,
                "--ref-to",
                "DoesNotExist",
                "--kind",
                "bookmark",
                "--anchor",
                "see X",
                "-o",
                out,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", out, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Dangling", result.stdout)

    def test_add_bookmark_cross_paragraph_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "first START here"},
                    {"type": "paragraph", "text": "middle paragraph"},
                    {"type": "paragraph", "text": "third END text"},
                ],
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_bookmark.py",
                odt,
                "--name",
                "CrossRange",
                "--start-anchor",
                "START",
                "--end-anchor",
                "END",
                "-o",
                out,
            )
            content = read_content(out)
            starts = [b for b in content.iter() if b.tag == q("text", "bookmark-start")]
            ends = [b for b in content.iter() if b.tag == q("text", "bookmark-end")]
            self.assertEqual(len(starts), 1)
            self.assertEqual(len(ends), 1)
            self.assertEqual(starts[0].attrib.get(q("text", "name")), "CrossRange")
            self.assertEqual(ends[0].attrib.get(q("text", "name")), "CrossRange")

    def test_add_reference_cross_paragraph_mark_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "Theorem 1 START stmt"},
                    {"type": "paragraph", "text": "proof body"},
                    {"type": "paragraph", "text": "END qed"},
                ],
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_reference.py",
                odt,
                "--mark-range",
                "thm1",
                "--start-anchor",
                "START",
                "--end-anchor",
                "END",
                "-o",
                out,
            )
            content = read_content(out)
            starts = [m for m in content.iter() if m.tag == q("text", "reference-mark-start")]
            ends = [m for m in content.iter() if m.tag == q("text", "reference-mark-end")]
            self.assertEqual(len(starts), 1)
            self.assertEqual(len(ends), 1)

    def test_validate_refs_detects_duplicate_bookmark_names(self) -> None:
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
                SKILLS / "odt" / "scripts" / "add_bookmark.py", odt, "--name", "DupBM", "--anchor", "First", "-o", first
            )
            second = tmp_path / "second.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_bookmark.py",
                first,
                "--name",
                "DupBM",
                "--anchor",
                "Second",
                "-o",
                second,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", second, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Duplicate", result.stdout)


if __name__ == "__main__":
    unittest.main()
