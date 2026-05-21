#!/usr/bin/env python3
"""Validate core ODS package, media, manifest, formulas, and style references."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from ods_common import NS, parse_xml_from_zip, q


ERROR_MARKERS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "Err:")


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
        manifest_paths = {e.attrib.get(q("manifest", "full-path")) for e in manifest.findall(".//manifest:file-entry", NS)}
    for node in content.iter():
        href = node.attrib.get(q("xlink", "href"))
        if href and not href.startswith("#") and "://" not in href:
            package_path = href.lstrip("./")
            if package_path not in names:
                errors.append(f"Missing package media target: {href}")
            if manifest_paths and package_path not in manifest_paths:
                warnings.append(f"Media target not listed in manifest: {package_path}")
        formula = node.attrib.get(q("table", "formula"))
        if formula and "#REF!" in formula:
            errors.append(f"Formula contains #REF!: {formula}")
        text = "".join(p.text or "" for p in node.findall(".//text:p", NS))
        if any(marker in text for marker in ERROR_MARKERS):
            errors.append(f"Cell displays formula error: {text}")
    return {"status": "ok" if not errors else "errors_found", "errors": sorted(set(errors)), "warnings": sorted(set(warnings))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ods", type=Path)
    args = parser.parse_args()
    result = validate(args.ods)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
