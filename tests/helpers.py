from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
FIXTURES = ROOT / "tests" / "fixtures"


def run_script(script: Path, *args: object, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *map(str, args)],
        cwd=script.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def assert_mimetype_first(testcase, path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        testcase.assertEqual(archive.namelist()[0], "mimetype")
