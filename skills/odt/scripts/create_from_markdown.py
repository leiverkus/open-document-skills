#!/usr/bin/env python3
"""Create an ODT file from a Markdown document.

A first-class Markdown authoring path: an agent writes rich prose
(headings, bold/italic, links, nested lists, tables, footnotes) and gets a
styled ODT without hand-assembling a block-level JSON spec. The Markdown
parser (md_parser.py) is standard-library only.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import md_parser as md
from create_minimal_odt import build_manifest, build_meta, build_settings
from odt_common import ODT_MIMETYPE, media_type_for, pack_dir_as_odt, q, unique_picture_name

MAX_IMAGE_WIDTH_CM = 15.0
DEFAULT_IMAGE = (12.0, 9.0)
INLINE_IMAGE = (1.2, 1.2)


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------


def _paragraph_style(styles: ET.Element, name: str, props: dict[str, str], text: dict[str, str]) -> None:
    style = ET.SubElement(styles, q("style", "style"), {q("style", "name"): name, q("style", "family"): "paragraph"})
    if props:
        ET.SubElement(style, q("style", "paragraph-properties"), props)
    if text:
        ET.SubElement(style, q("style", "text-properties"), text)


def _text_style(styles: ET.Element, name: str, text: dict[str, str]) -> None:
    style = ET.SubElement(styles, q("style", "style"), {q("style", "name"): name, q("style", "family"): "text"})
    ET.SubElement(style, q("style", "text-properties"), text)


def _list_style(styles: ET.Element, name: str, numbered: bool) -> None:
    """Append a three-level bullet or numbered list style."""
    ls = ET.SubElement(styles, q("text", "list-style"), {q("style", "name"): name})
    for level in (1, 2, 3):
        if numbered:
            lvl = ET.SubElement(
                ls,
                q("text", "list-level-style-number"),
                {
                    q("text", "level"): str(level),
                    q("style", "num-format"): "1",
                    q("style", "num-suffix"): ".",
                },
            )
        else:
            lvl = ET.SubElement(
                ls,
                q("text", "list-level-style-bullet"),
                {q("text", "level"): str(level), q("text", "bullet-char"): "•"},
            )
        ET.SubElement(
            lvl,
            q("style", "list-level-properties"),
            {
                q("text", "space-before"): f"{0.6 * level}cm",
                q("text", "min-label-width"): "0.6cm",
            },
        )


def build_styles() -> ET.Element:
    """Build office:document-styles with the Markdown authoring theme."""
    root = ET.Element(q("office", "document-styles"), {q("office", "version"): "1.3"})

    faces = ET.SubElement(root, q("office", "font-face-decls"))
    ET.SubElement(
        faces,
        q("style", "font-face"),
        {q("style", "name"): "Mono", q("svg", "font-family"): "'Liberation Mono', monospace"},
    )

    styles = ET.SubElement(root, q("office", "styles"))
    _paragraph_style(styles, "Body", {q("fo", "margin-bottom"): "0.25cm"}, {q("fo", "font-size"): "11pt"})
    headings = [
        ("Heading1", "20pt", "bold", "normal"),
        ("Heading2", "16pt", "bold", "normal"),
        ("Heading3", "13pt", "bold", "normal"),
        ("Heading4", "11pt", "bold", "normal"),
        ("Heading5", "11pt", "bold", "italic"),
        ("Heading6", "10pt", "bold", "normal"),
    ]
    for name, size, weight, slant in headings:
        _paragraph_style(
            styles,
            name,
            {q("fo", "margin-top"): "0.4cm", q("fo", "margin-bottom"): "0.2cm", q("fo", "keep-with-next"): "always"},
            {q("fo", "font-size"): size, q("fo", "font-weight"): weight, q("fo", "font-style"): slant},
        )
    _paragraph_style(
        styles,
        "Quote",
        {q("fo", "margin-left"): "1cm", q("fo", "margin-bottom"): "0.25cm"},
        {q("fo", "font-style"): "italic"},
    )
    _paragraph_style(
        styles,
        "CodeBlock",
        {q("fo", "background-color"): "#F2F2F2", q("fo", "margin-bottom"): "0cm"},
        {q("style", "font-name"): "Mono", q("fo", "font-size"): "10pt"},
    )
    _paragraph_style(
        styles,
        "HorizontalLine",
        {
            q("fo", "border-bottom"): "0.5pt solid #999999",
            q("fo", "margin-top"): "0.2cm",
            q("fo", "margin-bottom"): "0.2cm",
        },
        {},
    )
    _paragraph_style(styles, "TableHeader", {}, {q("fo", "font-weight"): "bold"})
    _paragraph_style(styles, "CellCenter", {q("fo", "text-align"): "center"}, {})
    _paragraph_style(styles, "CellRight", {q("fo", "text-align"): "end"}, {})

    _text_style(styles, "Strong", {q("fo", "font-weight"): "bold"})
    _text_style(styles, "Emphasis", {q("fo", "font-style"): "italic"})
    _text_style(styles, "StrongEmphasis", {q("fo", "font-weight"): "bold", q("fo", "font-style"): "italic"})
    _text_style(styles, "Code", {q("style", "font-name"): "Mono", q("fo", "background-color"): "#F2F2F2"})

    _list_style(styles, "ListBullet", numbered=False)
    _list_style(styles, "ListNumber", numbered=True)

    automatic = ET.SubElement(root, q("office", "automatic-styles"))
    layout = ET.SubElement(automatic, q("style", "page-layout"), {q("style", "name"): "A4"})
    ET.SubElement(
        layout,
        q("style", "page-layout-properties"),
        {q("fo", "page-width"): "21cm", q("fo", "page-height"): "29.7cm", q("fo", "margin"): "2cm"},
    )
    masters = ET.SubElement(root, q("office", "master-styles"))
    ET.SubElement(
        masters, q("style", "master-page"), {q("style", "name"): "Standard", q("style", "page-layout-name"): "A4"}
    )
    return root


# --------------------------------------------------------------------------
# Image dimensions
# --------------------------------------------------------------------------


def _image_dimensions(path: Path) -> tuple[float, float]:
    """Return (width_cm, height_cm) for a PNG/GIF/JPEG, scaled to fit the page."""
    px = _image_pixels(path)
    if px is None:
        return DEFAULT_IMAGE
    width_px, height_px = px
    if width_px <= 0 or height_px <= 0:
        return DEFAULT_IMAGE
    width_cm = width_px / 96 * 2.54
    height_cm = height_px / 96 * 2.54
    if width_cm > MAX_IMAGE_WIDTH_CM:
        scale = MAX_IMAGE_WIDTH_CM / width_cm
        width_cm, height_cm = width_cm * scale, height_cm * scale
    return round(width_cm, 2), round(height_cm, 2)


def _image_pixels(path: Path) -> tuple[int, int] | None:
    """Read pixel dimensions from a PNG, GIF, or JPEG header. None if unknown."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    if data[:2] == b"\xff\xd8":  # JPEG
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return w, h
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", data[i + 2 : i + 4])[0]
            i += 2 + seg
    return None


