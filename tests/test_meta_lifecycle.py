"""Tests for meta.xml lifecycle updates on edit operations."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import FIXTURES, SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def read_meta(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        with archive.open("meta.xml") as handle:
            return ET.parse(handle).getroot()


def meta_field(meta: ET.Element, prefix: str, local: str) -> str | None:
    el = meta.find(f".//{{{NS[prefix]}}}{local}")
    return el.text if el is not None else None


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class MetaLifecycleTests(unittest.TestCase):
    def test_odt_replace_text_sets_modification_and_generator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            time.sleep(1)
            replaced = tmp_path / "replaced.odt"
            run_script(scripts / "replace_text.py", odt, "Hello ODT", "Hi", "-o", replaced)
            meta = read_meta(replaced)
            self.assertIsNotNone(meta_field(meta, "meta", "modification-date"))
            generator = meta_field(meta, "meta", "generator")
            assert generator is not None
            self.assertTrue(generator.startswith("open-document-skills/"))
            self.assertEqual(meta_field(meta, "meta", "editing-cycles"), "1")

    def test_odt_repeated_edits_increment_editing_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            first = tmp_path / "first.odt"
            run_script(scripts / "replace_text.py", odt, "Hello ODT", "Hi", "-o", first)
            second = tmp_path / "second.odt"
            run_script(scripts / "replace_text.py", first, "Hi", "Hi again", "-o", second)
            self.assertEqual(meta_field(read_meta(second), "meta", "editing-cycles"), "2")

    def test_odt_add_image_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            with_image = tmp_path / "with_image.odt"
            run_script(scripts / "add_image.py", odt, FIXTURES / "image.svg", "-o", with_image)
            meta = read_meta(with_image)
            self.assertEqual(meta_field(meta, "meta", "editing-cycles"), "1")
            self.assertIsNotNone(meta_field(meta, "meta", "modification-date"))

    def test_odp_replace_text_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = write_json(tmp_path / "deck.json", {"slides": [{"name": "S", "title": "Old"}]})
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            out = tmp_path / "out.odp"
            run_script(scripts / "replace_text.py", odp, "Old", "New", "-o", out)
            self.assertEqual(meta_field(read_meta(out), "meta", "editing-cycles"), "1")

    def test_odp_clone_slide_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = write_json(tmp_path / "deck.json", {"slides": [{"name": "S", "title": "T"}]})
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            out = tmp_path / "out.odp"
            run_script(scripts / "clone_slide.py", odp, "--source-slide", "1", "--name", "Clone", "-o", out)
            self.assertEqual(meta_field(read_meta(out), "meta", "editing-cycles"), "1")

    def test_ods_replace_cells_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            spec = write_json(tmp_path / "wb.json", {"sheets": [{"name": "Data", "rows": [["A"]]}]})
            ods = tmp_path / "wb.ods"
            run_script(scripts / "create_minimal_ods.py", spec, ods)
            out = tmp_path / "out.ods"
            run_script(scripts / "replace_cells.py", ods, "Data!B2=42", "-o", out)
            self.assertEqual(meta_field(read_meta(out), "meta", "editing-cycles"), "1")

    def test_odg_replace_text_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            spec = write_json(
                tmp_path / "d.json",
                {"pages": [{"name": "P", "items": [{"type": "text", "text": "Old"}]}]},
            )
            odg = tmp_path / "d.odg"
            run_script(scripts / "create_minimal_odg.py", spec, odg)
            out = tmp_path / "out.odg"
            run_script(scripts / "replace_text.py", odg, "Old", "New", "-o", out)
            self.assertEqual(meta_field(read_meta(out), "meta", "editing-cycles"), "1")

    def test_odg_add_image_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            spec = write_json(
                tmp_path / "d.json",
                {"pages": [{"name": "P"}]},
            )
            odg = tmp_path / "d.odg"
            run_script(scripts / "create_minimal_odg.py", spec, odg)
            out = tmp_path / "out.odg"
            run_script(scripts / "add_image.py", odg, FIXTURES / "image.svg", "-o", out)
            self.assertEqual(meta_field(read_meta(out), "meta", "editing-cycles"), "1")


if __name__ == "__main__":
    unittest.main()
