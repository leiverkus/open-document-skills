"""Tests for ODP master-page customization via customize_master.py."""

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
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_styles(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("styles.xml"))


class MasterPageTests(unittest.TestCase):
    def _make_deck(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "deck.json",
            {"slides": [{"name": "A", "title": "T"}]},
        )
        odp = tmp_path / "deck.odp"
        run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", spec, odp)
        return odp

    def test_background_color(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "customize_master.py",
                deck,
                "--master",
                "Default",
                "--background-color",
                "#02416C",
                "-o",
                out,
            )
            styles = read_styles(out)
            master = next(
                m for m in styles.iter(q("style", "master-page")) if m.attrib.get(q("style", "name")) == "Default"
            )
            props = master.find(q("style", "drawing-page-properties"))
            assert props is not None
            self.assertEqual(props.attrib.get(q("draw", "fill")), "solid")
            self.assertEqual(props.attrib.get(q("draw", "fill-color")), "#02416C")

    def test_clone_to_new_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "customize_master.py",
                deck,
                "--master",
                "Default",
                "--clone-to",
                "DAO-Brand",
                "--background-color",
                "#02416C",
                "-o",
                out,
            )
            styles = read_styles(out)
            names = {m.attrib.get(q("style", "name")) for m in styles.iter(q("style", "master-page"))}
            self.assertIn("Default", names)
            self.assertIn("DAO-Brand", names)

    def test_footer_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "customize_master.py",
                deck,
                "--master",
                "Default",
                "--footer-text",
                "DAO 2026",
                "-o",
                out,
            )
            styles = read_styles(out)
            master = next(
                m for m in styles.iter(q("style", "master-page")) if m.attrib.get(q("style", "name")) == "Default"
            )
            # Find a frame with presentation:class="footer"
            footer_frames = [
                f for f in master.findall(q("draw", "frame")) if f.attrib.get(q("presentation", "class")) == "footer"
            ]
            self.assertEqual(len(footer_frames), 1)


if __name__ == "__main__":
    unittest.main()
