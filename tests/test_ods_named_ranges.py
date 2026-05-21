"""Tests for ODS named ranges + named expressions API."""

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


class NamedRangeTests(unittest.TestCase):
    def _make_ods(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "spec.json",
            {"sheets": [{"name": "Sales", "rows": [["Month", "Revenue"], ["Jan", "1000"], ["Feb", "1500"]]}]},
        )
        ods = tmp_path / "wb.ods"
        run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, ods)
        return ods

    def test_add_named_range_cell_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                ods,
                "--name",
                "Revenue",
                "--range",
                "Sales.B2:B3",
                "-o",
                out,
            )
            content = read_content(out)
            ranges = list(content.iter(q("table", "named-range")))
            self.assertEqual(len(ranges), 1)
            self.assertEqual(ranges[0].attrib.get(q("table", "name")), "Revenue")
            self.assertIn("Sales", ranges[0].attrib.get(q("table", "cell-range-address"), ""))

    def test_add_named_expression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                ods,
                "--name",
                "TaxRate",
                "--expression",
                "0.19",
                "-o",
                out,
            )
            content = read_content(out)
            exprs = list(content.iter(q("table", "named-expression")))
            self.assertEqual(len(exprs), 1)
            self.assertEqual(exprs[0].attrib.get(q("table", "name")), "TaxRate")
            self.assertEqual(exprs[0].attrib.get(q("table", "expression")), "0.19")

    def test_add_named_range_sheet_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                ods,
                "--name",
                "Local",
                "--range",
                "Sales.B2:B3",
                "--scope",
                "sheet:Sales",
                "-o",
                out,
            )
            content = read_content(out)
            # Sheet-scoped: decls nested under the sheet
            sheet = next(s for s in content.iter(q("table", "table")) if s.attrib.get(q("table", "name")) == "Sales")
            sheet_decls = sheet.find(q("table", "named-expressions"))
            assert sheet_decls is not None
            self.assertEqual(len(sheet_decls), 1)

    def test_list_named_ranges_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            with_nr = tmp_path / "nr.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                ods,
                "--name",
                "R",
                "--range",
                "Sales.B2:B3",
                "-o",
                with_nr,
            )
            with_both = tmp_path / "both.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                with_nr,
                "--name",
                "T",
                "--expression",
                "0.19",
                "-o",
                with_both,
            )
            result = run_script(SKILLS / "ods" / "scripts" / "list_named_ranges.py", with_both, "--json").stdout
            data = json.loads(result)
            names = {entry["name"] for entry in data}
            self.assertEqual(names, {"R", "T"})

    def test_add_named_range_idempotent(self) -> None:
        """Re-adding the same name replaces the entry, not duplicates."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            first = tmp_path / "first.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                ods,
                "--name",
                "X",
                "--range",
                "Sales.B2:B3",
                "-o",
                first,
            )
            second = tmp_path / "second.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                first,
                "--name",
                "X",
                "--expression",
                "42",
                "-o",
                second,
            )
            content = read_content(second)
            entries = list(content.iter(q("table", "named-range"))) + list(content.iter(q("table", "named-expression")))
            xs = [e for e in entries if e.attrib.get(q("table", "name")) == "X"]
            self.assertEqual(len(xs), 1)
            # The second add wins — it's a named-expression
            self.assertEqual(xs[0].tag, q("table", "named-expression"))

    def test_validate_refs_detects_unknown_sheet_in_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = self._make_ods(tmp_path)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "add_named_range.py",
                ods,
                "--name",
                "Bad",
                "--range",
                "MissingSheet.A1:A10",
                "-o",
                out,
            )
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", out, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MissingSheet", result.stdout)


if __name__ == "__main__":
    unittest.main()
