"""Shared helpers for small ODT scripts."""

from __future__ import annotations

import mimetypes
import posixpath
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


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


def parse_xml_from_zip(path: Path, member: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as handle:
            return ET.parse(handle).getroot()


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_odt_with_replacements(input_odt: Path, output_odt: Path, replacements: dict[str, bytes]) -> None:
    with zipfile.ZipFile(input_odt) as src:
        names = src.namelist()
        with zipfile.ZipFile(output_odt, "w") as dst:
            if "mimetype" in names:
                dst.writestr("mimetype", replacements.get("mimetype", src.read("mimetype")), compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype":
                    continue
                dst.writestr(name, replacements.get(name, src.read(name)), compress_type=zipfile.ZIP_DEFLATED)


def pack_dir_as_odt(source_dir: Path, output_odt: Path) -> None:
    mimetype = source_dir / "mimetype"
    if not mimetype.exists():
        raise SystemExit(f"Missing mimetype file in {source_dir}")
    with zipfile.ZipFile(output_odt, "w") as archive:
        archive.write(mimetype, "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir() or path == mimetype:
                continue
            archive.write(path, path.relative_to(source_dir).as_posix(), compress_type=zipfile.ZIP_DEFLATED)


def ensure_manifest_entry(manifest_root: ET.Element, full_path: str, media_type: str) -> None:
    for entry in manifest_root.findall(".//manifest:file-entry", NS):
        if entry.attrib.get(q("manifest", "full-path")) == full_path:
            entry.set(q("manifest", "media-type"), media_type)
            return
    ET.SubElement(
        manifest_root,
        q("manifest", "file-entry"),
        {q("manifest", "full-path"): full_path, q("manifest", "media-type"): media_type},
    )


def media_type_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def unique_picture_name(existing: set[str], image: Path) -> str:
    base = image.name.replace("\\", "_").replace("/", "_")
    candidate = posixpath.join("Pictures", base)
    stem = image.stem
    suffix = image.suffix
    counter = 1
    while candidate in existing:
        candidate = posixpath.join("Pictures", f"{stem}-{counter}{suffix}")
        counter += 1
    return candidate


def copy_into_package(input_odt: Path, output_odt: Path, package_path: str, source: Path, replacements: dict[str, bytes]) -> None:
    with zipfile.ZipFile(input_odt) as src:
        names = src.namelist()
        with zipfile.ZipFile(output_odt, "w") as dst:
            if "mimetype" in names:
                dst.writestr("mimetype", replacements.get("mimetype", src.read("mimetype")), compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype" or name == package_path:
                    continue
                dst.writestr(name, replacements.get(name, src.read(name)), compress_type=zipfile.ZIP_DEFLATED)
            dst.write(source, package_path, compress_type=zipfile.ZIP_DEFLATED)


def clear_children(element: ET.Element) -> None:
    element[:] = []
