#!/usr/bin/env python3
"""Edit a table inside an ODT — add/delete rows and columns, set cells.

One operation per call (by --table name):
- --add-row [VALUE ...]      append a row
- --add-column [HEADER]      append a column to every row
- --delete-row N             delete the Nth row (1-based)
- --delete-column N          delete the Nth column (1-based)
- --set-cell ROW COL VALUE   set one cell (1-based)
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from xml.etree import ElementTree as ET

from odt_common import (
    parse_xml_from_zip,
    q,
    update_meta_for_edit,
    write_odt_with_replacements,
    xml_bytes,
)

CELL_TAGS = {q("table", "table-cell"), q("table", "covered-table-cell")}


def find_table(content: ET.Element, name: str) -> ET.Element:
    for table in content.iter(q("table", "table")):
        if table.attrib.get(q("table", "name")) == name:
            return table
    raise SystemExit(f"table not found: {name!r}")


def expand_repeats(table: ET.Element) -> None:
    """Expand number-rows-repeated / number-columns-repeated into explicit elements."""
    for parent, tag, attr in (
        (table, q("table", "table-column"), q("table", "number-columns-repeated")),
        (table, q("table", "table-row"), q("table", "number-rows-repeated")),
    ):
        for child in list(parent):
            if child.tag != tag:
                continue
            count = int(child.attrib.get(attr, "1") or "1")
            if count > 1:
                del child.attrib[attr]
                index = list(parent).index(child)
                for offset in range(1, count):
                    parent.insert(index + offset, copy.deepcopy(child))
    for row in table.findall(q("table", "table-row")):
        for cell in list(row):
            if cell.tag not in CELL_TAGS:
                continue
            count = int(cell.attrib.get(q("table", "number-columns-repeated"), "1") or "1")
            if count > 1:
                del cell.attrib[q("table", "number-columns-repeated")]
                index = list(row).index(cell)
                for offset in range(1, count):
                    row.insert(index + offset, copy.deepcopy(cell))


def new_cell(value: str = "") -> ET.Element:
    cell = ET.Element(q("table", "table-cell"), {q("office", "value-type"): "string"})
    paragraph = ET.SubElement(cell, q("text", "p"))
    paragraph.text = value
    return cell


def set_cell_text(cell: ET.Element, value: str) -> None:
    for child in list(cell):
        cell.remove(child)
    cell.set(q("office", "value-type"), "string")
    paragraph = ET.SubElement(cell, q("text", "p"))
    paragraph.text = value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--table", required=True, help="table:name of the table to edit")
    op = parser.add_mutually_exclusive_group(required=True)
    op.add_argument("--add-row", nargs="*", metavar="VALUE", help="append a row")
    op.add_argument("--add-column", nargs="?", const="", metavar="HEADER", help="append a column")
    op.add_argument("--delete-row", type=int, metavar="N", help="delete the Nth row")
    op.add_argument("--delete-column", type=int, metavar="N", help="delete the Nth column")
    op.add_argument("--set-cell", nargs=3, metavar=("ROW", "COL", "VALUE"), help="set one cell")
    args = parser.parse_args()

    content = parse_xml_from_zip(args.input_odt, "content.xml")
    table = find_table(content, args.table)
    expand_repeats(table)
    rows = table.findall(q("table", "table-row"))
    columns = table.findall(q("table", "table-column"))
    ncols = len(columns) or (max((len(r.findall(q("table", "table-cell"))) for r in rows), default=0))

    if args.add_row is not None:
        values = args.add_row
        row = ET.SubElement(table, q("table", "table-row"))
        for col in range(ncols):
            row.append(new_cell(values[col] if col < len(values) else ""))
        summary = "added 1 row"
    elif args.add_column is not None:
        if columns:
            table.insert(list(table).index(columns[-1]) + 1, ET.Element(q("table", "table-column")))
        else:
            table.insert(0, ET.Element(q("table", "table-column")))
        for index, row in enumerate(rows):
            row.append(new_cell(args.add_column if index == 0 else ""))
        summary = "added 1 column"
    elif args.delete_row is not None:
        if args.delete_row < 1 or args.delete_row > len(rows):
            raise SystemExit(f"--delete-row out of range: {args.delete_row} (have {len(rows)})")
        table.remove(rows[args.delete_row - 1])
        summary = f"deleted row {args.delete_row}"
    elif args.delete_column is not None:
        if args.delete_column < 1 or args.delete_column > ncols:
            raise SystemExit(f"--delete-column out of range: {args.delete_column} (have {ncols})")
        if args.delete_column <= len(columns):
            table.remove(columns[args.delete_column - 1])
        for row in rows:
            cells = [c for c in row if c.tag in CELL_TAGS]
            if args.delete_column <= len(cells):
                row.remove(cells[args.delete_column - 1])
        summary = f"deleted column {args.delete_column}"
    else:  # --set-cell
        try:
            r, c = int(args.set_cell[0]), int(args.set_cell[1])
        except ValueError:
            raise SystemExit("--set-cell ROW and COL must be integers")
        if r < 1 or r > len(rows):
            raise SystemExit(f"--set-cell row out of range: {r} (have {len(rows)})")
        cells = [cell for cell in rows[r - 1] if cell.tag in CELL_TAGS]
        if c < 1 or c > len(cells):
            raise SystemExit(f"--set-cell column out of range: {c} (have {len(cells)})")
        set_cell_text(cells[c - 1], args.set_cell[2])
        summary = f"set cell ({r},{c})"

    meta = parse_xml_from_zip(args.input_odt, "meta.xml")
    update_meta_for_edit(meta)
    write_odt_with_replacements(
        args.input_odt,
        args.output,
        {"content.xml": xml_bytes(content), "meta.xml": xml_bytes(meta)},
    )
    print(f"{args.table}: {summary}")


if __name__ == "__main__":
    main()
