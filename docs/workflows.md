# OpenDocument Workflows

The skills prefer native OpenDocument package/XML workflows. LibreOffice is treated as an interoperability and visual QA tool.

## Common Loop

1. Create or modify the ODF package with the relevant script.
2. Inspect package structure.
3. Extract text, sheets, formulas, shapes, or slide content.
4. Validate package references.
5. Render or recalculate with LibreOffice when visual or formula QA matters.

## ODT

Create:

```bash
python3 skills/odt/scripts/create_minimal_odt.py examples/odt_document.json example.odt
```

Check:

```bash
python3 skills/odt/scripts/inspect_package.py example.odt
python3 skills/odt/scripts/extract_text.py example.odt
python3 skills/odt/scripts/validate_refs.py example.odt
```

Render:

```bash
python3 skills/odt/scripts/render.py example.odt --outdir qa --png
```

## ODP

Create:

```bash
python3 skills/odp/scripts/create_minimal_odp.py examples/odp_slides.json example.odp
```

Check:

```bash
python3 skills/odp/scripts/inspect_package.py example.odp
python3 skills/odp/scripts/extract_text.py example.odp
python3 skills/odp/scripts/list_masters.py example.odp
python3 skills/odp/scripts/validate_refs.py example.odp
```

Render:

```bash
python3 skills/odp/scripts/render.py example.odp --outdir qa --png
```

Style and brand:

```bash
# Per-master tweak: background colour written into the master's drawing-page style.
python3 skills/odp/scripts/customize_master.py example.odp \
    --master Default --background-color "#02416C" -o branded.odp
```

