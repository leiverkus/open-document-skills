"""Regression tests for formula namespaces, recalc, index refresh, Markdown styles, template carry-over and install docs.

- Formula namespace declarations (``xmlns:of`` & co.) survive generation and
  ElementTree round trips, so LibreOffice evaluates the formulas.
- ``recalc.py`` actually recalculates (it used to convert the file onto itself,
  which soffice refuses while still exiting 0).
- ``convert_with_soffice`` no longer reports success from a stale output.
- ``update_indexes.py`` fills index bodies from a fresh profile and does not
  hang.
- ``create_from_markdown.py`` table cell styles inherit from ``Body``, header
  cells follow column alignment, footnotes get their own style.
- ``apply_template.py`` keeps document styles the template does not define.
- Standalone installs bundle the docs SKILL.md links to.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import ROOT, SKILLS, run_script

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from odf_lib.odf_common import find_soffice, xml_bytes  # noqa: E402

SOFFICE = find_soffice()

OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
OF = "urn:oasis:names:tc:opendocument:xmlns:of:1.2"

# A spreadsheet as LibreOffice writes it: xmlns:of declared on the root but
# used only inside the table:formula attribute value.
LO_STYLE_FODS = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="{OFFICE}" xmlns:table="{TABLE}" xmlns:text="{TEXT}" xmlns:of="{OF}"
 office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.spreadsheet">
<office:meta/>
<office:body><office:spreadsheet><table:table table:name="S"><table:table-row>
<table:table-cell office:value-type="float" office:value="2"><text:p>2</text:p></table:table-cell>
<table:table-cell table:formula="of:=[.A1]*10" office:value-type="float" office:value="20"><text:p>20</text:p></table:table-cell>
</table:table-row></table:table></office:spreadsheet></office:body></office:document>
"""


def _content(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read("content.xml")


def _styles(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("styles.xml"))


def _soffice(*args: object, profile: Path) -> None:
    subprocess.run(
        [SOFFICE, f"-env:UserInstallation={profile.as_uri()}", "--headless", *map(str, args)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
    )


class FormulaNamespaceTests(unittest.TestCase):
    def test_xml_bytes_declares_value_prefix(self) -> None:
        root = ET.Element(f"{{{TABLE}}}table-cell", {f"{{{TABLE}}}formula": "of:=1+1"})
        out = xml_bytes(root)
        self.assertIn(b'xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2"', out)
        ET.fromstring(out)  # still well-formed
        # The caller's element is not mutated.
        self.assertNotIn("xmlns:of", root.attrib)

    def test_xml_bytes_leaves_documents_without_formulas_alone(self) -> None:
        root = ET.Element(f"{{{TEXT}}}p")
        root.text = "of: not a formula attribute"
        self.assertNotIn(b"xmlns:of", xml_bytes(root))

    def test_generated_ods_declares_of(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(
                '{"sheets":[{"name":"S","rows":[[1],[2]],"cells":{"A3":{"formula":"of:=SUM([.A1:.A2])"}}}]}',
                encoding="utf-8",
            )
            out = tmp_path / "out.ods"
            run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, out)
            self.assertIn(b"xmlns:of=", _content(out))

    def test_replace_cells_preserves_of_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "src.ods"
            run_script(SKILLS / "ods" / "scripts" / "unpack_fods.py", self._write_fods(tmp_path), "-o", src)
            out = tmp_path / "out.ods"
            run_script(SKILLS / "ods" / "scripts" / "replace_cells.py", src, "S!A1=5", "-o", out)
            content = _content(out)
            self.assertIn(b"xmlns:of=", content)
            self.assertIn(b'table:formula="of:=[.A1]*10"', content)

    @staticmethod
    def _write_fods(tmp_path: Path) -> Path:
        fods = tmp_path / "src.fods"
        fods.write_text(LO_STYLE_FODS, encoding="utf-8")
        return fods

    @unittest.skipUnless(SOFFICE, "LibreOffice/soffice not available")
    def test_edited_formula_evaluates_in_libreoffice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "src.ods"
            run_script(SKILLS / "ods" / "scripts" / "unpack_fods.py", self._write_fods(tmp_path), "-o", src)
            out = tmp_path / "edited.ods"
            run_script(SKILLS / "ods" / "scripts" / "replace_cells.py", src, "S!A1=5", "-o", out)
            csv_dir = tmp_path / "csv"
            _soffice("--convert-to", "csv", "--outdir", csv_dir, out, profile=tmp_path / "profile")
            self.assertEqual((csv_dir / "edited.csv").read_text(encoding="utf-8").strip(), "5,50")


@unittest.skipUnless(SOFFICE, "LibreOffice/soffice not available")
class RecalcTests(unittest.TestCase):
    def test_recalc_writes_computed_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(
                '{"sheets":[{"name":"S","rows":[[1],[2]],"cells":{"A3":{"formula":"of:=SUM([.A1:.A2])"}}}]}',
                encoding="utf-8",
            )
            src = tmp_path / "book.ods"
            run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, src)
            qa = tmp_path / "qa"
            run_script(SKILLS / "ods" / "scripts" / "recalc.py", src, "--outdir", qa)
            root = ET.fromstring(_content(qa / "book.ods"))
            cells = [c for c in root.iter(f"{{{TABLE}}}table-cell") if c.get(f"{{{TABLE}}}formula")]
            self.assertEqual(len(cells), 1)
            self.assertEqual(float(cells[0].get(f"{{{OFFICE}}}value")), 3.0)

    def test_recalc_works_when_outdir_holds_the_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text('{"sheets":[{"name":"S","rows":[[4]],"cells":{"B1":{"formula":"of:=[.A1]*2"}}}]}')
            src = tmp_path / "book.ods"
            run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, src)
            # Previously this converted book.ods onto itself and silently did nothing.
            run_script(SKILLS / "ods" / "scripts" / "recalc.py", src, "--outdir", tmp_path)
            self.assertIn(b'office:value="8"', _content(src))


