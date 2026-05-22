"""Tests for the Markdown → ODT authoring path — the stdlib parser and the
inline rich-text emitter (text:span, text:a, footnotes, tables, images)."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

ODT_SCRIPTS = SKILLS / "odt" / "scripts"
sys.path.insert(0, str(ODT_SCRIPTS))

import md_parser as md  # noqa: E402

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def member(path: Path, name: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read(name))


# --------------------------------------------------------------------------
# Parser unit tests
# --------------------------------------------------------------------------


class ParserBlockTests(unittest.TestCase):
    def test_headings_all_levels(self) -> None:
        doc = md.parse("\n\n".join(f"{'#' * n} Level {n}" for n in range(1, 7)))
        self.assertEqual([type(b).__name__ for b in doc.children], ["Heading"] * 6)
        self.assertEqual([b.level for b in doc.children], [1, 2, 3, 4, 5, 6])

    def test_nested_bullet_list(self) -> None:
        doc = md.parse("- a\n- b\n  - b1\n  - b2\n- c")
        lst = doc.children[0]
        self.assertIsInstance(lst, md.ListNode)
        self.assertFalse(lst.ordered)
        self.assertEqual(len(lst.items), 3)
        nested = [b for b in lst.items[1].children if isinstance(b, md.ListNode)]
        self.assertEqual(len(nested), 1)
        self.assertEqual(len(nested[0].items), 2)

    def test_ordered_list_start(self) -> None:
        doc = md.parse("3. three\n4. four")
        lst = doc.children[0]
        self.assertIsInstance(lst, md.ListNode)
        self.assertTrue(lst.ordered)
        self.assertEqual(lst.start, 3)

    def test_fenced_code_block(self) -> None:
        doc = md.parse("```python\nx = 1\ny = 2\n```")
        block = doc.children[0]
        self.assertIsInstance(block, md.CodeBlock)
        self.assertEqual(block.language, "python")
        self.assertEqual(block.text, "x = 1\ny = 2")

    def test_blockquote(self) -> None:
        doc = md.parse("> quoted line one\n> quoted line two")
        quote = doc.children[0]
        self.assertIsInstance(quote, md.BlockQuote)
        self.assertIsInstance(quote.children[0], md.Paragraph)

    def test_thematic_break(self) -> None:
        doc = md.parse("text\n\n---\n\nmore")
        self.assertIsInstance(doc.children[1], md.ThematicBreak)

    def test_gfm_table_with_alignment(self) -> None:
        doc = md.parse("| A | B | C |\n|:--|:-:|--:|\n| 1 | 2 | 3 |")
        table = doc.children[0]
        self.assertIsInstance(table, md.Table)
        self.assertEqual(table.alignments, ["left", "center", "right"])
        self.assertEqual(len(table.header), 3)
        self.assertEqual(len(table.rows), 1)

    def test_block_image(self) -> None:
        doc = md.parse("![alt text](pic.png)")
        image = doc.children[0]
        self.assertIsInstance(image, md.BlockImage)
        self.assertEqual(image.src, "pic.png")


class ParserInlineTests(unittest.TestCase):
    def _inline(self, text: str) -> list[md.Inline]:
        doc = md.parse(text)
        para = doc.children[0]
        assert isinstance(para, md.Paragraph)
        return para.children

    def test_bold_italic_code(self) -> None:
        nodes = self._inline("a **bold** and *italic* and `code` end")
        kinds = [type(n).__name__ for n in nodes]
        self.assertIn("Strong", kinds)
        self.assertIn("Emphasis", kinds)
        self.assertIn("Code", kinds)

    def test_bold_italic_combined(self) -> None:
        nodes = self._inline("***both***")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], md.Strong)
        self.assertIsInstance(nodes[0].children[0], md.Emphasis)

    def test_inline_link(self) -> None:
        nodes = self._inline("see [the docs](https://example.org) now")
        link = next(n for n in nodes if isinstance(n, md.Link))
        self.assertEqual(link.href, "https://example.org")

    def test_reference_link(self) -> None:
        nodes = self._inline("see [the docs][ref] now\n\n[ref]: https://ref.example")
        link = next(n for n in nodes if isinstance(n, md.Link))
        self.assertEqual(link.href, "https://ref.example")

    def test_footnote_ref_and_def(self) -> None:
        doc = md.parse("text with a note.[^x]\n\n[^x]: the note body")
        para = doc.children[0]
        assert isinstance(para, md.Paragraph)
        self.assertTrue(any(isinstance(n, md.FootnoteRef) for n in para.children))
        self.assertIn("x", doc.footnotes)

    def test_underscore_in_word_is_literal(self) -> None:
        nodes = self._inline("a snake_case_name here")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], md.Text)

    def test_backslash_escape(self) -> None:
        nodes = self._inline(r"not \*emphasised\* here")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], md.Text)
        self.assertEqual(nodes[0].value, "not *emphasised* here")


# --------------------------------------------------------------------------
# End-to-end MD → ODT
# --------------------------------------------------------------------------

SAMPLE_MD = """# Report Title

