"""Tests for ODP slide transitions via add_transition.py."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


class TransitionTests(unittest.TestCase):
    def _make_deck(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "deck.json",
            {"slides": [{"name": "A", "title": "T1"}, {"name": "B", "title": "T2"}]},
        )
        odp = tmp_path / "deck.odp"
        run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", spec, odp)
        return odp

    def test_add_fade_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_transition.py",
                deck,
                "--slide",
                "1",
                "--type",
                "fade",
                "--duration",
                "700ms",
                "-o",
                out,
            )
            content = read_content(out)
            slides = list(content.iter(q("draw", "page")))
            self.assertIsNotNone(slides[0].attrib.get(q("draw", "style-name")))

    def test_add_wipe_all_slides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_transition.py",
                deck,
                "--slide",
                "all",
                "--type",
                "wipe",
                "--direction",
                "left",
                "-o",
                out,
            )
            content = read_content(out)
            slides = list(content.iter(q("draw", "page")))
            for s in slides:
                self.assertIsNotNone(s.attrib.get(q("draw", "style-name")))

    def test_remove_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            with_trans = tmp_path / "trans.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_transition.py",
                deck,
                "--slide",
                "1",
                "--type",
                "fade",
                "-o",
                with_trans,
            )
            removed = tmp_path / "removed.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_transition.py",
                with_trans,
                "--slide",
                "1",
                "--remove",
                "-o",
                removed,
            )
            content = read_content(removed)
            slides = list(content.iter(q("draw", "page")))
            self.assertIsNone(slides[0].attrib.get(q("draw", "style-name")))

    def test_list_transitions_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_transition.py",
                deck,
                "--slide",
                "all",
                "--type",
                "cover",
                "-o",
                out,
            )
            result = run_script(SKILLS / "odp" / "scripts" / "list_transitions.py", out, "--json").stdout
            data = json.loads(result)
            self.assertEqual(len(data), 2)
            for entry in data:
                self.assertEqual(entry["type"], "cover")


if __name__ == "__main__":
    unittest.main()