class ConvertGuardTests(unittest.TestCase):
    def test_convert_onto_itself_is_refused(self) -> None:
        from odf_lib.odf_common import convert_with_soffice

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "book.ods"
            src.write_bytes(b"not used")
            with self.assertRaises(SystemExit):
                convert_with_soffice(src, "ods", Path(tmp))


@unittest.skipUnless(SOFFICE, "LibreOffice/soffice not available")
class UpdateIndexesTests(unittest.TestCase):
    def test_toc_is_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md = tmp_path / "doc.md"
            md.write_text("# Alpha\n\ntext\n\n## Beta\n\nmore\n", encoding="utf-8")
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_from_markdown.py", md, odt)
            toc = tmp_path / "toc.odt"
            run_script(SKILLS / "odt" / "scripts" / "add_toc.py", odt, "--at", "start", "-o", toc)
            qa = tmp_path / "qa"
            result = run_script(
                SKILLS / "odt" / "scripts" / "update_indexes.py", toc, "--outdir", qa, "--timeout", "90"
            )
            self.assertNotIn("did not grow", result.stdout)
            root = ET.fromstring(_content(qa / "toc.odt"))
            body = next(root.iter(f"{{{TEXT}}}index-body"))
            entries = "".join(body.itertext())
            self.assertIn("Alpha", entries)
            self.assertIn("Beta", entries)


class MarkdownStyleTests(unittest.TestCase):
    def _build(self, tmp_path: Path) -> Path:
        md = tmp_path / "doc.md"
        md.write_text(
            "Text.[^1]\n\n| A | B |\n|:--|--:|\n| x | 1 |\n\n[^1]: Note.\n",
            encoding="utf-8",
        )
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_from_markdown.py", md, odt)
        return odt

    def test_cell_styles_inherit_body_and_header_follows_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odt = self._build(Path(tmp))
            styles = _styles(odt)
            parents = {
                s.get(f"{{{STYLE}}}name"): s.get(f"{{{STYLE}}}parent-style-name")
                for s in styles.iter(f"{{{STYLE}}}style")
            }
            self.assertEqual(parents["TableHeader"], "Body")
            self.assertEqual(parents["TableCell"], "Body")
            self.assertEqual(parents["CellRight"], "TableCell")
            self.assertEqual(parents["TableHeaderRight"], "TableHeader")
            content = _content(odt)
            self.assertIn(b'text:style-name="TableHeaderRight">B<', content)
            self.assertIn(b'text:style-name="CellRight">1<', content)

    def test_footnote_body_uses_footnote_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            odt = self._build(Path(tmp))
            root = ET.fromstring(_content(odt))
            note_body = next(root.iter(f"{{{TEXT}}}note-body"))
            self.assertEqual(note_body[0].get(f"{{{TEXT}}}style-name"), "Footnote")


