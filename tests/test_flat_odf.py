"""Tests for flat ODF (.fodt/.fodp/.fods/.fodg) pack/unpack roundtrips."""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import FIXTURES, SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class FlatOdfTests(unittest.TestCase):
    def test_odt_zipped_to_flat_to_zipped_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            fodt = tmp_path / "doc.fodt"
            run_script(scripts / "pack_fodt.py", odt, "-o", fodt)
            roundtrip = tmp_path / "round.odt"
            run_script(scripts / "unpack_fodt.py", fodt, "-o", roundtrip)
            run_script(scripts / "validate_refs.py", roundtrip)
            orig = run_script(scripts / "extract_text.py", odt).stdout
            after = run_script(scripts / "extract_text.py", roundtrip).stdout
            self.assertEqual(orig, after)

    def test_odp_flat_preserves_slide_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = write_json(
                tmp_path / "deck.json",
                {"slides": [{"name": "A", "title": "T1"}, {"name": "B", "title": "T2"}]},
            )
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            fodp = tmp_path / "deck.fodp"
            run_script(scripts / "pack_fodp.py", odp, "-o", fodp)
            roundtrip = tmp_path / "round.odp"
            run_script(scripts / "unpack_fodp.py", fodp, "-o", roundtrip)
            run_script(scripts / "validate_refs.py", roundtrip)
            data = json.loads(run_script(scripts / "extract_text.py", roundtrip, "--json").stdout)
            self.assertEqual(len(data), 2)

    def test_ods_flat_preserves_cell_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            spec = write_json(
                tmp_path / "wb.json",
                {"sheets": [{"name": "Data", "rows": [["Hello", "World"], ["1", "2"]]}]},
            )
            ods = tmp_path / "wb.ods"
            run_script(scripts / "create_minimal_ods.py", spec, ods)
            fods = tmp_path / "wb.fods"
            run_script(scripts / "pack_fods.py", ods, "-o", fods)
            roundtrip = tmp_path / "round.ods"
            run_script(scripts / "unpack_fods.py", fods, "-o", roundtrip)
            run_script(scripts / "validate_refs.py", roundtrip)
            orig = run_script(scripts / "extract_sheets.py", ods).stdout
            after = run_script(scripts / "extract_sheets.py", roundtrip).stdout
            self.assertEqual(orig, after)

    def test_odg_flat_preserves_shape_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            spec = write_json(
                tmp_path / "d.json",
                {
                    "pages": [
                        {
                            "name": "P",
                            "items": [
                                {"type": "rect", "width": "5cm", "height": "3cm"},
                                {"type": "text", "text": "Label"},
                            ],
                        }
                    ]
                },
            )
            odg = tmp_path / "d.odg"
            run_script(scripts / "create_minimal_odg.py", spec, odg)
            fodg = tmp_path / "d.fodg"
            run_script(scripts / "pack_fodg.py", odg, "-o", fodg)
            roundtrip = tmp_path / "round.odg"
            run_script(scripts / "unpack_fodg.py", fodg, "-o", roundtrip)
            run_script(scripts / "validate_refs.py", roundtrip)
            shapes_before = json.loads(run_script(scripts / "extract_shapes.py", odg).stdout)
            shapes_after = json.loads(run_script(scripts / "extract_shapes.py", roundtrip).stdout)
            self.assertEqual(len(shapes_before), len(shapes_after))
            self.assertGreaterEqual(len(shapes_after), 1)

    def test_flat_embeds_image_as_base64(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            with_image = tmp_path / "with_image.odt"
            run_script(scripts / "add_image.py", odt, FIXTURES / "image.svg", "-o", with_image)
            fodt = tmp_path / "with_image.fodt"
            run_script(scripts / "pack_fodt.py", with_image, "-o", fodt)
            root = ET.parse(fodt).getroot()
            images = root.findall(".//draw:image", NS)
            self.assertGreater(len(images), 0)
            with_binary = [img for img in images if img.find("office:binary-data", NS) is not None]
            self.assertEqual(len(with_binary), 1, "image must be embedded as binary-data")
            self.assertIsNone(
                with_binary[0].attrib.get(f"{{{NS['xlink']}}}href"),
                "embedded image must not have an xlink:href",
            )
            binary = with_binary[0].find("office:binary-data", NS)
            assert binary is not None
            self.assertGreater(len(base64.b64decode(binary.text or "")), 0)

    def test_flat_unpack_recreates_manifest_with_pictures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            with_image = tmp_path / "with_image.odt"
            run_script(scripts / "add_image.py", odt, FIXTURES / "image.svg", "-o", with_image)
            fodt = tmp_path / "with_image.fodt"
            run_script(scripts / "pack_fodt.py", with_image, "-o", fodt)
            roundtrip = tmp_path / "round.odt"
            run_script(scripts / "unpack_fodt.py", fodt, "-o", roundtrip)
            with zipfile.ZipFile(roundtrip) as archive:
                names = archive.namelist()
                pictures = [n for n in names if n.startswith("Pictures/")]
                self.assertGreaterEqual(len(pictures), 1)
                manifest = ET.fromstring(archive.read("META-INF/manifest.xml"))
            entries = {
                e.attrib.get(f"{{{NS['manifest']}}}full-path") for e in manifest.findall("manifest:file-entry", NS)
            }
            self.assertIn("content.xml", entries)
            self.assertIn("styles.xml", entries)
            for picture in pictures:
                self.assertIn(picture, entries)

    def test_flat_mimetype_attribute_matches_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            fodt = tmp_path / "doc.fodt"
            run_script(scripts / "pack_fodt.py", odt, "-o", fodt)
            root = ET.parse(fodt).getroot()
            self.assertEqual(
                root.attrib.get(f"{{{NS['office']}}}mimetype"),
                "application/vnd.oasis.opendocument.text",
            )


if __name__ == "__main__":
    unittest.main()
