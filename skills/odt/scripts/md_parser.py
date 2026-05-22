"""A small, dependency-free Markdown parser.

Parses a pragmatic CommonMark subset plus GFM tables and Markdown footnotes
into a typed AST. Standard library only — no external dependency, so the
Markdown → ODT path keeps the project's zero-install promise.

Supported: ATX headings, paragraphs, bullet/ordered lists (nested),
blockquotes, fenced code blocks, thematic breaks, GFM tables, block and
inline images, links (inline + reference), bold/italic/inline-code, hard
line breaks, backslash escapes, and footnotes (``[^id]`` + ``[^id]:`` defs).

Not supported (documented limits): indented code blocks, setext headings,
raw HTML, autolinks ``<url>``, and task-list checkboxes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# AST — inline nodes
# --------------------------------------------------------------------------


@dataclass
class Text:
    value: str


@dataclass
class Strong:
    children: list[Inline]


@dataclass
class Emphasis:
    children: list[Inline]


@dataclass
class Code:
    value: str


@dataclass
class Link:
    href: str
    title: str | None
    children: list[Inline]


@dataclass
class InlineImage:
    src: str
    alt: str


@dataclass
class LineBreak:
    pass


@dataclass
class FootnoteRef:
    identifier: str


Inline = Text | Strong | Emphasis | Code | Link | InlineImage | LineBreak | FootnoteRef


# --------------------------------------------------------------------------
# AST — block nodes
# --------------------------------------------------------------------------


@dataclass
class Heading:
    level: int
    children: list[Inline]


@dataclass
class Paragraph:
    children: list[Inline]


@dataclass
class CodeBlock:
    language: str | None
    text: str


@dataclass
class BlockQuote:
    children: list[Block]


@dataclass
class ListItem:
    children: list[Block]


@dataclass
class ListNode:
    ordered: bool
    start: int
    items: list[ListItem]


@dataclass
class ThematicBreak:
    pass


@dataclass
class TableCell:
    children: list[Inline]


@dataclass
class Table:
    alignments: list[str]  # "left" | "center" | "right" | "default"
    header: list[TableCell]
    rows: list[list[TableCell]]


@dataclass
class BlockImage:
    src: str
    alt: str


Block = Heading | Paragraph | CodeBlock | BlockQuote | ListNode | ThematicBreak | Table | BlockImage


@dataclass
class FootnoteDef:
    identifier: str
    children: list[Block]


@dataclass
class Document:
    children: list[Block]
    footnotes: dict[str, FootnoteDef] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^(```+|~~~+)\s*([^`]*)$")
_THEMATIC = re.compile(r"^ {0,3}([-*_])(?:\s*\1){2,}\s*$")
_LIST_MARKER = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(\s+)(.*)$")
_BLOCKQUOTE = re.compile(r"^ {0,3}>\s?(.*)$")
_LINK_REF_DEF = re.compile(r'^ {0,3}\[([^\]]+)\]:\s*(\S+?)(?:\s+"([^"]*)")?\s*$')
_FOOTNOTE_DEF = re.compile(r"^ {0,3}\[\^([^\]]+)\]:\s?(.*)$")
_TABLE_DELIM = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")
_ESCAPABLE = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def parse(markdown: str) -> Document:
    """Parse Markdown text into a Document AST."""
    raw_lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    link_refs, footnote_defs_text, lines = _prescan(raw_lines)
    children = _parse_blocks(lines, link_refs)
    footnotes: dict[str, FootnoteDef] = {}
    for identifier, def_lines in footnote_defs_text.items():
        footnotes[identifier] = FootnoteDef(identifier, _parse_blocks(def_lines, link_refs))
    return Document(children, footnotes)


# --------------------------------------------------------------------------
# Pass 1 — collect link-reference and footnote definitions
# --------------------------------------------------------------------------


def _prescan(lines: list[str]) -> tuple[dict[str, tuple[str, str | None]], dict[str, list[str]], list[str]]:
    """Pull out link-reference and footnote definitions; return the rest."""
    link_refs: dict[str, tuple[str, str | None]] = {}
    footnotes: dict[str, list[str]] = {}
    remaining: list[str] = []
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line.strip()) and not line.startswith("    "):
            in_fence = not in_fence
            remaining.append(line)
            i += 1
            continue
        if in_fence:
            remaining.append(line)
            i += 1
            continue
        fn = _FOOTNOTE_DEF.match(line)
        if fn:
            identifier = fn.group(1)
            body = [fn.group(2)]
            i += 1
            # Continuation lines: blank or indented by >= 4 spaces.
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith("    ")):
                body.append(lines[i][4:] if lines[i].startswith("    ") else "")
                i += 1
            while body and not body[-1].strip():
                body.pop()
            footnotes[identifier] = body
            continue
        ref = _LINK_REF_DEF.match(line)
        if ref and not line.lstrip().startswith("[^"):
            label = ref.group(1).strip().lower()
            link_refs[label] = (ref.group(2), ref.group(3))
            i += 1
            continue
        remaining.append(line)
        i += 1
    return link_refs, footnotes, remaining


# --------------------------------------------------------------------------
# Pass 2 — block parsing
# --------------------------------------------------------------------------


def _parse_blocks(lines: list[str], link_refs: dict[str, tuple[str, str | None]]) -> list[Block]:
    blocks: list[Block] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        heading = _HEADING.match(line)
        if heading:
            blocks.append(Heading(len(heading.group(1)), _parse_inline(heading.group(2), link_refs)))
            i += 1
            continue

        fence = _FENCE.match(line.strip())
        if fence and not line.startswith("    "):
            marker = fence.group(1)
            lang = fence.group(2).strip() or None
            body: list[str] = []
            i += 1
            while i < n and lines[i].strip()[: len(marker)] != marker:
                body.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            blocks.append(CodeBlock(lang, "\n".join(body)))
            continue

        if _THEMATIC.match(line):
            blocks.append(ThematicBreak())
            i += 1
            continue

        if _BLOCKQUOTE.match(line):
            quote_lines: list[str] = []
            while i < n and (_BLOCKQUOTE.match(lines[i]) or (lines[i].strip() and not _is_block_start(lines[i]))):
                m = _BLOCKQUOTE.match(lines[i])
                quote_lines.append(m.group(1) if m else lines[i].strip())
                i += 1
            blocks.append(BlockQuote(_parse_blocks(quote_lines, link_refs)))
            continue

        if _LIST_MARKER.match(line):
            node, i = _parse_list(lines, i, link_refs)
            blocks.append(node)
            continue

        if "|" in line and i + 1 < n and _TABLE_DELIM.match(lines[i + 1]):
            table, i = _parse_table(lines, i, link_refs)
            blocks.append(table)
            continue

        # Paragraph — gather until blank line or a new block starter.
        para: list[str] = [line]
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines[i]):
            if i + 1 < n and "|" in lines[i] and _TABLE_DELIM.match(lines[i + 1]):
                break
            para.append(lines[i])
            i += 1
        block_image = _as_block_image("\n".join(para))
        blocks.append(block_image if block_image else Paragraph(_parse_inline("\n".join(para), link_refs)))
    return blocks


def _is_block_start(line: str) -> bool:
    """Whether *line* begins a block that interrupts a paragraph."""
    stripped = line.strip()
    if not stripped:
        return True
    return bool(
        _HEADING.match(line)
        or _FENCE.match(stripped)
        or _THEMATIC.match(line)
        or _BLOCKQUOTE.match(line)
        or _LIST_MARKER.match(line)
    )


def _as_block_image(text: str) -> BlockImage | None:
    """Return a BlockImage if *text* is exactly one image, else None."""
    m = re.fullmatch(r"\s*!\[([^\]]*)\]\(\s*(\S+?)(?:\s+\"[^\"]*\")?\s*\)\s*", text)
    return BlockImage(m.group(2), m.group(1)) if m else None


def _parse_list(lines: list[str], start: int, link_refs: dict[str, tuple[str, str | None]]) -> tuple[ListNode, int]:
    """Parse a (possibly nested) list starting at *start*."""
    first = _LIST_MARKER.match(lines[start])
    assert first is not None
    base_indent = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    start_num = int(first.group(2)[:-1]) if ordered else 1
    items: list[ListItem] = []
    i = start
    n = len(lines)
    while i < n:
        marker = _LIST_MARKER.match(lines[i])
        if marker and len(marker.group(1)) == base_indent and (marker.group(2)[0].isdigit() == ordered):
            content_indent = len(marker.group(1)) + len(marker.group(2)) + len(marker.group(3))
            item_lines: list[str] = [marker.group(4)]
            i += 1
            while i < n:
                cur = lines[i]
                if not cur.strip():
                    item_lines.append("")
                    i += 1
                    continue
                indent = len(cur) - len(cur.lstrip())
                nxt = _LIST_MARKER.match(cur)
                if nxt and len(nxt.group(1)) == base_indent:
                    break  # next sibling item
                if indent >= content_indent or nxt:
                    item_lines.append(cur[content_indent:] if len(cur) >= content_indent else cur.lstrip())
                    i += 1
                    continue
                break
            while item_lines and not item_lines[-1].strip():
                item_lines.pop()
            items.append(ListItem(_parse_blocks(item_lines, link_refs)))
            continue
        if not lines[i].strip():
            i += 1
            continue
        break
    return ListNode(ordered, start_num, items), i


def _split_table_row(line: str) -> list[str]:
    """Split a GFM table row into trimmed cell strings."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    cells: list[str] = []
    buf: list[str] = []
    k = 0
    while k < len(s):
        ch = s[k]
        if ch == "\\" and k + 1 < len(s):
            buf.append(s[k : k + 2])
            k += 2
            continue
        if ch == "|":
            cells.append("".join(buf).strip())
            buf = []
            k += 1
            continue
        buf.append(ch)
        k += 1
    cells.append("".join(buf).strip())
    return cells


