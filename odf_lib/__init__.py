"""odf_lib — the shared OpenDocument Format library.

This package is the substance behind the four ODF agent skills (ODT, ODP,
ODS, ODG). It provides format-agnostic helpers for reading, editing, and
writing OpenDocument ZIP packages and flat (single-XML) ODF files, with
nothing but the Python standard library at its core.

The names re-exported here are the **public API** and follow semantic
versioning from 1.0 onward. Anything in ``odf_lib.odf_common`` that is not
re-exported here (notably ``_``-prefixed helpers) is internal and may
change without notice.

    from odf_lib import pack_flat_odf, replace_text_in_element, xml_bytes

Note: ``q()`` is intentionally not exported — it needs a format-specific
namespace dict and lives in each skill's ``*_common.py`` wrapper.
"""

from __future__ import annotations

from odf_lib.odf_common import (
    FLAT_EXTENSIONS,
    ODF_NAMESPACES,
    VERSION,
    apply_strict_schema_check,
    build_contact_sheet,
    clear_children,
    copy_into_package,
    copy_with_multiple_members,
    embed_pictures,
    ensure_manifest_entry,
    ensure_schema,
    ensure_sequence_declarations,
    extract_text_range_from_element,
    find_pandoc,
    find_soffice,
    find_text_position_in_element,
    inject_styles_from_file,
    insert_after_text_in_element,
    insert_in_paragraph,
    latex_to_mathml,
    local_name,
    media_type_for,
    pack_dir_as_odf,
    pack_flat_odf,
    parse_xml_from_zip,
    pdf_to_pngs,
    render_to_pdf,
    replace_pattern_with_element_in_element,
    replace_text_in_element,
    sniff_image_mime,
    unique_object_name,
    unique_picture_name,
    unpack_flat_odf,
    unpack_to_temp,
    update_meta_for_edit,
    validate_against_schema,
    wrap_text_across_elements,
    wrap_text_with_pair_in_element,
    write_odf_with_replacements,
    xml_bytes,
)

__version__ = VERSION

__all__ = [
    # Constants
    "VERSION",
    "ODF_NAMESPACES",
    "FLAT_EXTENSIONS",
    # ZIP / XML core
    "parse_xml_from_zip",
    "xml_bytes",
    "write_odf_with_replacements",
    "pack_dir_as_odf",
    "copy_into_package",
    "copy_with_multiple_members",
    "unpack_to_temp",
    # Manifest / media
    "ensure_manifest_entry",
    "media_type_for",
    "sniff_image_mime",
    "unique_picture_name",
    "unique_object_name",
    # Metadata
    "update_meta_for_edit",
    # Flat ODF
    "pack_flat_odf",
    "unpack_flat_odf",
    # Text walker / locator / insertion
    "replace_text_in_element",
    "replace_pattern_with_element_in_element",
    "find_text_position_in_element",
    "extract_text_range_from_element",
    "insert_after_text_in_element",
    "insert_in_paragraph",
    "wrap_text_with_pair_in_element",
    "wrap_text_across_elements",
    "ensure_sequence_declarations",
    "clear_children",
    "local_name",
    # Styles / pictures
    "inject_styles_from_file",
    "embed_pictures",
    # Schema validation
    "ensure_schema",
    "validate_against_schema",
    "apply_strict_schema_check",
    # External tooling
    "find_soffice",
    "find_pandoc",
    "latex_to_mathml",
    # Rendering
    "render_to_pdf",
    "pdf_to_pngs",
    "build_contact_sheet",
]
