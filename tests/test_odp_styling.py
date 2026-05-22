"""Tests for ODP presentation styling — drawing-page background, graphic
frame styles (no blue boxes), text colours, and the styles.xml inject path."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import ROOT, SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

ODP_SCRIPTS = SKILLS / "odp" / "scripts"
DECK_STYLES = ROOT / "examples" / "deck" / "styles.xml"


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def member(path: Path, name: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read(name))


def make_deck(tmp_path: Path) -> Path:
    spec = tmp_path / "deck.json"
    spec.write_text(
        json.dumps(
            {
                "title": "Styling test",
                "slides": [
                    {"name": "A", "title": "Hello", "body": ["one", "two"]},
                    {"name": "B", "title": "World", "body": "single"},
                ],
            }
        ),
        encoding="utf-8",
    )
    odp = tmp_path / "deck.odp"
    run_script(ODP_SCRIPTS / "create_minimal_odp.py", spec, odp)
    return odp


def graphic_styles(styles: ET.Element) -> dict[str, ET.Element]:
    out: dict[str, ET.Element] = {}
    for st in styles.iter(q("style", "style")):
        if st.attrib.get(q("style", "family")) == "graphic":
            name = st.attrib.get(q("style", "name"))
            if name:
                out[name] = st
    return out


class GeneratedStylingTests(unittest.TestCase):
    def test_frames_reference_a_graphic_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(Path(tmp))
            content = member(odp, "content.xml")
            frames = list(content.iter(q("draw", "frame")))
            self.assertGreater(len(frames), 0)
            for frame in frames:
                self.assertIsNotNone(
                    frame.attrib.get(q("draw", "style-name")),
                    "every generated frame must carry a draw:style-name",
                )

    def test_graphic_styles_suppress_default_fill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(Path(tmp))
            styles = member(odp, "styles.xml")
            grs = graphic_styles(styles)
            for name in ("gr-title", "gr-body", "gr-notes", "gr-image"):
                self.assertIn(name, grs, f"missing graphic style {name}")
                props = grs[name].find(q("style", "graphic-properties"))
                assert props is not None
                self.assertEqual(props.attrib.get(q("draw", "fill")), "none")
                self.assertEqual(props.attrib.get(q("draw", "stroke")), "none")

    def test_drawing_page_background_style_is_referenced_by_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(Path(tmp))
            styles = member(odp, "styles.xml")
            master = next(
                m for m in styles.iter(q("style", "master-page")) if m.attrib.get(q("style", "name")) == "Default"
            )
            dp_name = master.attrib.get(q("draw", "style-name"))
            self.assertIsNotNone(dp_name, "master page must reference a drawing-page style")
            dp_style = next(
                s
                for s in styles.iter(q("style", "style"))
                if s.attrib.get(q("style", "name")) == dp_name and s.attrib.get(q("style", "family")) == "drawing-page"
            )
            props = dp_style.find(q("style", "drawing-page-properties"))
            assert props is not None
            self.assertEqual(props.attrib.get(q("draw", "fill")), "solid")
            self.assertIsNotNone(props.attrib.get(q("draw", "fill-color")))

    def test_paragraph_styles_carry_explicit_colour(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(Path(tmp))
            styles = member(odp, "styles.xml")
            for name in ("Title", "Body", "Notes"):
                style = next(
                    s
                    for s in styles.iter(q("style", "style"))
                    if s.attrib.get(q("style", "name")) == name and s.attrib.get(q("style", "family")) == "paragraph"
                )
                tp = style.find(q("style", "text-properties"))
                assert tp is not None
                self.assertIsNotNone(tp.attrib.get(q("fo", "color")), f"{name} must set fo:color")


class InjectStylesTests(unittest.TestCase):
    def test_inject_branded_styles_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp = make_deck(tmp_path)

            import sys

            sys.path.insert(0, str(ODP_SCRIPTS))
            from odp_common import inject_styles_from_file

            out = tmp_path / "branded.odp"
            missing = inject_styles_from_file(odp, DECK_STYLES, out)
            # The branded styles.xml redefines every named style the
            # generator emits, so no content reference should dangle.
            self.assertEqual(missing, [])

            styles = member(out, "styles.xml")
            dp = next(s for s in styles.iter(q("style", "style")) if s.attrib.get(q("style", "name")) == "dp-default")
            props = dp.find(q("style", "drawing-page-properties"))
            assert props is not None
            self.assertEqual(props.attrib.get(q("draw", "fill-color")), "#02416C")
            # mimetype must stay the first, stored entry.
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(archive.namelist()[0], "mimetype")


class CustomizeMasterBackgroundTests(unittest.TestCase):
    def test_background_color_lands_in_drawing_page_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp = make_deck(tmp_path)
            out = tmp_path / "bg.odp"
            run_script(
                ODP_SCRIPTS / "customize_master.py",
                odp,
                "--master",
                "Default",
                "--background-color",
                "#123456",
                "-o",
                out,
            )
            styles = member(out, "styles.xml")
            master = next(
                m for m in styles.iter(q("style", "master-page")) if m.attrib.get(q("style", "name")) == "Default"
            )
            dp_name = master.attrib.get(q("draw", "style-name"))
            dp_style = next(
                s
                for s in styles.iter(q("style", "style"))
                if s.attrib.get(q("style", "name")) == dp_name and s.attrib.get(q("style", "family")) == "drawing-page"
            )
            props = dp_style.find(q("style", "drawing-page-properties"))
            assert props is not None
            self.assertEqual(props.attrib.get(q("draw", "fill-color")), "#123456")
            # The customized background must not be written onto the master
            # element itself — that variant does not render.
            self.assertIsNone(master.find(q("style", "drawing-page-properties")))


if __name__ == "__main__":
    unittest.main()
