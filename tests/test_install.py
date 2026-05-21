from __future__ import annotations

# SPDX-License-Identifier: MIT

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT


class InstallTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
