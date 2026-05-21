from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURES, SKILLS, assert_mimetype_first, run_script


def odg_fixture_with_image(tmp_path: Path) -> Path:
    spec = json.loads((FIXTURES / "odg_drawing.json").read_text(encoding="utf-8"))
    spec["pages"][0]["items"][-1]["path"] = str(FIXTURES / "image.svg")
    path = tmp_path / "drawing.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


class SmokeTests(unittest.TestCase):
    def test_odt_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "test.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            assert_mimetype_first(self, odt)
            run_script(scripts / "validate_refs.py", odt)
            self.assertIn("Hello ODT", run_script(scripts / "extract_text.py", odt).stdout)
            replaced = tmp_path / "replaced.odt"
            run_script(scripts / "replace_text.py", odt, "Hello ODT", "Hello Writer", "-o", replaced)
            self.assertIn("Hello Writer", run_script(scripts / "extract_text.py", replaced).stdout)
            with_image = tmp_path / "image.odt"
            run_script(scripts / "add_image.py", odt, FIXTURES / "image.svg", "-o", with_image)
            package = json.loads(run_script(scripts / "inspect_package.py", with_image).stdout)
            self.assertEqual(package["images"], 1)

    def test_odp_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            odp = tmp_path / "test.odp"
            run_script(scripts / "create_minimal_odp.py", FIXTURES / "odp_slides.json", odp)
            assert_mimetype_first(self, odp)
            run_script(scripts / "validate_refs.py", odp)
            self.assertIn("Hello ODP", run_script(scripts / "extract_text.py", odp).stdout)
            cloned = tmp_path / "cloned.odp"
            run_script(scripts / "clone_slide.py", odp, "--source-slide", "1", "--name", "Clone", "--replace", "Hello ODP=Cloned", "-o", cloned)
            self.assertIn("Cloned", run_script(scripts / "extract_text.py", cloned).stdout)
            with_image = tmp_path / "image.odp"
            run_script(scripts / "add_image.py", odp, FIXTURES / "image.svg", "-o", with_image)
            package = json.loads(run_script(scripts / "inspect_package.py", with_image).stdout)
            self.assertEqual(package["slides"][0]["images"], 1)

    def test_ods_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            ods = tmp_path / "test.ods"
            run_script(scripts / "create_minimal_ods.py", FIXTURES / "ods_workbook.json", ods)
            assert_mimetype_first(self, ods)
            run_script(scripts / "validate_refs.py", ods)
            self.assertIn("C2=of:=[.B2]*2", run_script(scripts / "extract_sheets.py", ods).stdout)
            formulas = json.loads(run_script(scripts / "extract_formulas.py", ods).stdout)
            self.assertEqual(formulas[0]["address"], "C2")
            replaced = tmp_path / "replaced.ods"
            run_script(scripts / "replace_cells.py", ods, "Data!B3=25", "Data!C3=formula:of:=[.B3]*2", "-o", replaced)
            self.assertIn("B3=25.0", run_script(scripts / "extract_sheets.py", replaced).stdout)
            csv_path = tmp_path / "data.csv"
            run_script(scripts / "export_csv.py", ods, "--sheet", "Data", "--output", csv_path)
            self.assertIn("Item,Value", csv_path.read_text(encoding="utf-8"))

    def test_odg_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            odg = tmp_path / "test.odg"
            run_script(scripts / "create_minimal_odg.py", odg_fixture_with_image(tmp_path), odg)
            assert_mimetype_first(self, odg)
            run_script(scripts / "validate_refs.py", odg)
            self.assertIn("Hello Draw", run_script(scripts / "extract_text.py", odg).stdout)
            shapes = json.loads(run_script(scripts / "extract_shapes.py", odg).stdout)
            self.assertGreaterEqual({shape["type"] for shape in shapes}, {"frame", "rect", "ellipse", "line"})
            replaced = tmp_path / "replaced.odg"
            run_script(scripts / "replace_text.py", odg, "Hello Draw", "Updated Draw", "-o", replaced)
            self.assertIn("Updated Draw", run_script(scripts / "extract_text.py", replaced).stdout)


if __name__ == "__main__":
    unittest.main()
