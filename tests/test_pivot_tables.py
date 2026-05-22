"""Tests for the ODS pivot-table API (add_pivot_table.py / list_pivot_tables.py)."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

HAVE_LXML = importlib.util.find_spec("lxml") is not None

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

SALES_ROWS = [
    ["Region", "Product", "Quarter", "Revenue"],
    ["North", "Widget", "Q1", "100"],
    ["North", "Widget", "Q2", "120"],
    ["North", "Gadget", "Q1", "80"],
    ["South", "Widget", "Q1", "150"],
    ["South", "Gadget", "Q2", "70"],
    ["East", "Widget", "Q1", "200"],
]


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def sheet_grid(content: ET.Element, name: str) -> list[list[str]]:
    """Return a sheet's cells as a list of string rows (plain text content)."""
    sheet = next(s for s in content.iter(q("table", "table")) if s.attrib.get(q("table", "name")) == name)
    grid: list[list[str]] = []
    for row in sheet.findall(q("table", "table-row")):
        cells: list[str] = []
        for cell in row.findall(q("table", "table-cell")):
            para = cell.find(q("text", "p"))
            cells.append(para.text or "" if para is not None else "")
        grid.append(cells)
    return grid


def make_sales(tmp_path: Path) -> Path:
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"sheets": [{"name": "Data", "rows": SALES_ROWS}]}), encoding="utf-8")
    ods = tmp_path / "sales.ods"
    run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, ods)
    return ods


def add_pivot(ods: Path, out: Path, *args: object) -> str:
    result = run_script(SKILLS / "ods" / "scripts" / "add_pivot_table.py", ods, *args, "-o", out)
    return result.stdout


class PivotTableTests(unittest.TestCase):
    def test_pivot_grid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_sales(tmp_path)
            out = tmp_path / "out.ods"
            add_pivot(
                ods,
                out,
                "--source",
                "Data.A1:D7",
                "--rows",
                "Region",
                "--columns",
                "Quarter",
                "--data",
                "Revenue",
                "--function",
                "sum",
                "--target",
                "Pivot.A1",
            )
            grid = sheet_grid(read_content(out), "Pivot")
            # Header: Region, Q1, Q2, Total
            self.assertEqual(grid[0], ["Region", "Q1", "Q2", "Total"])
            rows = {r[0]: r for r in grid[1:]}
            # North: Q1 = 100+80 = 180, Q2 = 120, Total = 300
            self.assertEqual(rows["North"], ["North", "180", "120", "300"])
            # East: Q1 = 200, no Q2
            self.assertEqual(rows["East"], ["East", "200", "", "200"])
            # Grand total row
            self.assertEqual(grid[-1][0], "Total")
            self.assertEqual(grid[-1][-1], "720")

    def test_data_pilot_table_definition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_sales(tmp_path)
            out = tmp_path / "out.ods"
            add_pivot(
                ods,
                out,
                "--source",
                "Data.A1:D7",
                "--rows",
                "Region,Product",
                "--columns",
                "Quarter",
                "--data",
                "Revenue",
                "--target",
                "Pivot.A1",
            )
            content = read_content(out)
            pivot = content.find(".//table:data-pilot-table", NS)
            assert pivot is not None
            self.assertEqual(pivot.attrib.get(q("table", "name")), "DataPilot1")
            source = pivot.find(q("table", "source-cell-range"))
            assert source is not None
            self.assertEqual(source.attrib.get(q("table", "cell-range-address")), "Data.A1:Data.D7")
            fields = pivot.findall(q("table", "data-pilot-field"))
            orientations = [f.attrib.get(q("table", "orientation")) for f in fields]
            self.assertEqual(orientations, ["row", "row", "column", "data"])
            data_field = fields[-1]
            self.assertEqual(data_field.attrib.get(q("table", "function")), "sum")

    def test_function_count_and_average(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_sales(tmp_path)
            out = tmp_path / "count.ods"
            add_pivot(
                ods,
                out,
                "--source",
                "Data.A1:D7",
                "--rows",
                "Region",
                "--data",
                "Revenue",
                "--function",
                "count",
                "--target",
                "Pivot.A1",
            )
            grid = sheet_grid(read_content(out), "Pivot")
            rows = {r[0]: r for r in grid[1:]}
            # North has 3 records, South 2, East 1.
            self.assertEqual(rows["North"][1], "3")
            self.assertEqual(rows["East"][1], "1")

    def test_creates_target_sheet_and_no_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_sales(tmp_path)
            out = tmp_path / "out.ods"
            add_pivot(
                ods,
                out,
                "--source",
                "Data.A1:D7",
                "--rows",
                "Region",
                "--data",
                "Revenue",
                "--function",
                "sum",
                "--target",
                "Summary.B2",
            )
            content = read_content(out)
            names = {s.attrib.get(q("table", "name")) for s in content.iter(q("table", "table"))}
            self.assertIn("Summary", names)
            grid = sheet_grid(content, "Summary")
            # Anchored at B2: row 1 is empty, the grid starts on row 2 col B.
            header = grid[1]
            self.assertEqual(header[1], "Region")
            self.assertEqual(header[2], "sum of Revenue")

    def test_list_pivot_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_sales(tmp_path)
            out = tmp_path / "out.ods"
            add_pivot(
                ods,
                out,
                "--source",
                "Data.A1:D7",
                "--rows",
                "Region",
                "--columns",
                "Quarter",
                "--data",
                "Revenue",
                "--target",
                "Pivot.A1",
            )
            result = run_script(SKILLS / "ods" / "scripts" / "list_pivot_tables.py", out, "--json")
            data = json.loads(result.stdout)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["name"], "DataPilot1")
            self.assertEqual(data[0]["source_range"], "Data.A1:Data.D7")
            field_names = [f["name"] for f in data[0]["fields"]]
            self.assertEqual(field_names, ["Region", "Quarter", "Revenue"])

    def test_validate_refs_detects_unknown_source_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_sales(tmp_path)
            out = tmp_path / "out.ods"
            add_pivot(
                ods,
                out,
                "--source",
                "Data.A1:D7",
                "--rows",
                "Region",
                "--data",
                "Revenue",
                "--target",
                "Pivot.A1",
            )
            broken = tmp_path / "broken.ods"
            with zipfile.ZipFile(out) as src:
                content = src.read("content.xml").decode("utf-8").replace("Data.A1:Data.D7", "Ghost.A1:Ghost.D7")
                with zipfile.ZipFile(broken, "w") as dst:
                    for name in src.namelist():
                        data = content.encode("utf-8") if name == "content.xml" else src.read(name)
                        mode = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
                        dst.writestr(name, data, mode)
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", broken, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown sheet", result.stdout)

    @unittest.skipUnless(HAVE_LXML, "lxml not installed")
    def test_strict_validation_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_sales(tmp_path)
            out = tmp_path / "out.ods"
            add_pivot(
                ods,
                out,
                "--source",
                "Data.A1:D7",
                "--rows",
                "Region,Product",
                "--columns",
                "Quarter",
                "--data",
                "Revenue",
                "--target",
                "Pivot.A1",
            )
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", out, "--strict")
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")


if __name__ == "__main__":
    unittest.main()
