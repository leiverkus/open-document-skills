"""Shared helpers for small ODP scripts.

All format-agnostic functions live in lib.odf_common.
This module adds the ODP namespace, MIMETYPE, and thin wrappers.
"""

from __future__ import annotations

import copy
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
    find_soffice,
    media_type_for,
    pack_dir_as_odf,
    parse_xml_from_zip,
    unique_picture_name,
    unpack_to_temp,
    write_odf_with_replacements as _write_base,
    xml_bytes,
)

# Direct re-exports.
__all__ = [
    "NS", "ODP_MIMETYPE", "q",
    "clear_children", "copy_into_package", "copy_slide",
    "ensure_manifest_entry", "find_soffice", "find_slides",
    "media_type_for", "pack_dir_as_odp", "parse_xml_from_zip",
    "select_slide", "unique_picture_name", "unpack_to_temp",
    "write_odp_with_replacements", "xml_bytes",
]

NS = {
    "anim": "urn:oasis:names:tc:opendocument:xmlns:animation:1.0",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    "smil": "urn:oasis:names:tc:opendocument:xmlns:smil-compatible:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}

ODP_MIMETYPE = "application/vnd.oasis.opendocument.presentation"

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def ensure_manifest_entry(
    manifest_root: ET.Element, full_path: str, media_type: str,
) -> None:
    _ensure_base(manifest_root, full_path, media_type, NS, q)


def copy_into_package(
    input_odp: Path, output_odp: Path, package_path: str,
    source: Path, replacements: dict[str, bytes],
) -> None:
    _copy_base(
        input_odp, output_odp, package_path, source, replacements,
        ODP_MIMETYPE,
    )


def pack_dir_as_odp(source_dir: Path, output_odp: Path) -> None:
    pack_dir_as_odf(source_dir, output_odp, ODP_MIMETYPE)


def write_odp_with_replacements(
    input_odp: Path, output_odp: Path, replacements: dict[str, bytes],
) -> None:
    _write_base(input_odp, output_odp, replacements, ODP_MIMETYPE)


def find_slides(content_root: ET.Element) -> list[ET.Element]:
    """Return all draw:page elements from ODP content."""
    return content_root.findall(".//draw:page", NS)


def select_slide(content_root: ET.Element, slide: str | None) -> ET.Element:
    """Select a slide by index (1-based string) or name."""
    slides = find_slides(content_root)
    if not slides:
        raise SystemExit("No draw:page slides found")
    if slide is None:
        return slides[0]
    if slide.isdigit():
        index = int(slide)
        if index < 1 or index > len(slides):
            raise SystemExit(f"Slide index out of range: {index}")
        return slides[index - 1]
    for page in slides:
        if page.attrib.get(q("draw", "name")) == slide:
            return page
    raise SystemExit(f"Slide not found: {slide}")


def copy_slide(page: ET.Element) -> ET.Element:
    """Deep-copy a draw:page element."""
    return copy.deepcopy(page)
