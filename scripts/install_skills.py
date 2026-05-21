#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install OpenDocument skills into a Codex skills directory."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DEFAULT_SKILLS = ("odt", "odp", "ods", "odg")


def default_destination() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def install_skill(name: str, dest: Path, replace: bool) -> str:
    source = SKILLS_DIR / name
    target = dest / name
    if not source.exists():
        raise SystemExit(f"Unknown skill: {name}")
    if target.exists():
        if not replace:
            return f"skip {name}: already exists at {target}"
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return f"install {name}: {target}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=default_destination(),
        help="destination skills directory; defaults to $CODEX_HOME/skills or ~/.codex/skills",
    )
    parser.add_argument(
        "--skills",
        nargs="+",
        default=list(DEFAULT_SKILLS),
        help="skills to install; defaults to odt odp ods odg",
    )
    parser.add_argument("--replace", action="store_true", help="replace existing destination skill directories")
    args = parser.parse_args()

    dest = args.dest.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    for name in args.skills:
        print(install_skill(name, dest, args.replace))

    print("Restart Codex to pick up newly installed skills.")


if __name__ == "__main__":
    main()
