"""Tests for the ODT footnote API: add_footnote.py, list_notes.py, validate_refs note checks."""

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
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def read_meta(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("meta.xml"))


def write_zip_replacement(input_file: Path, output_file: Path, member: str, xml_root: ET.Element) -> None:
    """Replace a single member in a ZIP-based ODF."""
    payload = ET.tostring(xml_root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(input_file) as src:
        with zipfile.ZipFile(output_file, "w") as dst:
            for name in src.namelist():
                if name == "mimetype":
                    dst.writestr("mimetype", src.read("mimetype"), compress_type=zipfile.ZIP_STORED)
                elif name == member:
                    dst.writestr(name, payload, compress_type=zipfile.ZIP_DEFLATED)
                else:
                    dst.writestr(name, src.read(name), compress_type=zipfile.ZIP_DEFLATED)


class FootnoteAPITests(unittest.TestCase):
    def _make_odt(self, tmp_path: Path, blocks: list[dict]) -> Path:
        spec = write_json(tmp_path / "spec.json", {"title": "T", "blocks": blocks})
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, odt)
        return odt

    def test_add_footnote_with_text_anchor_inserts_after_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello ODT world"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--anchor",
                "Hello ODT",
                "--body",
                "First note",
                "-o",
                out,
            )
            content = read_content(out)
            notes = [n for n in content.iter() if n.tag == q("text", "note")]
            self.assertEqual(len(notes), 1)
            note = notes[0]
            self.assertEqual(note.attrib.get(q("text", "id")), "ftn0")

    def test_add_footnote_with_paragraph_index_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "First"},
                    {"type": "paragraph", "text": "Second"},
                ],
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--paragraph",
                "2",
                "--position",
                "end",
                "--body",
                "Tail note",
                "-o",
                out,
            )
            content = read_content(out)
            notes = [n for n in content.iter() if n.tag == q("text", "note")]
            self.assertEqual(len(notes), 1)

    def test_add_footnote_anchor_in_inline_span_preserves_span(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "PLACEHOLDER"}])
            # Patch content.xml: replace the simple paragraph with one containing a span
            content = read_content(odt)
            text_el = content.find(".//office:text", NS)
            assert text_el is not None
            for child in list(text_el):
                text_el.remove(child)
            ns_attrs = (
                'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
                'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            )
            injected = ET.fromstring(f"<text:p {ns_attrs}>Hallo <text:span>Welt</text:span>!</text:p>")
            text_el.append(injected)
            patched = tmp_path / "patched.odt"
            write_zip_replacement(odt, patched, "content.xml", content)
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                patched,
                "--anchor",
                "Welt",
                "--body",
                "Note",
                "-o",
                out,
            )
            content2 = read_content(out)
            spans = [s for s in content2.iter() if s.tag == q("text", "span")]
            self.assertEqual(len(spans), 1, "text:span must be preserved")
            self.assertEqual(spans[0].text, "Welt")
            notes = [n for n in content2.iter() if n.tag == q("text", "note")]
            self.assertEqual(len(notes), 1)

    def test_add_footnote_auto_increments_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello ODT"}])
            first = tmp_path / "first.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--anchor",
                "Hello",
                "--body",
                "First",
                "-o",
                first,
            )
            second = tmp_path / "second.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                first,
                "--anchor",
                "ODT",
                "--body",
                "Second",
                "-o",
                second,
            )
            content = read_content(second)
            ids = [
                n.attrib.get(q("text", "id"))
                for n in content.iter()
                if n.tag == q("text", "note") and n.attrib.get(q("text", "id"))
            ]
            self.assertIn("ftn0", ids)
            self.assertIn("ftn1", ids)

    def test_add_endnote_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--anchor",
                "Hello",
                "--body",
                "End",
                "--class",
                "endnote",
                "-o",
                out,
            )
            content = read_content(out)
            notes = [n for n in content.iter() if n.tag == q("text", "note")]
            self.assertEqual(notes[0].attrib.get(q("text", "note-class")), "endnote")
            self.assertTrue(notes[0].attrib.get(q("text", "id")).startswith("edn"))

    def test_list_notes_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello ODT world"}])
            with_note = tmp_path / "with_note.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--anchor",
                "Hello ODT",
                "--body",
                "Hello note",
                "-o",
                with_note,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "list_notes.py", with_note, "--json").stdout
            data = json.loads(result)
            anchored = [n for n in data if n["paragraph_index"] is not None]
            self.assertEqual(len(anchored), 1)
            self.assertEqual(anchored[0]["id"], "ftn0")
            self.assertEqual(anchored[0]["body"], "Hello note")
            self.assertIn("Hello ODT", anchored[0]["anchor_context"])
            self.assertIn("{NOTE}", anchored[0]["anchor_context"])

    def test_validate_refs_detects_duplicate_note_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello"}])
            first = tmp_path / "first.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--anchor",
                "Hello",
                "--id",
                "ftn0",
                "--body",
                "A",
                "-o",
                first,
            )
            second = tmp_path / "second.odt"
            # Force duplicate id by manually injecting another note with same id
            content = read_content(first)
            text_el = content.find(".//office:text", NS)
            assert text_el is not None
            # Add a sibling paragraph with another note ftn0
            ns_attrs = (
                'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
                'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            )
            dup = ET.fromstring(
                f'<text:p {ns_attrs}>Other<text:note text:note-class="footnote" text:id="ftn0">'
                f"<text:note-citation>*</text:note-citation>"
                f"<text:note-body><text:p>dup</text:p></text:note-body></text:note></text:p>"
            )
            text_el.append(dup)
            write_zip_replacement(first, second, "content.xml", content)
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", second, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Duplicate", result.stdout)

    def test_add_footnote_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--anchor",
                "Hello",
                "--body",
                "x",
                "-o",
                out,
            )
            meta = read_meta(out)
            cycles = meta.find(f".//{{{NS['meta']}}}editing-cycles")
            assert cycles is not None
            self.assertEqual(cycles.text, "1")

    def test_add_footnote_no_match_warns_and_no_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello"}])
            out = tmp_path / "out.odt"
            result = run_script(
                SKILLS / "odt" / "scripts" / "add_footnote.py",
                odt,
                "--anchor",
                "MissingText",
                "--body",
                "x",
                "-o",
                out,
            )
            # Note count in output should match input (no new note)
            content_in = read_content(odt)
            content_out = read_content(out)
            notes_in = [n for n in content_in.iter() if n.tag == q("text", "note")]
            notes_out = [n for n in content_out.iter() if n.tag == q("text", "note")]
            self.assertEqual(len(notes_in), len(notes_out))
            self.assertIn("anchor not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
