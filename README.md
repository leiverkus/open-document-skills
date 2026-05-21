# Open Document Skills

Codex skills for working with OpenDocument Format files directly:

- `odt` - OpenDocument Text / LibreOffice Writer
- `odp` - OpenDocument Presentation / LibreOffice Impress
- `ods` - OpenDocument Spreadsheet / LibreOffice Calc
- `odg` - OpenDocument Graphics / LibreOffice Draw

The skills favor native ODF package/XML workflows over unnecessary DOCX/PPTX/XLSX round trips. Each skill includes small Python helper scripts for direct generation, package inspection, XML-safe edits, validation, and rendering/export workflows where LibreOffice is available.

## What This Is

These are Codex skills: self-contained folders with a `SKILL.md` file and optional scripts. They teach Codex how to handle a specific file family with repeatable workflows and bundled tools.

The goal is not to replace LibreOffice. The goal is to make automated ODF work safer by combining:

- format-specific instructions
- small deterministic scripts
- package/manifest validation
- smoke tests
- optional LibreOffice rendering/recalculation checks

## Repository Layout

```text
skills/
  odt/
    SKILL.md
    scripts/
  odp/
    SKILL.md
    scripts/
  ods/
    SKILL.md
    scripts/
  odg/
    SKILL.md
    scripts/
tests/
  test_smoke.py
```

Each skill is MIT-licensed and also contains its own `LICENSE.txt`.

## Installation

Copy the skill folders into your Codex skills directory:

```bash
cp -R skills/odt skills/odp skills/ods skills/odg ~/.agents/skills/
```

If your Codex setup uses another skills directory, copy the four folders there instead.

## Requirements

Core scripts use only the Python standard library.

Recommended optional tools:

- LibreOffice, for rendering/export/recalculation workflows
- `pdftoppm` from Poppler, when you want PDF pages rendered to images
- Pandoc, for some conversion fallback workflows

On macOS, LibreOffice usually provides `soffice` at:

```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice
```

The render/recalc scripts also look for common Linux and Windows locations.

## Skills

### ODT

OpenDocument Text / LibreOffice Writer.

Focus:

- template-first document editing
- direct ODT XML generation
- headings, paragraphs, lists, tables, footnotes, images
- style/page-layout awareness
- PDF QA through LibreOffice

Useful scripts:

```bash
python skills/odt/scripts/create_minimal_odt.py document.json output.odt
python skills/odt/scripts/extract_text.py output.odt
python skills/odt/scripts/inspect_package.py output.odt
python skills/odt/scripts/replace_text.py input.odt "{{NAME}}" "Patrick Leiverkus" -o output.odt
python skills/odt/scripts/add_image.py input.odt figure.png -o output.odt
python skills/odt/scripts/validate_refs.py output.odt
```

### ODP

OpenDocument Presentation / LibreOffice Impress.

Focus:

- template-first presentations
- direct ODP XML generation
- `draw:page`, speaker notes, master pages
- slide text/media inspection
- package and visual QA

Useful scripts:

```bash
python skills/odp/scripts/create_minimal_odp.py slides.json output.odp
python skills/odp/scripts/extract_text.py output.odp
python skills/odp/scripts/inspect_package.py output.odp
python skills/odp/scripts/clone_slide.py template.odp --source-slide 1 --name "Agenda" -o output.odp
python skills/odp/scripts/add_image.py input.odp figure.png -o output.odp
python skills/odp/scripts/validate_refs.py output.odp
```

### ODS

OpenDocument Spreadsheet / LibreOffice Calc.

Focus:

- direct ODS XML generation
- template-first spreadsheet editing
- typed cell values
- formulas
- repeated rows/cells
- CSV export and formula QA

Useful scripts:

```bash
python skills/ods/scripts/create_minimal_ods.py workbook.json output.ods
python skills/ods/scripts/extract_sheets.py output.ods
python skills/ods/scripts/extract_formulas.py output.ods
python skills/ods/scripts/replace_cells.py input.ods 'Data!B2=42' 'Data!C2=formula:of:=[.B2]*2' -o output.ods
python skills/ods/scripts/export_csv.py output.ods --sheet Data --output data.csv
python skills/ods/scripts/validate_refs.py output.ods
```

### ODG

OpenDocument Graphics / LibreOffice Draw.

Focus:

- direct ODG XML generation
- template-first diagram editing
- vector shapes, text boxes, lines, connectors, images
- geometry inspection
- PDF/SVG/PNG export QA

Useful scripts:

```bash
python skills/odg/scripts/create_minimal_odg.py drawing.json output.odg
python skills/odg/scripts/extract_text.py output.odg
python skills/odg/scripts/extract_shapes.py output.odg
python skills/odg/scripts/inspect_package.py output.odg
python skills/odg/scripts/replace_text.py input.odg "{{LABEL}}" "Updated label" -o output.odg
python skills/odg/scripts/validate_refs.py output.odg
```

## Testing

Run the dependency-free smoke tests:

```bash
python -m unittest discover -s tests
```

The tests create minimal ODT, ODP, ODS, and ODG files, then exercise extraction, validation, editing, media insertion, and export helpers that do not require LibreOffice.

GitHub Actions runs the same smoke test suite on every push and pull request.

## LibreOffice Workflows

Some workflows are intentionally optional because they require LibreOffice:

- render ODT/ODP/ODG to PDF or images
- export ODG to SVG/PNG
- recalculate ODS formulas
- round-trip conversions from DOCX/PPTX/XLSX or Markdown/HTML

The skills treat these as QA or interoperability steps. Native ODF package generation and XML-safe edits remain the preferred path when the target deliverable is an ODF file.

## Current Limits

The scripts are intentionally small and conservative.

They currently cover:

- minimal direct generation
- basic package validation
- text/formula/shape extraction
- XML-safe replacements
- image embedding
- repacking with `mimetype` first and uncompressed

They do not yet attempt to fully model every OpenDocument feature, such as:

- tracked changes and comments
- complex indexes and generated tables of contents
- advanced Impress animations
- complex Calc charts, named ranges, protection, and pivot tables
- advanced Draw glue points, groups, and custom path editing

Those should be added incrementally with fixtures and tests.

## Development

Recommended loop:

```bash
python -m unittest discover -s tests
git status --short
```

When adding a new script or behavior:

1. Add the smallest useful script interface.
2. Add or update a smoke test.
3. Run local tests.
4. Push and let GitHub Actions verify the repo.

## License

MIT. See [LICENSE](LICENSE).