def _parse_table(lines: list[str], start: int, link_refs: dict[str, tuple[str, str | None]]) -> tuple[Table, int]:
    header = _split_table_row(lines[start])
    delim = _split_table_row(lines[start + 1])
    alignments: list[str] = []
    for spec in delim:
        left = spec.startswith(":")
        right = spec.endswith(":")
        alignments.append("center" if left and right else "right" if right else "left" if left else "default")
    i = start + 2
    rows: list[list[TableCell]] = []
    while i < len(lines) and "|" in lines[i] and lines[i].strip():
        cells = _split_table_row(lines[i])
        rows.append([TableCell(_parse_inline(c, link_refs)) for c in cells])
        i += 1
    return (
        Table(alignments, [TableCell(_parse_inline(c, link_refs)) for c in header], rows),
        i,
    )


# --------------------------------------------------------------------------
# Inline parsing
# --------------------------------------------------------------------------


def _parse_inline(text: str, link_refs: dict[str, tuple[str, str | None]]) -> list[Inline]:
    """Parse inline Markdown into a list of inline nodes."""
    nodes: list[Inline] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            nodes.append(Text("".join(buf)))
            buf.clear()

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        # Hard line break: two+ trailing spaces or a backslash before newline.
        if ch == "\n":
            if buf and buf[-1] == "\\":
                buf.pop()
                flush()
                nodes.append(LineBreak())
            elif len(buf) >= 2 and buf[-1] == " " and buf[-2] == " ":
                while buf and buf[-1] == " ":
                    buf.pop()
                flush()
                nodes.append(LineBreak())
            else:
                while buf and buf[-1] == " ":
                    buf.pop()
                buf.append(" ")
            i += 1
            continue

        if ch == "\\" and i + 1 < n and text[i + 1] in _ESCAPABLE:
            buf.append(text[i + 1])
            i += 2
            continue

        if ch == "`":
            span, end = _scan_code_span(text, i)
            if span is not None:
                flush()
                nodes.append(span)
                i = end
                continue

        if ch == "!" and i + 1 < n and text[i + 1] == "[":
            img, end = _scan_image(text, i, link_refs)
            if img is not None:
                flush()
                nodes.append(img)
                i = end
                continue

        if ch == "[":
            note = re.match(r"\[\^([^\]]+)\]", text[i:])
            if note:
                flush()
                nodes.append(FootnoteRef(note.group(1)))
                i += note.end()
                continue
            link, end = _scan_link(text, i, link_refs)
            if link is not None:
                flush()
                nodes.append(link)
                i = end
                continue

        if ch in "*_":
            emph, end = _scan_emphasis(text, i, link_refs)
            if emph is not None:
                flush()
                nodes.append(emph)
                i = end
                continue

        buf.append(ch)
        i += 1

    flush()
    return nodes


