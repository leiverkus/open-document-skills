#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install OpenDocument skills for Codex, Claude Code, or OpenCode."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DEFAULT_SKILLS = ("odt", "odp", "ods", "odg")
PLUGIN_FILES = ("README.md", "LICENSE")
PLUGIN_DIRS = (".claude-plugin", "skills")

# Junk that must never end up in an installed skill or plugin bundle.
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def default_codex_destination() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def default_opencode_destination() -> Path:
    opencode_config = os.environ.get("OPENCODE_CONFIG_DIR")
    if opencode_config:
        return Path(opencode_config).expanduser() / "skills"
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config).expanduser() / "opencode" / "skills"
    return Path.home() / ".config" / "opencode" / "skills"


def default_destination(target: str) -> Path | None:
    if target == "codex":
        return default_codex_destination()
    if target == "agents":
        return Path.home() / ".agents" / "skills"
    if target == "opencode":
        return default_opencode_destination()
    return None


def install_skill(name: str, dest: Path, replace: bool) -> str:
    source = SKILLS_DIR / name
    target = dest / name
    if not source.exists():
        raise SystemExit(f"Unknown skill: {name}")
    if target.exists():
        if not replace:
            return f"skip {name}: already exists at {target}"
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=_IGNORE)
    # Bundle the shared odf_lib/ package so the skill runs standalone —
    # the scripts search upward from their own location for odf_lib/.
    shutil.copytree(ROOT / "odf_lib", target / "odf_lib", ignore=_IGNORE)
    return f"install {name}: {target}"


def install_skills(dest: Path, skills: list[str], replace: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in skills:
        print(install_skill(name, dest, replace))


def install_claude_plugin(dest: Path, replace: bool) -> None:
    if dest.exists():
        if not replace:
            print(f"skip claude-plugin: already exists at {dest}")
            return
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for filename in PLUGIN_FILES:
        shutil.copy2(ROOT / filename, dest / filename)
    for dirname in PLUGIN_DIRS:
        shutil.copytree(ROOT / dirname, dest / dirname, ignore=_IGNORE)
    # Bundle the shared odf_lib/ package at the plugin root so the skill
    # scripts resolve it via their upward search.
    shutil.copytree(ROOT / "odf_lib", dest / "odf_lib", ignore=_IGNORE)
    print(f"install claude-plugin: {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=["codex", "agents", "opencode", "claude"],
        default="codex",
        help="installation target; codex is the default",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        help=(
            "destination directory; defaults depend on --target. "
            "Claude target requires an explicit plugin destination such as ./dist/open-document-skills."
        ),
    )
    parser.add_argument(
        "--skills",
        nargs="+",
        default=list(DEFAULT_SKILLS),
        help="skills to install; defaults to odt odp ods odg",
    )
    parser.add_argument("--replace", action="store_true", help="replace existing destination skill directories")
    args = parser.parse_args()

    dest = args.dest or default_destination(args.target)
    if dest is None:
        raise SystemExit("--target claude requires --dest pointing to the plugin directory to create")
    dest = dest.expanduser().resolve()

    if args.target == "claude":
        install_claude_plugin(dest, args.replace)
        print("Add or install this plugin directory in Claude Code, then restart Claude Code if needed.")
        return

    install_skills(dest, args.skills, args.replace)
    if args.target == "opencode":
        print("Restart OpenCode to pick up newly installed skills.")
    else:
        print("Restart Codex to pick up newly installed skills.")


if __name__ == "__main__":
    main()
