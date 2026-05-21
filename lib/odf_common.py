"""Shared helpers for OpenDocument Format scripts.

All four ODF skills (ODT, ODP, ODS, ODG) use these functions.
Format-specific *_common.py modules import from here and add their
own NS dict, MIMETYPE constant, and format-specific helpers.
"""

from __future__ import annotations

import base64
import mimetypes
import posixpath
import re
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Mapping, Set
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

VERSION = "0.3.0"  # keep in sync with pyproject.toml (see CONTRIBUTING.md)

ODF_NAMESPACES: dict[str, str] = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "smil": "urn:oasis:names:tc:opendocument:xmlns:smil-compatible:1.0",
    "anim": "urn:oasis:names:tc:opendocument:xmlns:animation:1.0",
    "chart": "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
    "form": "urn:oasis:names:tc:opendocument:xmlns:form:1.0",
    "script": "urn:oasis:names:tc:opendocument:xmlns:script:1.0",
    "math": "http://www.w3.org/1998/Math/MathML",
    "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    "of": "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
}

FLAT_EXTENSIONS: dict[str, str] = {
    "application/vnd.oasis.opendocument.text": ".fodt",
    "application/vnd.oasis.opendocument.presentation": ".fodp",
    "application/vnd.oasis.opendocument.spreadsheet": ".fods",
    "application/vnd.oasis.opendocument.graphics": ".fodg",
}


def parse_xml_from_zip(path: Path, member: str) -> ET.Element:
    """Parse an XML member from a ZIP-based ODF file.

    Args:
        path: Path to the ODF ZIP file.
        member: Internal ZIP member name (e.g. ``"content.xml"``).

    Returns:
        The root XML element of the parsed member.
    """
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as handle:
            return ET.parse(handle).getroot()


def xml_bytes(root: ET.Element) -> bytes:
    """Serialize an XML element to UTF-8 bytes with XML declaration.

    Args:
        root: The XML element to serialize.

    Returns:
        UTF-8 encoded bytes including the ``<?xml ...?>`` declaration.
    """
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_odf_with_replacements(
    input_path: Path,
    output_path: Path,
    replacements: Mapping[str, bytes],
    mimetype_value: str,
) -> None:
    """Copy an ODF ZIP, replacing specified members with new content.

    The mimetype entry is always written first and uncompressed.

    Args:
        input_path: Source ODF file.
        output_path: Destination ODF file (overwritten).
        replacements: Mapping of member names to replacement bytes.
        mimetype_value: The mimetype string to write if not in *replacements*.
    """
    with zipfile.ZipFile(input_path) as src:
        names: list[str] = src.namelist()
        with zipfile.ZipFile(output_path, "w") as dst:
            if "mimetype" in names:
                dst.writestr(
                    "mimetype",
                    replacements.get("mimetype", mimetype_value.encode()),
                    compress_type=zipfile.ZIP_STORED,
                )
            for name in names:
                if name == "mimetype":
                    continue
                dst.writestr(
                    name,
                    replacements.get(name, src.read(name)),
                    compress_type=zipfile.ZIP_DEFLATED,
                )


