"""Shared helpers for OpenDocument Format scripts.

All four ODF skills (ODT, ODP, ODS, ODG) use these functions.
Import from ``odf_lib`` or ``odf_lib.odf_common``:

    from odf_lib import pack_dir_as_odf, find_soffice, xml_bytes

Note: ``q()`` is NOT re-exported here — it needs a format-specific
namespace dict and lives in each ``*_common.py`` wrapper.
"""

from __future__ import annotations

from odf_lib.odf_common import (
    clear_children,
    copy_into_package,
    ensure_manifest_entry,
    find_soffice,
    local_name,
    media_type_for,
    pack_dir_as_odf,
    parse_xml_from_zip,
    unique_picture_name,
    unpack_to_temp,
    write_odf_with_replacements,
    xml_bytes,
)

__all__ = [
    "clear_children",
    "copy_into_package",
    "ensure_manifest_entry",
    "find_soffice",
    "local_name",
    "media_type_for",
    "pack_dir_as_odf",
    "parse_xml_from_zip",
    "unique_picture_name",
    "unpack_to_temp",
    "write_odf_with_replacements",
    "xml_bytes",
]
