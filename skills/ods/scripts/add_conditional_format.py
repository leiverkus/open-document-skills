#!/usr/bin/env python3
"""Add conditional highlighting to an ODS cell range.

Each rule is written in two forms that share one apply style:

* ``calcext:conditional-formats`` in content.xml — the form LibreOffice Calc
  renders. (LibreOffice extension, outside the OASIS core schema; treated as a
  known extension by ``validate_refs --strict``.)
* ``style:map`` on a per-range cell style in styles.xml — the ODF-core form,
  for other ODF consumers.

Conditions (--condition):
    value > N          value < N          value >= N        value <= N
    value = N          value != N
    value between A B  value not-between A B
    formula:EXPR       (arbitrary ODF formula, true → apply)

Repeating the command on the same --range appends another rule (first match
wins, in document order).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from ods_common import (
    ensure_cell,
    find_sheet,
    index_to_col,
    parse_range,
    parse_xml_from_zip,
    q,
    update_meta_for_edit,
    write_ods_with_replacements,
    xml_bytes,
)

# Each operator maps to (ODF style:condition operator, calcext:value operator).
_OPERATORS = {
    ">": (">", ">"),
    "<": ("<", "<"),
    ">=": (">=", ">="),
    "<=": ("<=", "<="),
    "=": ("=", "="),
    "==": ("=", "="),
    "!=": ("!=", "!="),
}


def _operand(token: str) -> str:
    """Pass numbers through; quote anything else as an ODF string literal."""
    token = token.strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return token
    try:
        float(token)
    except ValueError:
        return '"' + token.replace('"', '\\"') + '"'
    return token


def parse_condition(expr: str) -> tuple[str, str]:
    """Map a user condition to (ODF style:condition, calcext:value) strings."""
    expr = expr.strip()
    if expr.startswith("formula:"):
        formula = expr[len("formula:") :].strip()
        if not formula:
            raise SystemExit("formula: condition is empty")
        return f"is-true-formula({formula})", f"formula-is({formula})"
    parts = expr.split()
    if len(parts) == 4 and parts[0] == "value" and parts[1] in ("between", "not-between"):
        lo, hi = _operand(parts[2]), _operand(parts[3])
        if parts[1] == "between":
            return f"cell-content-is-between({lo},{hi})", f"between({lo},{hi})"
        return f"cell-content-is-not-between({lo},{hi})", f"not-between({lo},{hi})"
    if len(parts) == 3 and parts[0] == "value":
        ops = _OPERATORS.get(parts[1])
        if ops is None:
            raise SystemExit(f"unknown operator {parts[1]!r}; use one of {sorted(_OPERATORS)}")
        odf_op, calc_op = ops
        operand = _operand(parts[2])
        return f"cell-content(){odf_op}{operand}", f"{calc_op}{operand}"
    raise SystemExit(
        f"invalid --condition {expr!r}; expected 'value OP N', "
        "'value between A B', 'value not-between A B', or 'formula:EXPR'"
    )


def _sheet_ref(sheet: str) -> str:
    """Quote a sheet name for an ODF cell address when it is not a plain name."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", sheet):
        return sheet
    return "'" + sheet.replace("'", "''") + "'"


def odf_base_address(sheet: str, row: int, col: int) -> str:
    """Absolute ODF cell address ($Sheet.$B$2) for style:base-cell-address."""
    return f"${_sheet_ref(sheet)}.${index_to_col(col)}${row}"


def calcext_address(sheet: str, row: int, col: int) -> str:
    """Plain ODF cell address (Sheet.B2) for calcext attributes."""
    return f"{_sheet_ref(sheet)}.{index_to_col(col)}{row}"


def ensure_office_styles(styles_root: ET.Element) -> ET.Element:
    """Locate or create office:styles inside a styles.xml document root."""
    office_styles = styles_root.find(q("office", "styles"))
    if office_styles is not None:
        return office_styles
    office_styles = ET.Element(q("office", "styles"))
    insert_at = len(styles_root)
    for i, child in enumerate(list(styles_root)):
        if child.tag in (q("office", "automatic-styles"), q("office", "master-styles")):
            insert_at = i
            break
    styles_root.insert(insert_at, office_styles)
    return office_styles


def build_apply_style(
    name: str,
    background: str | None,
    text_color: str | None,
    bold: bool,
    italic: bool,
) -> ET.Element:
    """Build a named table-cell style holding the highlight formatting."""
    style = ET.Element(
        q("style", "style"),
        {q("style", "name"): name, q("style", "family"): "table-cell"},
    )
    if background:
        ET.SubElement(
            style,
            q("style", "table-cell-properties"),
            {q("fo", "background-color"): background},
        )
    text_attrs: dict[str, str] = {}
    if text_color:
        text_attrs[q("fo", "color")] = text_color
    if bold:
        text_attrs[q("fo", "font-weight")] = "bold"
    if italic:
        text_attrs[q("fo", "font-style")] = "italic"
    if text_attrs:
        ET.SubElement(style, q("style", "text-properties"), text_attrs)
    return style


