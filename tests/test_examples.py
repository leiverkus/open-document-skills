from __future__ import annotations

# SPDX-License-Identifier: MIT
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, assert_mimetype_first


class ExampleTests(unittest.TestCase):
    def test_build_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp) / "examples"
            subprocess.run(
                [sys.executable, str(ROOT / "examples" / "build_examples.py"), "--outdir", str(outdir)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for filename in ["example.odt", "example.odp", "example.ods", "example.odg"]:
                path = outdir / filename
                self.assertTrue(path.exists(), filename)
                assert_mimetype_first(self, path)


if __name__ == "__main__":
    unittest.main()
