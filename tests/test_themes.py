"""Tests for the curated theme registry and the generators' --theme flag."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import ROOT, SKILLS, run_script

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from odf_lib.themes import THEMES, get_theme, theme_font_faces  # noqa: E402

HAVE_LXML = importlib.util.find_spec("lxml") is not None

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def read(path: Path, member: str) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read(member))


class ThemeRegistryTests(unittest.TestCase):
    def test_five_named_themes(self) -> None:
        self.assertEqual(
            set(THEMES),
            {"corporate-blue", "warm-editorial", "high-contrast", "slate-mono", "forest"},
        )

    def test_get_theme_unknown_errors(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            get_theme("does-not-exist")
        self.assertIn("unknown theme", str(ctx.exception))

    def test_font_faces_carry_generic(self) -> None:
        # Every theme's faces must end in a known generic family for safe fallback.
        for name, theme in THEMES.items():
            for face_name, family, generic in theme_font_faces(theme):
                self.assertIn(generic, {"swiss", "roman", "modern"}, f"{name}/{face_name}")
                self.assertTrue(family, f"{name}/{face_name}")


class ThemedGeneratorTests(unittest.TestCase):
    def test_odt_theme_applies_colour_and_font(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps({"title": "T", "blocks": [{"type": "heading", "level": 1, "text": "H"}]}),
                encoding="utf-8",
            )
            out = tmp_path / "themed.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, out, "--theme", "corporate-blue")
            styles = read(out, "styles.xml")
            faces = {f.attrib.get(q("style", "name")) for f in styles.iter(q("style", "font-face"))}
            self.assertEqual(faces, {"theme-heading", "theme-body"})
            heading = next(
                s for s in styles.iter(q("style", "style")) if s.attrib.get(q("style", "name")) == "Heading1"
            )
            tp = heading.find(q("style", "text-properties"))
            assert tp is not None
            self.assertEqual(tp.attrib.get(q("fo", "color")), THEMES["corporate-blue"].accent)
            self.assertEqual(tp.attrib.get(q("style", "font-name")), "theme-heading")

    def test_odt_without_theme_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(json.dumps({"title": "T", "blocks": []}), encoding="utf-8")
            out = tmp_path / "plain.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, out)
            styles = read(out, "styles.xml")
            self.assertEqual(list(styles.iter(q("style", "font-face"))), [])
            for tp in styles.iter(q("style", "text-properties")):
                self.assertIsNone(tp.attrib.get(q("fo", "color")))

    def test_markdown_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md = tmp_path / "in.md"
            md.write_text("# Title\n\nBody text.\n", encoding="utf-8")
            out = tmp_path / "themed.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_from_markdown.py", md, out, "--theme", "forest")
            styles = read(out, "styles.xml")
            faces = {f.attrib.get(q("style", "name")) for f in styles.iter(q("style", "font-face"))}
            self.assertIn("theme-heading", faces)
            self.assertIn("Mono", faces)  # the markdown code face is preserved

    def test_odp_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(json.dumps({"slides": [{"title": "Hi"}]}), encoding="utf-8")
            out = tmp_path / "themed.odp"
            run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", spec, out, "--theme", "forest")
            styles = read(out, "styles.xml")
            gr_title = next(
                s for s in styles.iter(q("style", "style")) if s.attrib.get(q("style", "name")) == "gr-title"
            )
            tp = gr_title.find(q("style", "text-properties"))
            assert tp is not None
            self.assertEqual(tp.attrib.get(q("fo", "color")), THEMES["forest"].accent)
            self.assertEqual(tp.attrib.get(q("style", "font-name")), "theme-heading")

    def test_odg_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps({"pages": [{"name": "P", "items": [{"type": "rect", "text": "Box"}]}]}),
                encoding="utf-8",
            )
            out = tmp_path / "themed.odg"
            run_script(SKILLS / "odg" / "scripts" / "create_minimal_odg.py", spec, out, "--theme", "warm-editorial")
            styles = read(out, "styles.xml")
            standard = next(
                s for s in styles.iter(q("style", "style")) if s.attrib.get(q("style", "name")) == "standard"
            )
            # The standard graphic style carries the theme's shape fill.
            self.assertIn(THEMES["warm-editorial"].shape_fill, ET.tostring(standard, encoding="unicode"))
            faces = {f.attrib.get(q("style", "name")) for f in styles.iter(q("style", "font-face"))}
            self.assertEqual(faces, {"theme-heading", "theme-body"})

    def test_ods_theme_styles_the_header_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps({"sheets": [{"name": "Data", "rows": [["A", "B"], ["1", "2"]]}]}),
                encoding="utf-8",
            )
            out = tmp_path / "themed.ods"
            run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, out, "--theme", "high-contrast")
            styles = read(out, "styles.xml")
            names = {s.attrib.get(q("style", "name")) for s in styles.iter(q("style", "style"))}
            self.assertIn("ce-header", names)
            self.assertTrue(list(styles.iter(q("style", "default-style"))))
            content = read(out, "content.xml")
            header_cells = [
                c
                for c in content.iter(q("table", "table-cell"))
                if c.attrib.get(q("table", "style-name")) == "ce-header"
            ]
            self.assertEqual(len(header_cells), 2)

    def test_ods_without_theme_is_unstyled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(json.dumps({"sheets": [{"name": "S", "rows": [["x"]]}]}), encoding="utf-8")
            out = tmp_path / "plain.ods"
            run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, out)
            styles = read(out, "styles.xml")
            self.assertEqual(list(styles.iter(q("style", "font-face"))), [])
            self.assertEqual(list(styles.iter(q("style", "style"))), [])

    @unittest.skipUnless(HAVE_LXML, "lxml not installed")
    def test_strict_clean_for_every_format(self) -> None:
        cases = [
            ("odt", "create_minimal_odt.py", {"title": "T", "blocks": [{"type": "paragraph", "text": "p"}]}),
            ("odp", "create_minimal_odp.py", {"slides": [{"title": "S"}]}),
            ("ods", "create_minimal_ods.py", {"sheets": [{"name": "D", "rows": [["h"], ["v"]]}]}),
            ("odg", "create_minimal_odg.py", {"pages": [{"name": "P", "items": [{"type": "rect"}]}]}),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fmt, script, spec_data in cases:
                spec = tmp_path / f"{fmt}.json"
                spec.write_text(json.dumps(spec_data), encoding="utf-8")
                out = tmp_path / f"doc.{fmt}"
                run_script(SKILLS / fmt / "scripts" / script, spec, out, "--theme", "slate-mono")
                result = run_script(SKILLS / fmt / "scripts" / "validate_refs.py", out, "--strict")
                self.assertEqual(json.loads(result.stdout)["status"], "ok", fmt)


if __name__ == "__main__":
    unittest.main()
