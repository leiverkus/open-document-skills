#!/usr/bin/env python3
"""Replace text labels in an ODG file."""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

from odg_common import NS, element_text, parse_xml_from_zip, write_odg_with_replacements, xml_bytes


def set_plain_text(paragraph: ET.Element, value: str) -> None:
    attrs = dict(paragraph.attrib)
    paragraph[:] = []
    paragraph.attrib.clear()
    paragraph.attrib.update(attrs)
    paragraph.text = value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odg", type=Path)
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    content = parse_xml_from_zip(args.input_odg, "content.xml")
    count = 0
    for paragraph in content.findall(".//text:p", NS):
        current = element_text(paragraph)
        if args.old in current:
            set_plain_text(paragraph, current.replace(args.old, args.new))
            count += 1
    write_odg_with_replacements(args.input_odg, args.output, {"content.xml": xml_bytes(content)})
    print(f"replacements: {count}")


if __name__ == "__main__":
    main()
