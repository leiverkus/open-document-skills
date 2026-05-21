"""Tests for ODS chart embedding via add_chart.py."""

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
    "chart": "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_member(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read(name)


class ChartTests(unittest.TestCase):
    def _make_ods(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "spec.json",
            {"sheets": [{"name": "Sales", "rows": [["Month", "Revenue"], ["Jan", "1000"], ["Feb", "1500"]]}]},
        )
        ods = tmp_path / "wb.ods"
        run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, ods)
        return ods

    def test_add_bar_chart_creates_object_subpackage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "bar",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.D1",
                "--title",
                "Bar Test",
                "-o",
                out,
            )
            with zipfile.ZipFile(out) as archive:
                names = archive.namelist()
                self.assertIn("Object 1/content.xml", names)
                obj = archive.read("Object 1/content.xml")
            chart = ET.fromstring(obj).find(".//chart:chart", NS)
            assert chart is not None
            self.assertEqual(chart.attrib.get(q("chart", "class")), "chart:bar")

    def test_add_line_chart_with_axis_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "line",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.D1",
                "--x-label",
                "Month",
                "--y-label",
                "Revenue",
                "-o",
                out,
            )
            obj = read_member(out, "Object 1/content.xml")
            chart = ET.fromstring(obj).find(".//chart:chart", NS)
            assert chart is not None
            self.assertEqual(chart.attrib.get(q("chart", "class")), "chart:line")
            axes = chart.findall(".//chart:axis", NS)
            self.assertEqual(len(axes), 2)

    def test_add_pie_chart_circle_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "pie",
                "--data",
                "Sales.A2:B3",
                "--cell",
                "Sales.D1",
                "-o",
                out,
            )
            obj = read_member(out, "Object 1/content.xml")
            chart = ET.fromstring(obj).find(".//chart:chart", NS)
            assert chart is not None
            self.assertEqual(chart.attrib.get(q("chart", "class")), "chart:circle")
            # Pie has no axes
            self.assertEqual(len(chart.findall(".//chart:axis", NS)), 0)

    def test_add_scatter_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "scatter",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.D1",
                "-o",
                out,
            )
            obj = read_member(out, "Object 1/content.xml")
            chart = ET.fromstring(obj).find(".//chart:chart", NS)
            assert chart is not None
            self.assertEqual(chart.attrib.get(q("chart", "class")), "chart:scatter")

    def test_add_chart_creates_two_manifest_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "bar",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.D1",
                "-o",
                out,
            )
            manifest = ET.fromstring(read_member(out, "META-INF/manifest.xml"))
            entries = {
                e.attrib.get(q("manifest", "full-path")): e.attrib.get(q("manifest", "media-type"))
                for e in manifest.findall("manifest:file-entry", NS)
            }
            self.assertEqual(entries.get("Object 1/"), "application/vnd.oasis.opendocument.chart")
            self.assertEqual(entries.get("Object 1/content.xml"), "text/xml")

    def test_add_chart_two_consecutive_uses_object_1_and_object_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            first = tmp_path / "first.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "bar",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.D1",
                "-o",
                first,
            )
            second = tmp_path / "second.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                first,
                "--type",
                "line",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.F1",
                "-o",
                second,
            )
            with zipfile.ZipFile(second) as archive:
                names = archive.namelist()
                self.assertIn("Object 1/content.xml", names)
                self.assertIn("Object 2/content.xml", names)

    def test_list_charts_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            with_bar = tmp_path / "bar.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "bar",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.D1",
                "--title",
                "T1",
                "-o",
                with_bar,
            )
            with_pie = tmp_path / "pie.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                with_bar,
                "--type",
                "pie",
                "--data",
                "Sales.A2:B3",
                "--cell",
                "Sales.D10",
                "--title",
                "T2",
                "-o",
                with_pie,
            )
            result = run_script(SKILLS / "ods" / "scripts" / "list_charts.py", with_pie, "--json").stdout
            data = json.loads(result)
            self.assertEqual(len(data), 2)
            types = {entry["type"] for entry in data}
            self.assertEqual(types, {"bar", "pie"})

    def test_validate_refs_passes_with_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_chart.py",
                ods,
                "--type",
                "bar",
                "--data",
                "Sales.A1:B3",
                "--cell",
                "Sales.D1",
                "-o",
                out,
            )
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", out)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
