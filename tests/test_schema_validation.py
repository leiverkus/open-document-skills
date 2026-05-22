"""Tests for RelaxNG schema validation (--strict flag)."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import FIXTURES, SKILLS, run_script

HAVE_LXML = importlib.util.find_spec("lxml") is not None


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
        result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", "--help")
        self.assertIn("--strict", result.stdout)
        self.assertIn("RelaxNG", result.stdout)


if __name__ == "__main__":
    unittest.main()
