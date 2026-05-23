"""Shared helpers for small ODT scripts.

All format-agnostic functions live in odf_lib.odf_common.
This module adds the ODT namespace, MIMETYPE, and thin wrappers
so that existing script imports (``from odt_common import …``)
continue to work unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

# Locate the bundled odf_lib/ package — at the repo root in a dev
# checkout, or inside the skill directory when installed standalone.
for _parent in Path(__file__).resolve().parents:
    if (_parent / "odf_lib" / "odf_common.py").is_file():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break
else:
    raise ImportError(
        "odf_lib not found near this script — reinstall the skill so its bundled odf_lib/ directory is present"
    )

# Single consolidated import block from odf_lib.odf_common.
from odf_lib.odf_common import (  # noqa: E402, I001
    build_contact_sheet,
    build_index_body_placeholder,
    clear_children,
    convert_with_soffice,
    copy_into_package as _copy_base,
    copy_with_multiple_members as _copy_members_base,
    ensure_manifest_entry as _ensure_base,
    ensure_sequence_declarations as _ensure_seq_base,
    embed_pictures as _embed_pictures_base,
    extract_text_range_from_element,
    find_pandoc,
    find_soffice,
    inject_styles_from_file as _inject_styles_base,
    pdf_to_pngs,
    render_to_pdf,
    find_text_position_in_element,
    insert_after_text_in_element,
    insert_in_paragraph,
    latex_to_mathml,
    media_type_for,
    pack_dir_as_odf,
    pack_flat_odf,
    parse_xml_from_zip,
    replace_pattern_with_element_in_element,
    replace_text_in_element,
    sniff_image_mime,
    unique_object_name,
    unique_picture_name,
    unpack_flat_odf,
    update_meta_for_edit as _update_meta_base,
    wrap_text_across_elements,
    wrap_text_with_pair_in_element,
    write_odf_with_replacements as _write_base,
    xml_bytes,
)
from odf_lib.themes import (  # noqa: E402, I001
    BODY_FACE,
    HEADING_FACE,
    Theme,
    get_theme,
    theme_font_faces,
)

# Direct re-exports.
__all__ = [
    "NS",
    "ODT_MIMETYPE",
    "q",
    "BODY_FACE",
    "HEADING_FACE",
    "Theme",
    "get_theme",
    "theme_font_faces",
    "build_contact_sheet",
    "build_index_body_placeholder",
    "clear_children",
    "convert_with_soffice",
    "copy_into_package",
    "copy_with_multiple_members",
    "ensure_manifest_entry",
    "embed_pictures",
    "ensure_sequence_declarations",
    "extract_text_range_from_element",
    "find_pandoc",
    "find_soffice",
    "inject_styles_from_file",
    "pdf_to_pngs",
    "render_to_pdf",
    "find_text_position_in_element",
    "inspect_styles_xml",
    "insert_after_text_in_element",
    "insert_in_paragraph",
    "latex_to_mathml",
    "load_styles_xml",
    "media_type_for",
    "pack_dir_as_odt",
    "pack_flat_odf",
    "parse_xml_from_zip",
    "replace_pattern_with_element_in_element",
    "replace_text_in_element",
    "sniff_image_mime",
    "unique_object_name",
    "unique_picture_name",
    "unpack_flat_odf",
    "update_meta_for_edit",
    "wrap_text_across_elements",
    "wrap_text_with_pair_in_element",
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


def copy_with_multiple_members(
    input_odt: Path,
    output_odt: Path,
    new_members: dict[str, bytes],
    replacements: dict[str, bytes],
) -> None:
    _copy_members_base(input_odt, output_odt, new_members, replacements, ODT_MIMETYPE)


def ensure_sequence_declarations(text_root: ET.Element, names: list[str]) -> None:
    _ensure_seq_base(text_root, names, NS)


def inject_styles_from_file(input_odt: Path, styles_path: Path, output_odt: Path) -> list[str]:
    return _inject_styles_base(input_odt, styles_path, output_odt, ODT_MIMETYPE)


def embed_pictures(input_odt: Path, pictures: dict[str, Path], output_odt: Path) -> None:
    _embed_pictures_base(input_odt, pictures, output_odt, ODT_MIMETYPE, NS, q)


# ---- Template inspection ----------------------------------------------------
#
# An ODT "template" is the layered set of named styles + master pages + page
# layouts (margins, headers, footers) + outline-style (heading numbering) +
# list-styles + font declarations defined in styles.xml. These helpers turn
# that styles.xml into a JSON-serialisable inventory so an agent can pick the
# right named styles + outline numbering for a generated document.


def _header_footer_preview(node: ET.Element | None) -> str:
    """First ~80 chars of concatenated text inside a <style:header>/<style:footer>."""
    if node is None:
        return ""
    parts: list[str] = []
    for descendant in node.iter():
        if descendant.text:
            parts.append(descendant.text)
        if descendant.tail:
            parts.append(descendant.tail)
    text = " ".join(p.strip() for p in parts if p.strip())
    return text[:80] + ("…" if len(text) > 80 else "")


def _frame_summary_odt(frame: ET.Element) -> dict[str, object]:
    image = frame.find("draw:image", NS)
    return {
        "name": frame.attrib.get(q("draw", "name")),
        "role": "image" if image is not None else "text",
        "x": frame.attrib.get(q("svg", "x")),
        "y": frame.attrib.get(q("svg", "y")),
        "width": frame.attrib.get(q("svg", "width")),
        "height": frame.attrib.get(q("svg", "height")),
    }


def _named_style_summary_odt(style: ET.Element) -> dict[str, object]:
    info: dict[str, object] = {
        "name": style.attrib.get(q("style", "name")),
        "family": style.attrib.get(q("style", "family")),
    }
    parent = style.attrib.get(q("style", "parent-style-name"))
    if parent:
        info["parent"] = parent
    outline = style.attrib.get(q("style", "default-outline-level"))
    if outline:
        info["outline_level"] = outline
    text_props = style.find("style:text-properties", NS)
    if text_props is not None:
        for key, attr in (
            ("font", q("style", "font-name")),
            ("font-size", q("fo", "font-size")),
            ("color", q("fo", "color")),
            ("font-weight", q("fo", "font-weight")),
            ("font-style", q("fo", "font-style")),
        ):
            value = text_props.attrib.get(attr)
            if value:
                info[key] = value
    para_props = style.find("style:paragraph-properties", NS)
    if para_props is not None:
        align = para_props.attrib.get(q("fo", "text-align"))
        if align:
            info["text-align"] = align
    return info


def _page_layout_summary(pl: ET.Element) -> dict[str, object]:
    info: dict[str, object] = {"name": pl.attrib.get(q("style", "name"))}
    props = pl.find("style:page-layout-properties", NS)
    if props is not None:
        for key, attr in (
            ("width", q("fo", "page-width")),
            ("height", q("fo", "page-height")),
            ("orientation", q("style", "print-orientation")),
        ):
            value = props.attrib.get(attr)
            if value:
                info[key] = value
        margins: dict[str, str] = {}
        for side, attr in (
            ("top", q("fo", "margin-top")),
            ("bottom", q("fo", "margin-bottom")),
            ("left", q("fo", "margin-left")),
            ("right", q("fo", "margin-right")),
        ):
            value = props.attrib.get(attr)
            if value:
                margins[side] = value
        if margins:
            info["margins"] = margins
    header_style = pl.find("style:header-style", NS)
    if header_style is not None:
        hsp = header_style.find("style:header-footer-properties", NS)
        if hsp is not None:
            mh = hsp.attrib.get(q("fo", "min-height"))
            if mh:
                info["header_height"] = mh
    footer_style = pl.find("style:footer-style", NS)
    if footer_style is not None:
        fsp = footer_style.find("style:header-footer-properties", NS)
        if fsp is not None:
            mh = fsp.attrib.get(q("fo", "min-height"))
            if mh:
                info["footer_height"] = mh
    return info


def _outline_style_summary(os_el: ET.Element) -> dict[str, object]:
    levels: list[dict[str, object]] = []
    for lvl in os_el.findall("text:outline-level-style", NS):
        levels.append(
            {
                "level": lvl.attrib.get(q("text", "level")),
                "num_format": lvl.attrib.get(q("style", "num-format")),
                "num_suffix": lvl.attrib.get(q("style", "num-suffix")),
                "num_prefix": lvl.attrib.get(q("style", "num-prefix")),
                "display_levels": lvl.attrib.get(q("text", "display-levels")),
            }
        )
    return {"name": os_el.attrib.get(q("style", "name")), "levels": levels}


def inspect_styles_xml(styles_root: ET.Element) -> dict[str, object]:
    """Inspect a parsed ODT ``styles.xml`` and return a template inventory.

    Returns a dict with keys:

    - ``page_layouts``: `{name, width, height, margins, orientation,
      header_height, footer_height}` per ``style:page-layout``.
    - ``master_pages``: `{name, page_layout, has_header, has_footer,
      header_preview, footer_preview, frames}` per ``style:master-page``.
    - ``outline_styles``: `{name, levels: [{level, num_format, …}]}` per
      ``text:outline-style`` — the heading-numbering schemes.
    - ``paragraph_styles``, ``text_styles``: named styles from
      ``office:styles`` by family.
    - ``list_styles``: ``[{name}]`` (inventory only).
    - ``font_face_decls``: declared font face names.

    Agent-facing: this is what ``inspect_template.py`` prints as JSON.
    """
    # Page layouts (live in office:automatic-styles in styles.xml).
    page_layouts: list[dict[str, object]] = [
        _page_layout_summary(pl) for pl in styles_root.findall(".//office:automatic-styles/style:page-layout", NS)
    ]

    # Master pages with header/footer previews.
    masters: list[dict[str, object]] = []
    for master in styles_root.findall(".//style:master-page", NS):
        header = master.find("style:header", NS)
        footer = master.find("style:footer", NS)
        frames = [_frame_summary_odt(f) for f in master.findall(".//draw:frame", NS)]
        masters.append(
            {
                "name": master.attrib.get(q("style", "name")),
                "page_layout": master.attrib.get(q("style", "page-layout-name")),
                "has_header": header is not None,
                "has_footer": footer is not None,
                "header_preview": _header_footer_preview(header),
                "footer_preview": _header_footer_preview(footer),
                "frames": frames,
            }
        )

    # Outline styles (heading numbering).
    outline_styles = [
        _outline_style_summary(os_el) for os_el in styles_root.findall(".//office:styles/text:outline-style", NS)
    ]

    # Named paragraph / text styles in office:styles.
    paragraph_styles: list[dict[str, object]] = []
    text_styles: list[dict[str, object]] = []
    for style in styles_root.findall(".//office:styles/style:style", NS):
        family = style.attrib.get(q("style", "family"))
        if family == "paragraph":
            paragraph_styles.append(_named_style_summary_odt(style))
        elif family == "text":
            text_styles.append(_named_style_summary_odt(style))

    # List styles (inventory only).
    list_styles = [
        {"name": ls.attrib.get(q("text", "name"))} for ls in styles_root.findall(".//office:styles/text:list-style", NS)
    ]

    # Font face declarations.
    font_faces = [
        ff.attrib.get(q("style", "name"))
        for ff in styles_root.findall(".//office:font-face-decls/style:font-face", NS)
        if ff.attrib.get(q("style", "name"))
    ]

    return {
        "page_layouts": page_layouts,
        "master_pages": masters,
        "outline_styles": outline_styles,
        "paragraph_styles": paragraph_styles,
        "text_styles": text_styles,
        "list_styles": list_styles,
        "font_face_decls": font_faces,
    }


def load_styles_xml(path: Path) -> ET.Element:
    """Load ``styles.xml`` from an ODT/OTT package or a standalone XML file.

    Detects by extension: ZIP-packaged ODF (``.odt``/``.ott``/``.fodt``) goes
    through :func:`parse_xml_from_zip`; otherwise parsed as XML directly.
    Falls back to direct XML parsing for files that look like packages but
    aren't (e.g. a stray ``styles.xml`` saved with a ``.odt`` extension).
    """
    import zipfile

    if path.suffix.lower() in {".odt", ".ott", ".fodt"}:
        try:
            return parse_xml_from_zip(path, "styles.xml")
        except zipfile.BadZipFile:
            pass
    return ET.parse(path).getroot()