`create_minimal_odp.py` already emits a designed default theme — a real
`drawing-page` background style and no-fill `graphic` frame styles, so frames
never render as blue boxes. For a full branded theme, write a curated
`styles.xml` that redefines the same named styles and inject it with
`inject_styles_from_file` (see [examples/deck/](#branded-deck-example)).

## ODS

Create:

```bash
python3 skills/ods/scripts/create_minimal_ods.py examples/ods_workbook.json example.ods
```

Check:

```bash
python3 skills/ods/scripts/inspect_package.py example.ods
python3 skills/ods/scripts/extract_sheets.py example.ods
python3 skills/ods/scripts/extract_formulas.py example.ods
python3 skills/ods/scripts/validate_refs.py example.ods
```

Recalculate:

```bash
python3 skills/ods/scripts/recalc.py example.ods --outdir qa
```

## ODG

Create:

```bash
python3 skills/odg/scripts/create_minimal_odg.py examples/odg_drawing.json example.odg
```

Check:

```bash
python3 skills/odg/scripts/inspect_package.py example.odg
python3 skills/odg/scripts/extract_text.py example.odg
python3 skills/odg/scripts/extract_shapes.py example.odg
python3 skills/odg/scripts/validate_refs.py example.odg
```

Export:

```bash
python3 skills/odg/scripts/render.py example.odg --outdir qa --formats pdf,svg,png
```

## Scholarly authoring (ODT)

ODT supports footnotes, endnotes, and citation insertion natively. The skill ships direct ODF-native helpers — no DOCX or pandoc-citeproc round-trip needed.

### Footnotes and endnotes

```bash
python3 skills/odt/scripts/add_footnote.py input.odt \
    --anchor "claim text" --body "Source: Müller 2020, p. 42" -o output.odt
python3 skills/odt/scripts/list_notes.py output.odt --json
```

IDs auto-increment (`ftn0`, `ftn1`, ... or `edn0`, `edn1`, ... for endnotes). Inline children (`text:span`, `text:bookmark`) around the anchor are preserved by the structure-preserving walker introduced in v0.2.0.

### Cross-references and figure numbering

```bash
# Point bookmark + reference to it (with chapter display):
python3 skills/odt/scripts/add_bookmark.py input.odt \
    --name "Methodik" --anchor "3. Methodik" -o output.odt
python3 skills/odt/scripts/add_reference.py output.odt \
    --ref-to "Methodik" --kind bookmark \
    --anchor "siehe Kapitel" --display chapter -o output.odt

# Auto-numbered figure caption + ref:
python3 skills/odt/scripts/add_sequence.py input.odt \
    --sequence Figure --name "fig:karte" \
    --anchor "Karte zeigt" -o output.odt
python3 skills/odt/scripts/add_sequence.py output.odt \
    --ref-to "fig:karte" --anchor "siehe Abbildung" -o output.odt

# Inspect everything:
python3 skills/odt/scripts/list_refs.py output.odt --json
```

`text:bookmark` (point + intra-paragraph range), `text:reference-mark` (point + range), and `text:sequence` (Figure/Table/Equation auto-numbering) are all supported. The validator detects dangling refs and duplicate names. See [examples/dao/build_grant_proposal.py](../examples/dao/build_grant_proposal.py) for an end-to-end pipeline combining citations, footnotes, cross-references, sequences, and MathML.

### Math formulas (LaTeX → MathML)

```bash
# LaTeX (requires pandoc):
python3 skills/odt/scripts/add_math.py input.odt \
    --latex "N(t) = N_0 e^{-\\lambda t}" \
    --anchor "Datierungsformel" -o output.odt

# Raw MathML file:
python3 skills/odt/scripts/add_math.py input.odt \
    --mathml formula.mml --anchor "Equation" -o output.odt
```

Formulas are embedded as `Object N/` sub-packages — LibreOffice's native convention. Each formula adds two manifest entries (`application/vnd.oasis.opendocument.formula` for the folder, `text/xml` for its content). LibreOffice renders inline math correctly without further editing.

### Citations from BibTeX or CSL-JSON

```bash
# Bulk pandoc-style placeholder replacement (recommended for prose templates):
python3 skills/odt/scripts/fill_citations.py template.odt \
    --source refs.bib -o output.odt
# Scans for [@bibkey] markers and replaces each with text:bibliography-mark.

# Single citation by text anchor:
python3 skills/odt/scripts/add_citation.py input.odt \
    --anchor "earlier studies" --source refs.json --key Mueller2020 -o output.odt

# Inspect:
python3 skills/odt/scripts/list_citations.py output.odt --json
```

LibreOffice renders citations through its bibliography style and generates the bibliography index from the inserted `text:bibliography-mark` elements. BibTeX support requires `pip install open-document-skills[scholarly]`; CSL-JSON uses stdlib only.

## Spreadsheet authoring: ranges, validation, charts (ODS)

ODS v0.6 adds direct ODF-native helpers for the three core spreadsheet features beyond plain cells:

```bash
# Named range — reusable in formulas as a name:
python3 skills/ods/scripts/add_named_range.py wb.ods \
    --name Sales --range 'Sheet1.B2:B100' -o wb.ods

# Named expression — formula/constant alias:
python3 skills/ods/scripts/add_named_range.py wb.ods \
    --name TaxRate --expression '0.19' -o wb.ods

# Dropdown for data entry:
python3 skills/ods/scripts/add_data_validation.py wb.ods \
    --name months --type list --values 'Jan,Feb,Mar,Apr' \
    --apply 'Sheet1.A2:A100' -o wb.ods

# Bar chart embedded into a cell:
python3 skills/ods/scripts/add_chart.py wb.ods --type bar \
    --data 'Sheet1.A1:B10' --title 'Q1 Sales' \
    --cell 'Sheet1.D1' -o wb.ods

# Inspect:
python3 skills/ods/scripts/list_named_ranges.py wb.ods --json
python3 skills/ods/scripts/list_charts.py wb.ods --json
```

Chart types: `bar`, `line`, `pie`, `scatter`. Charts use the LibreOffice-native `Object N/` sub-package convention (parallel to v0.4 MathML formulas) — two manifest entries per chart, `application/vnd.oasis.opendocument.chart` MIME for the directory and `text/xml` for `Object N/content.xml`. LibreOffice renders charts when opening or converting to PDF.

The `validate_refs.py` ODS validator detects: unknown sheet names in named-range targets, duplicate named-range/expression names, dangling `table:content-validation-name` references, and missing chart `Object N/` package targets.

## Schema validation (--strict)

`validate_refs.py --strict` runs OASIS ODF 1.3 RelaxNG validation against `content.xml` and `META-INF/manifest.xml`. The OASIS `content` schema is shared across formats, so the `--strict` flag works for all four — ODT, ODP, ODS, and ODG. The schemas are downloaded once on first use to `~/.cache/open-document-skills/schemas/` and reused afterwards.

```bash
pip install open-document-lib[validate]
python3 skills/odt/scripts/validate_refs.py output.odt --strict
python3 skills/ods/scripts/validate_refs.py output.ods --strict
python3 skills/odp/scripts/validate_refs.py output.odp --strict
python3 skills/odg/scripts/validate_refs.py output.odg --strict
```

Without `--strict`, only the internal consistency checks run (manifest, media, style references, note ids, citation identifiers, cross-references). Use `--strict` before delivery if exact OASIS conformance matters; the strict check catches non-trivial issues like `text:p` containing content the schema does not permit. Note that LibreOffice-native files often use ODF 1.3 *extended* features (`loext:` extensions) that the pure OASIS schema rejects — `--strict` is strictest against documents the skills generate themselves.

## DAO branded template (example)

The `examples/dao/` directory ships a complete grant-proposal pipeline with DAO branding:

```bash
python3 examples/dao/build_grant_proposal.py
# Output: examples/dao/output/grant_proposal.{odt,pdf}
```

The build runs `create_minimal_odt.py` then injects `examples/dao/styles.xml` (Nunito Sans, `#02416C`, DFG-Antrag margins, logo placeholder header, page-number footer) before filling citations, footnotes, cross-references, and a LaTeX math formula.

## Branded deck (example)

The `examples/deck/` directory ships a branded presentation pipeline:

```bash
python3 examples/deck/build_deck.py
# Output: examples/deck/output/deck.{odp,pdf}
```

The build runs `create_minimal_odp.py`, then injects `examples/deck/styles.xml`
(deep-blue background, light typography) and embeds a logo. Because the branded
`styles.xml` redefines the same named styles the generator emits, the injection
swaps the whole theme without touching `content.xml`.

## Flat ODF (Git-friendly)

Every format has `pack_*` and `unpack_*` scripts that convert between the zipped ODF package and a flat single-XML file (`.fodt`, `.fodp`, `.fods`, `.fodg`). Flat ODF is part of the OASIS specification, opens directly in LibreOffice, and produces readable diffs under Git.

```bash
python3 skills/odt/scripts/pack_fodt.py document.odt -o document.fodt
git diff document.fodt
python3 skills/odt/scripts/unpack_fodt.py document.fodt -o document.odt
```

Embedded images are inlined as base64 inside `<office:binary-data>` when packing, and extracted back to `Pictures/` on unpack. The mimetype is preserved via the `office:mimetype` attribute on the root.

## Examples

Build all example files:

```bash
python3 examples/build_examples.py
```

Build and run optional QA:

```bash
python3 examples/build_examples.py --render --png
```

