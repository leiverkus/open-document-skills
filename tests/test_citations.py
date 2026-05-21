"""Tests for the ODT citation API: add_citation.py, list_citations.py."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import FIXTURES, SKILLS, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
}


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read_content(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


try:
    import bibtexparser  # noqa: F401

    HAVE_BIBTEXPARSER = True
except ImportError:
    HAVE_BIBTEXPARSER = False


class CitationAPITests(unittest.TestCase):
    def _make_odt(self, tmp_path: Path, blocks: list[dict]) -> Path:
        spec = write_json(tmp_path / "spec.json", {"title": "T", "blocks": blocks})
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_minimal_odt.py", spec, odt)
        return odt

    def test_add_citation_inline_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "frühere Studien"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--anchor",
                "frühere Studien",
                "--identifier",
                "Mueller2020",
                "--field",
                "bibliography-type=article",
                "--field",
                "author=Müller, Klaus",
                "--field",
                "year=2020",
                "--field",
                "title=Test",
                "-o",
                out,
            )
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "bibliography-mark")]
            self.assertEqual(len(marks), 1)
            mark = marks[0]
            self.assertEqual(mark.attrib.get(q("text", "identifier")), "Mueller2020")
            self.assertEqual(mark.attrib.get(q("text", "author")), "Müller, Klaus")
            self.assertEqual(mark.attrib.get(q("text", "year")), "2020")
            self.assertEqual(mark.text, "Mueller2020")

    def test_add_citation_from_csl_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "frühere Studien"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--anchor",
                "frühere Studien",
                "--source",
                FIXTURES / "refs.csl.json",
                "--key",
                "Mueller2020",
                "-o",
                out,
            )
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "bibliography-mark")]
            self.assertEqual(len(marks), 1)
            mark = marks[0]
            self.assertEqual(mark.attrib.get(q("text", "bibliography-type")), "article")
            self.assertEqual(mark.attrib.get(q("text", "author")), "Müller, Klaus")
            self.assertEqual(mark.attrib.get(q("text", "year")), "2020")
            self.assertEqual(
                mark.attrib.get(q("text", "journal")), "Zeitschrift für die alttestamentliche Wissenschaft"
            )

    def test_add_citation_csl_json_chapter_maps_to_incollection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Sammelband"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--anchor",
                "Sammelband",
                "--source",
                FIXTURES / "refs.csl.json",
                "--key",
                "Weber2015",
                "-o",
                out,
            )
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "bibliography-mark")]
            self.assertEqual(marks[0].attrib.get(q("text", "bibliography-type")), "incollection")
            self.assertEqual(
                marks[0].attrib.get(q("text", "booktitle")) or marks[0].attrib.get(q("text", "journal")),
                "Handbuch der biblischen Forschung",
            )

    @unittest.skipUnless(HAVE_BIBTEXPARSER, "bibtexparser not installed")
    def test_add_citation_from_bibtex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "frühere Studien"}])
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--anchor",
                "frühere Studien",
                "--source",
                FIXTURES / "refs.bib",
                "--key",
                "Mueller2020",
                "-o",
                out,
            )
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "bibliography-mark")]
            self.assertEqual(len(marks), 1)
            self.assertEqual(marks[0].attrib.get(q("text", "bibliography-type")), "article")
            self.assertEqual(marks[0].attrib.get(q("text", "year")), "2020")

    def test_list_citations_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "frühere Studien"}])
            with_cite = tmp_path / "with_cite.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--anchor",
                "frühere Studien",
                "--source",
                FIXTURES / "refs.csl.json",
                "--key",
                "Mueller2020",
                "-o",
                with_cite,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "list_citations.py", with_cite, "--json").stdout
            data = json.loads(result)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["identifier"], "Mueller2020")
            self.assertEqual(data[0]["fields"]["bibliography-type"], "article")
            self.assertEqual(data[0]["fields"]["year"], "2020")

    def test_add_citation_inline_anchor_in_span_preserves_span(self) -> None:
        # Reuse test pattern from footnote tests: span around the anchor.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "placeholder"}])
            content = read_content(odt)
            text_el = content.find(".//office:text", NS)
            assert text_el is not None
            for child in list(text_el):
                text_el.remove(child)
            ns_attrs = (
                'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
                'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            )
            injected = ET.fromstring(f"<text:p {ns_attrs}>Hi <text:span>important</text:span> end</text:p>")
            text_el.append(injected)
            patched = tmp_path / "patched.odt"
            with zipfile.ZipFile(odt) as src:
                with zipfile.ZipFile(patched, "w") as dst:
                    for name in src.namelist():
                        if name == "mimetype":
                            dst.writestr("mimetype", src.read("mimetype"), zipfile.ZIP_STORED)
                        elif name == "content.xml":
                            dst.writestr(name, ET.tostring(content, encoding="utf-8", xml_declaration=True))
                        else:
                            dst.writestr(name, src.read(name))
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                patched,
                "--anchor",
                "important",
                "--identifier",
                "X",
                "-o",
                out,
            )
            content2 = read_content(out)
            spans = [s for s in content2.iter() if s.tag == q("text", "span")]
            self.assertEqual(len(spans), 1)
            self.assertEqual(spans[0].text, "important")
            marks = [m for m in content2.iter() if m.tag == q("text", "bibliography-mark")]
            self.assertEqual(len(marks), 1)

    def test_add_citation_no_match_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(tmp_path, [{"type": "paragraph", "text": "Hello"}])
            out = tmp_path / "out.odt"
            result = run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--anchor",
                "nope",
                "--identifier",
                "X",
                "-o",
                out,
            )
            self.assertIn("anchor not found", result.stdout)
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "bibliography-mark")]
            self.assertEqual(len(marks), 0)

    def test_fill_citations_replaces_known_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                FIXTURES / "template_with_placeholders.json",
                odt,
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "fill_citations.py",
                odt,
                "--source",
                FIXTURES / "refs.csl.json",
                "-o",
                out,
            )
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "bibliography-mark")]
            identifiers = {m.attrib.get(q("text", "identifier")) for m in marks}
            self.assertEqual(identifiers, {"Mueller2020", "Schmidt1998", "Weber2015"})

    def test_fill_citations_leaves_unknown_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                FIXTURES / "template_with_placeholders.json",
                odt,
            )
            out = tmp_path / "out.odt"
            result = run_script(
                SKILLS / "odt" / "scripts" / "fill_citations.py",
                odt,
                "--source",
                FIXTURES / "refs.csl.json",
                "-o",
                out,
            )
            # stderr is folded into stdout by helpers.run_script (subprocess.STDOUT)
            self.assertIn("[@UnknownKey]", result.stdout)
            # The placeholder is left in some paragraph's text
            content = read_content(out)
            all_text: list[str] = []
            for p in content.iter():
                if p.text:
                    all_text.append(p.text)
                if p.tail:
                    all_text.append(p.tail)
            combined = "".join(all_text)
            self.assertIn("[@UnknownKey]", combined)

    def test_fill_citations_updates_meta_when_replacing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                FIXTURES / "template_with_placeholders.json",
                odt,
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "fill_citations.py",
                odt,
                "--source",
                FIXTURES / "refs.csl.json",
                "-o",
                out,
            )
            with zipfile.ZipFile(out) as archive:
                meta_root = ET.fromstring(archive.read("meta.xml"))
            cycles = meta_root.find(f".//{{{NS['meta']}}}editing-cycles")
            assert cycles is not None
            self.assertEqual(cycles.text, "1")

    def test_validate_refs_warns_on_leftover_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = tmp_path / "doc.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "create_minimal_odt.py",
                FIXTURES / "template_with_placeholders.json",
                odt,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", odt)
            self.assertIn("Unfilled citation placeholder", result.stdout)

    def test_validate_refs_warns_on_duplicate_citation_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "First"},
                    {"type": "paragraph", "text": "Second"},
                ],
            )
            first = tmp_path / "first.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--anchor",
                "First",
                "--identifier",
                "DupKey",
                "-o",
                first,
            )
            second = tmp_path / "second.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                first,
                "--anchor",
                "Second",
                "--identifier",
                "DupKey",
                "-o",
                second,
            )
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", second)
            self.assertIn("Duplicate", result.stdout)
            self.assertIn("DupKey", result.stdout)

    def test_add_citation_paragraph_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odt = self._make_odt(
                tmp_path,
                [
                    {"type": "paragraph", "text": "First"},
                    {"type": "paragraph", "text": "Second"},
                ],
            )
            out = tmp_path / "out.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_citation.py",
                odt,
                "--paragraph",
                "2",
                "--position",
                "end",
                "--identifier",
                "X",
                "-o",
                out,
            )
            content = read_content(out)
            marks = [m for m in content.iter() if m.tag == q("text", "bibliography-mark")]
            self.assertEqual(len(marks), 1)


if __name__ == "__main__":
    unittest.main()
