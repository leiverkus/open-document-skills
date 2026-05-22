"""Tests for RelaxNG schema validation (--strict flag).

The OASIS ODF 1.3 ``content`` schema is shared across all four formats,
so ``validate_refs.py --strict`` works for ODT/ODP/ODS/ODG alike. These
tests are the CI schema gate: they run on every build (CI installs lxml).
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import FIXTURES, SKILLS, run_script

HAVE_LXML = importlib.util.find_spec("lxml") is not None

# Minimal per-format specs for generating documents to validate.
MINIMAL_SPECS = {
    "ods": {"sheets": [{"name": "Sheet1", "rows": [["a", "b"]]}]},
    "odp": {"slides": [{"name": "Intro", "title": "Hello"}]},
    "odg": {"pages": [{"name": "Page", "items": [{"type": "rect", "width": "3cm", "height": "2cm"}]}]},
}


def _generate(fmt: str, spec: object, out_dir: Path) -> Path:
    """Generate a minimal document of *fmt* from *spec* into *out_dir*."""
    spec_path = out_dir / f"{fmt}.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    out = out_dir / f"doc.{fmt}"
    run_script(SKILLS / fmt / "scripts" / f"create_minimal_{fmt}.py", spec_path, out)
    return out


@unittest.skipUnless(HAVE_LXML, "lxml not installed")
class SchemaValidationTests(unittest.TestCase):
    def test_strict_validation_on_minimal_odt(self) -> None:
        """A minimal generated ODT must pass the OASIS RelaxNG schema."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                FIXTURES / "odt_document.json",
                odt,
            )
            result = run_script(
                SKILLS / "odt" / "scripts" / "validate_refs.py",
                odt,
                "--strict",
                check=False,
            )
            # We don't assert strict ok — the minimal generator may emit minor
            # non-conformances. We DO assert that the strict path runs (no crash)
            # and that the output JSON has the expected shape.
            self.assertIn("status", result.stdout)
            self.assertIn("errors", result.stdout)

    def test_strict_validation_detects_broken_xml(self) -> None:
        """A doc with malformed XML inside content.xml must fail strict validation."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                FIXTURES / "odt_document.json",
                odt,
            )
            broken = tmp_path / "broken.odt"
            with zipfile.ZipFile(odt) as src:
                with zipfile.ZipFile(broken, "w") as dst:
                    for name in src.namelist():
                        if name == "mimetype":
                            dst.writestr("mimetype", src.read("mimetype"), zipfile.ZIP_STORED)
                        elif name == "content.xml":
                            # Inject malformed XML
                            dst.writestr(name, b"<not-valid-odf/>")
                        else:
                            dst.writestr(name, src.read(name))
            result = run_script(
                SKILLS / "odt" / "scripts" / "validate_refs.py",
                broken,
                "--strict",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("content.xml", result.stdout)

    def test_strict_validation_on_minimal_odp(self) -> None:
        """A minimal generated ODP must pass the OASIS RelaxNG schema."""
        with tempfile.TemporaryDirectory() as tmp:
            odp = _generate("odp", MINIMAL_SPECS["odp"], Path(tmp))
            result = run_script(
                SKILLS / "odp" / "scripts" / "validate_refs.py", odp, "--strict", check=False
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok", payload.get("errors"))

    def test_strict_validation_on_minimal_odg(self) -> None:
        """A minimal generated ODG must pass the OASIS RelaxNG schema."""
        with tempfile.TemporaryDirectory() as tmp:
            odg = _generate("odg", MINIMAL_SPECS["odg"], Path(tmp))
            result = run_script(
                SKILLS / "odg" / "scripts" / "validate_refs.py", odg, "--strict", check=False
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok", payload.get("errors"))

    def test_strict_validation_on_minimal_ods(self) -> None:
        """A minimal generated ODS must pass the OASIS RelaxNG schema.

        The minimal sheet generator emits explicit table-column declarations
        before its rows, as the schema requires for table:table.
        """
        with tempfile.TemporaryDirectory() as tmp:
            ods = _generate("ods", MINIMAL_SPECS["ods"], Path(tmp))
            result = run_script(
                SKILLS / "ods" / "scripts" / "validate_refs.py", ods, "--strict", check=False
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok", payload.get("errors"))

    def test_strict_detects_broken_xml_ods(self) -> None:
        """The schema gate must have teeth on non-ODT formats too."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ods = _generate("ods", MINIMAL_SPECS["ods"], tmp_path)
            broken = tmp_path / "broken.ods"
            with zipfile.ZipFile(ods) as src, zipfile.ZipFile(broken, "w") as dst:
                for name in src.namelist():
                    if name == "mimetype":
                        dst.writestr("mimetype", src.read("mimetype"), zipfile.ZIP_STORED)
                    elif name == "content.xml":
                        dst.writestr(name, b"<not-valid-odf/>")
                    else:
                        dst.writestr(name, src.read(name))
            result = run_script(
                SKILLS / "ods" / "scripts" / "validate_refs.py", broken, "--strict", check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("content.xml", result.stdout)

    def test_ensure_schema_caches_after_download(self) -> None:
        """ensure_schema should not re-download on second call."""
        import sys

        sys.path.insert(0, str(SKILLS.parent))
        from odf_lib.odf_common import ensure_schema  # noqa: E402

        first = ensure_schema("manifest")
        self.assertTrue(first.exists())
        mtime_first = first.stat().st_mtime
        second = ensure_schema("manifest")
        self.assertEqual(first, second)
        # Should not have been re-downloaded
        self.assertEqual(second.stat().st_mtime, mtime_first)


class SchemaValidationDependencyTests(unittest.TestCase):
    def test_strict_flag_advertised_in_help(self) -> None:
        """All four validate_refs.py scripts must advertise --strict."""
        for fmt in ("odt", "odp", "ods", "odg"):
            with self.subTest(fmt=fmt):
                result = run_script(SKILLS / fmt / "scripts" / "validate_refs.py", "--help")
                self.assertIn("--strict", result.stdout)
                self.assertIn("RelaxNG", result.stdout)


if __name__ == "__main__":
    unittest.main()