def pack_dir_as_odf(source_dir: Path, output_path: Path, mimetype_value: str) -> None:
    """Repack an extracted ODF directory into a valid ODF file.

    The mimetype file must exist in *source_dir* and is written first
    and uncompressed, as required by the ODF specification.

    Args:
        source_dir: Directory containing extracted ODF contents.
        output_path: Destination ODF file (overwritten).
        mimetype_value: The mimetype string (written to ``mimetype`` member).
    """
    mimetype: Path = source_dir / "mimetype"
    if not mimetype.exists():
        raise SystemExit(f"Missing mimetype file in {source_dir}")
    with zipfile.ZipFile(output_path, "w") as archive:
        archive.write(mimetype, "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir() or path == mimetype:
                continue
            archive.write(
                path,
                path.relative_to(source_dir).as_posix(),
                compress_type=zipfile.ZIP_DEFLATED,
            )


def ensure_manifest_entry(
    manifest_root: ET.Element,
    full_path: str,
    media_type: str,
    ns: Mapping[str, str],
    q_fn: Callable[[str, str], str],
) -> None:
    """Add or update a manifest file-entry.

    If an entry for *full_path* already exists, its media-type is updated.
    Otherwise a new file-entry is appended.

    Args:
        manifest_root: The ``<manifest:manifest>`` element.
        full_path: The ``manifest:full-path`` attribute value.
        media_type: The ``manifest:media-type`` attribute value.
        ns: Namespace prefix-to-URI mapping.
        q_fn: Qualified-name builder (e.g. ``q("manifest", "full-path")``).
    """
    manifest_ns: str = ns.get("manifest", "")
    entry_tag: str = f"{{{manifest_ns}}}file-entry"
    for entry in manifest_root.findall(f".//{entry_tag}"):
        if entry.attrib.get(q_fn("manifest", "full-path")) == full_path:
            entry.set(q_fn("manifest", "media-type"), media_type)
            return
    ET.SubElement(
        manifest_root,
        entry_tag,
        {
            q_fn("manifest", "full-path"): full_path,
            q_fn("manifest", "media-type"): media_type,
        },
    )


def update_meta_for_edit(
    meta_root: ET.Element,
    ns: Mapping[str, str],
    q_fn: Callable[[str, str], str],
) -> None:
    """Mark an edit in ``meta.xml``: modification-date, generator, editing-cycles.

    Locates or creates the ``<meta:modification-date>``, ``<meta:generator>``,
    and ``<meta:editing-cycles>`` elements under the document's ``<office:meta>``
    node. Modification-date is set to the current UTC ISO timestamp.
    Generator is set to ``open-document-skills/<VERSION>``. Editing-cycles is
    incremented (or initialised to ``1`` if absent or unparseable).

    Args:
        meta_root: The root of ``meta.xml`` (typically ``office:document-meta``).
        ns: Namespace prefix-to-URI mapping; must contain ``office`` and ``meta``.
        q_fn: Qualified-name builder, e.g. ``q("meta", "generator")``.

    Raises:
        SystemExit: If no ``office:meta`` element can be located or created.
    """
    office_ns: str = ns.get("office", "")
    meta_tag: str = f"{{{office_ns}}}meta"
    meta_el: ET.Element | None = meta_root.find(meta_tag)
    if meta_el is None:
        if local_name(meta_root.tag) == "meta":
            meta_el = meta_root
        else:
            raise SystemExit("office:meta element not found in meta.xml")

    def _find_or_create(tag: str) -> ET.Element:
        el: ET.Element | None = meta_el.find(tag)
        if el is None:
            el = ET.SubElement(meta_el, tag)
        return el

    mod_tag: str = q_fn("meta", "modification-date")
    mod_el: ET.Element = _find_or_create(mod_tag)
    mod_el.text = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    gen_tag: str = q_fn("meta", "generator")
    gen_el: ET.Element = _find_or_create(gen_tag)
    gen_el.text = f"open-document-skills/{VERSION}"

    cycles_tag: str = q_fn("meta", "editing-cycles")
    cycles_el: ET.Element = _find_or_create(cycles_tag)
    current: int
    try:
        current = int((cycles_el.text or "0").strip())
    except ValueError:
        current = 0
    cycles_el.text = str(current + 1)


def media_type_for(path: Path) -> str:
    """Guess the MIME type for a file path, falling back to octet-stream.

    Args:
        path: File path (only the extension is used for guessing).

    Returns:
        MIME type string, e.g. ``"image/png"`` or ``"application/octet-stream"``.
    """
    guessed: str | None
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def unique_picture_name(existing: Set[str], image: Path) -> str:
    """Return a unique ``Pictures/…`` path that does not clash with *existing*.

    Args:
        existing: Set of already-used package paths.
        image: Source image file path.

    Returns:
        A ``Pictures/<filename>`` path, with ``-N`` suffix if needed.
    """
    base: str = image.name.replace("\\", "_").replace("/", "_")
    candidate: str = posixpath.join("Pictures", base)
    stem: str = image.stem
    suffix: str = image.suffix
    counter: int = 1
    while candidate in existing:
        candidate = posixpath.join("Pictures", f"{stem}-{counter}{suffix}")
        counter += 1
    return candidate


def copy_into_package(
    input_path: Path,
    output_path: Path,
    package_path: str,
    source: Path,
    replacements: Mapping[str, bytes],
    mimetype_value: str,
) -> None:
    """Copy an ODF ZIP, replacing members and adding *source* at *package_path*.

    Args:
        input_path: Source ODF file.
        output_path: Destination ODF file (overwritten).
        package_path: Internal ZIP path for the new file.
        source: Local file to insert.
        replacements: Mapping of member names to replacement bytes.
        mimetype_value: The mimetype string to write if not in *replacements*.
    """
    with zipfile.ZipFile(input_path) as src:
        names: list[str] = src.namelist()
        with zipfile.ZipFile(output_path, "w") as dst:
            if "mimetype" in names:
                dst.writestr(
                    "mimetype",
                    replacements.get("mimetype", mimetype_value.encode()),
                    compress_type=zipfile.ZIP_STORED,
                )
            for name in names:
                if name == "mimetype" or name == package_path:
                    continue
                dst.writestr(
                    name,
                    replacements.get(name, src.read(name)),
                    compress_type=zipfile.ZIP_DEFLATED,
                )
            dst.write(source, package_path, compress_type=zipfile.ZIP_DEFLATED)


def clear_children(element: ET.Element) -> None:
    """Remove all child elements from *element* in-place.

    Args:
        element: The XML element to clear.
    """
    element[:] = []


def _collect_text_slots(element: ET.Element) -> list[tuple[ET.Element, str]]:
    """Collect (node, attr) text-slot pairs in document order.

    Walker and locator helpers share this structure. For *element*, yields
    ``(element, "text")`` first; then for every descendant in DFS order,
    yields ``(node, "text")`` before recursing and ``(node, "tail")`` after.
    The root's ``.tail`` is intentionally not included (it lives outside the
    element's content).

    Args:
        element: Root of the subtree to collect from.

    Returns:
        Ordered list of ``(node, attr)`` pairs where ``attr`` is ``"text"`` or ``"tail"``.
    """
    slots: list[tuple[ET.Element, str]] = []

    def visit(node: ET.Element, is_root: bool) -> None:
        slots.append((node, "text"))
        for child in list(node):
            visit(child, False)
        if not is_root:
            slots.append((node, "tail"))

    visit(element, True)
    return slots


def _build_parent_map(element: ET.Element) -> dict[ET.Element, ET.Element]:
    """Build a descendant → parent mapping for *element*'s subtree.

    The root *element* is not present as a key (it has no parent within the subtree).

    Args:
        element: Root of the subtree.

    Returns:
        Dict mapping each descendant to its direct parent.
    """
    parent_map: dict[ET.Element, ET.Element] = {}
    for parent in element.iter():
        for child in parent:
            parent_map[child] = parent
    return parent_map


def find_text_position_in_element(element: ET.Element, needle: str) -> tuple[ET.Element, str, int] | None:
    """Find the FIRST occurrence of *needle* in *element*'s text content.

    Walks ``.text`` of *element* and every descendant, plus ``.tail`` of every
    descendant, in document order. Returns the slot (node, attr) and local
    offset where the match BEGINS. A match may span multiple slots — only the
    starting slot is reported.

    Args:
        element: The element to search.
        needle: Substring to look for. Empty string returns None.

    Returns:
        ``(node, attr, local_offset)`` where ``attr`` is ``"text"`` or ``"tail"``,
        or ``None`` if not found.
    """
    if not needle:
        return None
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)
    idx: int = combined.find(needle)
    if idx < 0:
        return None
    running: int = 0
    for (node, attr), value in zip(slots, values):
        if running <= idx < running + len(value):
            return node, attr, idx - running
        running += len(value)
    return None


