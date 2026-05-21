"""Tests for ODG glue points."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

NS = {
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


class GluePointTests(unittest.TestCase):
    def _make_odg(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "spec.json",
            {
                "pages": [
                    {
                        "name": "P",
                        "items": [
                            {"type": "rect", "x": "1cm", "y": "1cm", "width": "3cm", "height": "1.5cm", "name": "Box"}
                        ],
                    }
                ]
            },
        )
        odg = tmp_path / "d.odg"
        run_script(SKILLS / "odg" / "scripts" / "create_minimal_odg.py", spec, odg)
        return odg

    def test_add_gluepoint_to_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "add_gluepoint.py",
                odg,
                "--shape",
                "Box",
                "--position",
                "0.5,0",
                "--escape",
                "up",
                "-o",
                out,
            )
            content = read_content(out)
            gps = list(content.iter(q("draw", "glue-point")))
            self.assertEqual(len(gps), 1)
            self.assertEqual(gps[0].attrib.get(q("draw", "escape-direction")), "up")
            self.assertEqual(gps[0].attrib.get(q("draw", "id")), "4")

    def test_add_multiple_gluepoints_increment_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            first = tmp_path / "first.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "add_gluepoint.py",
                odg,
                "--shape",
                "Box",
                "--position",
                "0.5,0",
                "--escape",
                "up",
                "-o",
                first,
            )
            second = tmp_path / "second.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "add_gluepoint.py",
                first,
                "--shape",
                "Box",
                "--position",
                "1,0.5",
                "--escape",
                "right",
                "-o",
                second,
            )
            content = read_content(second)
            ids = sorted(gp.attrib.get(q("draw", "id")) for gp in content.iter(q("draw", "glue-point")))
            self.assertEqual(ids, ["4", "5"])

    def test_gluepoint_escape_direction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "add_gluepoint.py",
                odg,
                "--shape",
                "Box",
                "--position",
                "0,0.5",
                "--escape",
                "left",
                "-o",
                out,
            )
            content = read_content(out)
            gp = next(content.iter(q("draw", "glue-point")))
            self.assertEqual(gp.attrib.get(q("draw", "escape-direction")), "left")


if __name__ == "__main__":
    unittest.main()
