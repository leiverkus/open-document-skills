"""Tests for the ODS conditional-formatting API (add_conditional_format.py)."""

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
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "calcext": "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def read_member(path: Path, member: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read(member))


def make_ods(tmp_path: Path) -> Path:
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "sheets": [
                    {
                        "name": "Data",
                        "rows": [
                            ["Region", "Revenue"],
                            ["North", "150"],
                            ["South", "80"],
                            ["East", "220"],
                            ["West", "45"],
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ods = tmp_path / "wb.ods"
    run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, ods)
    return ods


def add_cf(ods: Path, out: Path, *args: object) -> None:
    run_script(SKILLS / "ods" / "scripts" / "add_conditional_format.py", ods, *args, "-o", out)


class ConditionalFormatTests(unittest.TestCase):
    def test_value_condition_builds_styles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_ods(tmp_path)
            out = tmp_path / "out.ods"
            add_cf(ods, out, "--range", "Data.B2:B5", "--condition", "value > 100", "--background", "#C8E6C9")
            styles = read_member(out, "styles.xml")
            office_styles = styles.find(q("office", "styles"))
            assert office_styles is not None
            names = {s.attrib.get(q("style", "name")) for s in office_styles.findall(q("style", "style"))}
            self.assertIn("cf_Data_B2_B5", names)
            self.assertIn("cf_Data_B2_B5_a1", names)
            # The condition style carries one style:map.
            cond = next(
                s
                for s in office_styles.findall(q("style", "style"))
                if s.attrib.get(q("style", "name")) == "cf_Data_B2_B5"
            )
            maps = cond.findall(q("style", "map"))
            self.assertEqual(len(maps), 1)
            self.assertEqual(maps[0].attrib.get(q("style", "condition")), "cell-content()>100")
            # The apply style holds the background.
            apply = next(
                s
                for s in office_styles.findall(q("style", "style"))
                if s.attrib.get(q("style", "name")) == "cf_Data_B2_B5_a1"
            )
            props = apply.find(q("style", "table-cell-properties"))
            assert props is not None
            self.assertEqual(props.attrib.get(q("fo", "background-color")), "#C8E6C9")

    def test_calcext_conditional_format_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_ods(tmp_path)
            out = tmp_path / "out.ods"
            add_cf(ods, out, "--range", "Data.B2:B5", "--condition", "value > 100", "--background", "#C8E6C9")
            content = read_member(out, "content.xml")
            table = content.find(".//table:table", NS)
            assert table is not None
            # calcext:conditional-formats must be the last child of table:table.
            self.assertEqual(list(table)[-1].tag, q("calcext", "conditional-formats"))
            condition = content.find(".//calcext:condition", NS)
            assert condition is not None
            self.assertEqual(condition.attrib.get(q("calcext", "value")), ">100")

    def test_between_and_formula_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_ods(tmp_path)
            out1 = tmp_path / "between.ods"
            add_cf(ods, out1, "--range", "Data.B2:B5", "--condition", "value between 50 200", "--bold")
            styles = read_member(out1, "styles.xml")
            mp = styles.find(".//style:map", NS)
            assert mp is not None
            self.assertEqual(mp.attrib.get(q("style", "condition")), "cell-content-is-between(50,200)")
            cond = read_member(out1, "content.xml").find(".//calcext:condition", NS)
            assert cond is not None
            self.assertEqual(cond.attrib.get(q("calcext", "value")), "between(50,200)")

            out2 = tmp_path / "formula.ods"
            add_cf(ods, out2, "--range", "Data.B2:B5", "--condition", "formula:[.B2]>100", "--italic")
            mp2 = read_member(out2, "styles.xml").find(".//style:map", NS)
            assert mp2 is not None
            self.assertEqual(mp2.attrib.get(q("style", "condition")), "is-true-formula([.B2]>100)")

    def test_rules_stack_on_repeated_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_ods(tmp_path)
            step1 = tmp_path / "step1.ods"
            step2 = tmp_path / "step2.ods"
            add_cf(ods, step1, "--range", "Data.B2:B5", "--condition", "value > 100", "--background", "#C8E6C9")
            add_cf(step1, step2, "--range", "Data.B2:B5", "--condition", "value < 50", "--background", "#FFCDD2")
            styles = read_member(step2, "styles.xml")
            cond = next(
                s for s in styles.iter(q("style", "style")) if s.attrib.get(q("style", "name")) == "cf_Data_B2_B5"
            )
            self.assertEqual(len(cond.findall(q("style", "map"))), 2)
            content = read_member(step2, "content.xml")
            conditions = list(content.iter(q("calcext", "condition")))
            self.assertEqual(len(conditions), 2)

    def test_validate_refs_detects_dangling_style_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_ods(tmp_path)
            out = tmp_path / "out.ods"
            add_cf(ods, out, "--range", "Data.B2:B5", "--condition", "value > 100", "--background", "#C8E6C9")
            broken = tmp_path / "broken.ods"
            with zipfile.ZipFile(out) as src:
                styles = (
                    src.read("styles.xml")
                    .decode("utf-8")
                    .replace(
                        '<style:style style:name="cf_Data_B2_B5_a1"',
                        '<style:style style:name="renamed_a1"',
                        1,
                    )
                )
                with zipfile.ZipFile(broken, "w") as dst:
                    for name in src.namelist():
                        data = styles.encode("utf-8") if name == "styles.xml" else src.read(name)
                        mode = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
                        dst.writestr(name, data, mode)
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", broken, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("style:map references unknown style", result.stdout)

    @unittest.skipUnless(HAVE_LXML, "lxml not installed")
    def test_strict_validation_treats_calcext_as_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = make_ods(tmp_path)
            out = tmp_path / "out.ods"
            add_cf(ods, out, "--range", "Data.B2:B5", "--condition", "value > 100", "--background", "#C8E6C9")
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", out, "--strict")
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertTrue(any("calcext" in w for w in payload["warnings"]))


if __name__ == "__main__":
    unittest.main()
