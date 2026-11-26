#!/usr/bin/env python3
"""Recalculate an ODS with LibreOffice and validate formula/error references."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ods_common import convert_with_soffice


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ods", type=Path)
    parser.add_argument("--outdir", type=Path, default=Path("qa"))
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    target = args.outdir / args.ods.name

    # Convert from a scratch copy into a separate scratch directory: soffice
    # cannot overwrite the file it has open (it reports an error yet exits 0),
    # so converting the target onto itself silently skipped recalculation.
    with tempfile.TemporaryDirectory(prefix="odf-recalc-") as scratch:
        scratch_dir = Path(scratch)
        source = scratch_dir / "in" / args.ods.name
        source.parent.mkdir()
        shutil.copyfile(args.ods, source)
        recalculated = convert_with_soffice(source, "ods", scratch_dir / "out")
        shutil.move(str(recalculated), target)

    print(target)
    validate = Path(__file__).with_name("validate_refs.py")
    result = subprocess.run(
        [sys.executable, str(validate), str(target)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
