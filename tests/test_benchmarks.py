"""Smoke test for the performance benchmark script.

Runs benchmarks/run_benchmarks.py in --quick mode so the script cannot
rot. It asserts only that the run succeeds and emits a results table —
not any latency threshold (CI-runner variance makes those unreliable).
"""

from __future__ import annotations

import subprocess
import sys
import unittest

from helpers import ROOT


class BenchmarkSmokeTests(unittest.TestCase):
    def test_quick_benchmark_runs(self) -> None:
        script = ROOT / "benchmarks" / "run_benchmarks.py"
        self.assertTrue(script.is_file(), "benchmark script missing")
        result = subprocess.run(
            [sys.executable, "-B", str(script), "--quick"],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        # Every format and the results table must appear.
        for token in ("ODT", "ODS", "ODP", "ODG", "| Format | Operation |"):
            self.assertIn(token, result.stdout)


if __name__ == "__main__":
    unittest.main()