# --------------------------------------------------------------------------
# Emitter
# --------------------------------------------------------------------------


class Emitter:
    """Walks a parsed Markdown Document and builds ODT content.xml."""

    def __init__(self, document: md.Document, root_dir: Path, manifest_entries: list[tuple[str, str]]) -> None:
        self.doc = document
        self.root_dir = root_dir
        self.manifest_entries = manifest_entries
        self.existing_media: set[str] = set()
        self.footnote_counter = 0

    # -- blocks -----------------------------------------------------------

    def emit_blocks(self, parent: ET.Element, blocks: list[md.Block], para_style: str = "Body") -> None:
        for block in blocks:
            self.emit_block(parent, block, para_style)

    def emit_block(self, parent: ET.Element, block: md.Block, para_style: str) -> None:
        if isinstance(block, md.Heading):
            heading = ET.SubElement(
                parent,
                q("text", "h"),
                {q("text", "outline-level"): str(block.level), q("text", "style-name"): f"Heading{block.level}"},
            )
            self.emit_inline(heading, block.children)
        elif isinstance(block, md.Paragraph):
            self.emit_paragraph(parent, block.children, para_style)
        elif isinstance(block, md.BlockQuote):
            self.emit_blocks(parent, block.children, "Quote")
        elif isinstance(block, md.CodeBlock):
            self.emit_code_block(parent, block)
        elif isinstance(block, md.ThematicBreak):
            ET.SubElement(parent, q("text", "p"), {q("text", "style-name"): "HorizontalLine"})
        elif isinstance(block, md.ListNode):
            self.emit_list(parent, block)
        elif isinstance(block, md.Table):
            self.emit_table(parent, block)
        elif isinstance(block, md.BlockImage):
            self.emit_block_image(parent, block)

    def emit_paragraph(self, parent: ET.Element, nodes: list[md.Inline], style: str) -> ET.Element:
        paragraph = ET.SubElement(parent, q("text", "p"), {q("text", "style-name"): style})
        self.emit_inline(paragraph, nodes)
        return paragraph

    def emit_code_block(self, parent: ET.Element, block: md.CodeBlock) -> None:
        for line in block.text.split("\n"):
            paragraph = ET.SubElement(parent, q("text", "p"), {q("text", "style-name"): "CodeBlock"})
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if indent:
                ET.SubElement(paragraph, q("text", "s"), {q("text", "c"): str(indent)})
                last = paragraph[-1]
                last.tail = stripped
            else:
                paragraph.text = line

    def emit_list(self, parent: ET.Element, node: md.ListNode) -> None:
        style = "ListNumber" if node.ordered else "ListBullet"
        list_el = ET.SubElement(parent, q("text", "list"), {q("text", "style-name"): style})
        for index, item in enumerate(node.items):
            item_el = ET.SubElement(list_el, q("text", "list-item"))
            if index == 0 and node.ordered and node.start != 1:
                item_el.set(q("text", "start-value"), str(node.start))
            if not item.children:
                ET.SubElement(item_el, q("text", "p"), {q("text", "style-name"): "Body"})
            else:
                self.emit_blocks(item_el, item.children)

    def emit_table(self, parent: ET.Element, table: md.Table) -> None:
        table_el = ET.SubElement(parent, q("table", "table"), {q("table", "name"): "Table"})
        ncols = max(len(table.header), max((len(r) for r in table.rows), default=0))
        column = ET.SubElement(table_el, q("table", "table-column"))
        if ncols > 1:
            column.set(q("table", "number-columns-repeated"), str(ncols))
        self._emit_table_row(table_el, table.header, table.alignments, header=True, ncols=ncols)
        for row in table.rows:
            self._emit_table_row(table_el, row, table.alignments, header=False, ncols=ncols)

    def _emit_table_row(
        self,
        table_el: ET.Element,
        cells: list[md.TableCell],
        alignments: list[str],
        header: bool,
        ncols: int,
    ) -> None:
        row_el = ET.SubElement(table_el, q("table", "table-row"))
        for col in range(ncols):
            cell_el = ET.SubElement(row_el, q("table", "table-cell"), {q("office", "value-type"): "string"})
            align = alignments[col] if col < len(alignments) else "default"
            if header:
                style = "TableHeader"
            elif align == "center":
                style = "CellCenter"
            elif align == "right":
                style = "CellRight"
            else:
                style = "Body"
            cell = cells[col] if col < len(cells) else md.TableCell([])
            self.emit_paragraph(cell_el, cell.children, style)

    def emit_block_image(self, parent: ET.Element, block: md.BlockImage) -> None:
        paragraph = ET.SubElement(parent, q("text", "p"), {q("text", "style-name"): "Body"})
        self._image_frame(paragraph, block.src, block.alt, anchor="paragraph")

    # -- inline -----------------------------------------------------------

    def emit_inline(self, parent: ET.Element, nodes: list[md.Inline]) -> None:
        last: ET.Element | None = None
        for node in nodes:
            if isinstance(node, md.Text):
                self._append_text(parent, last, node.value)
            elif isinstance(node, md.LineBreak):
                last = ET.SubElement(parent, q("text", "line-break"))
            elif isinstance(node, md.Code):
                span = ET.SubElement(parent, q("text", "span"), {q("text", "style-name"): "Code"})
                span.text = node.value
                last = span
            elif isinstance(node, md.Strong):
                last = self._emit_styled_span(parent, node.children, "Strong", inner_emphasis=True)
            elif isinstance(node, md.Emphasis):
                last = self._emit_styled_span(parent, node.children, "Emphasis", inner_emphasis=False)
            elif isinstance(node, md.Link):
                anchor = ET.SubElement(
                    parent,
                    q("text", "a"),
                    {q("xlink", "href"): node.href, q("xlink", "type"): "simple"},
                )
                self.emit_inline(anchor, node.children)
                last = anchor
            elif isinstance(node, md.InlineImage):
                last = self._image_frame(parent, node.src, node.alt, anchor="as-char")
            elif isinstance(node, md.FootnoteRef):
                last = self._emit_footnote(parent, node.identifier)

    def _emit_styled_span(
        self, parent: ET.Element, children: list[md.Inline], style: str, inner_emphasis: bool
    ) -> ET.Element:
        # Collapse Strong(Emphasis(...)) into a single StrongEmphasis span.
        if inner_emphasis and len(children) == 1 and isinstance(children[0], md.Emphasis):
            span = ET.SubElement(parent, q("text", "span"), {q("text", "style-name"): "StrongEmphasis"})
            self.emit_inline(span, children[0].children)
            return span
        span = ET.SubElement(parent, q("text", "span"), {q("text", "style-name"): style})
        self.emit_inline(span, children)
        return span

    @staticmethod
    def _append_text(parent: ET.Element, last: ET.Element | None, value: str) -> None:
        if last is None:
            parent.text = (parent.text or "") + value
        else:
            last.tail = (last.tail or "") + value

    def _emit_footnote(self, parent: ET.Element, identifier: str) -> ET.Element:
        definition = self.doc.footnotes.get(identifier)
        if definition is None:
            # No definition — leave a literal marker rather than dropping it.
            marker = ET.SubElement(parent, q("text", "span"))
            marker.text = f"[^{identifier}]"
            return marker
        self.footnote_counter += 1
        note = ET.SubElement(
            parent,
            q("text", "note"),
            {q("text", "note-class"): "footnote", q("text", "id"): f"ftn{self.footnote_counter}"},
        )
        citation = ET.SubElement(note, q("text", "note-citation"))
        citation.text = str(self.footnote_counter)
        body = ET.SubElement(note, q("text", "note-body"))
        if definition.children:
            self.emit_blocks(body, definition.children)
        else:
            ET.SubElement(body, q("text", "p"), {q("text", "style-name"): "Body"})
        return note

    def _image_frame(self, parent: ET.Element, src: str, alt: str, anchor: str) -> ET.Element:
        href = self._resolve_image(src)
        default = INLINE_IMAGE if anchor == "as-char" else DEFAULT_IMAGE
        width, height = default
        local = not src.lower().startswith(("http://", "https://"))
        if local and href is not None:
            dims = _image_dimensions(self.root_dir / href)
            if anchor != "as-char":
                width, height = dims
        if href is None:
            # Missing local file — emit the alt text so nothing is silently lost.
            span = ET.SubElement(parent, q("text", "span"))
            span.text = alt or "[image]"
            return span
        frame = ET.SubElement(
            parent,
            q("draw", "frame"),
            {
                q("text", "anchor-type"): anchor,
                q("svg", "width"): f"{width}cm",
                q("svg", "height"): f"{height}cm",
            },
        )
        if alt:
            frame.set(q("draw", "name"), alt)
        ET.SubElement(
            frame,
            q("draw", "image"),
            {
                q("xlink", "href"): href,
                q("xlink", "type"): "simple",
                q("xlink", "show"): "embed",
                q("xlink", "actuate"): "onLoad",
            },
        )
        if alt:
            title = ET.SubElement(frame, q("svg", "title"))
            title.text = alt
        return frame

    def _resolve_image(self, src: str) -> str | None:
        """Return the href for an image: a Pictures/ path (embedded) or the URL."""
        if src.lower().startswith(("http://", "https://")):
            return src
        source = Path(src)
        if not source.is_file():
            print(f"warning: image not found, skipping: {src}", file=sys.stderr)
            return None
        package_path = unique_picture_name(self.existing_media, source)
        self.existing_media.add(package_path)
        target = self.root_dir / package_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        self.manifest_entries.append((package_path, media_type_for(source)))
        return package_path


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _document_title(document: md.Document, override: str | None) -> str | None:
    if override:
        return override
    for block in document.children:
        if isinstance(block, md.Heading) and block.level == 1:
            return "".join(_plain_text(block.children)).strip() or None
    return None


