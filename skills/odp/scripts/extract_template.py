#!/usr/bin/env python3
"""Extract a reusable ODP template from an existing presentation.

Inputs:

- ``.odp`` / ``.otp`` — read directly.
- ``.pptx`` / ``.ppt`` — auto-converted to ODP first via the v1.11
  ``convert_with_soffice`` bridge, then extracted.

Output: a template directory ``<outdir>/<name>/`` containing:

- ``styles.xml`` — extracted and auto-style-filtered (only the styles
  master pages actually reference are kept; per-slide anonyms like ``gr1``,
  ``P3`` from ``office:automatic-styles`` are dropped).
- ``Pictures/`` — only the images referenced from master pages (logos,
  background bitmaps); per-slide images are excluded.
- ``LICENSE.txt`` — placeholder for the redistributable license. Set
  ``--license LICENSE_ID --source URL`` to populate automatically.
- ``PROVENANCE.md`` — source filename, date, and tool version.
- ``README.md`` — auto-generated inventory (masters, layouts, named styles)
  so a human can browse what the template offers.

The output directory is directly usable by ``apply_template.py``.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from odp_common import (
    NS,
    convert_with_soffice,
    inspect_styles_xml,
    parse_xml_from_zip,
    q,
    xml_bytes,
)


def _seed_referenced_auto_style_names(styles_root: ET.Element) -> set[str]:
    """Names of auto-styles directly referenced by master pages."""
    seed: set[str] = set()
    for master in styles_root.findall(".//style:master-page", NS):
        ds = master.attrib.get(q("draw", "style-name"))
        if ds:
            seed.add(ds)
        pl = master.attrib.get(q("style", "page-layout-name"))
        if pl:
            seed.add(pl)
    return seed


def _build_auto_style_index(styles_root: ET.Element) -> dict[str, ET.Element]:
    """Map of auto-style name → element for resolving parent-style chains."""
    index: dict[str, ET.Element] = {}
    name_attr = q("style", "name")
    auto = styles_root.find(".//office:automatic-styles", NS)
    if auto is None:
        return index
    for child in list(auto):
        name = child.attrib.get(name_attr)
        if name:
            index[name] = child
    return index


def _expand_auto_style_keep(seed: set[str], auto_index: dict[str, ET.Element]) -> set[str]:
    """Expand seed with parent-style chains; drop names not in auto_index."""
    parent_attr = q("style", "parent-style-name")
    keep: set[str] = set()
    queue: list[str] = list(seed)
    while queue:
        name = queue.pop()
        if name in keep:
            continue
        if name not in auto_index:
            # Probably a built-in style (e.g. ``standard``) — nothing to keep.
            continue
        keep.add(name)
        parent = auto_index[name].attrib.get(parent_attr)
        if parent:
            queue.append(parent)
    return keep


def filter_auto_styles(styles_root: ET.Element) -> tuple[ET.Element, int, int]:
    """Strip per-slide anonyms from styles_root's ``office:automatic-styles``.

    Walks the master pages to collect referenced names, then keeps only those
    auto-styles (and their parent chains). Modifies styles_root in place;
    returns ``(styles_root, kept_count, dropped_count)`` for logging.
    """
    seed = _seed_referenced_auto_style_names(styles_root)
    auto_index = _build_auto_style_index(styles_root)
    keep = _expand_auto_style_keep(seed, auto_index)

    auto = styles_root.find(".//office:automatic-styles", NS)
    if auto is None:
        return styles_root, 0, 0
    name_attr = q("style", "name")
    kept = 0
    dropped = 0
    for child in list(auto):
        name = child.attrib.get(name_attr)
        if name and name in keep:
            kept += 1
        else:
            auto.remove(child)
            dropped += 1
    return styles_root, kept, dropped


def _collect_master_pictures(styles_root: ET.Element) -> set[str]:
    """Picture paths referenced by master-page <draw:image xlink:href>."""
    paths: set[str] = set()
    for master in styles_root.findall(".//style:master-page", NS):
        for image in master.iter(q("draw", "image")):
            href = image.attrib.get(q("xlink", "href"))
            if href and not href.startswith("#") and "://" not in href:
                paths.add(href.lstrip("./"))
    return paths


def _readme_for(name: str, inventory: dict[str, object], source: Path) -> str:
    def names(key: str) -> str:
        rows = inventory.get(key, [])
        if not isinstance(rows, list):
            return "—"
        names_list = [str(r.get("name")) for r in rows if isinstance(r, dict) and r.get("name")]
        return ", ".join(names_list) or "—"

    fonts_value = inventory.get("font_face_decls", [])
    fonts: list[str] = [str(f) for f in fonts_value if f] if isinstance(fonts_value, list) else []
    fonts_line = ", ".join(fonts) if fonts else "—"

    return (
        f"# {name}\n\n"
        f"Extracted from `{source.name}`.\n\n"
        f"## What this template offers\n\n"
        f"- **Master pages**: {names('master_pages')}\n"
        f"- **Slide layouts**: {names('presentation_page_layouts')}\n"
        f"- **Paragraph styles**: {names('paragraph_styles')}\n"
        f"- **Graphic styles**: {names('graphic_styles')}\n"
        f"- **Fonts declared**: {fonts_line}\n\n"
        f"## How to apply\n\n"
        f"```bash\n"
        f"python3 skills/odp/scripts/apply_template.py deck.odp \\\n"
        f"    --template skills/odp/templates/{name} -o branded.odp\n"
        f"```\n\n"
        f"See ``PROVENANCE.md`` for source attribution and ``LICENSE.txt``\n"
        f"for redistribution terms.\n"
    )


def _provenance_for(name: str, source: Path, source_url: str | None) -> str:
    when = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    parts = [
        f"# Provenance: {name}",
        "",
        f"- **Extracted from**: `{source.name}`",
        f"- **Extracted at**: {when}",
        "- **Tool**: `skills/odp/scripts/extract_template.py`",
    ]
    if source_url:
        parts.append(f"- **Source URL**: {source_url}")
    return "\n".join(parts) + "\n"


def _license_for(license_id: str | None) -> str:
    if license_id:
        return f"This template is distributed under: {license_id}\n\nSee PROVENANCE.md for source attribution.\n"
    return (
        "# Source unknown — set this before redistribution.\n\n"
        "Run ``extract_template.py --license LICENSE_ID --source URL`` to\n"
        "populate this file automatically.\n"
    )


def extract_to_dir(
    input_path: Path,
    name: str,
    outdir: Path,
    license_id: str | None,
    source_url: str | None,
) -> Path:
    """Extract a template from input_path into outdir/<name>/."""
    # Step 1: PPTX/PPT → ODP via v1.11 bridge if needed.
    if input_path.suffix.lower() in {".pptx", ".ppt"}:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp_path = convert_with_soffice(input_path, "odp", tmp_path)
            return _extract_odp(odp_path, name, outdir, input_path, license_id, source_url)
    elif input_path.suffix.lower() in {".odp", ".otp", ".fodp"}:
        return _extract_odp(input_path, name, outdir, input_path, license_id, source_url)
    else:
        raise SystemExit(f"unsupported input: {input_path.suffix!r}; expected .odp/.otp/.pptx/.ppt")


def _extract_odp(
    odp_path: Path,
    name: str,
    outdir: Path,
    source_for_provenance: Path,
    license_id: str | None,
    source_url: str | None,
) -> Path:
    target = outdir / name
    if target.exists():
        raise SystemExit(f"target already exists: {target} (remove it first)")
    target.mkdir(parents=True)

    # Step 2: parse styles.xml and filter auto-styles.
    styles_root = parse_xml_from_zip(odp_path, "styles.xml")
    styles_root, kept, dropped = filter_auto_styles(styles_root)
    (target / "styles.xml").write_bytes(xml_bytes(styles_root))

    # Step 3: copy master-page-referenced pictures only.
    master_pictures = _collect_master_pictures(styles_root)
    if master_pictures:
        pictures_dir = target / "Pictures"
        pictures_dir.mkdir()
        with zipfile.ZipFile(odp_path) as archive:
            for picture_path in master_pictures:
                # Picture paths in master-pages are like "Pictures/logo.png".
                try:
                    blob = archive.read(picture_path)
                except KeyError:
                    print(
                        f"warning: master references {picture_path!r} but it's not in the package",
                        file=sys.stderr,
                    )
                    continue
                # Strip "Pictures/" prefix when writing under target/Pictures/.
                rel = picture_path
                if rel.startswith("Pictures/"):
                    rel = rel[len("Pictures/") :]
                dest = pictures_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(blob)

    # Step 4: license + provenance + README.
    (target / "LICENSE.txt").write_text(_license_for(license_id), encoding="utf-8")
    (target / "PROVENANCE.md").write_text(_provenance_for(name, source_for_provenance, source_url), encoding="utf-8")
    inventory = inspect_styles_xml(styles_root)
    (target / "README.md").write_text(_readme_for(name, inventory, source_for_provenance), encoding="utf-8")

    print(
        f"extracted to {target}: kept {kept} auto-styles, dropped {dropped}, "
        f"copied {len(master_pictures)} master picture(s)"
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--name", required=True, help="directory name under --outdir")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("skills/odp/templates"),
        help="parent directory for the template (default: %(default)s)",
    )
    parser.add_argument("--license", dest="license_id", help="license identifier (e.g. MIT, CC-BY-4.0)")
    parser.add_argument("--source", dest="source_url", help="source URL of the original template")
    args = parser.parse_args()

    if not args.input_file.exists():
        raise SystemExit(f"input not found: {args.input_file}")

    extract_to_dir(args.input_file, args.name, args.outdir, args.license_id, args.source_url)


if __name__ == "__main__":
    main()
