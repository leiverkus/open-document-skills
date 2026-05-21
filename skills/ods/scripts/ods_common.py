"""Shared helpers for small ODS scripts."""

from __future__ import annotations

import csv
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}

ODS_MIMETYPE = "application/vnd.oasis.opendocument.spreadsheet"

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def col_to_index(col: str) -> int:
    value = 0
    for char in col.upper():
        if not ("A" <= char <= "Z"):
            raise ValueError(f"Invalid column: {col}")
        value = value * 26 + ord(char) - ord("A") + 1
    return value


def index_to_col(index: int) -> str:
    chars = []
    while index:
        index, rem = divmod(index - 1, 26)
        chars.append(chr(ord("A") + rem))
    return "".join(reversed(chars))


def parse_a1(address: str) -> tuple[str, int, int]:
    if "!" in address:
        sheet, cell = address.split("!", 1)
    else:
        sheet, cell = "", address
    match = re.fullmatch(r"\$?([A-Za-z]+)\$?([0-9]+)", cell)
    if not match:
        raise SystemExit(f"Invalid A1 address: {address}")
    return sheet, int(match.group(2)), col_to_index(match.group(1))


def a1(row: int, col: int) -> str:
    return f"{index_to_col(col)}{row}"


def parse_xml_from_zip(path: Path, member: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as handle:
            return ET.parse(handle).getroot()


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_ods_with_replacements(input_ods: Path, output_ods: Path, replacements: dict[str, bytes]) -> None:
    with zipfile.ZipFile(input_ods) as src:
        names = src.namelist()
        with zipfile.ZipFile(output_ods, "w") as dst:
            if "mimetype" in names:
                dst.writestr("mimetype", replacements.get("mimetype", src.read("mimetype")), compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype":
                    continue
                dst.writestr(name, replacements.get(name, src.read(name)), compress_type=zipfile.ZIP_DEFLATED)


def pack_dir_as_ods(source_dir: Path, output_ods: Path) -> None:
    mimetype = source_dir / "mimetype"
    if not mimetype.exists():
        raise SystemExit(f"Missing mimetype file in {source_dir}")
    with zipfile.ZipFile(output_ods, "w") as archive:
        archive.write(mimetype, "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir() or path == mimetype:
                continue
            archive.write(path, path.relative_to(source_dir).as_posix(), compress_type=zipfile.ZIP_DEFLATED)


def cell_text(cell: ET.Element) -> str:
    return " ".join("".join(node.text or "" for node in cell.findall(".//text:p", NS)).split())


def cell_value(cell: ET.Element) -> object:
    value_type = cell.attrib.get(q("office", "value-type"))
    if value_type in {"float", "percentage", "currency"}:
        raw = cell.attrib.get(q("office", "value"))
        try:
            return float(raw) if raw is not None else None
        except ValueError:
            return raw
    if value_type == "boolean":
        return cell.attrib.get(q("office", "boolean-value")) == "true"
    if value_type == "date":
        return cell.attrib.get(q("office", "date-value"))
    if value_type == "time":
        return cell.attrib.get(q("office", "time-value"))
    return cell_text(cell)


def repeated(node: ET.Element, attr: str) -> int:
    raw = node.attrib.get(q("table", attr))
    if raw is None:
        return 1
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def iter_sheets(root: ET.Element):
    yield from root.findall(".//table:table", NS)


def sheet_name(sheet: ET.Element) -> str:
    return sheet.attrib.get(q("table", "name"), "")


def expanded_rows(sheet: ET.Element, max_repeat: int = 1000) -> list[list[ET.Element]]:
    rows: list[list[ET.Element]] = []
    for row in sheet.findall("table:table-row", NS):
        row_cells: list[ET.Element] = []
        for cell in list(row):
            if cell.tag not in {q("table", "table-cell"), q("table", "covered-table-cell")}:
                continue
            count = min(repeated(cell, "number-columns-repeated"), max_repeat)
            row_cells.extend([cell] * count)
        for _ in range(min(repeated(row, "number-rows-repeated"), max_repeat)):
            rows.append(row_cells)
    return rows


def set_cell_value(cell: ET.Element, value: str, formula: bool = False) -> None:
    cell.attrib.pop(q("table", "number-columns-repeated"), None)
    for child in list(cell):
        cell.remove(child)
    if formula:
        cell.set(q("table", "formula"), value)
        cell.set(q("office", "value-type"), "float")
    else:
        try:
            number = float(value)
        except ValueError:
            cell.set(q("office", "value-type"), "string")
        else:
            cell.set(q("office", "value-type"), "float")
            cell.set(q("office", "value"), str(number))
    p = ET.SubElement(cell, q("text", "p"))
    p.text = "" if formula else value


def ensure_cell(sheet: ET.Element, row_index: int, col_index: int) -> ET.Element:
    rows = sheet.findall("table:table-row", NS)
    while len(rows) < row_index:
        ET.SubElement(sheet, q("table", "table-row"))
        rows = sheet.findall("table:table-row", NS)
    row = rows[row_index - 1]
    cells = [c for c in list(row) if c.tag == q("table", "table-cell")]
    while len(cells) < col_index:
        ET.SubElement(row, q("table", "table-cell"))
        cells = [c for c in list(row) if c.tag == q("table", "table-cell")]
    return cells[col_index - 1]


def find_sheet(root: ET.Element, name: str) -> ET.Element:
    sheets = list(iter_sheets(root))
    if not name and sheets:
        return sheets[0]
    for sheet in sheets:
        if sheet_name(sheet) == name:
            return sheet
    raise SystemExit(f"Sheet not found: {name}")


def write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def find_soffice() -> str:
    candidates = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "/usr/local/bin/libreoffice",
        "/snap/bin/libreoffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        "/c/Program Files/LibreOffice/program/soffice.exe",
        "/mnt/c/Program Files/LibreOffice/program/soffice.exe",
    ]
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise SystemExit("LibreOffice/soffice not found")