def _plain_text(nodes: list[md.Inline]) -> list[str]:
    out: list[str] = []
    for node in nodes:
        if isinstance(node, md.Text):
            out.append(node.value)
        elif isinstance(node, md.Code):
            out.append(node.value)
        elif isinstance(node, (md.Strong, md.Emphasis, md.Link)):
            out.extend(_plain_text(node.children))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_md", type=Path, help="Markdown source file")
    parser.add_argument("output_odt", type=Path)
    parser.add_argument("--title", help="document title (default: first H1)")
    args = parser.parse_args()

    if not args.input_md.exists():
        raise SystemExit(f"Markdown file not found: {args.input_md}")
    document = md.parse(args.input_md.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        (root_dir / "META-INF").mkdir()
        (root_dir / "Pictures").mkdir()
        (root_dir / "mimetype").write_text(ODT_MIMETYPE)
        manifest_entries = [
            ("content.xml", "text/xml"),
            ("styles.xml", "text/xml"),
            ("meta.xml", "text/xml"),
            ("settings.xml", "text/xml"),
        ]

        content = ET.Element(q("office", "document-content"), {q("office", "version"): "1.3"})
        body = ET.SubElement(content, q("office", "body"))
        text = ET.SubElement(body, q("office", "text"))
        emitter = Emitter(document, root_dir, manifest_entries)
        emitter.emit_blocks(text, document.children)

        title = _document_title(document, args.title)
        ET.ElementTree(content).write(root_dir / "content.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_styles()).write(root_dir / "styles.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_meta(title)).write(root_dir / "meta.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_settings()).write(root_dir / "settings.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_manifest(manifest_entries)).write(
            root_dir / "META-INF" / "manifest.xml", encoding="utf-8", xml_declaration=True
        )
        pack_dir_as_odt(root_dir, args.output_odt)
    print(args.output_odt)


if __name__ == "__main__":
    main()
