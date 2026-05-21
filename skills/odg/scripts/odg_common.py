"""Shared helpers for small ODG scripts.

All format-agnostic functions live in lib.odf_common.
This module adds the ODG namespace, MIMETYPE, and drawing-specific helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

# Add repo root to sys.path so we can import from lib/
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Single consolidated import block from lib.odf_common.
from lib.odf_common import (  # noqa: E402, I001
    copy_into_package as _copy_base,
    ensure_manifest_entry as _ensure_base,
    find_soffice,
    local_name,
    media_type_for,
    pack_dir_as_odf,
    pack_flat_odf,
    parse_xml_from_zip,
    replace_text_in_element,
    sniff_image_mime,
    unique_picture_name,
    unpack_flat_odf,
    update_meta_for_edit as _update_meta_base,
    write_odf_with_replacements as _write_base,
    xml_bytes,
)

# Direct re-exports.
__all__ = [
    "NS",
    "ODG_MIMETYPE",
    "SHAPE_TAGS",
    "q",
    "copy_into_package",
    "element_text",
    "ensure_manifest_entry",
    "find_soffice",
    "iter_pages",
    "iter_shapes",
    "local_name",
    "media_type_for",
    "pack_dir_as_odg",
    "pack_flat_odf",
    "page_name",
    "parse_xml_from_zip",
    "replace_text_in_element",
    "sniff_image_mime",
    "unique_picture_name",
    "unpack_flat_odf",
    "update_meta_for_edit",
    "write_odg_with_replacements",
    "xml_bytes",
]

NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}

ODG_MIMETYPE = "application/vnd.oasis.opendocument.graphics"
SHAPE_TAGS = {
    "frame",
    "rect",
    "ellipse",
    "line",
    "connector",
    "path",
    "custom-shape",
}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def ensure_manifest_entry(
    manifest_root: ET.Element,
    full_path: str,
    media_type: str,
) -> None:
    _ensure_base(manifest_root, full_path, media_type, NS, q)


def copy_into_package(
    input_odg: Path,
    output_odg: Path,
    package_path: str,
    source: Path,
    replacements: dict[str, bytes],
) -> None:
    _copy_base(
        input_odg,
        output_odg,
        package_path,
        source,
        replacements,
        ODG_MIMETYPE,
    )


def pack_dir_as_odg(source_dir: Path, output_odg: Path) -> None:
    pack_dir_as_odf(source_dir, output_odg, ODG_MIMETYPE)


def write_odg_with_replacements(
    input_odg: Path,
    output_odg: Path,
    replacements: dict[str, bytes],
) -> None:
    _write_base(input_odg, output_odg, replacements, ODG_MIMETYPE)


def update_meta_for_edit(meta_root: ET.Element) -> None:
    _update_meta_base(meta_root, NS, q)


def element_text(element: ET.Element) -> str:
    """Extract all visible text from an ODG element and its descendants."""
    parts = []
    for node in element.iter():
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return " ".join("".join(parts).split())


def iter_pages(root: ET.Element):
    """Yield all draw:page elements from ODG content."""
    yield from root.findall(".//draw:page", NS)


def page_name(page: ET.Element) -> str:
    """Return the draw:name attribute of a page."""
    return page.attrib.get(q("draw", "name"), "")


def iter_shapes(page: ET.Element):
    """Yield all shape elements from a draw:page."""
    for node in page.iter():
        if local_name(node.tag) in SHAPE_TAGS:
            yield node
