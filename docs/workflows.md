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

Author from Markdown:

```bash
python3 skills/odt/scripts/create_from_markdown.py article.md example.odt
```

`create_from_markdown.py` is the high-level authoring path — write ordinary
Markdown (headings, bold/italic, links, nested lists, GFM tables, footnotes,
images) and get rich-text ODT with `text:span` runs. The parser is standard
library only, no Pandoc. See [examples/article/](#markdown-article-example).

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

### Slide layouts and masters (ODP)

ODP v1.8 adds named slide layouts and multiple master pages. A `draw:page`
references a master (background/chrome) and a slide layout
(`style:presentation-page-layout` — the placeholder zones) independently;
six layouts ship: `title-slide`, `title-content`, `two-content`,
`section-header`, `title-only`, `blank`.

```bash
# A spec with per-slide layouts and an extra master:
cat > deck.json <<'JSON'
{"masters": [{"name": "Brand", "background_color": "#02416C"}],
 "slides": [
   {"layout": "title-slide", "master": "Brand", "title": "Review", "subtitle": "2026"},
   {"layout": "two-content", "title": "Regions",
    "body_left": ["North", "East"], "body_right": ["South", "West"]}]}
JSON
python3 skills/odp/scripts/create_minimal_odp.py deck.json deck.odp

# Reassign layout/master on existing slides — placeholder frames are moved:
python3 skills/odp/scripts/set_layout.py deck.odp --slide 2 --layout title-only -o deck.odp
python3 skills/odp/scripts/list_masters.py deck.odp   # masters + layouts + usage
```

Specs without a `layout` key are unchanged — `title`/`body` fill the default
`title-content` layout. `validate_refs.py` flags slides whose master or
slide-layout reference does not resolve.

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

Render:

```bash
python3 skills/ods/scripts/render.py example.ods --outdir qa --contact-sheet
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

Style and brand:

`create_minimal_odg.py` emits a designed default theme — a designed `standard`
graphic style and role styles, so shapes never render as LibreOffice's generic
blue. Spec items accept per-shape styling keys (`fill`, `stroke`,
`stroke-width`, `text-color`, `font-size`, `corner-radius`). For a full branded
theme, write a curated `styles.xml` that redefines the same named styles and
inject it with `inject_styles_from_file` (see
[examples/diagram/](#branded-flowchart-example)).

## Visual design loop

Every format has a `render.py`. Treat rendering as a **design step**, not
only a final check: render an early draft, look at it, fix what is wrong,
then continue.

```bash
python3 skills/odp/scripts/render.py deck.odp --outdir qa --contact-sheet
python3 skills/odt/scripts/render.py doc.odt --outdir qa --png
```

`--contact-sheet` composes every page or slide into a **single labelled grid
image** — the fastest way to judge layout and cross-page consistency at a
glance. It needs LibreOffice, Poppler (`pdftoppm`), and Pillow
(`pip install open-document-lib[render]`). `--png` writes one image per page;
plain `render.py` writes a PDF.

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

## Document review: tracked changes and comments (ODT)

Record edits as tracked changes a human can accept or reject, and attach
comments — the redlining workflow, ODF-native:

```bash
# Comment on a passage:
python3 skills/odt/scripts/add_comment.py doc.odt --anchor "claim" \
    --author "Reviewer" --text "Needs a source." -o reviewed.odt

# Record edits as tracked changes:
python3 skills/odt/scripts/track_change.py reviewed.odt \
    --replace "old wording" --with "clearer wording" --author "Reviewer" -o reviewed.odt

# Inspect, then accept or reject:
python3 skills/odt/scripts/list_changes.py reviewed.odt
python3 skills/odt/scripts/resolve_changes.py reviewed.odt --accept --all -o final.odt
```

LibreOffice shows tracked changes as underline (insertions) and
strike-through (deletions) with a change bar in the margin. Tracked
deletions operate on a text run within one paragraph; insertions and
comments work at any anchor.

## Structural editing (ODT)

Beyond `replace_text.py`, four scripts restructure an existing document:

```bash
# Bulk-restyle every heading:
python3 skills/odt/scripts/restyle.py doc.odt --headings --style "DAO-Heading-1" -o out.odt

# Insert a block fragment (JSON blocks array) after an anchor:
python3 skills/odt/scripts/insert_blocks.py doc.odt --blocks frag.json --after-anchor "Summary" -o out.odt

# Delete a block; edit a table by name:
python3 skills/odt/scripts/delete_block.py doc.odt --anchor "Obsolete section" -o out.odt
python3 skills/odt/scripts/edit_table.py doc.odt --table "Results" --add-row 2024 1500 -o out.odt
```

`insert_blocks.py` reuses the `blocks` JSON format of `create_minimal_odt.py`,
so one call can splice in a whole multi-block fragment. `edit_table.py`
supports `--add-row`/`--add-column`/`--delete-row`/`--delete-column`/
`--set-cell`.

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

## Conditional formatting and pivot tables (ODS)

ODS v1.7 adds conditional highlighting and pivot tables:

```bash
# Conditional formatting — highlight cells by value or formula. Rules stack:
python3 skills/ods/scripts/add_conditional_format.py wb.ods \
    --range 'Data.B2:B100' --condition 'value > 100' \
    --background '#C8E6C9' --text-color '#1B5E20' -o wb.ods
python3 skills/ods/scripts/add_conditional_format.py wb.ods \
    --range 'Data.B2:B100' --condition 'value < 50' \
    --background '#FFCDD2' --bold -o wb.ods

# Pivot table — group, aggregate, and write the result grid + definition:
python3 skills/ods/scripts/add_pivot_table.py wb.ods \
    --source 'Data.A1:D100' --rows Region,Product --columns Quarter \
    --data Revenue --function sum --target 'Pivot.A1' -o wb.ods

# Inspect:
python3 skills/ods/scripts/list_pivot_tables.py wb.ods --json
```

Conditions accept `value OP N` (`>`, `<`, `>=`, `<=`, `=`, `!=`), `value between A B`,
`value not-between A B`, and `formula:EXPR`. Each rule is written both as a
`calcext:conditional-format` (the form LibreOffice renders) and as an ODF-core
`style:map`. The `calcext` namespace is a documented LibreOffice extension; under
`--strict` it is excluded from the OASIS core-schema check and reported as a warning.

Pivot tables are computed in Python (group-by + aggregation with `sum`/`count`/
`average`/`min`/`max`) and the result grid is written into the target range, so
LibreOffice shows it immediately. A matching ODF-core `table:data-pilot-table`
is written alongside, so LibreOffice treats it as a real, refreshable pivot.
`--rows` takes one or more comma-separated fields; `--columns` is optional; the
target sheet is created if it does not exist.

`validate_refs.py` additionally flags dangling `style:map` style references and
pivot tables whose source or target range names an unknown sheet.

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

## Branded flowchart (example)

The `examples/diagram/` directory ships a branded drawing pipeline:

```bash
python3 examples/diagram/build_diagram.py
# Output: examples/diagram/output/diagram.{odg,pdf}
```

The build runs `create_minimal_odg.py` (with per-shape `fill`/`stroke`/
`text-color` keys in `spec.json`), connects the nodes with `connect_shapes.py`,
then injects `examples/diagram/styles.xml` (a white-card theme on a light-grey
page). Per-shape overrides live in `content.xml`, so the theme swap re-themes
the default-styled shapes while the per-shape colours survive.

## Markdown article (example)

The `examples/article/` directory ships a sample Markdown document:

```bash
python3 skills/odt/scripts/create_from_markdown.py examples/article/sample.md article.odt
```

`sample.md` exercises every supported construct — headings, inline
formatting, links, nested lists, blockquotes, fenced code, a GFM table, a
thematic break, and a footnote. The conversion is pure Python; LibreOffice
is only needed for the optional PDF render.

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