def find_or_create_condition_style(container: ET.Element, name: str) -> ET.Element:
    """Locate the per-range condition style (carries style:map) or create one."""
    for style in container.findall(q("style", "style")):
        if style.attrib.get(q("style", "name")) == name and style.attrib.get(q("style", "family")) == "table-cell":
            return style
    style = ET.Element(
        q("style", "style"),
        {q("style", "name"): name, q("style", "family"): "table-cell"},
    )
    container.append(style)
    return style


def find_or_create_calcext_format(sheet: ET.Element, range_address: str) -> ET.Element:
    """Locate the calcext:conditional-format for this range or create one.

    The calcext:conditional-formats container must be the last child of the
    sheet's table:table element — LibreOffice silently drops it otherwise — so
    it is (re)moved to the end here. Call this only after all rows exist.
    """
    container = sheet.find(q("calcext", "conditional-formats"))
    if container is None:
        container = ET.Element(q("calcext", "conditional-formats"))
    else:
        sheet.remove(container)
    sheet.append(container)
    for fmt in container.findall(q("calcext", "conditional-format")):
        if fmt.attrib.get(q("calcext", "target-range-address")) == range_address:
            return fmt
    return ET.SubElement(
        container,
        q("calcext", "conditional-format"),
        {q("calcext", "target-range-address"): range_address},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_ods", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--range", required=True, help="target cell range like 'Sheet1.B2:B100'")
    parser.add_argument("--condition", required=True, help="condition expression (see --help)")
    parser.add_argument("--background", help="cell background colour, hex like '#FFCDD2'")
    parser.add_argument("--text-color", help="text colour, hex like '#B71C1C'")
    parser.add_argument("--bold", action="store_true", help="render matching cells bold")
    parser.add_argument("--italic", action="store_true", help="render matching cells italic")
    args = parser.parse_args()

    if not (args.background or args.text_color or args.bold or args.italic):
        raise SystemExit("specify at least one of --background, --text-color, --bold, --italic")

    sheet_name, row1, col1, row2, col2 = parse_range(args.range)
    odf_condition, calcext_value = parse_condition(args.condition)

    content = parse_xml_from_zip(args.input_ods, "content.xml")
    styles = parse_xml_from_zip(args.input_ods, "styles.xml")
    office_styles = ensure_office_styles(styles)

    # The condition style is keyed per range so repeat calls stack their rules.
    safe = re.sub(r"[^A-Za-z0-9]", "_", args.range)
    cond_name = f"cf_{safe}"
    cond_style = find_or_create_condition_style(office_styles, cond_name)

    rule_index = len(cond_style.findall(q("style", "map"))) + 1
    apply_name = f"{cond_name}_a{rule_index}"
    office_styles.append(build_apply_style(apply_name, args.background, args.text_color, args.bold, args.italic))

    odf_base = odf_base_address(sheet_name, row1, col1)
    calc_base = calcext_address(sheet_name, row1, col1)

    # ODF-core form: a style:map on the per-range condition style.
    ET.SubElement(
        cond_style,
        q("style", "map"),
        {
            q("style", "condition"): odf_condition,
            q("style", "apply-style-name"): apply_name,
            q("style", "base-cell-address"): odf_base,
        },
    )

    sheet = find_sheet(content, sheet_name)

    # Wire the ODF-core style:map to the cells via table:style-name. This may
    # append new rows, so it must run before the calcext container is placed.
    count = 0
    for row in range(row1, row2 + 1):
        for col in range(col1, col2 + 1):
            cell = ensure_cell(sheet, row, col)
            cell.set(q("table", "style-name"), cond_name)
            count += 1

    # LibreOffice-rendered form: a calcext:condition on the range's format.
    # find_or_create_calcext_format keeps the container as the last child.
    range_address = f"{calcext_address(sheet_name, row1, col1)}:{calcext_address(sheet_name, row2, col2)}"
    calcext_format = find_or_create_calcext_format(sheet, range_address)
    ET.SubElement(
        calcext_format,
        q("calcext", "condition"),
        {
            q("calcext", "apply-style-name"): apply_name,
            q("calcext", "value"): calcext_value,
            q("calcext", "base-cell-address"): calc_base,
        },
    )

    meta = parse_xml_from_zip(args.input_ods, "meta.xml")
    update_meta_for_edit(meta)
    write_ods_with_replacements(
        args.input_ods,
        args.output,
        {
            "content.xml": xml_bytes(content),
            "styles.xml": xml_bytes(styles),
            "meta.xml": xml_bytes(meta),
        },
    )
    print(f"conditional format (rule {rule_index}) applied to {count} cells in {args.range}")


if __name__ == "__main__":
    main()
