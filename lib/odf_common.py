"""Shared helpers for OpenDocument Format scripts.

All four ODF skills (ODT, ODP, ODS, ODG) use these functions.
Format-specific *_common.py modules import from here and add their
own NS dict, MIMETYPE constant, and format-specific helpers.
"""

from __future__ import annotations

import mimetypes
import posixpath
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Mapping, Set
from pathlib import Path
from xml.etree import ElementTree as ET


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


def local_name(tag: str) -> str:
    """Extract the local name from a Clark-notation tag ``'{ns}local'``.

    Args:
        tag: XML tag in Clark notation (e.g. ``"{urn:...}text"``) or plain name.

    Returns:
        The local name part (e.g. ``"text"``).
    """
    return tag.split("}", 1)[1] if tag.startswith("{") else tag
