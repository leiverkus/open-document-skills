#!/usr/bin/env python3
"""Validate core ODS package, media, manifest, formulas, and style references."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from ods_common import (
    NS,
    cell_value,
    expanded_rows,
    find_sheet,
    parse_range,
    parse_xml_from_zip,
    q,
)

ERROR_MARKERS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "Err:")


def _source_header_fields(content: ET.Element, source_addr: str) -> set[str] | None:
    """Return the first-row field names of a pivot source range, or None."""
    try:
        sheet_name, r1, c1, _, c2 = parse_range(source_addr)
        sheet = find_sheet(content, sheet_name)
    except SystemExit:
        return None
    rows = expanded_rows(sheet)
    if r1 - 1 >= len(rows):
        return None
    header_row = rows[r1 - 1]
    fields: set[str] = set()
    for ci in range(c1 - 1, c2):
        if ci < len(header_row):
            fields.add(str(cell_value(header_row[ci])))
    return fields


def validate(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    required = {"mimetype", "content.xml", "styles.xml", "meta.xml", "settings.xml", "META-INF/manifest.xml"}
    for missing in sorted(required - set(names)):
        errors.append(f"Missing package file: {missing}")
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
            # Sub-package object references (e.g. './Object 1' / './Object 1/')
            # resolve via directory contents — validated in the draw:object loop.
            is_object_ref = node.tag == q("draw", "object")
            # ObjectReplacements/* is LibreOffice's optional preview-bitmap cache.
            is_replacement = package_path.startswith("ObjectReplacements/")
            if package_path.endswith("/") or is_object_ref:
                pass
            elif is_replacement:
                if package_path not in names:
                    warnings.append(f"Missing object-replacement preview: {package_path}")
            else:
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

    # Named range and named expression checks
    sheet_names: set[str] = set()
    for sheet in content.findall(".//table:table", NS):
        sn = sheet.attrib.get(q("table", "name"))
        if sn:
            sheet_names.add(sn)
    name_counts: dict[str, int] = {}
    for nr in content.iter(q("table", "named-range")):
        name = nr.attrib.get(q("table", "name"))
        addr = nr.attrib.get(q("table", "cell-range-address"), "")
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1
        # Address shape: '$Sheet.$A1:.$B2' — extract sheet name from leading '$Sheet.'.
        if addr.startswith("$") and "." in addr:
            sheet_part = addr[1:].split(".", 1)[0]
            if sheet_part not in sheet_names:
                errors.append(f"Named range {name!r} references unknown sheet {sheet_part!r}")
    for ne in content.iter(q("table", "named-expression")):
        name = ne.attrib.get(q("table", "name"))
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1
    for name, count in name_counts.items():
        if count > 1:
            errors.append(f"Duplicate named-range/expression {name!r} ({count} occurrences)")

    # Content-validation references
    validation_names: set[str] = set()
    for cv in content.iter(q("table", "content-validation")):
        n = cv.attrib.get(q("table", "name"))
        if n:
            validation_names.add(n)
    for cell in content.iter(q("table", "table-cell")):
        ref = cell.attrib.get(q("table", "content-validation-name"))
        if ref and ref not in validation_names:
            errors.append(f"Dangling content-validation reference: {ref}")

    # Chart object package targets
    for obj in content.iter(q("draw", "object")):
        href = obj.attrib.get(q("xlink", "href"))
        if not href:
            continue
        target = href.lstrip("./").rstrip("/")
        if not any(n.startswith(target + "/") for n in names):
            errors.append(f"Missing draw:object package target: {href}")

    # Conditional-formatting style:map references (content.xml + styles.xml)
    style_roots: list[ET.Element] = [content]
    if "styles.xml" in names:
        style_roots.append(parse_xml_from_zip(path, "styles.xml"))
    style_names: set[str] = set()
    for root in style_roots:
        for el in root.iter():
            sn = el.attrib.get(q("style", "name"))
            if sn:
                style_names.add(sn)
    for root in style_roots:
        for mp in root.iter(q("style", "map")):
            applied = mp.attrib.get(q("style", "apply-style-name"))
            if applied and applied not in style_names:
                errors.append(f"style:map references unknown style: {applied}")

    # Pivot table (table:data-pilot-table) checks
    for pivot in content.iter(q("table", "data-pilot-table")):
        pname = pivot.attrib.get(q("table", "name"), "?")
        target_addr = pivot.attrib.get(q("table", "target-range-address"), "")
        src_el = pivot.find(q("table", "source-cell-range"))
        src_addr = src_el.attrib.get(q("table", "cell-range-address"), "") if src_el is not None else ""
        for label, addr in (("source", src_addr), ("target", target_addr)):
            if not addr:
                continue
            head = addr.split(":", 1)[0].lstrip("$")
            sheet_part = head.split(".", 1)[0].strip("'") if "." in head else ""
            if sheet_part and sheet_part not in sheet_names:
                errors.append(f"Pivot table {pname!r} {label} references unknown sheet {sheet_part!r}")
        header_fields = _source_header_fields(content, src_addr) if src_addr else None
        if header_fields is not None:
            for field in pivot.findall(q("table", "data-pilot-field")):
                fname = field.attrib.get(q("table", "source-field-name"))
                if fname and fname not in header_fields:
                    warnings.append(f"Pivot table {pname!r} field {fname!r} not in source header")

    return {
        "status": "ok" if not errors else "errors_found",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ods", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also validate content.xml and META-INF/manifest.xml against the OASIS ODF 1.3 RelaxNG schemas (requires lxml; install via `pip install open-document-lib[validate]`)",
    )
    args = parser.parse_args()
    result = validate(args.ods)
    if args.strict:
        # ods_common (imported above) has already put odf_lib on sys.path.
        from odf_lib.odf_common import apply_strict_schema_check

        apply_strict_schema_check(args.ods, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
