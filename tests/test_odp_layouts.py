"""Tests for the ODP slide-layout API (odp_layouts / create_minimal_odp / set_layout)."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import SKILLS, run_script

HAVE_LXML = importlib.util.find_spec("lxml") is not None

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
}

ODP_SCRIPTS = SKILLS / "odp" / "scripts"


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def read_member(path: Path, member: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read(member))


def make_deck(tmp_path: Path, spec: dict, name: str = "deck.odp") -> Path:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    out = tmp_path / name
    run_script(ODP_SCRIPTS / "create_minimal_odp.py", spec_path, out)
    return out


def frames(content: ET.Element, slide_index: int) -> list[ET.Element]:
    page = content.findall(".//draw:page", NS)[slide_index]
    return page.findall(q("draw", "frame"))


class SlideLayoutTests(unittest.TestCase):
    def test_build_styles_emits_six_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(Path(tmp), {"slides": [{"title": "Hi"}]})
            styles = read_member(odp, "styles.xml")
            names = {p.attrib.get(q("style", "name")) for p in styles.iter(q("style", "presentation-page-layout"))}
            self.assertEqual(
                names,
                {
                    "pl-title-content",
                    "pl-title-slide",
                    "pl-two-content",
                    "pl-section-header",
                    "pl-title-only",
                    "pl-blank",
                },
            )

    def test_layout_driven_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(
                Path(tmp),
                {"slides": [{"layout": "title-slide", "title": "Big", "subtitle": "Small"}]},
            )
            content = read_member(odp, "content.xml")
            page = content.findall(".//draw:page", NS)[0]
            self.assertEqual(page.attrib.get(q("presentation", "presentation-page-layout-name")), "pl-title-slide")
            by_class = {f.attrib.get(q("presentation", "class")): f for f in frames(content, 0)}
            self.assertEqual(set(by_class), {"title", "subtitle"})
            # title-slide title zone: x=2cm y=5cm.
            self.assertEqual(by_class["title"].attrib.get(q("svg", "x")), "2cm")
            self.assertEqual(by_class["title"].attrib.get(q("svg", "y")), "5cm")

    def test_backward_compat_default_layout(self) -> None:
        """A spec with no layout key behaves exactly as before layouts existed."""
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(Path(tmp), {"slides": [{"title": "T", "body": ["one", "two"]}]})
            content = read_member(odp, "content.xml")
            page = content.findall(".//draw:page", NS)[0]
            self.assertEqual(page.attrib.get(q("presentation", "presentation-page-layout-name")), "pl-title-content")
            names = {f.attrib.get(q("draw", "name")) for f in frames(content, 0)}
            self.assertEqual(names, {"Title", "Body"})
            body = next(f for f in frames(content, 0) if f.attrib.get(q("draw", "name")) == "Body")
            # Unchanged geometry: 1.4cm / 3.2cm / 25cm / 8cm.
            self.assertEqual(body.attrib.get(q("svg", "x")), "1.4cm")
            self.assertEqual(body.attrib.get(q("svg", "width")), "25cm")

    def test_two_content_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(
                Path(tmp),
                {"slides": [{"layout": "two-content", "title": "T", "body_left": ["L"], "body_right": ["R"]}]},
            )
            content = read_member(odp, "content.xml")
            names = {f.attrib.get(q("draw", "name")) for f in frames(content, 0)}
            self.assertEqual(names, {"Title", "BodyLeft", "BodyRight"})
            right = next(f for f in frames(content, 0) if f.attrib.get(q("draw", "name")) == "BodyRight")
            self.assertEqual(right.attrib.get(q("svg", "x")), "14.6cm")

    def test_multiple_masters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(
                Path(tmp),
                {
                    "masters": [{"name": "Brand", "background_color": "#02416C"}],
                    "slides": [{"master": "Brand", "title": "A"}, {"title": "B"}],
                },
            )
            styles = read_member(odp, "styles.xml")
            master_names = {m.attrib.get(q("style", "name")) for m in styles.iter(q("style", "master-page"))}
            self.assertEqual(master_names, {"Default", "Brand"})
            content = read_member(odp, "content.xml")
            pages = content.findall(".//draw:page", NS)
            self.assertEqual(pages[0].attrib.get(q("draw", "master-page-name")), "Brand")
            self.assertEqual(pages[1].attrib.get(q("draw", "master-page-name")), "Default")
            # The Brand master has its own drawing-page style with the colour.
            dp = next(s for s in styles.iter(q("style", "style")) if s.attrib.get(q("style", "name")) == "dp-Brand")
            props = dp.find(q("style", "drawing-page-properties"))
            assert props is not None
            self.assertEqual(
                props.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}fill-color"), "#02416C"
            )

    def test_unknown_master_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "spec.json"
            spec.write_text(json.dumps({"slides": [{"master": "Ghost", "title": "x"}]}), encoding="utf-8")
            result = run_script(ODP_SCRIPTS / "create_minimal_odp.py", spec, Path(tmp) / "out.odp", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown master", result.stdout)

    def test_unknown_layout_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "spec.json"
            spec.write_text(json.dumps({"slides": [{"layout": "nope", "title": "x"}]}), encoding="utf-8")
            result = run_script(ODP_SCRIPTS / "create_minimal_odp.py", spec, Path(tmp) / "out.odp", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown layout", result.stdout)

    def test_set_layout_repositions_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp = make_deck(tmp_path, {"slides": [{"title": "T", "body": ["x"]}]})
            out = tmp_path / "relayout.odp"
            run_script(ODP_SCRIPTS / "set_layout.py", odp, "--slide", "1", "--layout", "two-content", "-o", out)
            content = read_member(out, "content.xml")
            page = content.findall(".//draw:page", NS)[0]
            self.assertEqual(page.attrib.get(q("presentation", "presentation-page-layout-name")), "pl-two-content")
            body = next(f for f in frames(content, 0) if f.attrib.get(q("draw", "name")) == "Body")
            # Repositioned to the first outline zone of two-content (width 12cm).
            self.assertEqual(body.attrib.get(q("svg", "width")), "12cm")

    def test_set_layout_assigns_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp = make_deck(
                tmp_path,
                {"masters": [{"name": "Brand"}], "slides": [{"title": "A"}, {"title": "B"}]},
            )
            out = tmp_path / "out.odp"
            run_script(ODP_SCRIPTS / "set_layout.py", odp, "--slide", "all", "--master", "Brand", "-o", out)
            content = read_member(out, "content.xml")
            for page in content.findall(".//draw:page", NS):
                self.assertEqual(page.attrib.get(q("draw", "master-page-name")), "Brand")

    def test_list_masters_reports_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(Path(tmp), {"slides": [{"layout": "title-slide", "title": "A"}]})
            result = run_script(ODP_SCRIPTS / "list_masters.py", odp, "--json")
            data = json.loads(result.stdout)
            layout_names = {layout["name"] for layout in data["presentation_page_layouts"]}
            self.assertIn("pl-two-content", layout_names)
            title_slide = next(
                layout for layout in data["presentation_page_layouts"] if layout["name"] == "pl-title-slide"
            )
            self.assertEqual(len(title_slide["placeholders"]), 2)

    def test_validate_refs_detects_dangling_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp = make_deck(tmp_path, {"slides": [{"title": "A"}]})
            broken = tmp_path / "broken.odp"
            with zipfile.ZipFile(odp) as src:
                content = src.read("content.xml").decode("utf-8").replace("pl-title-content", "pl-ghost")
                with zipfile.ZipFile(broken, "w") as dst:
                    for member in src.namelist():
                        data = content.encode("utf-8") if member == "content.xml" else src.read(member)
                        mode = zipfile.ZIP_STORED if member == "mimetype" else zipfile.ZIP_DEFLATED
                        dst.writestr(member, data, mode)
            result = run_script(ODP_SCRIPTS / "validate_refs.py", broken, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing presentation-page-layout", result.stdout)

    @unittest.skipUnless(HAVE_LXML, "lxml not installed")
    def test_strict_validation_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odp = make_deck(
                Path(tmp),
                {
                    "masters": [{"name": "Brand", "background_color": "#02416C"}],
                    "slides": [
                        {"layout": "title-slide", "master": "Brand", "title": "A", "subtitle": "B"},
                        {"layout": "two-content", "title": "C", "body_left": ["L"], "body_right": ["R"]},
                    ],
                },
            )
            result = run_script(ODP_SCRIPTS / "validate_refs.py", odp, "--strict")
            self.assertEqual(json.loads(result.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
