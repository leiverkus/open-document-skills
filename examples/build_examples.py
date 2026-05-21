#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build example ODF files from the JSON specs in this directory."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


EXAMPLE_JOBS = [
    ("odt", "odt_document.json", "example.odt", "create_minimal_odt.py"),
    ("odp", "odp_slides.json", "example.odp", "create_minimal_odp.py"),
    ("ods", "ods_workbook.json", "example.ods", "create_minimal_ods.py"),
    ("odg", "odg_drawing.json", "example.odg", "create_minimal_odg.py"),
]


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=EXAMPLES / "output")
    parser.add_argument("--render", action="store_true", help="also render/recalculate with LibreOffice where supported")
    parser.add_argument("--png", action="store_true", help="render PDF pages to PNG for ODT/ODP")
    args = parser.parse_args()

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    for skill, spec_name, output_name, script_name in EXAMPLE_JOBS:
        run(
            [
                sys.executable,
                str(ROOT / "skills" / skill / "scripts" / script_name),
                str(EXAMPLES / spec_name),
                str(outdir / output_name),
            ]
        )
        run([sys.executable, str(ROOT / "skills" / skill / "scripts" / "validate_refs.py"), str(outdir / output_name)])

    if args.render:
        render_jobs = [
            ("odt", "render.py", "example.odt"),
            ("odp", "render.py", "example.odp"),
            ("ods", "recalc.py", "example.ods"),
            ("odg", "render.py", "example.odg"),
        ]
        for skill, script_name, filename in render_jobs:
            command = [
                sys.executable,
                str(ROOT / "skills" / skill / "scripts" / script_name),
                str(outdir / filename),
                "--outdir",
                str(outdir / "qa" / skill),
            ]
            if args.png and skill in {"odt", "odp"}:
                command.append("--png")
            run(command)

    print(f"Built examples in {outdir}")


if __name__ == "__main__":
    main()
