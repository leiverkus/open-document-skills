#!/usr/bin/env python3
"""Apply a template (styles + master pictures) to an existing ODT in one shot.

The template is a directory laid out by ``extract_template.py`` (or
hand-curated and shipped under ``skills/odt/templates/<name>/``):

- ``styles.xml`` — the curated branded styles to inject.
- ``Pictures/`` (optional) — master-page-referenced images (e.g. letterhead
  logo).
- ``LICENSE.txt`` / ``PROVENANCE.md`` / ``README.md`` — metadata, ignored
  by this script.

This wraps the v1.1 ``inject_styles_from_file`` + ``embed_pictures`` +
``validate_refs`` chain into a single command. No ``content.xml``
rewriting — paragraph/text style names must match between the input ODT
and the template; ``validate_refs`` warns about any dangling style refs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from odt_common import embed_pictures, inject_styles_from_file

DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _resolve_template(template_arg: Path | None, name_arg: str | None) -> Path:
    if template_arg is not None and name_arg is not None:
        raise SystemExit("provide either --template PATH or --template-name NAME, not both")
    if template_arg is not None:
        if not template_arg.is_dir():
            raise SystemExit(f"--template path is not a directory: {template_arg}")
        return template_arg
    if name_arg is not None:
        candidate = DEFAULT_TEMPLATES_DIR / name_arg
        if not candidate.is_dir():
            available = (
                ", ".join(sorted(p.name for p in DEFAULT_TEMPLATES_DIR.iterdir() if p.is_dir()))
                if DEFAULT_TEMPLATES_DIR.is_dir()
                else "(none — templates directory missing)"
            )
            raise SystemExit(f"template {name_arg!r} not found in {DEFAULT_TEMPLATES_DIR}. Available: {available}")
        return candidate
    raise SystemExit("provide --template PATH or --template-name NAME")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--template", type=Path, help="path to a template directory")
    where.add_argument("--template-name", help=f"name of a template under {DEFAULT_TEMPLATES_DIR}")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="skip the post-apply validate_refs.py check (still injects + embeds)",
    )
    args = parser.parse_args()

    template_dir = _resolve_template(args.template, args.template_name)
    styles_xml = template_dir / "styles.xml"
    if not styles_xml.is_file():
        raise SystemExit(f"template missing styles.xml: {styles_xml}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        intermediate = tmp_path / "styled.odt"
        missing = inject_styles_from_file(args.input_odt, styles_xml, intermediate)
        for ref in missing:
            print(
                f"warning: content.xml references style {ref!r} not in template",
                file=sys.stderr,
            )

        pictures_dir = template_dir / "Pictures"
        if pictures_dir.is_dir():
            pictures: dict[str, Path] = {}
            for picture_file in pictures_dir.rglob("*"):
                if not picture_file.is_file():
                    continue
                rel = picture_file.relative_to(pictures_dir).as_posix()
                pictures[f"Pictures/{rel}"] = picture_file
            if pictures:
                embed_pictures(intermediate, pictures, args.output)
            else:
                args.output.write_bytes(intermediate.read_bytes())
        else:
            args.output.write_bytes(intermediate.read_bytes())

    if not args.skip_validate:
        validate = Path(__file__).with_name("validate_refs.py")
        result = subprocess.run(
            [sys.executable, str(validate), str(args.output)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.exit(result.returncode)
        return

    print(args.output)


if __name__ == "__main__":
    main()
