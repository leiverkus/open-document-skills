"""Tests for ODP shape-level animations via add_animation.py."""

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
    "anim": "urn:oasis:names:tc:opendocument:xmlns:animation:1.0",
    "smil": "urn:oasis:names:tc:opendocument:xmlns:smil-compatible:1.0",
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


class AnimationTests(unittest.TestCase):
    def _make_deck(self, tmp_path: Path) -> Path:
        spec = write_json(
            tmp_path / "deck.json",
            {"slides": [{"name": "Intro", "title": "Hello"}, {"name": "Body", "title": "Punkte"}]},
        )
        odp = tmp_path / "deck.odp"
        run_script(SKILLS / "odp" / "scripts" / "create_minimal_odp.py", spec, odp)
        return odp

    def test_add_entrance_appear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "entrance:appear",
                "-o",
                out,
            )
            content = read_content(out)
            anims = list(content.iter(q("anim", "par")))
            # outer + inner = 2 (plus timing-root parent maybe)
            self.assertGreaterEqual(len(anims), 2)
            presets = [a.attrib.get(q("presentation", "preset-id")) for a in anims]
            self.assertIn("ooo-entrance-appear", presets)

    def test_add_entrance_fly_in_with_direction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "entrance:fly-in",
                "--direction",
                "from-bottom",
                "--duration",
                "800ms",
                "-o",
                out,
            )
            content = read_content(out)
            preset_ids = {a.attrib.get(q("presentation", "preset-id")) for a in content.iter(q("anim", "par"))}
            self.assertIn("ooo-entrance-fly-in-from-bottom", preset_ids)

    def test_add_exit_fade_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "exit:fade-out",
                "-o",
                out,
            )
            content = read_content(out)
            preset_ids = {a.attrib.get(q("presentation", "preset-id")) for a in content.iter(q("anim", "par"))}
            self.assertIn("ooo-exit-fade-out", preset_ids)

    def test_add_emphasis_pulse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "emphasis:pulse",
                "-o",
                out,
            )
            content = read_content(out)
            preset_ids = {a.attrib.get(q("presentation", "preset-id")) for a in content.iter(q("anim", "par"))}
            self.assertIn("ooo-emphasis-pulse", preset_ids)

    def test_add_motion_linear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "motion:linear",
                "--direction",
                "right",
                "-o",
                out,
            )
            content = read_content(out)
            # animateMotion must exist
            motions = list(content.iter(q("anim", "animateMotion")))
            self.assertEqual(len(motions), 1)

    def test_add_animation_assigns_shape_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "entrance:appear",
                "-o",
                out,
            )
            content = read_content(out)
            ids = [e.attrib.get(q("draw", "id")) for e in content.iter() if e.attrib.get(q("draw", "id"))]
            self.assertGreaterEqual(len(ids), 1)
            self.assertIn("shape-1", ids)

    def test_list_animations_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            with_anim = tmp_path / "anim.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "entrance:fade-in",
                "-o",
                with_anim,
            )
            result = run_script(SKILLS / "odp" / "scripts" / "list_animations.py", with_anim, "--json").stdout
            data = json.loads(result)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["preset_id"], "ooo-entrance-fade-in")
            self.assertEqual(data[0]["preset_class"], "entrance")

    def test_validate_refs_passes_with_animation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            deck = self._make_deck(tmp_path)
            out = tmp_path / "out.odp"
            run_script(
                SKILLS / "odp" / "scripts" / "add_animation.py",
                deck,
                "--slide",
                "1",
                "--shape",
                "Intro",
                "--effect",
                "entrance:fade-in",
                "-o",
                out,
            )
            result = run_script(SKILLS / "odp" / "scripts" / "validate_refs.py", out)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
