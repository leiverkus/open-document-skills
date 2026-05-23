"""Tests for ODT generated indexes: TOC, bibliography, illustration/table index,
alphabetical index, plus the ``add_index_mark`` marker script and the
``update_indexes`` soffice-driven refresh.

The refresh integration test is in ``test_libreoffice_integration.py``;
this file only exercises the offline-buildable parts.
"""

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
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class IndexInserterTests(unittest.TestCase):
    def _make_odt(self, tmp_path: Path, blocks: list[dict]) -> Path:
        spec = write_json(tmp_path / "spec.json", {"title": "T", "blocks": blocks})
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, odt)
        return odt

    def _doc_with_headings(self, tmp_path: Path) -> Path:
        return self._make_odt(
            tmp_path,
            [
                {"type": "heading", "level": 1, "text": "Intro"},
                {"type": "paragraph", "text": "First chapter."},
                {"type": "heading", "level": 2, "text": "Background"},
                {"type": "paragraph", "text": "More."},
                {"type": "heading", "level": 1, "text": "Methods"},
                {"type": "paragraph", "text": "Description."},
            ],
        )

    # ---- add_toc.py --------------------------------------------------------

    def test_add_toc_at_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--at", "start", "-o", out)
            content = read_content(out)
            tocs = list(content.iter(q("text", "table-of-content")))
            self.assertEqual(len(tocs), 1)
            toc = tocs[0]
            self.assertEqual(toc.attrib.get(q("text", "name")), "Table of Contents1")
            self.assertIsNotNone(toc.find(q("text", "table-of-content-source")))
            body = toc.find(q("text", "index-body"))
            self.assertIsNotNone(body)
            # Placeholder body has exactly one text:index-title child with one paragraph.
            titles = list(body.iter(q("text", "index-title")))
            self.assertEqual(len(titles), 1)
            self.assertEqual(titles[0].attrib.get(q("text", "name")), "Table of Contents1_Head")

    def test_add_toc_after_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--paragraph", "1", "-o", out)
            content = read_content(out)
            office_text = content.find(".//office:text", NS)
            assert office_text is not None
            top = [c for c in office_text if c.tag in {q("text", "h"), q("text", "p"), q("text", "table-of-content")}]
            # TOC should be the 2nd top-level block (after the first heading).
            self.assertEqual(top[1].tag, q("text", "table-of-content"))

    def test_add_toc_with_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--anchor", "Background", "-o", out)
            content = read_content(out)
            tocs = list(content.iter(q("text", "table-of-content")))
            self.assertEqual(len(tocs), 1)

    def test_add_toc_levels_clamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--at", "start", "--levels", "5", "-o", out)
            content = read_content(out)
            source = next(iter(content.iter(q("text", "table-of-content-source"))))
            self.assertEqual(source.attrib.get(q("text", "outline-level")), "5")
            entries = list(source.iter(q("text", "table-of-content-entry-template")))
            self.assertEqual(len(entries), 5)

    # ---- add_bibliography.py ----------------------------------------------

    def test_add_bibliography_at_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_bibliography.py", odt, "--at", "end", "-o", out)
            content = read_content(out)
            bibs = list(content.iter(q("text", "bibliography")))
            self.assertEqual(len(bibs), 1)
            self.assertIsNotNone(bibs[0].find(q("text", "bibliography-source")))
            self.assertIsNotNone(bibs[0].find(q("text", "index-body")))

    # ---- add_illustration_index.py ----------------------------------------

    def test_add_illustration_index_figure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_illustration_index.py",
                odt,
                "--at",
                "end",
                "--sequence",
                "Figure",
                "-o",
                out,
            )
            content = read_content(out)
            idx_list = list(content.iter(q("text", "illustration-index")))
            self.assertEqual(len(idx_list), 1)
            source = idx_list[0].find(q("text", "illustration-index-source"))
            self.assertIsNotNone(source)
            assert source is not None
            self.assertEqual(source.attrib.get(q("text", "caption-sequence-name")), "Figure")

    def test_add_illustration_index_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_illustration_index.py",
                odt,
                "--at",
                "end",
                "--sequence",
                "Table",
                "-o",
                out,
            )
            content = read_content(out)
            # --sequence Table uses text:table-index container.
            tables = list(content.iter(q("text", "table-index")))
            self.assertEqual(len(tables), 1)
            source = tables[0].find(q("text", "table-index-source"))
            self.assertIsNotNone(source)
            assert source is not None
            self.assertEqual(source.attrib.get(q("text", "caption-sequence-name")), "Table")

    # ---- add_alphabetical_index.py ----------------------------------------

    def test_add_alphabetical_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_alphabetical_index.py", odt, "--at", "end", "-o", out)
            content = read_content(out)
            idx_list = list(content.iter(q("text", "alphabetical-index")))
            self.assertEqual(len(idx_list), 1)
            self.assertIsNotNone(idx_list[0].find(q("text", "alphabetical-index-source")))

    # ---- add_index_mark.py ------------------------------------------------

    def test_add_index_mark_with_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_index_mark.py",
                odt,
                "--anchor",
                "First chapter",
                "--key1",
                "Chapters",
                "-o",
                out,
            )
            content = read_content(out)
            marks = list(content.iter(q("text", "alphabetical-index-mark")))
            self.assertEqual(len(marks), 1)
            self.assertEqual(marks[0].attrib.get(q("text", "key1")), "Chapters")
            self.assertEqual(marks[0].attrib.get(q("text", "string-value")), "Chapters")

    def test_add_index_mark_with_key2_and_string_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_index_mark.py",
                odt,
                "--anchor",
                "Background",
                "--key1",
                "Topics",
                "--key2",
                "Background",
                "--string-value",
                "Background research",
                "-o",
                out,
            )
            content = read_content(out)
            marks = list(content.iter(q("text", "alphabetical-index-mark")))
            self.assertEqual(len(marks), 1)
            self.assertEqual(marks[0].attrib.get(q("text", "key1")), "Topics")
            self.assertEqual(marks[0].attrib.get(q("text", "key2")), "Background")
            self.assertEqual(marks[0].attrib.get(q("text", "string-value")), "Background research")

    def test_add_index_mark_by_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_index_mark.py",
                odt,
                "--paragraph",
                "2",
                "--key1",
                "K",
                "-o",
                out,
            )
            content = read_content(out)
            self.assertEqual(len(list(content.iter(q("text", "alphabetical-index-mark")))), 1)

    # ---- validate_refs.py warn-checks -------------------------------------

    def test_validate_warns_on_empty_bibliography(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            with_bib = tmp_path / "bib.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_bibliography.py", odt, "--at", "end", "-o", with_bib)
            result = json.loads(run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", with_bib).stdout)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(
                any("text:bibliography" in w and "no text:bibliography-mark" in w for w in result["warnings"]),
                f"missing empty-bibliography warning: {result['warnings']}",
            )

    def test_validate_warns_on_illustration_index_without_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            with_idx = tmp_path / "illu.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_illustration_index.py",
                odt,
                "--at",
                "end",
                "--sequence",
                "Figure",
                "-o",
                with_idx,
            )
            result = json.loads(run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", with_idx).stdout)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(
                any("Figure" in w and "no matching text:sequence" in w for w in result["warnings"]),
                f"missing sequence-name mismatch warning: {result['warnings']}",
            )

    def test_validate_warns_on_alphabetical_index_without_marks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            with_idx = tmp_path / "alpha.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_alphabetical_index.py", odt, "--at", "end", "-o", with_idx)
            result = json.loads(run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", with_idx).stdout)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(
                any(
                    "text:alphabetical-index" in w and "no text:alphabetical-index-mark" in w
                    for w in result["warnings"]
                ),
                f"missing empty-alphabetical-index warning: {result['warnings']}",
            )

    def test_validate_no_warning_for_toc_with_headings(self) -> None:
        # A TOC over a doc with H1/H2 should NOT trigger the empty-TOC warning.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._doc_with_headings(tmp_path)
            with_toc = tmp_path / "toc.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--at", "start", "-o", with_toc)
            result = json.loads(run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", with_toc).stdout)
            for w in result["warnings"]:
                self.assertNotIn("no matching headings", w)

    def test_validate_warns_on_empty_toc(self) -> None:
        # A TOC over a doc with NO headings should trigger the warning.
        # create_minimal_odt emits a title heading when "title" is set, so we
        # build the spec without a title.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = write_json(
                tmp_path / "spec.json",
                {"blocks": [{"type": "paragraph", "text": "Just prose, no headings."}]},
            )
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, odt)
            with_toc = tmp_path / "toc.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--at", "start", "-o", with_toc)
            result = json.loads(run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", with_toc).stdout)
            self.assertTrue(
                any("no matching headings" in w for w in result["warnings"]),
                f"missing empty-TOC warning: {result['warnings']}",
            )


class StrictValidationTests(unittest.TestCase):
    """The four inserted indexes must keep ``validate_refs --strict`` green."""

    def _make(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "spec.json",
            {
                "title": "T",
                "blocks": [
                    {"type": "heading", "level": 1, "text": "Intro"},
                    {"type": "paragraph", "text": "Body."},
                ],
            },
        )
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, odt)
        return odt

    def test_indexes_pass_strict(self) -> None:
        try:
            import lxml  # noqa: F401
        except ImportError:
            self.skipTest("lxml not installed")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make(tmp_path)
            step1 = tmp_path / "1.odt"
            step2 = tmp_path / "2.odt"
            step3 = tmp_path / "3.odt"
            step4 = tmp_path / "4.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--at", "start", "-o", step1)
            run_script(SKILLS / "odt" / "scripts" / "add_bibliography.py", step1, "--at", "end", "-o", step2)
            run_script(
                SKILLS / "odt" / "scripts" / "add_illustration_index.py",
                step2,
                "--at",
                "end",
                "--sequence",
                "Figure",
                "-o",
                step3,
            )
            run_script(SKILLS / "odt" / "scripts" / "add_alphabetical_index.py", step3, "--at", "end", "-o", step4)
            result = json.loads(run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", step4, "--strict").stdout)
            self.assertEqual(result["status"], "ok", msg=str(result))


if __name__ == "__main__":
    unittest.main()
