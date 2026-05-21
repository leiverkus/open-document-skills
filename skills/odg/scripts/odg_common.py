"""Shared helpers for small ODG scripts."""

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
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}

ODG_MIMETYPE = "application/vnd.oasis.opendocument.graphics"
SHAPE_TAGS = {"frame", "rect", "ellipse", "line", "connector", "path", "custom-shape"}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def parse_xml_from_zip(path: Path, member: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as handle:
            return ET.parse(handle).getroot()


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_odg_with_replacements(input_odg: Path, output_odg: Path, replacements: dict[str, bytes]) -> None:
    with zipfile.ZipFile(input_odg) as src:
        names = src.namelist()
        with zipfile.ZipFile(output_odg, "w") as dst:
            if "mimetype" in names:
                dst.writestr("mimetype", replacements.get("mimetype", src.read("mimetype")), compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype":
                    continue
                dst.writestr(name, replacements.get(name, src.read(name)), compress_type=zipfile.ZIP_DEFLATED)


def pack_dir_as_odg(source_dir: Path, output_odg: Path) -> None:
    mimetype = source_dir / "mimetype"
    if not mimetype.exists():
        raise SystemExit(f"Missing mimetype file in {source_dir}")
    with zipfile.ZipFile(output_odg, "w") as archive:
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
    ET.SubElement(manifest_root, q("manifest", "file-entry"), {q("manifest", "full-path"): full_path, q("manifest", "media-type"): media_type})


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


def copy_into_package(input_odg: Path, output_odg: Path, package_path: str, source: Path, replacements: dict[str, bytes]) -> None:
    with zipfile.ZipFile(input_odg) as src:
        names = src.namelist()
        with zipfile.ZipFile(output_odg, "w") as dst:
            if "mimetype" in names:
                dst.writestr("mimetype", replacements.get("mimetype", src.read("mimetype")), compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype" or name == package_path:
                    continue
                dst.writestr(name, replacements.get(name, src.read(name)), compress_type=zipfile.ZIP_DEFLATED)
            dst.write(source, package_path, compress_type=zipfile.ZIP_DEFLATED)


def element_text(element: ET.Element) -> str:
    parts = []
    for node in element.iter():
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return " ".join("".join(parts).split())


def iter_pages(root: ET.Element):
    yield from root.findall(".//draw:page", NS)


def page_name(page: ET.Element) -> str:
    return page.attrib.get(q("draw", "name"), "")


def iter_shapes(page: ET.Element):
    for node in page.iter():
        if local_name(node.tag) in SHAPE_TAGS:
            yield node


def find_soffice() -> str:
    candidates = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "/usr/local/bin/libreoffice",
        "/snap/bin/libreoffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        "/c/Program Files/LibreOffice/program/soffice.exe",
        "/mnt/c/Program Files/LibreOffice/program/soffice.exe",
    ]
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise SystemExit("LibreOffice/soffice not found")
