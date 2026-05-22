"""Tests for edit_table.py — add/delete rows and columns, set cells."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

ODT = SKILLS / "odt" / "scripts"
NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def the_table(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        content = ET.fromstring(archive.read("content.xml"))
    return next(content.iter(q("table", "table")))


def grid(table: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall(q("table", "table-row")):
        cells = [c for c in row if c.tag == q("table", "table-cell")]
        rows.append(["".join(c.itertext()) for c in cells])
    return rows


def base_odt(tmp: Path) -> Path:
    spec = tmp / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "title": "T",
                "blocks": [{"type": "table", "name": "Data", "rows": [["Year", "Value"], ["2020", "100"]]}],
            }
        ),
        encoding="utf-8",
    )
    odt = tmp / "doc.odt"
    run_script(ODT / "create_minimal_odt.py", spec, odt)
    return odt


class TableEditingTests(unittest.TestCase):
    def test_add_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "t.odt"
            run_script(
                ODT / "edit_table.py", base_odt(tmp_path), "--table", "Data", "--add-row", "2021", "150", "-o", out
            )
            rows = grid(the_table(out))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[-1], ["2021", "150"])

    def test_add_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "t.odt"
            run_script(ODT / "edit_table.py", base_odt(tmp_path), "--table", "Data", "--add-column", "Note", "-o", out)
            rows = grid(the_table(out))
            self.assertTrue(all(len(r) == 3 for r in rows))
            self.assertEqual(rows[0][2], "Note")

    def test_set_cell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "t.odt"
            run_script(
                ODT / "edit_table.py", base_odt(tmp_path), "--table", "Data", "--set-cell", "2", "2", "999", "-o", out
            )
            self.assertEqual(grid(the_table(out))[1][1], "999")

    def test_delete_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "t.odt"
            run_script(ODT / "edit_table.py", base_odt(tmp_path), "--table", "Data", "--delete-row", "2", "-o", out)
            self.assertEqual(len(grid(the_table(out))), 1)

    def test_delete_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "t.odt"
            run_script(ODT / "edit_table.py", base_odt(tmp_path), "--table", "Data", "--delete-column", "1", "-o", out)
            rows = grid(the_table(out))
            self.assertTrue(all(len(r) == 1 for r in rows))
            self.assertEqual(rows[0], ["Value"])

    def test_unknown_table_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "t.odt"
            result = run_script(
                ODT / "edit_table.py", base_odt(tmp_path), "--table", "Missing", "--add-row", "-o", out, check=False
            )
            self.assertNotEqual(result.returncode, 0)

    def test_expands_repeated_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = base_odt(tmp_path)
            # Inject a row with a repeated-cell shorthand.
            with zipfile.ZipFile(odt) as archive:
                content = ET.fromstring(archive.read("content.xml"))
                names = archive.namelist()
                payload = {n: archive.read(n) for n in names}
            table = next(content.iter(q("table", "table")))
            row = ET.SubElement(table, q("table", "table-row"))
            cell = ET.SubElement(
                row,
                q("table", "table-cell"),
                {q("table", "number-columns-repeated"): "2"},
            )
            ET.SubElement(cell, q("text", "p")).text = "x"
            payload["content.xml"] = ET.tostring(content)
            repeated = tmp_path / "rep.odt"
            with zipfile.ZipFile(repeated, "w") as dst:
                for name in names:
                    dst.writestr(name, payload[name])
            out = tmp_path / "t.odt"
            run_script(ODT / "edit_table.py", repeated, "--table", "Data", "--set-cell", "3", "2", "ok", "-o", out)
            self.assertEqual(grid(the_table(out))[2][1], "ok")


if __name__ == "__main__":
    unittest.main()
