"""Tests for insert_blocks.py and delete_block.py — structural block editing."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

ODT = SKILLS / "odt" / "scripts"
NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def content_of(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def block_texts(path: Path) -> list[str]:
    body = content_of(path).find(".//office:text", NS)
    assert body is not None
    out: list[str] = []
    for child in body:
        if child.tag in {q("text", "h"), q("text", "p")}:
            out.append("".join(child.itertext()))
    return out


def base_odt(tmp: Path) -> Path:
    spec = tmp / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "title": "Doc",
                "blocks": [
                    {"type": "heading", "level": 1, "text": "Intro"},
                    {"type": "paragraph", "text": "Alpha paragraph."},
                    {"type": "paragraph", "text": "Beta paragraph."},
                    {"type": "table", "name": "T", "rows": [["a", "b"]]},
                ],
            }
        ),
        encoding="utf-8",
    )
    odt = tmp / "doc.odt"
    run_script(ODT / "create_minimal_odt.py", spec, odt)
    return odt


def fragment(tmp: Path) -> Path:
    path = tmp / "frag.json"
    path.write_text(
        json.dumps([{"type": "heading", "level": 2, "text": "NEW HEAD"}, {"type": "paragraph", "text": "NEW PARA"}]),
        encoding="utf-8",
    )
    return path


class InsertBlocksTests(unittest.TestCase):
    def test_insert_after_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "i.odt"
            run_script(
                ODT / "insert_blocks.py",
                base_odt(tmp_path),
                "--blocks",
                fragment(tmp_path),
                "--after-anchor",
                "Alpha paragraph",
                "-o",
                out,
            )
            texts = block_texts(out)
            self.assertEqual(texts[texts.index("Alpha paragraph.") + 1], "NEW HEAD")
            self.assertEqual(texts[texts.index("Alpha paragraph.") + 2], "NEW PARA")

    def test_insert_before_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "i.odt"
            run_script(
                ODT / "insert_blocks.py",
                base_odt(tmp_path),
                "--blocks",
                fragment(tmp_path),
                "--before-anchor",
                "Beta paragraph",
                "-o",
                out,
            )
            texts = block_texts(out)
            self.assertEqual(texts[texts.index("Beta paragraph.") - 1], "NEW PARA")

    def test_insert_at_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "i.odt"
            run_script(
                ODT / "insert_blocks.py", base_odt(tmp_path), "--blocks", fragment(tmp_path), "--at", "end", "-o", out
            )
            self.assertEqual(block_texts(out)[-1], "NEW PARA")

    def test_insert_rejects_image_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bad = tmp_path / "bad.json"
            bad.write_text(json.dumps([{"type": "image", "path": "x.png"}]), encoding="utf-8")
            out = tmp_path / "i.odt"
            result = run_script(
                ODT / "insert_blocks.py", base_odt(tmp_path), "--blocks", bad, "--at", "end", "-o", out, check=False
            )
            self.assertNotEqual(result.returncode, 0)


class DeleteBlockTests(unittest.TestCase):
    def test_delete_by_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "d.odt"
            run_script(ODT / "delete_block.py", base_odt(tmp_path), "--anchor", "Alpha paragraph", "-o", out)
            self.assertNotIn("Alpha paragraph.", block_texts(out))
            self.assertIn("Beta paragraph.", block_texts(out))

    def test_delete_table_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "d.odt"
            run_script(ODT / "delete_block.py", base_odt(tmp_path), "--paragraph", "1", "--type", "table", "-o", out)
            self.assertEqual(len(list(content_of(out).iter(q("table", "table")))), 0)

    def test_delete_by_paragraph_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "d.odt"
            # Top-level blocks: Doc(h), Intro(h), Alpha(p), Beta(p), T(table).
            run_script(ODT / "delete_block.py", base_odt(tmp_path), "--paragraph", "3", "-o", out)
            self.assertNotIn("Alpha paragraph.", block_texts(out))


if __name__ == "__main__":
    unittest.main()
