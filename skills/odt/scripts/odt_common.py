"""Shared helpers for small ODT scripts.

All format-agnostic functions live in lib.odf_common.
This module adds the ODT namespace, MIMETYPE, and thin wrappers
so that existing script imports (``from odt_common import …``)
continue to work unchanged.
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
    clear_children,
    copy_into_package as _copy_base,
    ensure_manifest_entry as _ensure_base,
    find_text_position_in_element,
    insert_after_text_in_element,
    insert_in_paragraph,
    media_type_for,
    pack_dir_as_odf,
    pack_flat_odf,
    parse_xml_from_zip,
    replace_pattern_with_element_in_element,
    replace_text_in_element,
    unique_picture_name,
    unpack_flat_odf,
    update_meta_for_edit as _update_meta_base,
    write_odf_with_replacements as _write_base,
    xml_bytes,
)

# Direct re-exports.
__all__ = [
    "NS",
    "ODT_MIMETYPE",
    "q",
    "clear_children",
    "copy_into_package",
    "ensure_manifest_entry",
    "find_text_position_in_element",
    "insert_after_text_in_element",
    "insert_in_paragraph",
    "media_type_for",
    "pack_dir_as_odt",
    "pack_flat_odf",
    "parse_xml_from_zip",
    "replace_pattern_with_element_in_element",
    "replace_text_in_element",
    "unique_picture_name",
    "unpack_flat_odf",
    "update_meta_for_edit",
    "write_odt_with_replacements",
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
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}

ODT_MIMETYPE = "application/vnd.oasis.opendocument.text"

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
    input_odt: Path,
    output_odt: Path,
    package_path: str,
    source: Path,
    replacements: dict[str, bytes],
) -> None:
    _copy_base(
        input_odt,
        output_odt,
        package_path,
        source,
        replacements,
        ODT_MIMETYPE,
    )


def pack_dir_as_odt(source_dir: Path, output_odt: Path) -> None:
    pack_dir_as_odf(source_dir, output_odt, ODT_MIMETYPE)


def write_odt_with_replacements(
    input_odt: Path,
    output_odt: Path,
    replacements: dict[str, bytes],
) -> None:
    _write_base(input_odt, output_odt, replacements, ODT_MIMETYPE)


def update_meta_for_edit(meta_root: ET.Element) -> None:
    _update_meta_base(meta_root, NS, q)