class ApplyTemplateCarryOverTests(unittest.TestCase):
    def test_document_styles_missing_from_template_are_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md = tmp_path / "doc.md"
            md.write_text("1. one\n2. two\n\n> quote\n", encoding="utf-8")
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_from_markdown.py", md, odt)
            out = tmp_path / "out.odt"
            result = run_script(
                SKILLS / "odt" / "scripts" / "apply_template.py", odt, "--template-name", "letterhead", "-o", out
            )
            self.assertNotIn("not in template", result.stdout)
            styles = _styles(out)
            names = {s.get(f"{{{STYLE}}}name") for s in styles.iter()}
            self.assertIn("ListNumber", names)
            self.assertIn("Quote", names)

    def test_no_carry_over_restores_old_behaviour(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md = tmp_path / "doc.md"
            md.write_text("1. one\n2. two\n", encoding="utf-8")
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_from_markdown.py", md, odt)
            out = tmp_path / "out.odt"
            result = run_script(
                SKILLS / "odt" / "scripts" / "apply_template.py",
                odt,
                "--template-name",
                "letterhead",
                "--no-carry-over",
                "-o",
                out,
            )
            self.assertIn("ListNumber", result.stdout)
            names = {s.get(f"{{{STYLE}}}name") for s in _styles(out).iter()}
            self.assertNotIn("ListNumber", names)


class InstallDocsTests(unittest.TestCase):
    def test_standalone_install_bundles_linked_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "skills"
            run_script(ROOT / "scripts" / "install_skills.py", "--target", "agents", "--dest", dest)
            for skill in ("odt", "odp", "ods", "odg"):
                text = (dest / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertNotIn("../../", text, skill)
                for doc in ("soffice-resolver.md", "script-reference.md"):
                    self.assertTrue((dest / skill / "docs" / doc).is_file(), (skill, doc))


def _schema_available() -> bool:
    from odf_lib.odf_common import ensure_schema

    try:
        ensure_schema("content")
        ensure_schema("manifest")
    except (SystemExit, OSError):
        return False
    return True


class CellValueTests(unittest.TestCase):
    def test_assigning_a_value_drops_the_old_formula(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fods = tmp_path / "src.fods"
            fods.write_text(LO_STYLE_FODS, encoding="utf-8")
            src = tmp_path / "src.ods"
            run_script(SKILLS / "ods" / "scripts" / "unpack_fods.py", fods, "-o", src)
            out = tmp_path / "out.ods"
            run_script(SKILLS / "ods" / "scripts" / "replace_cells.py", src, "S!B1=7", "-o", out)
            root = ET.fromstring(_content(out))
            cell = list(root.iter(f"{{{TABLE}}}table-cell"))[1]
            self.assertIsNone(cell.get(f"{{{TABLE}}}formula"))
            self.assertEqual(cell.get(f"{{{OFFICE}}}value"), "7.0")

    def test_formula_cell_has_no_value_type_without_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text('{"sheets":[{"name":"S","rows":[[1, null]],"cells":{"C1":{"formula":"of:=[.A1]"}}}]}')
            out = tmp_path / "out.ods"
            run_script(SKILLS / "ods" / "scripts" / "create_minimal_ods.py", spec, out)
            cells = list(ET.fromstring(_content(out)).iter(f"{{{TABLE}}}table-cell"))
            # JSON null → empty cell, not the string "None".
            self.assertEqual("".join(cells[1].itertext()), "")
            self.assertIsNone(cells[1].get(f"{{{OFFICE}}}value-type"))
            # Formula without a cached value → no value-type (schema requires both).
            self.assertIsNone(cells[2].get(f"{{{OFFICE}}}value-type"))


@unittest.skipUnless(_schema_available(), "ODF RelaxNG schema not available")
class StrictSchemaRegressionTests(unittest.TestCase):
    def test_generated_formula_workbook_passes_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "out.ods"
            run_script(
                SKILLS / "ods" / "scripts" / "create_minimal_ods.py", ROOT / "tests/fixtures/ods_workbook.json", out
            )
            result = run_script(SKILLS / "ods" / "scripts" / "validate_refs.py", out, "--strict")
            self.assertIn('"status": "ok"', result.stdout)

    def test_libreoffice_comment_extension_passes_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md = tmp_path / "doc.md"
            md.write_text("Some claim here.\n", encoding="utf-8")
            odt = tmp_path / "doc.odt"
            run_script(SKILLS / "odt" / "scripts" / "create_from_markdown.py", md, odt)
            commented = tmp_path / "c.odt"
            run_script(
                SKILLS / "odt" / "scripts" / "add_comment.py",
                odt,
                "--anchor",
                "claim",
                "--author",
                "R",
                "--text",
                "?",
                "-o",
                commented,
            )
            # Mimic LibreOffice's save: loext:resolved on the annotation.
            lo = tmp_path / "lo.odt"
            loext = "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0"
            with zipfile.ZipFile(commented) as src, zipfile.ZipFile(lo, "w") as dst:
                for info in src.infolist():
                    data = src.read(info)
                    if info.filename == "content.xml":
                        data = data.replace(b"<office:annotation ", b'<office:annotation loext:resolved="false" ', 1)
                        data = data.replace(
                            b"<office:document-content ", f'<office:document-content xmlns:loext="{loext}" '.encode(), 1
                        )
                    dst.writestr(info, data)
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", lo, "--strict", check=False)
            self.assertIn('"status": "ok"', result.stdout, result.stdout)


def _with_version(src: Path, dst: Path, version: str) -> None:
    """Copy an ODF package, rewriting every office:/manifest:version to *version*."""
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info)
            if info.filename.endswith(".xml"):
                data = data.replace(b'office:version="1.3"', f'office:version="{version}"'.encode())
                data = data.replace(b'manifest:version="1.3"', f'manifest:version="{version}"'.encode())
            zout.writestr(info, data, compress_type=info.compress_type)


def _schema_14_available() -> bool:
    from odf_lib.odf_common import ensure_schema

    try:
        ensure_schema("content", "1.4")
        ensure_schema("manifest", "1.4")
    except (SystemExit, OSError):
        return False
    return True


class OdfVersionTests(unittest.TestCase):
    def _generated_odt(self, tmp_path: Path) -> Path:
        md = tmp_path / "doc.md"
        md.write_text("# Title\n\nBody text.\n", encoding="utf-8")
        odt = tmp_path / "doc.odt"
        run_script(SKILLS / "odt" / "scripts" / "create_from_markdown.py", md, odt)
        return odt

    @unittest.skipUnless(_schema_14_available(), "ODF 1.4 RelaxNG schema not available")
    def test_odf_14_document_is_checked_against_14_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc14 = tmp_path / "doc14.odt"
            _with_version(self._generated_odt(tmp_path), doc14, "1.4")
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", doc14, "--strict", check=False)
            self.assertIn('"status": "ok"', result.stdout, result.stdout)

    def test_unsupported_version_is_skipped_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc12 = tmp_path / "doc12.odt"
            _with_version(self._generated_odt(tmp_path), doc12, "1.2")
            result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", doc12, "--strict", check=False)
            self.assertIn('"status": "ok"', result.stdout, result.stdout)
            self.assertIn("declares ODF 1.2", result.stdout)

    def test_flat_round_trip_preserves_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc14 = tmp_path / "doc14.odt"
            _with_version(self._generated_odt(tmp_path), doc14, "1.4")
            flat = tmp_path / "doc14.fodt"
            run_script(SKILLS / "odt" / "scripts" / "pack_fodt.py", doc14, "-o", flat)
            self.assertIn(b'office:version="1.4"', flat.read_bytes()[:2000])
            back = tmp_path / "back.odt"
            run_script(SKILLS / "odt" / "scripts" / "unpack_fodt.py", flat, "-o", back)
            with zipfile.ZipFile(back) as archive:
                for member in ("content.xml", "styles.xml", "meta.xml", "settings.xml"):
                    self.assertIn(b'office:version="1.4"', archive.read(member), member)
                self.assertIn(b'manifest:version="1.4"', archive.read("META-INF/manifest.xml"))


if __name__ == "__main__":
    unittest.main()
