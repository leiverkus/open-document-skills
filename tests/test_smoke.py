from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def run_script(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *map(str, args)],
        cwd=script.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_svg(path: Path, label: str) -> Path:
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="100">'
        f'<rect width="160" height="100" fill="#eef0ff"/>'
        f'<text x="20" y="55" font-size="22">{label}</text></svg>',
        encoding="utf-8",
    )
    return path


def assert_mimetype_first(testcase: unittest.TestCase, path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        testcase.assertEqual(archive.namelist()[0], "mimetype")


class SmokeTests(unittest.TestCase):
    def test_odt_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            spec = write_json(
                tmp_path / "doc.json",
                {
                    "title": "Test Document",
                    "blocks": [
                        {"type": "heading", "level": 2, "text": "Section"},
                        {"type": "paragraph", "text": "Hello ODT"},
                        {"type": "list", "items": ["First", "Second"]},
                        {"type": "table", "name": "Data", "rows": [["A", "B"], ["1", "2"]]},
                        {"type": "footnote", "text": "A note"},
                    ],
                },
            )
            odt = tmp_path / "test.odt"
            run_script(scripts / "create_minimal_odt.py", spec, odt)
            assert_mimetype_first(self, odt)
            run_script(scripts / "validate_refs.py", odt)
            self.assertIn("Hello ODT", run_script(scripts / "extract_text.py", odt).stdout)
            replaced = tmp_path / "replaced.odt"
            run_script(scripts / "replace_text.py", odt, "Hello ODT", "Hello Writer", "-o", replaced)
            self.assertIn("Hello Writer", run_script(scripts / "extract_text.py", replaced).stdout)
            image = write_svg(tmp_path / "image.svg", "ODT")
            with_image = tmp_path / "image.odt"
            run_script(scripts / "add_image.py", odt, image, "-o", with_image)
            package = json.loads(run_script(scripts / "inspect_package.py", with_image).stdout)
            self.assertEqual(package["images"], 1)

    def test_odp_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = write_json(
                tmp_path / "slides.json",
                {
                    "title": "Test Deck",
                    "slides": [
                        {"name": "Intro", "title": "Hello ODP", "body": ["First", "Second"], "notes": ["Speaker note"]}
                    ],
                },
            )
            odp = tmp_path / "test.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            assert_mimetype_first(self, odp)
            run_script(scripts / "validate_refs.py", odp)
            self.assertIn("Hello ODP", run_script(scripts / "extract_text.py", odp).stdout)
            cloned = tmp_path / "cloned.odp"
            run_script(scripts / "clone_slide.py", odp, "--source-slide", "1", "--name", "Clone", "--replace", "Hello ODP=Cloned", "-o", cloned)
            self.assertIn("Cloned", run_script(scripts / "extract_text.py", cloned).stdout)
            image = write_svg(tmp_path / "image.svg", "ODP")
            with_image = tmp_path / "image.odp"
            run_script(scripts / "add_image.py", odp, image, "-o", with_image)
            package = json.loads(run_script(scripts / "inspect_package.py", with_image).stdout)
            self.assertEqual(package["slides"][0]["images"], 1)

    def test_ods_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            spec = write_json(
                tmp_path / "workbook.json",
                {
                    "title": "Test Workbook",
                    "sheets": [
                        {
                            "name": "Data",
                            "rows": [["Item", "Value"], ["A", 10], ["B", 20]],
                            "cells": {"C2": {"formula": "of:=[.B2]*2"}},
                        }
                    ],
                },
            )
            ods = tmp_path / "test.ods"
            run_script(scripts / "create_minimal_ods.py", spec, ods)
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
            image = write_svg(tmp_path / "image.svg", "ODG")
            spec = write_json(
                tmp_path / "drawing.json",
                {
                    "pages": [
                        {
                            "name": "Diagram",
                            "items": [
                                {"type": "text", "text": "Hello Draw", "x": "1cm", "y": "1cm"},
                                {"type": "rect", "name": "Box", "x": "1cm", "y": "4cm", "text": "Box Label"},
                                {"type": "ellipse", "x": "8cm", "y": "4cm", "text": "Ellipse"},
                                {"type": "line", "x1": "1cm", "y1": "7cm", "x2": "12cm", "y2": "7cm"},
                                {"type": "image", "path": str(image), "x": "14cm", "y": "3cm"},
                            ],
                        }
                    ]
                },
            )
            odg = tmp_path / "test.odg"
            run_script(scripts / "create_minimal_odg.py", spec, odg)
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
