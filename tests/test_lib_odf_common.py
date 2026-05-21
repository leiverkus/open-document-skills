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
    VERSION,
    clear_children,
    copy_into_package,
    ensure_manifest_entry,
    find_soffice,
    find_text_position_in_element,
    insert_after_text_in_element,
    insert_in_paragraph,
    local_name,
    media_type_for,
    pack_dir_as_odf,
    parse_xml_from_zip,
    replace_text_in_element,
    unique_picture_name,
    unpack_to_temp,
    update_meta_for_edit,
    write_odf_with_replacements,
    xml_bytes,
)

NS = {
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
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

    def test_replace_text_simple(self) -> None:
        p = ET.fromstring("<p>Hello World</p>")
        n = replace_text_in_element(p, "World", "ODF")
        self.assertEqual(n, 1)
        self.assertEqual(p.text, "Hello ODF")

    def test_replace_text_preserves_child(self) -> None:
        p = ET.fromstring("<p>Hi <span>bold</span> and rest</p>")
        n = replace_text_in_element(p, "Hi", "Hello")
        self.assertEqual(n, 1)
        self.assertEqual(p.text, "Hello ")
        span = p.find("span")
        assert span is not None
        self.assertEqual(span.text, "bold")
        self.assertEqual(span.tail, " and rest")

    def test_replace_text_in_child_tail(self) -> None:
        p = ET.fromstring("<p>x<span>y</span>FOO bar</p>")
        n = replace_text_in_element(p, "FOO", "BAZ")
        self.assertEqual(n, 1)
        span = p.find("span")
        assert span is not None
        self.assertEqual(span.tail, "BAZ bar")

    def test_replace_text_straddles_child(self) -> None:
        p = ET.fromstring("<p>{{NA<span>ME</span>}}</p>")
        n = replace_text_in_element(p, "{{NAME}}", "Patrick")
        self.assertEqual(n, 1)
        self.assertEqual(p.text, "Patrick")
        span = p.find("span")
        assert span is not None
        # span element is preserved structurally but its content/tail are emptied.
        self.assertIsNone(span.text)
        self.assertIsNone(span.tail)

    def test_replace_text_multiple_non_overlapping(self) -> None:
        p = ET.fromstring("<p>aaXaaXaa</p>")
        n = replace_text_in_element(p, "X", "Y")
        self.assertEqual(n, 2)
        self.assertEqual(p.text, "aaYaaYaa")

    def test_replace_text_empty_old_is_noop(self) -> None:
        p = ET.fromstring("<p>Hello</p>")
        n = replace_text_in_element(p, "", "x")
        self.assertEqual(n, 0)
        self.assertEqual(p.text, "Hello")

    def test_replace_text_no_match(self) -> None:
        p = ET.fromstring("<p>Hello <span>x</span></p>")
        n = replace_text_in_element(p, "missing", "x")
        self.assertEqual(n, 0)
        self.assertEqual(p.text, "Hello ")

    def test_replace_text_match_consumes_grandchild(self) -> None:
        p = ET.fromstring("<p>A<x>B<y>C</y>D</x>E</p>")
        n = replace_text_in_element(p, "ABCDE", "Z")
        self.assertEqual(n, 1)
        self.assertEqual(p.text, "Z")
        # Structure preserved
        x = p.find("x")
        assert x is not None
        y = x.find("y")
        assert y is not None

    def test_find_text_position_simple_text(self) -> None:
        p = ET.fromstring("<p>Hello World</p>")
        result = find_text_position_in_element(p, "World")
        assert result is not None
        node, attr, offset = result
        self.assertEqual(node, p)
        self.assertEqual(attr, "text")
        self.assertEqual(offset, 6)

    def test_find_text_position_in_child_tail(self) -> None:
        p = ET.fromstring("<p>x<span>y</span>FOO bar</p>")
        result = find_text_position_in_element(p, "FOO")
        assert result is not None
        node, attr, offset = result
        self.assertEqual(node.tag, "span")
        self.assertEqual(attr, "tail")
        self.assertEqual(offset, 0)

    def test_find_text_position_in_child_text(self) -> None:
        p = ET.fromstring("<p>Hi <span>marker here</span> tail</p>")
        result = find_text_position_in_element(p, "marker")
        assert result is not None
        node, attr, offset = result
        self.assertEqual(node.tag, "span")
        self.assertEqual(attr, "text")
        self.assertEqual(offset, 0)

    def test_find_text_position_no_match(self) -> None:
        p = ET.fromstring("<p>Hello</p>")
        self.assertIsNone(find_text_position_in_element(p, "missing"))

    def test_find_text_position_empty_needle(self) -> None:
        p = ET.fromstring("<p>Hello</p>")
        self.assertIsNone(find_text_position_in_element(p, ""))

    def test_insert_after_in_text_slot(self) -> None:
        p = ET.fromstring("<p>Hello World</p>")
        note = ET.Element("note")
        note.text = "x"
        ok = insert_after_text_in_element(p, "Hello", note)
        self.assertTrue(ok)
        self.assertEqual(p.text, "Hello")
        children = list(p)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].tag, "note")
        self.assertEqual(children[0].tail, " World")

    def test_insert_after_in_child_tail_slot(self) -> None:
        p = ET.fromstring("<p>x<span>y</span>FOO bar</p>")
        note = ET.Element("note")
        ok = insert_after_text_in_element(p, "FOO", note)
        self.assertTrue(ok)
        # After insertion: <p>x<span>y</span>FOO<note/> bar</p>
        # — anchor "FOO" is preserved, note comes immediately after.
        children = list(p)
        self.assertEqual([c.tag for c in children], ["span", "note"])
        span = children[0]
        self.assertEqual(span.tail, "FOO")
        self.assertEqual(children[1].tail, " bar")

    def test_insert_after_preserves_existing_children(self) -> None:
        p = ET.fromstring("<p>Hi <span>bold</span> tail FOO end</p>")
        note = ET.Element("note")
        ok = insert_after_text_in_element(p, "FOO", note)
        self.assertTrue(ok)
        children = list(p)
        # Span must still be there
        spans = [c for c in children if c.tag == "span"]
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].text, "bold")
        # Note must be after span
        self.assertEqual([c.tag for c in children], ["span", "note"])

    def test_insert_after_no_match_returns_false(self) -> None:
        p = ET.fromstring("<p>Hello</p>")
        note = ET.Element("note")
        ok = insert_after_text_in_element(p, "missing", note)
        self.assertFalse(ok)
        self.assertEqual(len(list(p)), 0)

    def test_insert_in_paragraph_end_empty(self) -> None:
        p = ET.fromstring("<p>Hello</p>")
        note = ET.Element("note")
        insert_in_paragraph(p, "end", note)
        self.assertEqual(p.text, "Hello")
        self.assertEqual(list(p)[-1].tag, "note")

    def test_insert_in_paragraph_start(self) -> None:
        p = ET.fromstring("<p>Hello world</p>")
        note = ET.Element("note")
        insert_in_paragraph(p, "start", note)
        self.assertIsNone(p.text)
        children = list(p)
        self.assertEqual(children[0].tag, "note")
        self.assertEqual(children[0].tail, "Hello world")

    def test_insert_in_paragraph_invalid_position(self) -> None:
        p = ET.fromstring("<p>Hello</p>")
        with self.assertRaises(ValueError):
            insert_in_paragraph(p, "middle", ET.Element("x"))

    def test_update_meta_creates_missing_elements(self) -> None:
        root = ET.Element(q("office", "document-meta"))
        ET.SubElement(root, q("office", "meta"))
        update_meta_for_edit(root, NS, q)
        meta = root.find(q("office", "meta"))
        assert meta is not None
        self.assertIsNotNone(meta.find(q("meta", "modification-date")).text)
        self.assertEqual(
            meta.find(q("meta", "generator")).text,
            f"open-document-skills/{VERSION}",
        )
        self.assertEqual(meta.find(q("meta", "editing-cycles")).text, "1")

    def test_update_meta_increments_existing_cycles(self) -> None:
        root = ET.Element(q("office", "document-meta"))
        meta = ET.SubElement(root, q("office", "meta"))
        cycles = ET.SubElement(meta, q("meta", "editing-cycles"))
        cycles.text = "5"
        update_meta_for_edit(root, NS, q)
        self.assertEqual(meta.find(q("meta", "editing-cycles")).text, "6")

    def test_update_meta_unparseable_cycles_resets_to_one(self) -> None:
        root = ET.Element(q("office", "document-meta"))
        meta = ET.SubElement(root, q("office", "meta"))
        cycles = ET.SubElement(meta, q("meta", "editing-cycles"))
        cycles.text = "not-a-number"
        update_meta_for_edit(root, NS, q)
        self.assertEqual(meta.find(q("meta", "editing-cycles")).text, "1")

    def test_update_meta_raises_without_meta_element(self) -> None:
        root = ET.Element("garbage")
        with self.assertRaises(SystemExit):
            update_meta_for_edit(root, NS, q)

    def test_find_soffice_not_found(self) -> None:
        with (
            unittest.mock.patch("lib.odf_common.shutil.which", return_value=None),
            unittest.mock.patch.object(Path, "exists", return_value=False),
        ):
            with self.assertRaises(SystemExit):
                find_soffice()


if __name__ == "__main__":
    unittest.main()
