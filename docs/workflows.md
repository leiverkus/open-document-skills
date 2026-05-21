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

