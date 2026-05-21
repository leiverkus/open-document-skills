#!/usr/bin/env python3
"""Validate core ODG package, media, style references, and basic geometry."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from odg_common import NS, iter_pages, iter_shapes, parse_xml_from_zip, q


def numeric_unit(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"^(-?[0-9]+(?:\.[0-9]+)?)", value)
    return float(match.group(1)) if match else None


def validate(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    required = {"mimetype", "content.xml", "styles.xml", "meta.xml", "settings.xml", "META-INF/manifest.xml"}
    for name in sorted(required - set(names)):
        errors.append(f"Missing package file: {name}")
    if names and names[0] != "mimetype":
        errors.append("mimetype is not the first ZIP entry")
    if "content.xml" not in names:
        return {"status": "errors_found", "errors": errors, "warnings": warnings}
    content = parse_xml_from_zip(path, "content.xml")
    manifest = parse_xml_from_zip(path, "META-INF/manifest.xml") if "META-INF/manifest.xml" in names else None
    manifest_paths = set()
    if manifest is not None:
        manifest_paths = {
            e.attrib.get(q("manifest", "full-path")) for e in manifest.findall(".//manifest:file-entry", NS)
        }
    for node in content.iter():
        href = node.attrib.get(q("xlink", "href"))
        if href and not href.startswith("#") and "://" not in href:
            package_path = href.lstrip("./")
            if package_path not in names:
                errors.append(f"Missing package media target: {href}")
            if manifest_paths and package_path not in manifest_paths:
                warnings.append(f"Media target not listed in manifest: {package_path}")
    for page_idx, page in enumerate(iter_pages(content), start=1):
        for shape in iter_shapes(page):
            width = numeric_unit(shape.attrib.get(q("svg", "width")))
            height = numeric_unit(shape.attrib.get(q("svg", "height")))
            if width == 0 or height == 0:
                warnings.append(f"Page {page_idx} has zero-size shape")
            if width is not None and width < 0 or height is not None and height < 0:
                errors.append(f"Page {page_idx} has negative-size shape")
    return {
        "status": "ok" if not errors else "errors_found",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odg", type=Path)
    args = parser.parse_args()
    result = validate(args.odg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