def insert_after_text_in_element(element: ET.Element, anchor: str, new_element: ET.Element) -> bool:
    """Insert *new_element* immediately after the first occurrence of *anchor*.

    Splits the slot containing the END of the match, then inserts *new_element*
    either as a child (when the match ends in a ``.text`` slot) or as a sibling
    (when it ends in a ``.tail`` slot). The remainder of the slot becomes
    *new_element*'s ``.tail``. Other inline children of *element* are preserved.

    Args:
        element: The container in which to search.
        anchor: Substring that locates the insertion point.
        new_element: The element to insert.

    Returns:
        ``True`` if the anchor was found and the element inserted, else ``False``.
    """
    if not anchor:
        return False
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)
    idx: int = combined.find(anchor)
    if idx < 0:
        return False
    end: int = idx + len(anchor)
    running: int = 0
    target_index: int = -1
    for i, value in enumerate(values):
        if running <= end - 1 < running + len(value):
            target_index = i
            break
        running += len(value)
    if target_index < 0:
        return False
    target_node, target_attr = slots[target_index]
    local_end: int = end - running
    current_value: str = values[target_index]
    prefix: str = current_value[:local_end]
    suffix: str = current_value[local_end:]

    if target_attr == "text":
        target_node.text = prefix if prefix else None
        target_node.insert(0, new_element)
        new_element.tail = suffix if suffix else None
        return True

    target_node.tail = prefix if prefix else None
    parent_map: dict[ET.Element, ET.Element] = _build_parent_map(element)
    parent: ET.Element | None = parent_map.get(target_node)
    if parent is None:
        return False
    sibling_index: int = list(parent).index(target_node)
    parent.insert(sibling_index + 1, new_element)
    new_element.tail = suffix if suffix else None
    return True


