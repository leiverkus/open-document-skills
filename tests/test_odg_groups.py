"""Tests for ODG groups (group/ungroup) and list_structure."""

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


class GroupTests(unittest.TestCase):
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
                            {"type": "rect", "x": "11cm", "y": "1cm", "width": "3cm", "height": "1.5cm", "name": "C"},
                        ],
                    }
                ]
            },
        )
        odg = tmp_path / "d.odg"
        run_script(SKILLS / "odg" / "scripts" / "create_minimal_odg.py", spec, odg)
        return odg

    def test_group_three_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "group_shapes.py",
                odg,
                "--shapes",
                "A,B,C",
                "--name",
                "Block",
                "-o",
                out,
            )
            content = read_content(out)
            groups = list(content.iter(q("draw", "g")))
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0].attrib.get(q("draw", "name")), "Block")
            child_names = [c.attrib.get(q("draw", "name")) for c in groups[0]]
            self.assertEqual(child_names, ["A", "B", "C"])

    def test_ungroup_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            grouped = tmp_path / "grouped.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "group_shapes.py",
                odg,
                "--shapes",
                "A,B,C",
                "--name",
                "Block",
                "-o",
                grouped,
            )
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "ungroup.py",
                grouped,
                "--name",
                "Block",
                "-o",
                out,
            )
            content = read_content(out)
            self.assertEqual(len(list(content.iter(q("draw", "g")))), 0)
            # Shapes back at page level
            page = content.find(".//{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}page")
            assert page is not None
            names = [
                c.attrib.get(q("draw", "name")) for c in page if c.attrib.get(q("draw", "name")) in {"A", "B", "C"}
            ]
            self.assertEqual(names, ["A", "B", "C"])

    def test_ungroup_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            grouped = tmp_path / "grouped.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "group_shapes.py",
                odg,
                "--shapes",
                "A,B",
                "--name",
                "G1",
                "-o",
                grouped,
            )
            out = tmp_path / "out.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "ungroup.py",
                grouped,
                "--all",
                "-o",
                out,
            )
            content = read_content(out)
            self.assertEqual(len(list(content.iter(q("draw", "g")))), 0)

    def test_list_structure_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = self._make_odg(tmp_path)
            grouped = tmp_path / "grouped.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "group_shapes.py",
                odg,
                "--shapes",
                "A,B,C",
                "--name",
                "G1",
                "-o",
                grouped,
            )
            with_conn = tmp_path / "with_conn.odg"
            run_script(
                SKILLS / "odg" / "scripts" / "connect_shapes.py",
                grouped,
                "--from",
                "A",
                "--to",
                "B",
                "-o",
                with_conn,
            )
            result = run_script(SKILLS / "odg" / "scripts" / "list_structure.py", with_conn, "--json").stdout
            data = json.loads(result)
            self.assertEqual(len(data["pages"]), 1)
            page = data["pages"][0]
            self.assertEqual(len(page["groups"]), 1)
            self.assertEqual(len(page["connectors"]), 1)


if __name__ == "__main__":
    unittest.main()
