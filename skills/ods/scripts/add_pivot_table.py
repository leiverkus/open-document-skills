#!/usr/bin/env python3
"""Compute a pivot table from an ODS range and write it into the workbook.

The pivot is computed in Python (group-by + aggregation) and the result grid
is written into the target range, so LibreOffice shows it immediately. A
matching ODF-core ``table:data-pilot-table`` definition is written too, so
LibreOffice treats it as a real, refreshable pivot.

Example:
    add_pivot_table.py book.ods --source Data.A1:D100 \\
        --rows Region,Product --columns Quarter --data Revenue \\
        --function sum --target Pivot.A1 -o out.ods
"""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

from ods_common import (
    NS,
    a1,
    cell_value,
    ensure_cell,
    expanded_rows,
    find_sheet,
    parse_range,
    parse_xml_from_zip,
    q,
    set_cell_value,
    update_meta_for_edit,
    write_ods_with_replacements,
    xml_bytes,
)

FUNCTIONS = ("sum", "count", "average", "min", "max")


def _to_number(value: object) -> float | None:
    """Coerce a cell value to a float, or None when it is not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (ValueError, AttributeError):
        return None


def aggregate(values: list[object], function: str) -> float:
    """Apply an aggregation function to a list of raw cell values."""
    if function == "count":
        return float(len(values))
    numbers = [n for n in (_to_number(v) for v in values) if n is not None]
    if not numbers:
        return 0.0
    if function == "sum":
        return sum(numbers)
    if function == "average":
        return sum(numbers) / len(numbers)
    if function == "min":
        return min(numbers)
    if function == "max":
        return max(numbers)
    raise SystemExit(f"unknown --function {function!r}; choose from {FUNCTIONS}")


def read_source(content: ET.Element, source: str) -> tuple[str, list[str], list[list[object]]]:
    """Read the source range; return (sheet_name, header, data_rows)."""
    sheet_name, r1, c1, r2, c2 = parse_range(source)
    sheet = find_sheet(content, sheet_name)
    rows = expanded_rows(sheet)
    table: list[list[object]] = []
    for ri in range(r1 - 1, r2):
        if ri >= len(rows):
            break
        cells = rows[ri]
        record: list[object] = []
        for ci in range(c1 - 1, c2):
            record.append(cell_value(cells[ci]) if ci < len(cells) else "")
        table.append(record)
    if not table:
        raise SystemExit(f"source range {source!r} is empty")
    header = [str(v) for v in table[0]]
    return sheet_name, header, table[1:]


def compute_grid(
    header: list[str],
    body: list[list[object]],
    row_fields: list[str],
    column_field: str | None,
    data_field: str,
    function: str,
) -> tuple[list[list[object]], list[tuple[str, ...]], list[str]]:
    """Group the records and build the result grid.

    Returns (grid, row_keys, column_keys) where grid is a list of cell rows.
    """
    index = {name: i for i, name in enumerate(header)}
    for field in [*row_fields, data_field] + ([column_field] if column_field else []):
        if field not in index:
            raise SystemExit(f"field {field!r} not in source header {header}")
    row_idx = [index[f] for f in row_fields]
    col_idx = index[column_field] if column_field else None
    data_idx = index[data_field]

    groups: dict[tuple[tuple[str, ...], str | None], list[object]] = {}
    row_keys: list[tuple[str, ...]] = []
    column_keys: list[str] = []
    for record in body:
        row_key = tuple(str(record[i]) for i in row_idx)
        col_key = str(record[col_idx]) if col_idx is not None else None
        groups.setdefault((row_key, col_key), []).append(record[data_idx])
        if row_key not in row_keys:
            row_keys.append(row_key)
        if col_key is not None and col_key not in column_keys:
            column_keys.append(col_key)
    row_keys.sort()
    column_keys.sort()

    grid: list[list[object]] = []
    if column_field:
        grid.append([*row_fields, *column_keys, "Total"])
    else:
        grid.append([*row_fields, f"{function} of {data_field}"])

    for row_key in row_keys:
        line: list[object] = list(row_key)
        if column_field:
            row_total: list[object] = []
            for col_key in column_keys:
                values = groups.get((row_key, col_key), [])
                line.append(aggregate(values, function) if values else "")
                row_total.extend(values)
            line.append(aggregate(row_total, function))
        else:
            line.append(aggregate(groups.get((row_key, None), []), function))
        grid.append(line)

    total: list[object] = ["Total", *[""] * (len(row_fields) - 1)]
    if column_field:
        for col_key in column_keys:
            values = [v for rk in row_keys for v in groups.get((rk, col_key), [])]
            total.append(aggregate(values, function))
    everything = [v for bucket in groups.values() for v in bucket]
    total.append(aggregate(everything, function))
    grid.append(total)
    return grid, row_keys, column_keys


def ensure_sheet(content: ET.Element, name: str, min_columns: int) -> ET.Element:
    """Locate a sheet by name, or create it after the last existing sheet."""
    spreadsheet = content.find(".//office:spreadsheet", NS)
    if spreadsheet is None:
        raise SystemExit("office:spreadsheet not found")
    tables = spreadsheet.findall(q("table", "table"))
    for table in tables:
        if table.attrib.get(q("table", "name")) == name:
            return table
    sheet = ET.Element(q("table", "table"), {q("table", "name"): name})
    ET.SubElement(
        sheet,
        q("table", "table-column"),
        {q("table", "number-columns-repeated"): str(max(1, min_columns))},
    )
    index = list(spreadsheet).index(tables[-1]) + 1 if tables else len(spreadsheet)
    spreadsheet.insert(index, sheet)
    return sheet


def write_grid(sheet: ET.Element, anchor_row: int, anchor_col: int, grid: list[list[object]]) -> None:
    """Write the result grid into the sheet starting at the anchor cell."""
    for r, line in enumerate(grid):
        for c, value in enumerate(line):
            cell = ensure_cell(sheet, anchor_row + r, anchor_col + c)
            set_cell_value(cell, "" if value == "" else _format_value(value))


def _format_value(value: object) -> str:
    """Render a grid value as the string set_cell_value expects."""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    return str(value)


def _range_address(sheet: str, r1: int, c1: int, r2: int, c2: int) -> str:
    """Build a fully-qualified ODF range address (sheet on both ends)."""
    return f"{sheet}.{a1(r1, c1)}:{sheet}.{a1(r2, c2)}"


def build_data_pilot_field(
    source_field: str,
    orientation: str,
    members: list[str],
    function: str | None,
) -> ET.Element:
    """Build one table:data-pilot-field element (row/column/data)."""
    attribs = {
        q("table", "source-field-name"): source_field,
        q("table", "orientation"): orientation,
        q("table", "used-hierarchy"): "0",
    }
    if function is not None:
        attribs[q("table", "function")] = function
    field = ET.Element(q("table", "data-pilot-field"), attribs)
    if orientation == "data":
        return field
    level = ET.SubElement(field, q("table", "data-pilot-level"), {q("table", "show-empty"): "false"})
    member_box = ET.SubElement(level, q("table", "data-pilot-members"))
    for name in members:
        ET.SubElement(
            member_box,
            q("table", "data-pilot-member"),
            {
                q("table", "name"): name,
                q("table", "display"): "true",
                q("table", "show-details"): "true",
            },
        )
    ET.SubElement(
        level,
        q("table", "data-pilot-display-info"),
        {
            q("table", "enabled"): "false",
            q("table", "display-member-mode"): "from-top",
            q("table", "member-count"): "0",
            q("table", "data-field"): "",
        },
    )
    ET.SubElement(
        level,
        q("table", "data-pilot-sort-info"),
        {q("table", "order"): "ascending", q("table", "sort-mode"): "name"},
    )
    ET.SubElement(
        level,
        q("table", "data-pilot-layout-info"),
        {q("table", "add-empty-lines"): "false", q("table", "layout-mode"): "tabular-layout"},
    )
    return field


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_ods", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--source", required=True, help="source range like 'Data.A1:D100' (first row = header)")
    parser.add_argument("--rows", required=True, help="row field(s), comma-separated for nested grouping")
    parser.add_argument("--columns", help="optional single column field")
    parser.add_argument("--data", required=True, help="the data field to aggregate")
    parser.add_argument("--function", default="sum", choices=FUNCTIONS, help="aggregation function (default: sum)")
    parser.add_argument("--target", required=True, help="top-left anchor cell of the output, like 'Pivot.A1'")
    args = parser.parse_args()

    row_fields = [f.strip() for f in args.rows.split(",") if f.strip()]
    if not row_fields:
        raise SystemExit("--rows must name at least one field")

    content = parse_xml_from_zip(args.input_ods, "content.xml")
    source_sheet, header, body = read_source(content, args.source)
    grid, row_keys, column_keys = compute_grid(header, body, row_fields, args.columns, args.data, args.function)

    target_sheet_name, anchor_row, anchor_col, _, _ = parse_range(args.target)
    width = max(len(line) for line in grid)
    target_sheet = ensure_sheet(content, target_sheet_name, anchor_col - 1 + width)
    write_grid(target_sheet, anchor_row, anchor_col, grid)

    # ODF-core table:data-pilot-table — lets LibreOffice refresh the pivot.
    spreadsheet = content.find(".//office:spreadsheet", NS)
    assert spreadsheet is not None
    container = spreadsheet.find(q("table", "data-pilot-tables"))
    if container is None:
        container = ET.SubElement(spreadsheet, q("table", "data-pilot-tables"))
    pivot_index = len(container.findall(q("table", "data-pilot-table"))) + 1
    pivot_name = f"DataPilot{pivot_index}"

    s_sheet, sr1, sc1, sr2, sc2 = parse_range(args.source)
    target_range = _range_address(
        target_sheet_name, anchor_row, anchor_col, anchor_row + len(grid) - 1, anchor_col + width - 1
    )
    pivot = ET.SubElement(
        container,
        q("table", "data-pilot-table"),
        {
            q("table", "name"): pivot_name,
            q("table", "application-data"): "",
            q("table", "target-range-address"): target_range,
            q("table", "show-filter-button"): "false",
            q("table", "drill-down-on-double-click"): "false",
        },
    )
    ET.SubElement(
        pivot,
        q("table", "source-cell-range"),
        {q("table", "cell-range-address"): _range_address(s_sheet, sr1, sc1, sr2, sc2)},
    )
    for i, field in enumerate(row_fields):
        members = sorted({rk[i] for rk in row_keys})
        pivot.append(build_data_pilot_field(field, "row", members, None))
    if args.columns:
        pivot.append(build_data_pilot_field(args.columns, "column", sorted(column_keys), None))
    pivot.append(build_data_pilot_field(args.data, "data", [], args.function))

    meta = parse_xml_from_zip(args.input_ods, "meta.xml")
    update_meta_for_edit(meta)
    write_ods_with_replacements(
        args.input_ods,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    rows_written = len(grid)
    print(
        f"pivot {pivot_name!r}: {rows_written} rows × {width} cols written to "
        f"{target_sheet_name}.{a1(anchor_row, anchor_col)}; source {args.source}"
    )


if __name__ == "__main__":
    main()