def replace_pattern_with_element_in_element(
    element: ET.Element,
    pattern: re.Pattern[str],
    factory: Callable[[re.Match[str]], ET.Element],
) -> int:
    """Replace every regex match in *element*'s text content with a built element.

    For each non-overlapping match of *pattern* against the concatenated text
    content (``.text`` of *element* and descendants, plus ``.tail`` of every
    descendant), the match is removed and replaced with the element returned
    by ``factory(match)``. The element is inserted either as a child (when
    the match falls in a ``.text`` slot) or as a sibling (when in a ``.tail``
    slot). The new element's ``.tail`` carries the remainder of the original
    slot.

    Matches that straddle multiple slots are silently skipped — short
    placeholder patterns like ``[@bibkey]`` virtually never straddle inline
    children, and skipping is safer than corrupting structure.

    Args:
        element: Container to scan.
        pattern: Compiled regex.
        factory: Callable returning a new ET.Element per match.

    Returns:
        Number of replacements performed.
    """
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    offsets: list[int] = []
    running: int = 0
    for v in values:
        offsets.append(running)
        running += len(v)
    combined: str = "".join(values)

    matches: list[re.Match[str]] = list(pattern.finditer(combined))
    if not matches:
        return 0

    def slot_for(global_offset: int) -> int:
        lo, hi = 0, len(values) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offsets[mid] <= global_offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    parent_map: dict[ET.Element, ET.Element] = _build_parent_map(element)
    replaced: int = 0

    # Work right-to-left so earlier modifications don't shift later positions
    # within the paragraph structure.
    for match in reversed(matches):
        start, end = match.start(), match.end()
        i_slot = slot_for(start)
        j_slot = slot_for(end - 1) if end > start else i_slot
        if i_slot != j_slot:
            # Straddle — skip silently.
            continue
        target_node, target_attr = slots[i_slot]
        local_start = start - offsets[i_slot]
        local_end = end - offsets[i_slot]
        current = values[i_slot]
        prefix = current[:local_start]
        suffix = current[local_end:]
        new_element = factory(match)

        if target_attr == "text":
            target_node.text = prefix if prefix else None
            target_node.insert(0, new_element)
            new_element.tail = suffix if suffix else None
        else:
            target_node.tail = prefix if prefix else None
            parent = parent_map.get(target_node)
            if parent is None:
                continue
            sibling_index = list(parent).index(target_node)
            parent.insert(sibling_index + 1, new_element)
            new_element.tail = suffix if suffix else None

        # Update tracking so subsequent (earlier) matches see the new state.
        # We pessimistically rebuild slots; simpler than incremental updates.
        slots = _collect_text_slots(element)
        values = [getattr(n, a) or "" for n, a in slots]
        offsets = []
        running = 0
        for v in values:
            offsets.append(running)
            running += len(v)
        parent_map = _build_parent_map(element)
        replaced += 1

    return replaced


