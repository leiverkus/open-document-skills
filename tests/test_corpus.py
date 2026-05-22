"""Roundtrip tests for every v0.2-v0.8 helper against the real-world corpus.

The corpus (tests/fixtures/corpus/) holds LibreOffice-native ODF files. These
tests exercise validate_refs, flat-ODF pack/unpack, and format-specific edit
operations against each fixture — catching bugs where helpers assume our own
generator's output structure.
"""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import ROOT, SKILLS, run_script

CORPUS = ROOT / "tests" / "fixtures" / "corpus"

FORMAT_DIR = {".odt": "odt", ".odp": "odp", ".ods": "ods", ".odg": "odg"}
PACK_SCRIPT = {".odt": "pack_fodt.py", ".odp": "pack_fodp.py",
               ".ods": "pack_fods.py", ".odg": "pack_fodg.py"}
UNPACK_SCRIPT = {".odt": "unpack_fodt.py", ".odp": "unpack_fodp.py",
                 ".ods": "unpack_fods.py", ".odg": "unpack_fodg.py"}
FLAT_EXT = {".odt": ".fodt", ".odp": ".fodp", ".ods": ".fods", ".odg": ".fodg"}


def corpus_fixtures() -> list[Path]:
    if not CORPUS.is_dir():
        return []
    return sorted(p for p in CORPUS.iterdir() if p.suffix in FORMAT_DIR)


class CorpusRoundtripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = corpus_fixtures()
        if not self.fixtures:
            self.skipTest("corpus empty — run tests/fixtures/corpus/build_corpus.py")

    def test_corpus_size(self) -> None:
        self.assertGreaterEqual(
            len(self.fixtures), 12,
            "corpus too small — run build_corpus.py to regenerate",
        )

    def test_validate_refs_on_every_fixture(self) -> None:
        """Every LibreOffice-native fixture must pass internal validation."""
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture.name):
                skill = FORMAT_DIR[fixture.suffix]
                result = run_script(
                    SKILLS / skill / "scripts" / "validate_refs.py", fixture, check=False
                )
                payload = json.loads(result.stdout)
                self.assertEqual(
                    payload["status"], "ok",
                    f"{fixture.name}: validation errors {payload.get('errors')}",
                )

    def test_flat_odf_roundtrip_on_every_fixture(self) -> None:
        """pack → unpack → validate must stay green for every fixture."""
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture.name):
                skill = FORMAT_DIR[fixture.suffix]
                scripts = SKILLS / skill / "scripts"
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    flat = tmp_path / ("rt" + FLAT_EXT[fixture.suffix])
                    back = tmp_path / ("rt" + fixture.suffix)
                    run_script(scripts / PACK_SCRIPT[fixture.suffix], fixture, "-o", flat)
                    run_script(scripts / UNPACK_SCRIPT[fixture.suffix], flat, "-o", back)
                    result = run_script(scripts / "validate_refs.py", back, check=False)
                    payload = json.loads(result.stdout)
                    self.assertEqual(
                        payload["status"], "ok",
                        f"{fixture.name}: flat-ODF roundtrip broke validation: {payload.get('errors')}",
                    )

    def test_repack_stability_on_every_fixture(self) -> None:
        """Re-packing a fixture must keep mimetype first and the ZIP valid."""
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture.name):
                with zipfile.ZipFile(fixture) as archive:
                    names = archive.namelist()
                self.assertEqual(names[0], "mimetype", f"{fixture.name}: mimetype not first")

    def test_odt_edits(self) -> None:
        scripts = SKILLS / "odt" / "scripts"
        for fixture in [f for f in self.fixtures if f.suffix == ".odt"]:
            with self.subTest(fixture=fixture.name):
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp) / "out.odt"
                    # extract_text --json must parse
                    result = run_script(scripts / "extract_text.py", fixture, "--json")
                    json.loads(result.stdout)
                    # add_footnote at the document's first paragraph
                    run_script(scripts / "add_footnote.py", fixture,
                               "--paragraph", "1", "--body", "corpus note", "-o", out)
                    vr = run_script(scripts / "validate_refs.py", out, check=False)
                    self.assertEqual(json.loads(vr.stdout)["status"], "ok",
                                     f"{fixture.name}: add_footnote broke validation")

    def test_ods_edits(self) -> None:
        scripts = SKILLS / "ods" / "scripts"
        for fixture in [f for f in self.fixtures if f.suffix == ".ods"]:
            with self.subTest(fixture=fixture.name):
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp) / "out.ods"
                    sheets = json.loads(
                        run_script(scripts / "extract_sheets.py", fixture, "--json").stdout
                    )
                    self.assertGreaterEqual(len(sheets), 1)
                    sheet_name = sheets[0]["name"]
                    run_script(scripts / "replace_cells.py", fixture,
                               f"{sheet_name}!Z1=corpus", "-o", out)
                    vr = run_script(scripts / "validate_refs.py", out, check=False)
                    self.assertEqual(json.loads(vr.stdout)["status"], "ok",
                                     f"{fixture.name}: replace_cells broke validation")

    def test_odp_edits(self) -> None:
        scripts = SKILLS / "odp" / "scripts"
        for fixture in [f for f in self.fixtures if f.suffix == ".odp"]:
            with self.subTest(fixture=fixture.name):
                # extract_text --json must parse
                result = run_script(scripts / "extract_text.py", fixture, "--json")
                json.loads(result.stdout)

    def test_odg_edits(self) -> None:
        scripts = SKILLS / "odg" / "scripts"
        for fixture in [f for f in self.fixtures if f.suffix == ".odg"]:
            with self.subTest(fixture=fixture.name):
                # extract_shapes must parse
                result = run_script(scripts / "extract_shapes.py", fixture)
                json.loads(result.stdout)
                # list_structure must parse
                ls = run_script(scripts / "list_structure.py", fixture, "--json")
                json.loads(ls.stdout)


if __name__ == "__main__":
    unittest.main()
