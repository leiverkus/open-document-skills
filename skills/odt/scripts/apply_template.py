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
import copy
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from odt_common import (
    embed_pictures,
    inject_styles_from_file,
    parse_xml_from_zip,
    q,
    write_odt_with_replacements,
    xml_bytes,
)

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


def carry_over_document_styles(original_odt: Path, styled_odt: Path, names: list[str]) -> list[str]:
    """Copy named styles the template lacks from the original styles.xml.

    The template's ``styles.xml`` replaces the document's wholesale, so styles
    the content still references (e.g. the ``ListNumber`` list style or the
    ``TableHeader`` paragraph style written by ``create_from_markdown.py``)
    would vanish — numbered lists turn into bullets, table headers lose their
    weight. Template styles always win; only names the template does not
    define are carried over, together with their parent-style chain and the
    font-face declarations they use. Rewrites *styled_odt* in place and
    returns the names actually carried over.
    """
    if not names:
        return []
    old_root = parse_xml_from_zip(original_odt, "styles.xml")
    new_root = parse_xml_from_zip(styled_odt, "styles.xml")
    old_office = old_root.find(q("office", "styles"))
    new_office = new_root.find(q("office", "styles"))
    if old_office is None:
        return []
    if new_office is None:
        new_office = ET.SubElement(new_root, q("office", "styles"))

    name_attr = q("style", "name")
    new_defined = {el.get(name_attr) for el in new_office if el.get(name_attr)}
    old_by_name: dict[str, ET.Element] = {}
    for el in old_office:
        name = el.get(name_attr)
        if name and name not in old_by_name:
            old_by_name[name] = el

    wanted = [n for n in names if n in old_by_name and n not in new_defined]
    carried: list[str] = []
    carried_elements: list[ET.Element] = []
    while wanted:
        name = wanted.pop(0)
        if name in new_defined:
            continue
        element = copy.deepcopy(old_by_name[name])
        new_office.append(element)
        new_defined.add(name)
        carried.append(name)
        carried_elements.append(element)
        parent = element.get(q("style", "parent-style-name"))
        if parent and parent not in new_defined and parent in old_by_name:
            wanted.append(parent)

    # Font faces referenced by the carried styles.
    font_attr = q("style", "font-name")
    fonts_used = {node.get(font_attr) for element in carried_elements for node in element.iter() if node.get(font_attr)}
    old_faces = old_root.find(q("office", "font-face-decls"))
    if old_faces is not None and fonts_used:
        new_faces = new_root.find(q("office", "font-face-decls"))
        if new_faces is None:
            new_faces = ET.Element(q("office", "font-face-decls"))
            new_root.insert(0, new_faces)
        have = {face.get(name_attr) for face in new_faces}
        for face in old_faces:
            face_name = face.get(name_attr)
            if face_name in fonts_used and face_name not in have:
                new_faces.append(copy.deepcopy(face))

    if carried:
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / styled_odt.name
            write_odt_with_replacements(styled_odt, staged, {"styles.xml": xml_bytes(new_root)})
            styled_odt.write_bytes(staged.read_bytes())
    return carried


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
    parser.add_argument(
        "--no-carry-over",
        action="store_true",
        help="drop document styles the template does not define (previous behaviour)",
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
        if not args.no_carry_over:
            carried = carry_over_document_styles(args.input_odt, intermediate, missing)
            if carried:
                print(
                    "kept document styles the template does not define: " + ", ".join(carried),
                    file=sys.stderr,
                )
            missing = [ref for ref in missing if ref not in carried]
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
