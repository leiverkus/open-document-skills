"""Tests for ODG connectors with shape binding."""

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
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


class ConnectorTests(unittest.TestCase):
    def _make_odg(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "spec.json",
            {
                "pages": [
                    {
                        "name": "P",
                        "items": [
                            {"type": "rect", "x": "1cm", "y": "1cm", "width": "3cm", "height": "1.5cm", "name": "A"},
                            {"type": "rect", "x": "6cm", "y": "1cm", "width": "3cm", "height": "1.5cm", "name": "B"},
                        ],
                    }
                ]
            },
        )
        odg = tmp_path / "d.odg"
        run_script(SKILLS / "odg" / "scripts" / "create_minimal_odg.py", spec, odg)
        return odg

    def test_connect_two_shapes_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "connect_shapes.py",
                odg,
                "--from",
                "A",
                "--to",
                "B",
                "-o",
                out,
            )
            content = read_content(out)
            connectors = list(content.iter(q("draw", "connector")))
            self.assertEqual(len(connectors), 1)
            self.assertEqual(connectors[0].attrib.get(q("draw", "type")), "standard")
            self.assertIsNotNone(connectors[0].attrib.get(q("draw", "start-shape")))
            self.assertIsNotNone(connectors[0].attrib.get(q("draw", "end-shape")))

    def test_connect_curve_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "connect_shapes.py",
                odg,
                "--from",
                "A",
                "--to",
                "B",
                "--type",
                "curve",
                "-o",
                out,
            )
            content = read_content(out)
            connector = next(content.iter(q("draw", "connector")))
            self.assertEqual(connector.attrib.get(q("draw", "type")), "curve")

    def test_connect_with_explicit_glue_points(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "connect_shapes.py",
                odg,
                "--from",
                "A",
                "--from-glue",
                "1",
                "--to",
                "B",
                "--to-glue",
                "3",
                "-o",
                out,
            )
            content = read_content(out)
            connector = next(content.iter(q("draw", "connector")))
            self.assertEqual(connector.attrib.get(q("draw", "start-glue-point")), "1")
            self.assertEqual(connector.attrib.get(q("draw", "end-glue-point")), "3")

    def test_connect_auto_assigns_shape_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "connect_shapes.py",
                odg,
                "--from",
                "A",
                "--to",
                "B",
                "-o",
                out,
            )
            content = read_content(out)
            shape_ids = [el.attrib.get(q("draw", "id")) for el in content.iter() if el.attrib.get(q("draw", "id"))]
            self.assertGreaterEqual(len(shape_ids), 2)

    def test_validate_refs_passes_with_connector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "connect_shapes.py",
                odg,
                "--from",
                "A",
                "--to",
                "B",
                "-o",
                out,
            )
            result = run_script(SKILLS / "odg" / "scripts" / "validate_refs.py", out)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
