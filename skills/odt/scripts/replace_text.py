#!/usr/bin/env python3
"""Replace text in ODT XML, optionally scoped to content.xml or styles.xml."""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

from odt_common import clear_children, parse_xml_from_zip, q, write_odt_with_replacements, xml_bytes


def element_text(element: ET.Element) -> str:
    parts: list[str] = []
    for node in element.iter():
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return "".join(parts)


def set_plain_text(element: ET.Element, value: str) -> None:
    attrs = dict(element.attrib)
    clear_children(element)
    element.attrib.clear()
    element.attrib.update(attrs)
    element.text = value


def replace_in_root(root: ET.Element, old: str, new: str) -> int:
    count = 0
    for node in root.iter():
        if node.tag in {q("text", "p"), q("text", "h")}:
            current = element_text(node)
            if old in current:
                set_plain_text(node, current.replace(old, new))
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odt", type=Path)
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--scope", choices=["content", "styles", "both"], default="content")
    args = parser.parse_args()

    replacements: dict[str, bytes] = {}
    total = 0
    if args.scope in {"content", "both"}:
        content = parse_xml_from_zip(args.input_odt, "content.xml")
        total += replace_in_root(content, args.old, args.new)
        replacements["content.xml"] = xml_bytes(content)
    if args.scope in {"styles", "both"}:
        styles = parse_xml_from_zip(args.input_odt, "styles.xml")
        total += replace_in_root(styles, args.old, args.new)
        replacements["styles.xml"] = xml_bytes(styles)

    write_odt_with_replacements(args.input_odt, args.output, replacements)
    print(f"replacements: {total}")


if __name__ == "__main__":
    main()
