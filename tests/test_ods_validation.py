"""Tests for ODS data validation API."""

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
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


class DataValidationTests(unittest.TestCase):
    def _make_ods(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "spec.json",
            {"sheets": [{"name": "Sheet1", "rows": [["Header"], ["row1"], ["row2"]]}]},
        )
        ods = tmp_path / "wb.ods"
        run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, ods)
        return ods

    def test_add_list_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_data_validation.py",
                ods,
                "--name",
                "colors",
                "--type",
                "list",
                "--values",
                "Red,Green,Blue",
                "--apply",
                "Sheet1.A2:A10",
                "-o",
                out,
            )
            content = read_content(out)
            validations = list(content.iter(q("table", "content-validation")))
            self.assertEqual(len(validations), 1)
            self.assertEqual(validations[0].attrib.get(q("table", "name")), "colors")
            self.assertIn("cell-content-is-in-list", validations[0].attrib.get(q("table", "condition"), ""))

    def test_add_number_validation_with_condition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_data_validation.py",
                ods,
                "--name",
                "positive",
                "--type",
                "number",
                "--condition",
                "value() > 0",
                "--apply",
                "Sheet1.B1:B5",
                "-o",
                out,
            )
            content = read_content(out)
            validations = list(content.iter(q("table", "content-validation")))
            self.assertEqual(len(validations), 1)
            self.assertIn("value", validations[0].attrib.get(q("table", "condition"), ""))

    def test_validation_applies_to_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            result = run_script(
                SKILLS / "ods" / "scripts" / "add_data_validation.py",
                ods,
                "--name",
                "colors",
                "--type",
                "list",
                "--values",
                "A,B",
                "--apply",
                "Sheet1.A1:B2",
                "-o",
                out,
            )
            self.assertIn("4 cells", result.stdout)
            content = read_content(out)
            cells_with_validation = [
                c
                for c in content.iter(q("table", "table-cell"))
                if c.attrib.get(q("table", "content-validation-name")) == "colors"
            ]
            self.assertEqual(len(cells_with_validation), 4)

    def test_validation_with_help_and_error_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_data_validation.py",
                ods,
                "--name",
                "colors",
                "--type",
                "list",
                "--values",
                "Red",
                "--apply",
                "Sheet1.A1",
                "--message",
                "Pick a color",
                "--error-message",
                "Color required",
                "-o",
                out,
            )
            content = read_content(out)
            val = content.find(".//table:content-validation", NS)
            assert val is not None
            help_msg = val.find(
                "table:help-message/text:p", {**NS, "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
            )
            err_msg = val.find(
                "table:error-message/text:p", {**NS, "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
            )
            assert help_msg is not None and err_msg is not None
            self.assertEqual(help_msg.text, "Pick a color")
            self.assertEqual(err_msg.text, "Color required")

    def test_validate_refs_detects_dangling_validation_ref(self) -> None:
        """Manually inject a content-validation-name on a cell with no matching validation."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            broken = tmp_path / "broken.ods"
            content = read_content(ods)
            cell = content.find(".//table:table-cell", NS)
            assert cell is not None
            cell.set(q("table", "content-validation-name"), "doesnotexist")
            # Re-pack
            payload = ET.tostring(content, encoding="utf-8", xml_declaration=True)
            with zipfile.ZipFile(ods) as src:
                with zipfile.ZipFile(broken, "w") as dst:
                    for name in src.namelist():
                        if name == "mimetype":
                            dst.writestr("mimetype", src.read("mimetype"), zipfile.ZIP_STORED)
                        elif name == "content.xml":
                            dst.writestr(name, payload, zipfile.ZIP_DEFLATED)
                        else:
                            dst.writestr(name, src.read(name), zipfile.ZIP_DEFLATED)
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", broken, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Dangling content-validation", result.stdout)


if __name__ == "__main__":
    unittest.main()
