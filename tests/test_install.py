from __future__ import annotations

# SPDX-License-Identifier: MIT
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, run_script

MINIMAL_ODT_SPEC = {"title": "Install Test", "blocks": [{"type": "paragraph", "text": "Hi"}]}


class InstallTests(unittest.TestCase):
    def test_claude_plugin_manifest(self) -> None:
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "open-document-skills")
        self.assertEqual(manifest["license"], "MIT")
        self.assertIn("opendocument", manifest["keywords"])

    def test_install_skills_to_custom_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "skills"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "install_skills.py"), "--dest", str(dest)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("Restart Codex", result.stdout)
            for name in ["odt", "odp", "ods", "odg"]:
                self.assertTrue((dest / name / "SKILL.md").exists())
                self.assertTrue((dest / name / "LICENSE.txt").exists())
                self.assertTrue((dest / name / "scripts").is_dir())

            second = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "install_skills.py"), "--dest", str(dest)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("skip odt", second.stdout)

    def test_install_opencode_target_to_custom_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode" / "skills"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skills.py"),
                    "--target",
                    "opencode",
                    "--dest",
                    str(dest),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("Restart OpenCode", result.stdout)
            self.assertTrue((dest / "odp" / "SKILL.md").exists())

    def test_install_claude_plugin_to_custom_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "open-document-skills"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skills.py"),
                    "--target",
                    "claude",
                    "--dest",
                    str(dest),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertIn("install claude-plugin", result.stdout)
            self.assertTrue((dest / ".claude-plugin" / "plugin.json").exists())
            self.assertTrue((dest / "skills" / "odt" / "SKILL.md").exists())
            self.assertTrue((dest / "skills" / "odg" / "scripts").is_dir())

    def test_installed_skill_bundles_odf_lib_and_runs(self) -> None:
        """A standalone-installed skill must carry odf_lib/ and run its scripts.

        Regression: installs previously omitted the shared odf_lib/ package,
        so every script crashed with ModuleNotFoundError outside the repo
        checkout (surfaced when the plugin was installed in Claude Cowork).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dest = tmp_path / "skills"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skills.py"),
                    "--dest",
                    str(dest),
                    "--skills",
                    "odt",
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            # odf_lib/ must be bundled into the installed skill.
            self.assertTrue((dest / "odt" / "odf_lib" / "odf_common.py").is_file())
            # The install must be free of build junk.
            self.assertEqual(list(dest.rglob("__pycache__")), [])
            self.assertEqual(list(dest.rglob("*.pyc")), [])
            # A bundled script must run standalone — repo odf_lib/ is unreachable here.
            spec = tmp_path / "spec.json"
            spec.write_text(json.dumps(MINIMAL_ODT_SPEC), encoding="utf-8")
            out = tmp_path / "out.odt"
            run_script(dest / "odt" / "scripts" / "create_minimal_odt.py", spec, out)
            result = run_script(dest / "odt" / "scripts" / "validate_refs.py", out)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")

    def test_claude_plugin_bundle_runs_standalone(self) -> None:
        """The Claude plugin bundle must carry odf_lib/ and run its scripts."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dest = tmp_path / "plugin"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skills.py"),
                    "--target",
                    "claude",
                    "--dest",
                    str(dest),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertTrue((dest / "odf_lib" / "odf_common.py").is_file())
            spec = tmp_path / "spec.json"
            spec.write_text(json.dumps(MINIMAL_ODT_SPEC), encoding="utf-8")
            out = tmp_path / "out.odt"
            run_script(dest / "skills" / "odt" / "scripts" / "create_minimal_odt.py", spec, out)
            result = run_script(dest / "skills" / "odt" / "scripts" / "validate_refs.py", out)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")

    def test_claude_target_requires_destination(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "install_skills.py"), "--target", "claude"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target claude requires --dest", result.stdout)


if __name__ == "__main__":
    unittest.main()
