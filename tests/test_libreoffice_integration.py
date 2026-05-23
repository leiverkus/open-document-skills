from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURES, ROOT, SKILLS, run_script

# Import shared find_soffice from lib
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from odf_lib.odf_common import find_soffice  # noqa: E402

SOFFICE = find_soffice()


def odg_fixture_with_image(tmp_path: Path) -> Path:
    spec = json.loads((FIXTURES / "odg_drawing.json").read_text(encoding="utf-8"))
    spec["pages"][0]["items"][-1]["path"] = str(FIXTURES / "image.svg")
    path = tmp_path / "drawing.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


@unittest.skipUnless(SOFFICE, "LibreOffice/soffice not available")
class LibreOfficeIntegrationTests(unittest.TestCase):
    def test_odt_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            run_script(scripts / "render.py", odt, "--outdir", outdir)
            pdf = outdir / "doc.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_odp_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            odp = tmp_path / "deck.odp"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odp.py", FIXTURES / "odp_slides.json", odp)
            run_script(scripts / "render.py", odp, "--outdir", outdir)
            pdf = outdir / "deck.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_odg_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            odg = tmp_path / "drawing.odg"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_odg.py", odg_fixture_with_image(tmp_path), odg)
            run_script(scripts / "render.py", odg, "--outdir", outdir, "--formats", "pdf")
            pdf = outdir / "drawing.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_branded_odp_deck_renders_to_pdf(self) -> None:
        """A base ODP with the dao-conference template applied must render to PDF.

        Exercises the v1.12 apply_template pipeline (the v1.1 branded-deck
        styling now lives in skills/odp/templates/dao-conference/).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            deck = ROOT / "examples" / "deck"
            base = tmp_path / "base.odp"
            run_script(scripts / "create_minimal_odp.py", deck / "spec.json", base)
            final = tmp_path / "deck.odp"
            run_script(scripts / "apply_template.py", base, "--template-name", "dao-conference", "-o", final)

            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", final, "--outdir", outdir)
            pdf = outdir / "deck.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_ods_render_to_pdf(self) -> None:
        """The new ODS render.py must produce a PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            ods = tmp_path / "book.ods"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_ods.py", FIXTURES / "ods_workbook.json", ods)
            run_script(scripts / "render.py", ods, "--outdir", outdir)
            pdf = outdir / "book.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_contact_sheet_render(self) -> None:
        """render.py --contact-sheet must compose all pages into one PNG."""
        import shutil

        if not shutil.which("pdftoppm"):
            self.skipTest("pdftoppm (Poppler) not available")
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = tmp_path / "deck.json"
            spec.write_text(
                json.dumps({"slides": [{"name": f"S{i}", "title": f"Slide {i}"} for i in range(1, 4)]}),
                encoding="utf-8",
            )
            odp = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, odp)
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", odp, "--outdir", outdir, "--contact-sheet")
            sheet = outdir / "deck-contact.png"
            self.assertTrue(sheet.exists())
            self.assertGreater(sheet.stat().st_size, 0)

    def test_structural_edits_render_to_pdf(self) -> None:
        """An ODT restyled, with blocks inserted/deleted and a table edited,
        must still render to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps(
                    {
                        "title": "Edits",
                        "blocks": [
                            {"type": "heading", "level": 1, "text": "Keep"},
                            {"type": "paragraph", "text": "Anchor paragraph."},
                            {"type": "paragraph", "text": "Drop this paragraph."},
                            {"type": "table", "name": "Grid", "rows": [["a", "b"], ["1", "2"]]},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            frag = tmp_path / "frag.json"
            frag.write_text(json.dumps([{"type": "paragraph", "text": "Inserted."}]), encoding="utf-8")
            current = tmp_path / "0.odt"
            run_script(scripts / "create_minimal_odt.py", spec, current)
            steps = [
                ("restyle.py", ["--headings", "--style", "Heading2"]),
                ("insert_blocks.py", ["--blocks", str(frag), "--after-anchor", "Anchor paragraph"]),
                ("edit_table.py", ["--table", "Grid", "--add-row", "3", "4"]),
                ("delete_block.py", ["--anchor", "Drop this paragraph"]),
            ]
            for index, (script, extra) in enumerate(steps, start=1):
                nxt = tmp_path / f"{index}.odt"
                run_script(scripts / script, current, *extra, "-o", nxt)
                current = nxt
            run_script(scripts / "validate_refs.py", current, "--strict")
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", current, "--outdir", outdir)
            pdf = outdir / "4.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_tracked_changes_and_comments_render_to_pdf(self) -> None:
        """An ODT with tracked changes and a comment must render to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            src = tmp_path / "doc.md"
            src.write_text(
                "# Review\n\nThe quick brown fox jumps over the lazy dog.\n",
                encoding="utf-8",
            )
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_from_markdown.py", src, odt)
            commented = tmp_path / "commented.odt"
            run_script(
                scripts / "add_comment.py", odt, "--anchor", "fox", "--author", "Rev", "--text", "Note", "-o", commented
            )
            tracked = tmp_path / "tracked.odt"
            run_script(
                scripts / "track_change.py",
                commented,
                "--replace",
                "brown",
                "--with",
                "red",
                "--author",
                "Rev",
                "-o",
                tracked,
            )
            run_script(scripts / "validate_refs.py", tracked, "--strict")
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", tracked, "--outdir", outdir)
            pdf = outdir / "tracked.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_markdown_to_odt_renders_to_pdf(self) -> None:
        """An ODT built from Markdown must render to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            src = tmp_path / "doc.md"
            src.write_text(
                "# Title\n\nText with **bold** and a [link](https://x.io).\n\n"
                "- one\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n",
                encoding="utf-8",
            )
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_from_markdown.py", src, odt)
            run_script(scripts / "validate_refs.py", odt, "--strict")
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", odt, "--outdir", outdir)
            pdf = outdir / "doc.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_branded_odg_diagram_renders_to_pdf(self) -> None:
        """A base ODG with the branded diagram styles.xml injected must render
        to a non-empty PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odg" / "scripts"
            sys.path.insert(0, str(scripts))
            from odg_common import inject_styles_from_file

            diagram = ROOT / "examples" / "diagram"
            base = tmp_path / "base.odg"
            run_script(scripts / "create_minimal_odg.py", diagram / "spec.json", base)
            final = tmp_path / "diagram.odg"
            inject_styles_from_file(base, diagram / "styles.xml", final)
            run_script(scripts / "validate_refs.py", final)

            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", final, "--outdir", outdir, "--formats", "pdf")
            pdf = outdir / "diagram.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_libreoffice_opens_flat_fodt(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", FIXTURES / "odt_document.json", odt)
            fodt = tmp_path / "doc.fodt"
            run_script(scripts / "pack_fodt.py", odt, "-o", fodt)
            outdir = tmp_path / "qa"
            outdir.mkdir()
            subprocess.run(
                [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(fodt)],
                check=True,
                capture_output=True,
            )
            pdf = outdir / "doc.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_ods_recalc_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            ods = tmp_path / "book.ods"
            outdir = tmp_path / "qa"
            run_script(scripts / "create_minimal_ods.py", FIXTURES / "ods_workbook.json", ods)
            run_script(scripts / "recalc.py", ods, "--outdir", outdir)
            recalced = outdir / "book.ods"
            self.assertTrue(recalced.exists())
            run_script(scripts / "validate_refs.py", recalced)

    def test_conditional_format_and_pivot_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "ods" / "scripts"
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps(
                    {
                        "sheets": [
                            {
                                "name": "Data",
                                "rows": [
                                    ["Region", "Quarter", "Revenue"],
                                    ["North", "Q1", "150"],
                                    ["North", "Q2", "40"],
                                    ["South", "Q1", "220"],
                                    ["South", "Q2", "95"],
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            ods = tmp_path / "book.ods"
            run_script(scripts / "create_minimal_ods.py", spec, ods)
            cf = tmp_path / "cf.ods"
            run_script(
                scripts / "add_conditional_format.py",
                ods,
                "--range",
                "Data.C2:C5",
                "--condition",
                "value > 100",
                "--background",
                "#C8E6C9",
                "-o",
                cf,
            )
            pv = tmp_path / "pv.ods"
            run_script(
                scripts / "add_pivot_table.py",
                cf,
                "--source",
                "Data.A1:C5",
                "--rows",
                "Region",
                "--columns",
                "Quarter",
                "--data",
                "Revenue",
                "--function",
                "sum",
                "--target",
                "Pivot.A1",
                "-o",
                pv,
            )
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", pv, "--outdir", outdir)
            pdf = outdir / "pv.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_slide_layouts_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps(
                    {
                        "masters": [{"name": "Brand", "background_color": "#02416C"}],
                        "slides": [
                            {"layout": "title-slide", "master": "Brand", "title": "Deck", "subtitle": "v1.8"},
                            {"layout": "title-content", "title": "Points", "body": ["one", "two"]},
                            {"layout": "two-content", "title": "Split", "body_left": ["L"], "body_right": ["R"]},
                            {"layout": "section-header", "title": "Part Two"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            deck = tmp_path / "deck.odp"
            run_script(scripts / "create_minimal_odp.py", spec, deck)
            relayout = tmp_path / "relayout.odp"
            run_script(scripts / "set_layout.py", deck, "--slide", "2", "--layout", "title-only", "-o", relayout)
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", relayout, "--outdir", outdir)
            pdf = outdir / "relayout.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_themed_documents_render_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            odp_scripts = SKILLS / "odp" / "scripts"
            odt_scripts = SKILLS / "odt" / "scripts"
            deck_spec = tmp_path / "deck.json"
            deck_spec.write_text(
                json.dumps({"slides": [{"layout": "title-slide", "title": "Themed", "subtitle": "v1.9"}]}),
                encoding="utf-8",
            )
            deck = tmp_path / "deck.odp"
            run_script(odp_scripts / "create_minimal_odp.py", deck_spec, deck, "--theme", "warm-editorial")
            doc_spec = tmp_path / "doc.json"
            doc_spec.write_text(
                json.dumps({"title": "Report", "blocks": [{"type": "paragraph", "text": "Body."}]}),
                encoding="utf-8",
            )
            doc = tmp_path / "doc.odt"
            run_script(odt_scripts / "create_minimal_odt.py", doc_spec, doc, "--theme", "forest")
            outdir = tmp_path / "qa"
            run_script(odp_scripts / "render.py", deck, "--outdir", outdir)
            run_script(odt_scripts / "render.py", doc, "--outdir", outdir)
            for name in ("deck.pdf", "doc.pdf"):
                pdf = outdir / name
                self.assertTrue(pdf.exists())
                self.assertGreater(pdf.stat().st_size, 0)

    def test_generated_indexes_round_trip(self) -> None:
        """ODT with all four index types + a marker survives soffice round-trip.

        The full ``update_indexes.py`` macro refresh requires the platform's
        headless macro execution to fire, which is blocked on some macOS
        LibreOffice bundles. Here we exercise the pieces that always work:
        every inserter produces a valid ODF document that LibreOffice opens
        cleanly (PDF render is non-empty), and ``validate_refs --strict``
        stays green over the whole chain.
        """
        try:
            import lxml  # noqa: F401
        except ImportError:
            self.skipTest("lxml not installed")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps(
                    {
                        "title": "Indexes Demo",
                        "blocks": [
                            {"type": "heading", "level": 1, "text": "Intro"},
                            {"type": "paragraph", "text": "Body of intro."},
                            {"type": "heading", "level": 2, "text": "Background"},
                            {"type": "paragraph", "text": "More text."},
                            {"type": "heading", "level": 1, "text": "Methods"},
                            {"type": "paragraph", "text": "Methods description."},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            base = tmp_path / "0.odt"
            run_script(scripts / "create_minimal_odt.py", spec, base)

            step1 = tmp_path / "1.odt"
            run_script(
                scripts / "add_sequence.py",
                base,
                "--sequence",
                "Figure",
                "--name",
                "fig1",
                "--anchor",
                "intro",
                "-o",
                step1,
            )
            step2 = tmp_path / "2.odt"
            run_script(scripts / "add_index_mark.py", step1, "--anchor", "Background", "--key1", "Topics", "-o", step2)
            step3 = tmp_path / "3.odt"
            run_script(scripts / "add_toc.py", step2, "--at", "start", "-o", step3)
            step4 = tmp_path / "4.odt"
            run_script(scripts / "add_bibliography.py", step3, "--at", "end", "-o", step4)
            step5 = tmp_path / "5.odt"
            run_script(scripts / "add_illustration_index.py", step4, "--at", "end", "--sequence", "Figure", "-o", step5)
            step6 = tmp_path / "6.odt"
            run_script(scripts / "add_alphabetical_index.py", step5, "--at", "end", "-o", step6)

            # Strict schema must stay green over the full chain.
            result = json.loads(run_script(scripts / "validate_refs.py", step6, "--strict").stdout)
            self.assertEqual(result["status"], "ok", msg=str(result))

            # LibreOffice must open and render the document.
            outdir = tmp_path / "qa"
            run_script(scripts / "render.py", step6, "--outdir", outdir)
            pdf = outdir / "6.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_odt_docx_odt_bridge(self) -> None:
        """Round-trip ODT → DOCX → ODT produces an ODT that passes the skill's
        internal consistency checks and renders to a non-empty PDF.

        Note: strict OASIS RelaxNG validation is *not* asserted here.
        LibreOffice's DOCX importer emits `loext:` extension attributes and
        slightly different attribute combinations on round-trip that don't
        match the strict ODF 1.3 schema, even though the document opens
        cleanly. This is a documented fidelity limitation of OOXML
        conversion — non-strict validation is the right gate.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odt" / "scripts"
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps(
                    {
                        "title": "Bridge",
                        "blocks": [
                            {"type": "heading", "level": 1, "text": "Section A"},
                            {"type": "paragraph", "text": "Some prose."},
                            {"type": "heading", "level": 2, "text": "Section B"},
                            {"type": "paragraph", "text": "More prose."},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            odt = tmp_path / "doc.odt"
            run_script(scripts / "create_minimal_odt.py", spec, odt)

            qa = tmp_path / "qa"
            run_script(scripts / "convert.py", odt, "--to", "docx", "--outdir", qa)
            self.assertTrue((qa / "doc.docx").exists())

            qa2 = tmp_path / "qa2"
            run_script(scripts / "convert.py", qa / "doc.docx", "--to", "odt", "--outdir", qa2)
            roundtripped = qa2 / "doc.odt"
            self.assertTrue(roundtripped.exists())

            # Internal consistency must still hold (non-strict validation).
            result = json.loads(run_script(scripts / "validate_refs.py", roundtripped).stdout)
            self.assertEqual(result["status"], "ok", msg=str(result))

            # And the document must render to a non-empty PDF.
            outdir = tmp_path / "pdf"
            run_script(scripts / "render.py", roundtripped, "--outdir", outdir)
            pdf = outdir / "doc.pdf"
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size, 0)

    def test_each_template_renders_to_pdf(self) -> None:
        """Every shipped ODP template must apply cleanly and render."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            base = tmp_path / "base.odp"
            run_script(scripts / "create_minimal_odp.py", FIXTURES / "odp_slides.json", base)
            templates_dir = SKILLS / "odp" / "templates"
            for template_dir in sorted(templates_dir.iterdir()):
                if not template_dir.is_dir():
                    continue
                with self.subTest(template=template_dir.name):
                    branded = tmp_path / f"{template_dir.name}.odp"
                    run_script(
                        scripts / "apply_template.py",
                        base,
                        "--template-name",
                        template_dir.name,
                        "-o",
                        branded,
                    )
                    outdir = tmp_path / f"{template_dir.name}-pdf"
                    run_script(scripts / "render.py", branded, "--outdir", outdir)
                    pdf = outdir / f"{template_dir.name}.pdf"
                    self.assertTrue(pdf.exists())
                    self.assertGreater(pdf.stat().st_size, 0)

    def test_extract_from_pptx_via_bridge(self) -> None:
        """extract_template.py accepts .pptx via the v1.11 convert_with_soffice bridge."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts = SKILLS / "odp" / "scripts"
            # Build an ODP, convert it to PPTX, then extract a template from the PPTX.
            base = tmp_path / "base.odp"
            run_script(scripts / "create_minimal_odp.py", FIXTURES / "odp_slides.json", base)
            pptx_dir = tmp_path / "pptx"
            run_script(scripts / "convert.py", base, "--to", "pptx", "--outdir", pptx_dir)
            pptx = pptx_dir / "base.pptx"
            self.assertTrue(pptx.exists())
            extract_dir = tmp_path / "templates"
            run_script(
                scripts / "extract_template.py",
                pptx,
                "--name",
                "from-pptx",
                "--outdir",
                extract_dir,
            )
            self.assertTrue((extract_dir / "from-pptx" / "styles.xml").exists())


if __name__ == "__main__":
    unittest.main()