def insert_in_paragraph(paragraph: ET.Element, position: str, new_element: ET.Element) -> None:
    """Insert *new_element* at the start or end of *paragraph*.

    ``"end"`` appends; ``"start"`` inserts as first child and pushes any
    existing ``paragraph.text`` to ``new_element.tail``.

    Args:
        paragraph: The container element (typically ``text:p`` or ``text:h``).
        position: Either ``"start"`` or ``"end"``.
        new_element: Element to insert.

    Raises:
        ValueError: If *position* is not ``"start"`` or ``"end"``.
    """
    if position == "end":
        paragraph.append(new_element)
        new_element.tail = None
    elif position == "start":
        old_text: str | None = paragraph.text
        paragraph.text = None
        paragraph.insert(0, new_element)
        new_element.tail = old_text
    else:
        raise ValueError(f"position must be 'start' or 'end', got {position!r}")


def replace_text_in_element(element: ET.Element, old: str, new: str) -> int:
    """Replace ``old`` with ``new`` in *element*'s text, preserving children.

    Walks all text nodes (``.text`` of *element* and every descendant, plus
    ``.tail`` of every descendant) in document order. Inline children such as
    ``text:span``, ``text:note``, ``text:bookmark``, ``text:a`` keep their
    identity. Matches that straddle child boundaries are still replaced — the
    new content is placed in the first containing slot, intermediate slots are
    cleared, and the trailing slot keeps only the suffix after the match.

    Args:
        element: The element whose textual content should be searched.
        old: Substring to search for. Empty string is a no-op.
        new: Replacement string.

    Returns:
        Number of non-overlapping replacements performed.
    """
    if not old:
        return 0

    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)

    matches: list[tuple[int, int]] = []
    pos: int = 0
    while True:
        i: int = combined.find(old, pos)
        if i < 0:
            break
        matches.append((i, i + len(old)))
        pos = i + len(old)
    if not matches:
        return 0

    offsets: list[int] = []
    running: int = 0
    for v in values:
        offsets.append(running)
        running += len(v)

    def slot_for(offset: int) -> int:
        lo: int = 0
        hi: int = len(values) - 1
        while lo < hi:
            mid: int = (lo + hi + 1) // 2
            if offsets[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    for match_start, match_end in reversed(matches):
        i_slot: int = slot_for(match_start)
        j_slot: int = slot_for(match_end - 1) if match_end > match_start else i_slot
        local_i: int = match_start - offsets[i_slot]
        local_j: int = match_end - offsets[j_slot]
        if i_slot == j_slot:
            v = values[i_slot]
            values[i_slot] = v[:local_i] + new + v[local_j:]
        else:
            values[i_slot] = values[i_slot][:local_i] + new
            for k in range(i_slot + 1, j_slot):
                values[k] = ""
            values[j_slot] = values[j_slot][local_j:]

    for (node, attr), value in zip(slots, values):
        setattr(node, attr, value if value else None)

    return len(matches)


def find_soffice() -> str:
    """Locate the LibreOffice/soffice executable.

    Checks PATH first, then common installation directories on macOS,
    Linux (including snap), and Windows (including WSL).

    Returns:
        Absolute path to the ``soffice`` or ``libreoffice`` executable.

    Raises:
        SystemExit: If no executable is found.
    """
    candidates: list[str] = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "/usr/local/bin/libreoffice",
        "/snap/bin/libreoffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        "/c/Program Files/LibreOffice/program/soffice.exe",
        "/mnt/c/Program Files/LibreOffice/program/soffice.exe",
    ]
    for name in ("soffice", "libreoffice"):
        found: str | None = shutil.which(name)
        if found:
            return found
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise SystemExit("LibreOffice/soffice not found")


def unpack_to_temp(path: Path) -> tempfile.TemporaryDirectory[str]:
    """Extract an ODF ZIP to a temporary directory.

    The caller is responsible for cleaning up the returned
    TemporaryDirectory (e.g. via a context manager or ``.cleanup()``).

    Args:
        path: Path to the ODF ZIP file.

    Returns:
        A ``tempfile.TemporaryDirectory`` containing the extracted contents.
    """
    temp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(path) as archive:
        archive.extractall(temp.name)
    return temp


_IMAGE_MAGIC: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"<?xml", ".svg"),
    (b"<svg", ".svg"),
    (b"BM", ".bmp"),
    (b"RIFF", ".webp"),
]


def _sniff_image_extension(data: bytes) -> str:
    for magic, ext in _IMAGE_MAGIC:
        if data.startswith(magic):
            return ext
    return ".bin"


