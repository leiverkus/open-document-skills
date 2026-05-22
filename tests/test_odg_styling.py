"""Tests for ODG drawing styling — designed graphic styles (no generic blue),
per-shape fill/stroke/text overrides, and the styles.xml inject path."""

from __future__ import annotations

import json
import sys
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
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
}

ODG_SCRIPTS = SKILLS / "odg" / "scripts"
DIAGRAM_STYLES = ROOT / "examples" / "diagram" / "styles.xml"
GENERIC_BLUE = "#729fcf"  # LibreOffice's default graphic-style fill


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def member(path: Path, name: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read(name))


def make_drawing(tmp_path: Path) -> Path:
    """Generate an ODG with a plain shape, a styled shape, and a text frame."""
    spec = tmp_path / "d.json"
    spec.write_text(
        json.dumps(
            {
                "pages": [
                    {
                        "name": "P",
                        "items": [
                            {"type": "text", "text": "Heading", "x": "1cm", "y": "1cm"},
                            {"type": "rect", "name": "Plain", "text": "Plain", "x": "1cm", "y": "4cm"},
                            {
                                "type": "rect",
                                "name": "Styled",
                                "text": "Styled",
                                "x": "8cm",
                                "y": "4cm",
                                "fill": "#F4C542",
                                "stroke": "#7A5C00",
                                "text-color": "#3A2E00",
                                "font-size": "20pt",
                            },
                            {"type": "ellipse", "name": "Round", "text": "Round", "x": "15cm", "y": "4cm"},
                            {"type": "line", "x1": "1cm", "y1": "8cm", "x2": "10cm", "y2": "8cm"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    odg = tmp_path / "d.odg"
    run_script(ODG_SCRIPTS / "create_minimal_odg.py", spec, odg)
    return odg


def styles_named(root: ET.Element) -> dict[str, ET.Element]:
    out: dict[str, ET.Element] = {}
    for st in root.iter(q("style", "style")):
        name = st.attrib.get(q("style", "name"))
        if name:
            out[name] = st
    return out


class GeneratedStylingTests(unittest.TestCase):
    def test_no_generic_blue_anywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odg = make_drawing(Path(tmp))
            for part in ("styles.xml", "content.xml"):
                raw = zipfile.ZipFile(odg).read(part).decode("utf-8").lower()
                self.assertNotIn(GENERIC_BLUE, raw, f"{part} still carries LibreOffice's default blue")

    def test_every_shape_references_a_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odg = make_drawing(Path(tmp))
            content = member(odg, "content.xml")
            shapes = [el for el in content.iter() if el.tag.split("}")[-1] in {"rect", "ellipse", "line", "frame"}]
            self.assertGreaterEqual(len(shapes), 5)
            for shape in shapes:
                self.assertIsNotNone(
                    shape.attrib.get(q("draw", "style-name")),
                    f"{shape.tag} carries no draw:style-name",
                )

    def test_standard_style_has_chosen_properties(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odg = make_drawing(Path(tmp))
            styles = styles_named(member(odg, "styles.xml"))
            self.assertIn("standard", styles)
            props = styles["standard"].find(q("style", "graphic-properties"))
            assert props is not None
            fill = props.attrib.get(q("draw", "fill-color"))
            self.assertIsNotNone(fill)
            self.assertNotEqual((fill or "").lower(), GENERIC_BLUE)

    def test_text_and_image_roles_are_unfilled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odg = make_drawing(Path(tmp))
            styles = styles_named(member(odg, "styles.xml"))
            for name in ("gr-text", "gr-image"):
                self.assertIn(name, styles)
                props = styles[name].find(q("style", "graphic-properties"))
                assert props is not None
                self.assertEqual(props.attrib.get(q("draw", "fill")), "none")
                self.assertEqual(props.attrib.get(q("draw", "stroke")), "none")

    def test_drawing_page_background_referenced_by_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odg = member(make_drawing(Path(tmp)), "styles.xml")
            master = next(
                m for m in odg.iter(q("style", "master-page")) if m.attrib.get(q("style", "name")) == "Default"
            )
            dp_name = master.attrib.get(q("draw", "style-name"))
            self.assertIsNotNone(dp_name, "master page must reference a drawing-page style")
            # The drawing-page style must sit in office:automatic-styles.
            auto = odg.find(q("office", "automatic-styles"))
            assert auto is not None
            dp = next(
                s
                for s in auto.findall(q("style", "style"))
                if s.attrib.get(q("style", "name")) == dp_name and s.attrib.get(q("style", "family")) == "drawing-page"
            )
            props = dp.find(q("style", "drawing-page-properties"))
            assert props is not None
            self.assertEqual(props.attrib.get(q("draw", "fill")), "solid")


class PerShapeStylingTests(unittest.TestCase):
    def test_graphic_overrides_produce_an_automatic_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(make_drawing(Path(tmp)), "content.xml")
            styled = next(el for el in content.iter(q("draw", "rect")) if el.attrib.get(q("draw", "name")) == "Styled")
            style_name = styled.attrib.get(q("draw", "style-name"))
            self.assertTrue((style_name or "").startswith("gr-auto-"))
            auto = content.find(q("office", "automatic-styles"))
            assert auto is not None
            style = next(s for s in auto.findall(q("style", "style")) if s.attrib.get(q("style", "name")) == style_name)
            self.assertEqual(style.attrib.get(q("style", "parent-style-name")), "gr-shape")
            props = style.find(q("style", "graphic-properties"))
            assert props is not None
            self.assertEqual(props.attrib.get(q("draw", "fill-color")), "#F4C542")
            self.assertEqual(props.attrib.get(q("svg", "stroke-color")), "#7A5C00")

    def test_text_overrides_produce_paragraph_and_text_styles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(make_drawing(Path(tmp)), "content.xml")
            styled = next(el for el in content.iter(q("draw", "rect")) if el.attrib.get(q("draw", "name")) == "Styled")
            paragraph = styled.find(q("text", "p"))
            assert paragraph is not None
            p_name = paragraph.attrib.get(q("text", "style-name"))
            self.assertIsNotNone(p_name)
            span = paragraph.find(q("text", "span"))
            assert span is not None
            t_name = span.attrib.get(q("text", "style-name"))
            self.assertIsNotNone(t_name)
            # The text style must carry the overridden colour.
            auto = content.find(q("office", "automatic-styles"))
            assert auto is not None
            t_style = next(s for s in auto.findall(q("style", "style")) if s.attrib.get(q("style", "name")) == t_name)
            tp = t_style.find(q("style", "text-properties"))
            assert tp is not None
            self.assertEqual(tp.attrib.get(q("fo", "color")), "#3A2E00")
            self.assertEqual(tp.attrib.get(q("fo", "font-size")), "20pt")

    def test_plain_shape_uses_role_style_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = member(make_drawing(Path(tmp)), "content.xml")
            plain = next(el for el in content.iter(q("draw", "rect")) if el.attrib.get(q("draw", "name")) == "Plain")
            self.assertEqual(plain.attrib.get(q("draw", "style-name")), "gr-shape")

    def test_corner_radius_lands_on_the_rect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "s.json"
            spec.write_text(
                json.dumps(
                    {"pages": [{"name": "P", "items": [{"type": "rect", "name": "R", "corner-radius": "0.4cm"}]}]}
                ),
                encoding="utf-8",
            )
            odg = tmp_path / "s.odg"
            run_script(ODG_SCRIPTS / "create_minimal_odg.py", spec, odg)
            rect = next(member(odg, "content.xml").iter(q("draw", "rect")))
            self.assertEqual(rect.attrib.get(q("draw", "corner-radius")), "0.4cm")


class InjectStylesTests(unittest.TestCase):
    def test_inject_branded_styles_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = make_drawing(tmp_path)
            sys.path.insert(0, str(ODG_SCRIPTS))
            from odg_common import inject_styles_from_file

            out = tmp_path / "branded.odg"
            missing = inject_styles_from_file(odg, DIAGRAM_STYLES, out)
            # The branded styles.xml redefines every role style, and per-shape
            # P/T styles live in content.xml — so nothing should dangle.
            self.assertEqual(missing, [])
            styles = styles_named(member(out, "styles.xml"))
            self.assertIn("standard", styles)
            self.assertIn("gr-shape", styles)
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(archive.namelist()[0], "mimetype")

    def test_embed_pictures_adds_manifest_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odg = make_drawing(tmp_path)
            sys.path.insert(0, str(ODG_SCRIPTS))
            from odg_common import embed_pictures

            png = tmp_path / "logo.png"
            png.write_bytes(
                bytes.fromhex(
                    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
                    "890000000a49444154789c6360000000020001e221bc330000000049454e44ae426082"
                )
            )
            out = tmp_path / "withpic.odg"
            embed_pictures(odg, {"Pictures/logo.png": png}, out)
            with zipfile.ZipFile(out) as archive:
                self.assertIn("Pictures/logo.png", archive.namelist())
                manifest = ET.fromstring(archive.read("META-INF/manifest.xml"))
            paths = {e.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}full-path") for e in manifest}
            self.assertIn("Pictures/logo.png", paths)


if __name__ == "__main__":
    unittest.main()