def _scan_code_span(text: str, i: int) -> tuple[Code | None, int]:
    """Scan a backtick code span starting at *i*."""
    n = len(text)
    j = i
    while j < n and text[j] == "`":
        j += 1
    ticks = j - i
    close = text.find("`" * ticks, j)
    while close != -1 and close + ticks < n and text[close + ticks] == "`":
        close = text.find("`" * ticks, close + ticks)
    if close == -1:
        return None, i
    content = text[j:close].replace("\n", " ")
    if len(content) >= 2 and content[0] == " " and content[-1] == " " and content.strip():
        content = content[1:-1]
    return Code(content), close + ticks


def _scan_delim_target(text: str, i: int) -> tuple[str, str | None, int] | None:
    """Parse a ``(url "title")`` destination at *i*; return (url, title, end)."""
    if i >= len(text) or text[i] != "(":
        return None
    depth = 0
    j = i
    n = len(text)
    while j < n:
        if text[j] == "\\" and j + 1 < n:
            j += 2
            continue
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                break
        j += 1
    if j >= n or depth != 0:
        return None
    inner = text[i + 1 : j].strip()
    title: str | None = None
    tm = re.search(r'\s+"([^"]*)"$', inner)
    if tm:
        title = tm.group(1)
        inner = inner[: tm.start()].strip()
    if inner.startswith("<") and inner.endswith(">"):
        inner = inner[1:-1]
    return inner, title, j + 1


