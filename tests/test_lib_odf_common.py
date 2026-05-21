"""Direct unit tests for lib.odf_common functions.

These tests call library functions directly (no subprocess) so that
pytest-cov can track coverage.
"""

from __future__ import annotations

import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from lib.odf_common import (
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

NS = {
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def _make_minimal_odf(tmp: Path, name: str = "test.odf") -> Path:
    """Create a minimal ODF ZIP with mimetype and content.xml."""
    odf = tmp / name
    with zipfile.ZipFile(odf, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.text", compress_type=zipfile.ZIP_STORED)
        archive.writestr("content.xml", b"<root/>")
    return odf


class LibOdfCommonTests(unittest.TestCase):
    def test_parse_xml_from_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odf = _make_minimal_odf(Path(tmp))
            root = parse_xml_from_zip(odf, "content.xml")
            self.assertEqual(root.tag, "root")

    def test_xml_bytes(self) -> None:
        elem = ET.Element("test")
        result = xml_bytes(elem)
        self.assertIsInstance(result, bytes)
        self.assertIn(b"<?xml", result)
        self.assertIn(b"<test", result)

    def test_write_odf_with_replacements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = _make_minimal_odf(Path(tmp), "src.odf")
            dst = Path(tmp) / "dst.odf"
            write_odf_with_replacements(
                src, dst, {"content.xml": b"<replaced/>"}, "application/vnd.oasis.opendocument.text"
            )
            with zipfile.ZipFile(dst) as archive:
                self.assertEqual(archive.read("content.xml"), b"<replaced/>")
                self.assertEqual(archive.namelist()[0], "mimetype")

    def test_pack_dir_as_odf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "extracted"
            src_dir.mkdir()
            (src_dir / "mimetype").write_text("application/vnd.oasis.opendocument.text")
            (src_dir / "content.xml").write_text("<root/>")
            output = Path(tmp) / "packed.odf"
            pack_dir_as_odf(src_dir, output, "application/vnd.oasis.opendocument.text")
            with zipfile.ZipFile(output) as archive:
                self.assertIn("mimetype", archive.namelist())
                self.assertIn("content.xml", archive.namelist())

    def test_pack_dir_as_odf_missing_mimetype(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "bad"
            src_dir.mkdir()
            output = Path(tmp) / "packed.odf"
            with self.assertRaises(SystemExit):
                pack_dir_as_odf(src_dir, output, "application/vnd.oasis.opendocument.text")

    def test_ensure_manifest_entry_new(self) -> None:
        manifest = ET.Element(q("manifest", "manifest"))
        ensure_manifest_entry(manifest, "content.xml", "text/xml", NS, q)
        entries = manifest.findall(f".//{q('manifest', 'file-entry')}")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].get(q("manifest", "full-path")), "content.xml")

    def test_ensure_manifest_entry_update(self) -> None:
        manifest = ET.Element(q("manifest", "manifest"))
        ensure_manifest_entry(manifest, "content.xml", "text/xml", NS, q)
        ensure_manifest_entry(manifest, "content.xml", "application/xml", NS, q)
        entries = manifest.findall(f".//{q('manifest', 'file-entry')}")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].get(q("manifest", "media-type")), "application/xml")

    def test_media_type_for(self) -> None:
        self.assertEqual(media_type_for(Path("image.png")), "image/png")
        self.assertEqual(media_type_for(Path("data.unknownext123")), "application/octet-stream")

    def test_unique_picture_name_no_conflict(self) -> None:
        result = unique_picture_name(set(), Path("photo.png"))
        self.assertEqual(result, "Pictures/photo.png")

    def test_unique_picture_name_with_conflict(self) -> None:
        existing = {"Pictures/photo.png"}
        result = unique_picture_name(existing, Path("photo.png"))
        self.assertEqual(result, "Pictures/photo-1.png")

    def test_unique_picture_name_multiple_conflicts(self) -> None:
        existing = {"Pictures/photo.png", "Pictures/photo-1.png"}
        result = unique_picture_name(existing, Path("photo.png"))
        self.assertEqual(result, "Pictures/photo-2.png")

    def test_copy_into_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = _make_minimal_odf(Path(tmp), "src.odf")
            dst = Path(tmp) / "dst.odf"
            image = Path(tmp) / "img.png"
            image.write_bytes(b"PNG")
            copy_into_package(
                src,
                dst,
                "Pictures/img.png",
                image,
                {"content.xml": b"<root/>"},
                "application/vnd.oasis.opendocument.text",
            )
            with zipfile.ZipFile(dst) as archive:
                self.assertIn("Pictures/img.png", archive.namelist())
                self.assertEqual(archive.read("Pictures/img.png"), b"PNG")

    def test_clear_children(self) -> None:
        root = ET.Element("root")
        ET.SubElement(root, "child1")
        ET.SubElement(root, "child2")
        self.assertEqual(len(root), 2)
        clear_children(root)
        self.assertEqual(len(root), 0)

    def test_unpack_to_temp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odf = _make_minimal_odf(Path(tmp))
            temp = unpack_to_temp(odf)
            try:
                self.assertTrue((Path(temp.name) / "mimetype").exists())
                self.assertTrue((Path(temp.name) / "content.xml").exists())
            finally:
                temp.cleanup()

    def test_local_name_clark(self) -> None:
        self.assertEqual(local_name("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p"), "p")

    def test_local_name_plain(self) -> None:
        self.assertEqual(local_name("p"), "p")

    def test_find_soffice_which_path(self) -> None:
        with unittest.mock.patch("lib.odf_common.shutil.which", return_value="/usr/bin/soffice"):
            result = find_soffice()
            self.assertEqual(result, "/usr/bin/soffice")

    def test_find_soffice_not_found(self) -> None:
        with (
            unittest.mock.patch("lib.odf_common.shutil.which", return_value=None),
            unittest.mock.patch.object(Path, "exists", return_value=False),
        ):
            with self.assertRaises(SystemExit):
                find_soffice()


if __name__ == "__main__":
    unittest.main()
