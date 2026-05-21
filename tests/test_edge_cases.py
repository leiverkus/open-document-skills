from __future__ import annotations

import json

# Import shared namespace helpers from the ODT common module
# (all four *_common.py modules share the same lib.odf_common base)
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import FIXTURES, SKILLS, run_script

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


# ODS-specific namespace for edge-case XML manipulation
NS = {
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def read_zip_xml(path: Path, member: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as handle:
            return ET.parse(handle).getroot()


def write_zip_replacement(input_file: Path, output_file: Path, member: str, xml_root: ET.Element) -> None:
    replacement = ET.tostring(xml_root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(input_file) as src:
        names = src.namelist()
        with zipfile.ZipFile(output_file, "w") as dst:
            if "mimetype" in names:
                dst.writestr("mimetype", src.read("mimetype"), compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype":
                    continue
                dst.writestr(name, replacement if name == member else src.read(name), compress_type=zipfile.ZIP_DEFLATED)


class EdgeCaseTests(unittest.TestCase):
    def test_ods_repeated_rows_and_cells_are_expanded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            spec = write_json(tmp_path / "workbook.json", {"sheets": [{"name": "Data", "rows": [["A"]]}]})
            ods = tmp_path / "base.ods"
            run_script(scripts / "create_minimal_ods.py", spec, ods)

            content = read_zip_xml(ods, "content.xml")
            sheet = content.find(".//table:table", NS)
            self.assertIsNotNone(sheet)
            sheet.clear()
            sheet.set(q("table", "name"), "Data")
            row = ET.SubElement(sheet, q("table", "table-row"), {q("table", "number-rows-repeated"): "2"})
            cell = ET.SubElement(
                row,
                q("table", "table-cell"),
                {
                    q("table", "number-columns-repeated"): "3",
                    q("office", "value-type"): "string",
                },
            )
            p = ET.SubElement(cell, q("text", "p"))
            p.text = "Repeated"
            repeated = tmp_path / "repeated.ods"
            write_zip_replacement(ods, repeated, "content.xml", content)

            data = json.loads(run_script(scripts / "extract_sheets.py", repeated, "--json").stdout)
            self.assertEqual(data[0]["rows"], 2)
            self.assertEqual(data[0]["columns"], 3)
            text = run_script(scripts / "extract_sheets.py", repeated).stdout
            self.assertIn("C2=Repeated", text)

    def test_ods_validate_refs_detects_formula_error_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            spec = write_json(tmp_path / "workbook.json", {"sheets": [{"name": "Data", "rows": [["#REF!"]]}]})
            ods = tmp_path / "error.ods"
            run_script(scripts / "create_minimal_ods.py", spec, ods)
            result = run_script(scripts / "validate_refs.py", ods, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cell displays formula error", result.stdout)

    def test_odt_json_extraction_preserves_table_and_footnote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            data = json.loads(run_script(scripts / "extract_text.py", odt, "--json").stdout)
            table = next(item for item in data if item["type"] == "table")
            note = next(item for item in data if item["type"] == "note")
            self.assertEqual(table["rows"][1], ["1", "2"])
            self.assertEqual(note["text"], "A note")

    def test_odp_notes_are_not_modified_by_visible_text_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = write_json(
                tmp_path / "slides.json",
                {"slides": [{"name": "Intro", "title": "Same", "body": ["Body"], "notes": ["Same"]}]},
            )
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            replaced = tmp_path / "replaced.odp"
            run_script(scripts / "replace_text.py", odp, "Same", "Visible", "-o", replaced)
            data = json.loads(run_script(scripts / "extract_text.py", replaced, "--json").stdout)
            self.assertIn("Visible", data[0]["text"])
            self.assertEqual(data[0]["notes"], ["Same"])

    def test_odp_list_masters_reports_used_default_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = write_json(tmp_path / "slides.json", {"slides": [{"name": "Intro", "title": "Hello"}]})
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            masters = json.loads(run_script(scripts / "list_masters.py", odp).stdout)
            self.assertEqual(masters["master_pages"][0]["name"], "Default")
            self.assertEqual(masters["master_pages"][0]["slides_using"], 1)

    def test_odg_validate_refs_detects_negative_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            spec = write_json(
                tmp_path / "drawing.json",
                {"pages": [{"name": "Bad", "items": [{"type": "rect", "width": "-1cm", "height": "2cm"}]}]},
            )
            odg = tmp_path / "bad.odg"
            run_script(scripts / "create_minimal_odg.py", spec, odg)
            result = run_script(scripts / "validate_refs.py", odg, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("negative-size shape", result.stdout)

    def test_odg_add_image_uses_unique_package_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            spec = write_json(tmp_path / "drawing.json", {"pages": [{"name": "Diagram", "items": [{"type": "image", "path": str(FIXTURES / "image.svg")}]}]})
            odg = tmp_path / "drawing.odg"
            run_script(scripts / "create_minimal_odg.py", spec, odg)
            with_image = tmp_path / "with-image.odg"
            out = run_script(scripts / "add_image.py", odg, FIXTURES / "image.svg", "-o", with_image).stdout
            self.assertIn("Pictures/image-1.svg", out)
            package = json.loads(run_script(scripts / "inspect_package.py", with_image).stdout)
            self.assertEqual(len(package["media_files"]), 2)

    def test_odt_replace_text_handles_xml_special_chars(self) -> None:
        """replace_text.py must not break on XML-reserved characters."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            replaced = tmp_path / "replaced.odt"
            # Replace with XML-special characters.
            run_script(scripts / "replace_text.py", odt, "Hello ODT", "A & B < C > D", "-o", replaced)
            # The output must still be a valid ODF package.
            run_script(scripts / "validate_refs.py", replaced)
            self.assertIn("A & B < C > D", run_script(scripts / "extract_text.py", replaced).stdout)

    def test_odt_create_fails_on_missing_spec(self) -> None:
        """create_minimal_odt.py must fail cleanly when spec file is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            result = run_script(
                scripts / "create_minimal_odt.py",
                tmp_path / "nonexistent.json", tmp_path / "out.odt",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Spec file not found", result.stdout)

    def test_odt_create_fails_on_invalid_json(self) -> None:
        """create_minimal_odt.py must fail cleanly on malformed JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            bad_json = tmp_path / "bad.json"
            bad_json.write_text("{invalid json", encoding="utf-8")
            result = run_script(
                scripts / "create_minimal_odt.py",
                bad_json, tmp_path / "out.odt",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid JSON", result.stdout)


if __name__ == "__main__":
    unittest.main()