def _find_matching_bracket(text: str, open_idx: int) -> int:
    """Return the index of the ``]`` matching the ``[`` at *open_idx*, or -1."""
    depth = 0
    j = open_idx
    n = len(text)
    while j < n:
        if text[j] == "\\" and j + 1 < n:
            j += 2
            continue
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def _scan_image(text: str, i: int, link_refs: dict[str, tuple[str, str | None]]) -> tuple[InlineImage | None, int]:
    """Scan ``![alt](src)`` or a reference image starting at the ``!`` at *i*."""
    close = _find_matching_bracket(text, i + 1)
    if close == -1:
        return None, i
    alt = text[i + 2 : close]
    target = _scan_delim_target(text, close + 1)
    if target is not None:
        return InlineImage(target[0], alt), target[2]
    ref = re.match(r"\[([^\]]*)\]", text[close + 1 :])
    label = (ref.group(1).strip() or alt).lower() if ref else alt.lower()
    if label in link_refs:
        end = close + 1 + (ref.end() if ref else 0)
        return InlineImage(link_refs[label][0], alt), end
    return None, i


def _scan_link(text: str, i: int, link_refs: dict[str, tuple[str, str | None]]) -> tuple[Link | None, int]:
    """Scan an inline or reference link starting at the ``[`` at *i*."""
    close = _find_matching_bracket(text, i)
    if close == -1:
        return None, i
    label_text = text[i + 1 : close]
    children = _parse_inline(label_text, link_refs)
    target = _scan_delim_target(text, close + 1)
    if target is not None:
        return Link(target[0], target[1], children), target[2]
    ref = re.match(r"\[([^\]]*)\]", text[close + 1 :])
    if ref is not None:
        label = (ref.group(1).strip() or label_text).lower()
        if label in link_refs:
            href, title = link_refs[label]
            return Link(href, title, children), close + 1 + ref.end()
        return None, i
    label = label_text.strip().lower()
    if label in link_refs:
        href, title = link_refs[label]
        return Link(href, title, children), close + 1
    return None, i


def _scan_emphasis(
    text: str, i: int, link_refs: dict[str, tuple[str, str | None]]
) -> tuple[Strong | Emphasis | None, int]:
    """Scan ``*``/``_`` emphasis or strong starting at *i*."""
    delim = text[i]
    n = len(text)
    j = i
    while j < n and text[j] == delim and j - i < 3:
        j += 1
    run = j - i
    # Underscore must not open inside a word (snake_case guard).
    if delim == "_" and i > 0 and (text[i - 1].isalnum()):
        return None, i
    if j < n and text[j].isspace():
        return None, i
    k = j
    while k < n:
        if text[k] == "\\" and k + 1 < n:
            k += 2
            continue
        if text[k] == delim and not text[k - 1].isspace():
            m = k
            while m < n and text[m] == delim and m - k < 3:
                m += 1
            close_run = m - k
            if close_run >= run and not (delim == "_" and m < n and text[m].isalnum()):
                inner = _parse_inline(text[j:k], link_refs)
                node: Strong | Emphasis
                if run == 1:
                    node = Emphasis(inner)
                elif run == 2:
                    node = Strong(inner)
                else:
                    node = Strong([Emphasis(inner)])
                return node, k + run
            k = m
            continue
        k += 1
    return None, i
