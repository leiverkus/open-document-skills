#!/usr/bin/env python3
"""List all table:data-pilot-table definitions in an ODS workbook as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ods_common import parse_xml_from_zip, q


def collect(ods_path: Path) -> list[dict[str, object]]:
    content = parse_xml_from_zip(ods_path, "content.xml")
    results: list[dict[str, object]] = []
    for pivot in content.iter(q("table", "data-pilot-table")):
        source_el = pivot.find(q("table", "source-cell-range"))
        fields: list[dict[str, str | None]] = []
        for field in pivot.findall(q("table", "data-pilot-field")):
            fields.append(
                {
                    "name": field.attrib.get(q("table", "source-field-name")),
                    "orientation": field.attrib.get(q("table", "orientation")),
                    "function": field.attrib.get(q("table", "function")),
                }
            )
        results.append(
            {
                "name": pivot.attrib.get(q("table", "name")),
                "source_range": (
                    source_el.attrib.get(q("table", "cell-range-address")) if source_el is not None else None
                ),
                "target_range": pivot.attrib.get(q("table", "target-range-address")),
                "fields": fields,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_ods", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = collect(args.input_ods)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if not data:
        print("(no pivot tables)")
        return
    for pivot in data:
        print(f"{pivot['name']}: {pivot['source_range']} -> {pivot['target_range']}")
        fields = pivot["fields"]
        if isinstance(fields, list):
            for field in fields:
                func = f" function={field['function']}" if field.get("function") else ""
                print(f"  [{field['orientation']}] {field['name']}{func}")


if __name__ == "__main__":
    main()