def pack_flat_odf(input_zip: Path, output_flat: Path) -> None:
    """Convert a zipped ODF package to flat (single-XML) ODF.

    The resulting file has a single ``<office:document>`` root with merged
    content, styles, meta, and settings, plus all embedded pictures encoded
    inline as ``<office:binary-data>`` children of their ``<draw:image>``.

    Args:
        input_zip: Source ODF file (``.odt``/``.odp``/``.ods``/``.odg``).
        output_flat: Destination flat ODF file (``.fodt``/``.fodp``/...).
    """
    for prefix, uri in ODF_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    office_ns: str = ODF_NAMESPACES["office"]
    xlink_ns: str = ODF_NAMESPACES["xlink"]
    draw_ns: str = ODF_NAMESPACES["draw"]

    with zipfile.ZipFile(input_zip) as archive:
        mimetype: str = archive.read("mimetype").decode("ascii").strip()
        meta_root: ET.Element = ET.fromstring(archive.read("meta.xml"))
        settings_root: ET.Element = ET.fromstring(archive.read("settings.xml"))
        styles_root: ET.Element = ET.fromstring(archive.read("styles.xml"))
        content_root: ET.Element = ET.fromstring(archive.read("content.xml"))
        pictures: dict[str, bytes] = {
            name: archive.read(name) for name in archive.namelist() if name.startswith("Pictures/")
        }

    flat_root: ET.Element = ET.Element(
        f"{{{office_ns}}}document",
        {
            f"{{{office_ns}}}version": "1.3",
            f"{{{office_ns}}}mimetype": mimetype,
        },
    )

    def _children_matching(source: ET.Element, names: set[str]) -> list[ET.Element]:
        return [child for child in source if local_name(child.tag) in names]

    for child in _children_matching(meta_root, {"meta"}):
        flat_root.append(child)
    for child in _children_matching(settings_root, {"settings"}):
        flat_root.append(child)
    for child in _children_matching(content_root, {"scripts"}):
        flat_root.append(child)
    for child in _children_matching(styles_root, {"font-face-decls"}):
        flat_root.append(child)
    for child in _children_matching(styles_root, {"styles"}):
        flat_root.append(child)

    merged_auto: ET.Element = ET.SubElement(flat_root, f"{{{office_ns}}}automatic-styles")
    for source in (styles_root, content_root):
        for auto in _children_matching(source, {"automatic-styles"}):
            for grandchild in list(auto):
                merged_auto.append(grandchild)

    for child in _children_matching(styles_root, {"master-styles"}):
        flat_root.append(child)
    for child in _children_matching(content_root, {"body"}):
        flat_root.append(child)

    for image in flat_root.iter(f"{{{draw_ns}}}image"):
        href: str | None = image.attrib.get(f"{{{xlink_ns}}}href")
        if href and href in pictures:
            for attr in (
                f"{{{xlink_ns}}}href",
                f"{{{xlink_ns}}}type",
                f"{{{xlink_ns}}}show",
                f"{{{xlink_ns}}}actuate",
            ):
                image.attrib.pop(attr, None)
            binary: ET.Element = ET.SubElement(image, f"{{{office_ns}}}binary-data")
            binary.text = base64.b64encode(pictures[href]).decode("ascii")

    output_flat.write_bytes(xml_bytes(flat_root))


