"""Direct unit tests for odf_lib.odf_common functions.

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

from odf_lib.odf_common import (
    VERSION,
    clear_children,
    copy_into_package,
    copy_with_multiple_members,
    ensure_manifest_entry,
    ensure_sequence_declarations,
    find_soffice,
    find_text_position_in_element,
    insert_after_text_in_element,
    insert_in_paragraph,
    local_name,
    media_type_for,
    pack_dir_as_odf,
    parse_xml_from_zip,
    replace_text_in_element,
    sniff_image_mime,
    unique_object_name,
    unique_picture_name,
    unpack_to_temp,
    update_meta_for_edit,
    wrap_text_across_elements,
    wrap_text_with_pair_in_element,
    write_odf_with_replacements,
    xml_bytes,
)

NS = {
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
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
        with unittest.mock.patch("odf_lib.odf_common.shutil.which", return_value="/usr/bin/soffice"):
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

    def test_wrap_text_with_pair_simple(self) -> None:
        p = ET.fromstring("<p>before START middle END after</p>")
        start = ET.Element("bms")
        end = ET.Element("bme")
        ok = wrap_text_with_pair_in_element(p, "START", "END", start, end)
        self.assertTrue(ok)
        children = list(p)
        self.assertEqual([c.tag for c in children], ["bms", "bme"])
        # bms.tail must contain " middle " (between start and end)
        self.assertIn("middle", children[0].tail)
        self.assertIn("after", children[1].tail)

    def test_wrap_text_with_pair_no_start_anchor(self) -> None:
        p = ET.fromstring("<p>Hello world</p>")
        ok = wrap_text_with_pair_in_element(p, "nope", "world", ET.Element("a"), ET.Element("b"))
        self.assertFalse(ok)
        self.assertEqual(len(list(p)), 0)

    def test_wrap_text_with_pair_no_end_anchor(self) -> None:
        p = ET.fromstring("<p>Hello world</p>")
        ok = wrap_text_with_pair_in_element(p, "Hello", "missing", ET.Element("a"), ET.Element("b"))
        self.assertFalse(ok)
        self.assertEqual(len(list(p)), 0)

    def test_wrap_text_with_pair_end_before_start_fails(self) -> None:
        p = ET.fromstring("<p>END marker then START marker</p>")
        # 'START' appears AFTER 'END' in the text — wrap_text_with_pair will
        # find 'END' first looking AFTER start_idx, so it actually depends on
        # implementation. Our impl uses combined.find(end_anchor, start_idx+len(start_anchor)).
        # Here START is at position 17, END is at 0 → find END after position 22 fails → returns False.
        ok = wrap_text_with_pair_in_element(p, "START", "END", ET.Element("a"), ET.Element("b"))
        self.assertFalse(ok)

    def test_wrap_across_elements_same_paragraph(self) -> None:
        p = ET.fromstring("<p>x START middle END y</p>")
        start = ET.Element("s")
        end = ET.Element("e")
        ok = wrap_text_across_elements([p], "START", "END", start, end)
        self.assertTrue(ok)
        self.assertEqual([c.tag for c in p], ["s", "e"])

    def test_wrap_across_elements_cross_paragraph(self) -> None:
        p1 = ET.fromstring("<p>first START here</p>")
        p2 = ET.fromstring("<p>middle paragraph</p>")
        p3 = ET.fromstring("<p>third END text</p>")
        start = ET.Element("s")
        end = ET.Element("e")
        ok = wrap_text_across_elements([p1, p2, p3], "START", "END", start, end)
        self.assertTrue(ok)
        # start_element is in p1; end_element is in p3
        self.assertEqual(list(p1)[0].tag, "s")
        self.assertEqual(len(list(p2)), 0)
        self.assertEqual(list(p3)[0].tag, "e")

    def test_wrap_across_elements_no_start(self) -> None:
        p1 = ET.fromstring("<p>nothing here</p>")
        p2 = ET.fromstring("<p>END only</p>")
        ok = wrap_text_across_elements([p1, p2], "START", "END", ET.Element("s"), ET.Element("e"))
        self.assertFalse(ok)
        self.assertEqual(len(list(p1)), 0)
        self.assertEqual(len(list(p2)), 0)

    def test_wrap_across_elements_no_end(self) -> None:
        p1 = ET.fromstring("<p>START in p1</p>")
        p2 = ET.fromstring("<p>nothing in p2</p>")
        ok = wrap_text_across_elements([p1, p2], "START", "END", ET.Element("s"), ET.Element("e"))
        self.assertFalse(ok)
        self.assertEqual(len(list(p1)), 0)
        self.assertEqual(len(list(p2)), 0)

    def test_ensure_sequence_declarations_creates_block(self) -> None:
        text = ET.Element(f"{{{NS['office']}}}text")
        ET.SubElement(text, f"{{{NS['text']}}}p")
        ensure_sequence_declarations(text, ["Figure", "Table"], NS)
        decls = text.find(f"{{{NS['text']}}}sequence-decls")
        assert decls is not None
        names = {d.attrib.get(f"{{{NS['text']}}}name") for d in decls.findall(f"{{{NS['text']}}}sequence-decl")}
        self.assertEqual(names, {"Figure", "Table"})
        # The decls block must be the FIRST child of office:text
        self.assertIs(list(text)[0], decls)

    def test_ensure_sequence_declarations_idempotent(self) -> None:
        text = ET.Element(f"{{{NS['office']}}}text")
        ensure_sequence_declarations(text, ["Figure"], NS)
        ensure_sequence_declarations(text, ["Figure", "Table"], NS)
        decls = text.find(f"{{{NS['text']}}}sequence-decls")
        assert decls is not None
        names = {d.attrib.get(f"{{{NS['text']}}}name") for d in decls.findall(f"{{{NS['text']}}}sequence-decl")}
        self.assertEqual(names, {"Figure", "Table"})

    def test_unique_object_name_first(self) -> None:
        self.assertEqual(unique_object_name(set()), "Object 1")

    def test_unique_object_name_collision(self) -> None:
        existing = {"Object 1/", "Object 1/content.xml", "Object 2/content.xml"}
        self.assertEqual(unique_object_name(existing), "Object 3")

    def test_copy_with_multiple_members(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = _make_minimal_odf(Path(tmp), "src.odf")
            dst = Path(tmp) / "dst.odf"
            copy_with_multiple_members(
                src,
                dst,
                new_members={
                    "Object 1/content.xml": b"<math:math xmlns:math='http://www.w3.org/1998/Math/MathML'/>",
                    "Object 1/styles.xml": b"<styles/>",
                },
                replacements={"content.xml": b"<root/>"},
                mimetype_value="application/vnd.oasis.opendocument.text",
            )
            with zipfile.ZipFile(dst) as archive:
                names = archive.namelist()
                self.assertIn("Object 1/content.xml", names)
                self.assertIn("Object 1/styles.xml", names)
                self.assertEqual(archive.read("content.xml"), b"<root/>")
                self.assertEqual(names[0], "mimetype")

    def test_sniff_image_mime_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "fake.unknown"
            png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            self.assertEqual(sniff_image_mime(png), "image/png")

    def test_sniff_image_mime_jpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jpg = Path(tmp) / "fake.png"
            jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            self.assertEqual(sniff_image_mime(jpg), "image/jpeg")

    def test_sniff_image_mime_gif(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gif = Path(tmp) / "fake.jpg"
            gif.write_bytes(b"GIF89a" + b"\x00" * 100)
            self.assertEqual(sniff_image_mime(gif), "image/gif")

    def test_sniff_image_mime_webp_requires_webp_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # RIFF without WEBP marker → should fall back to extension
            non_webp = Path(tmp) / "ambiguous.wav"
            non_webp.write_bytes(b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 100)
            # Should fall back to media_type_for; .wav → audio/wav (or octet-stream)
            self.assertNotEqual(sniff_image_mime(non_webp), "image/webp")
            # Real WebP:
            webp = Path(tmp) / "image.unknown"
            webp.write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100)
            self.assertEqual(sniff_image_mime(webp), "image/webp")

    def test_sniff_image_mime_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "noext"
            svg.write_bytes(b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"></svg>')
            self.assertEqual(sniff_image_mime(svg), "image/svg+xml")
            # XML without SVG → falls back
            xml = Path(tmp) / "ambiguous.xml"
            xml.write_bytes(b'<?xml version="1.0"?>\n<other/>')
            self.assertNotEqual(sniff_image_mime(xml), "image/svg+xml")

    def test_sniff_image_mime_falls_back_for_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            blob = Path(tmp) / "data.png"
            blob.write_bytes(b"\x00\x01\x02\x03" + b"random")
            # Magic doesn't match → falls back to extension → image/png
            self.assertEqual(sniff_image_mime(blob), "image/png")

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
            unittest.mock.patch("odf_lib.odf_common.shutil.which", return_value=None),
            unittest.mock.patch.object(Path, "exists", return_value=False),
        ):
            with self.assertRaises(SystemExit):
                find_soffice()


if __name__ == "__main__":
    unittest.main()