A paragraph with **bold**, *italic*, `code`, and a [link](https://example.org).
A footnote follows.[^a]

## Section Two

- one
- two
  - nested

1. first
2. second

> a quoted line

```python
print("hi")
```

| Name | Score |
|:-----|------:|
| Alice | 42 |

---

Done.

[^a]: The footnote text.
"""


class EndToEndTests(unittest.TestCase):
    def _build(self, tmp: Path, markdown: str = SAMPLE_MD) -> Path:
        src = tmp / "doc.md"
        src.write_text(markdown, encoding="utf-8")
        odt = tmp / "doc.odt"
        run_script(ODT_SCRIPTS / "create_from_markdown.py", src, odt)
        return odt

    def test_inline_runs_become_spans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(self._build(Path(tmp)), "content.xml")
            spans = list(content.iter(q("text", "span")))
            styles = {s.attrib.get(q("text", "style-name")) for s in spans}
            self.assertIn("Strong", styles)
            self.assertIn("Emphasis", styles)
            self.assertIn("Code", styles)

    def test_link_becomes_text_a(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(self._build(Path(tmp)), "content.xml")
            anchor = next(content.iter(q("text", "a")))
            self.assertEqual(anchor.attrib.get(q("xlink", "href")), "https://example.org")

    def test_headings_carry_outline_levels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(self._build(Path(tmp)), "content.xml")
            levels = sorted({h.attrib.get(q("text", "outline-level")) for h in content.iter(q("text", "h"))})
            self.assertEqual(levels, ["1", "2"])

    def test_lists_and_table_and_footnote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(self._build(Path(tmp)), "content.xml")
            self.assertGreaterEqual(len(list(content.iter(q("text", "list")))), 2)
            self.assertEqual(len(list(content.iter(q("table", "table")))), 1)
            notes = list(content.iter(q("text", "note")))
            self.assertEqual(len(notes), 1)
            self.assertTrue(notes[0].attrib.get(q("text", "id")))

    def test_code_block_uses_codeblock_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(self._build(Path(tmp)), "content.xml")
            code_paras = [
                p for p in content.iter(q("text", "p")) if p.attrib.get(q("text", "style-name")) == "CodeBlock"
            ]
            self.assertGreater(len(code_paras), 0)

    def test_title_from_first_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            meta = member(self._build(Path(tmp)), "meta.xml")
            titles = [t.text for t in meta.iter("{http://purl.org/dc/elements/1.1/}title")]
            self.assertEqual(titles, ["Report Title"])

    def test_embedded_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            png = tmp_path / "p.png"
            png.write_bytes(
                bytes.fromhex(
                    "89504e470d0a1a0a0000000d49484452000000040000000408060000"
                    "00b6f8b4570000000a49444154789c63600000000200013fd7e2d6"
                    "0000000049454e44ae426082"
                )
            )
            odt = self._build(tmp_path, f"# Pic\n\n![logo]({png})\n")
            with zipfile.ZipFile(odt) as archive:
                pictures = [n for n in archive.namelist() if n.startswith("Pictures/")]
            self.assertEqual(len(pictures), 1)
            content = member(odt, "content.xml")
            self.assertEqual(len(list(content.iter(q("draw", "image")))), 1)

    def test_output_passes_strict_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odt = self._build(Path(tmp))
            result = run_script(ODT_SCRIPTS / "validate_refs.py", odt, "--strict", check=False)
            self.assertIn('"status": "ok"', result.stdout)


if __name__ == "__main__":
    unittest.main()