def unpack_flat_odf(input_flat: Path, output_zip: Path) -> None:
    """Convert a flat ODF file back to a zipped ODF package.

    Splits the single ``<office:document>`` root into the standard four
    XML files (content/styles/meta/settings), extracts inline pictures
    from ``<office:binary-data>`` blobs into ``Pictures/`` entries, and
    rebuilds ``META-INF/manifest.xml``.

    Args:
        input_flat: Source flat ODF file.
        output_zip: Destination zipped ODF file.
    """
    for prefix, uri in ODF_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    office_ns: str = ODF_NAMESPACES["office"]
    xlink_ns: str = ODF_NAMESPACES["xlink"]
    draw_ns: str = ODF_NAMESPACES["draw"]
    style_ns: str = ODF_NAMESPACES["style"]
    manifest_ns: str = ODF_NAMESPACES["manifest"]

    flat_root: ET.Element = ET.parse(input_flat).getroot()
    mimetype: str | None = flat_root.attrib.get(f"{{{office_ns}}}mimetype")
    if not mimetype:
        raise SystemExit("flat ODF root missing office:mimetype attribute")

    meta_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-meta", {f"{{{office_ns}}}version": "1.3"})
    settings_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-settings", {f"{{{office_ns}}}version": "1.3"})
    styles_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-styles", {f"{{{office_ns}}}version": "1.3"})
    content_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-content", {f"{{{office_ns}}}version": "1.3"})

    styles_auto: ET.Element = ET.SubElement(styles_doc, f"{{{office_ns}}}automatic-styles")
    content_auto: ET.Element = ET.SubElement(content_doc, f"{{{office_ns}}}automatic-styles")

    for child in list(flat_root):
        name: str = local_name(child.tag)
        if name == "meta":
            meta_doc.append(child)
        elif name == "settings":
            settings_doc.append(child)
        elif name == "scripts":
            content_doc.append(child)
        elif name == "font-face-decls":
            styles_doc.append(child)
        elif name == "styles":
            styles_doc.append(child)
        elif name == "automatic-styles":
            for grandchild in list(child):
                if grandchild.tag == f"{{{style_ns}}}page-layout":
                    styles_auto.append(grandchild)
                else:
                    content_auto.append(grandchild)
        elif name == "master-styles":
            styles_doc.append(child)
        elif name == "body":
            content_doc.append(child)

    pictures: dict[str, bytes] = {}
    existing_names: set[str] = set()
    for image in content_doc.iter(f"{{{draw_ns}}}image"):
        binary: ET.Element | None = image.find(f"{{{office_ns}}}binary-data")
        if binary is None or not binary.text:
            continue
        data: bytes = base64.b64decode(binary.text.strip())
        ext: str = _sniff_image_extension(data)
        candidate: str = unique_picture_name(existing_names, Path(f"image{len(pictures) + 1}{ext}"))
        existing_names.add(candidate)
        pictures[candidate] = data
        image.remove(binary)
        image.set(f"{{{xlink_ns}}}href", candidate)
        image.set(f"{{{xlink_ns}}}type", "simple")
        image.set(f"{{{xlink_ns}}}show", "embed")
        image.set(f"{{{xlink_ns}}}actuate", "onLoad")

    manifest_doc: ET.Element = ET.Element(
        f"{{{manifest_ns}}}manifest",
        {f"{{{manifest_ns}}}version": "1.3"},
    )
    ET.SubElement(
        manifest_doc,
        f"{{{manifest_ns}}}file-entry",
        {
            f"{{{manifest_ns}}}full-path": "/",
            f"{{{manifest_ns}}}media-type": mimetype,
            f"{{{manifest_ns}}}version": "1.3",
        },
    )
    for name in ("content.xml", "styles.xml", "meta.xml", "settings.xml"):
        ET.SubElement(
            manifest_doc,
            f"{{{manifest_ns}}}file-entry",
            {
                f"{{{manifest_ns}}}full-path": name,
                f"{{{manifest_ns}}}media-type": "text/xml",
            },
        )
    for picture_path in pictures:
        ET.SubElement(
            manifest_doc,
            f"{{{manifest_ns}}}file-entry",
            {
                f"{{{manifest_ns}}}full-path": picture_path,
                f"{{{manifest_ns}}}media-type": media_type_for(Path(picture_path)),
            },
        )

    with zipfile.ZipFile(output_zip, "w") as archive:
        archive.writestr("mimetype", mimetype, compress_type=zipfile.ZIP_STORED)
        archive.writestr("content.xml", xml_bytes(content_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("styles.xml", xml_bytes(styles_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("meta.xml", xml_bytes(meta_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("settings.xml", xml_bytes(settings_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", xml_bytes(manifest_doc), compress_type=zipfile.ZIP_DEFLATED)
        for path, data in pictures.items():
            archive.writestr(path, data, compress_type=zipfile.ZIP_DEFLATED)


def local_name(tag: str) -> str:
    """Extract the local name from a Clark-notation tag ``'{ns}local'``.

    Args:
        tag: XML tag in Clark notation (e.g. ``"{urn:...}text"``) or plain name.

    Returns:
        The local name part (e.g. ``"text"``).
    """
    return tag.split("}", 1)[1] if tag.startswith("{") else tag
