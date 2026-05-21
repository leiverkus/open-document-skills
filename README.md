# Open Document Skills

[![Tests](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
  fixtures/
  test_smoke.py
  test_edge_cases.py
  test_libreoffice_integration.py
scripts/
  install_skills.py
examples/
  README.md
  build_examples.py
  *.json
```

Each skill is MIT-licensed and also contains its own `LICENSE.txt`.

## Installation

Install the four skills into the default Codex skills directory:

```bash
python3 scripts/install_skills.py
```

By default, the installer writes to `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise to:

```bash
~/.codex/skills
```

If your setup uses the older `.agents` directory, install there explicitly:

```bash
python3 scripts/install_skills.py --dest ~/.agents/skills
```

Existing skill directories are skipped by default. To intentionally overwrite the installed copies:

```bash
python3 scripts/install_skills.py --dest ~/.agents/skills --replace
```

To install from a local checkout:

```bash
git clone https://github.com/leiverkus/open-document-skills.git
cd open-document-skills
python3 scripts/install_skills.py
```

## Requirements

Core scripts use only the Python standard library.

Recommended optional tools:

- LibreOffice, for rendering/export/recalculation workflows
- `pdftoppm` from Poppler, when you want PDF pages rendered to images
- Pandoc, for some conversion fallback workflows

On macOS, install Poppler with Homebrew:

```bash
brew install poppler
```

LibreOffice usually provides `soffice` inside the app bundle, not directly on the shell `PATH`:

```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice
```

The render/recalc scripts look for that macOS path automatically. They also check common Linux and Windows locations.

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

Script reference:

| Script | Purpose |
| --- | --- |
| `create_minimal_odt.py` | Build a minimal ODT from a JSON document spec. |
| `extract_text.py` | Print visible document text, including footnotes. |
| `inspect_package.py` | Summarize package files, manifest entries, images, and document metadata. |
| `list_styles.py` | List styles found in `styles.xml` and `content.xml`. |
| `replace_text.py` | XML-safe text replacement in document content. |
| `add_image.py` | Add an image to the document package and manifest. |
| `pack_odt.py` | Repack an unpacked ODT directory with correct `mimetype` handling. |
| `render.py` | Render ODT to PDF, optionally PNG pages, through LibreOffice/Poppler. |
| `validate_refs.py` | Validate manifest and embedded image references. |

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

Script reference:

| Script | Purpose |
| --- | --- |
| `create_minimal_odp.py` | Build a minimal ODP from a JSON slide spec. |
| `extract_text.py` | Print slide text and speaker notes. |
| `inspect_package.py` | Summarize slides, notes, images, package files, and manifest entries. |
| `list_masters.py` | List master pages and page-layout references. |
| `clone_slide.py` | Clone a slide from a template deck with optional text replacements. |
| `replace_text.py` | XML-safe text replacement in slides and notes. |
| `add_image.py` | Add an image to a slide and update package references. |
| `pack_odp.py` | Repack an unpacked ODP directory with correct `mimetype` handling. |
| `render.py` | Render ODP to PDF, optionally PNG pages, through LibreOffice/Poppler. |
| `validate_refs.py` | Validate manifest and embedded image references. |

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

Script reference:

| Script | Purpose |
| --- | --- |
| `create_minimal_ods.py` | Build a minimal ODS workbook from a JSON spec. |
| `extract_sheets.py` | Print sheet cell values and formulas. |
| `extract_formulas.py` | Emit formulas as structured JSON. |
| `inspect_package.py` | Summarize package files, sheets, manifest entries, and metadata. |
| `list_styles.py` | List spreadsheet styles. |
| `replace_cells.py` | Set values or formulas by sheet and A1 address. |
| `export_csv.py` | Export one sheet to CSV. |
| `pack_ods.py` | Repack an unpacked ODS directory with correct `mimetype` handling. |
| `recalc.py` | Recalculate a workbook through LibreOffice and validate references. |
| `validate_refs.py` | Validate manifest/package references and basic formula errors. |

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

Script reference:

| Script | Purpose |
| --- | --- |
| `create_minimal_odg.py` | Build a minimal ODG drawing from a JSON spec. |
| `extract_text.py` | Print text from drawing pages and shapes. |
| `extract_shapes.py` | Emit drawing shapes, frames, geometry, and text as structured JSON. |
| `inspect_package.py` | Summarize pages, shapes, images, package files, and manifest entries. |
| `list_styles.py` | List Draw styles and page layouts. |
| `replace_text.py` | XML-safe text replacement in drawing content. |
| `add_image.py` | Add an image to a drawing page and update package references. |
| `pack_odg.py` | Repack an unpacked ODG directory with correct `mimetype` handling. |
| `render.py` | Export ODG to PDF, SVG, and/or PNG through LibreOffice. |
| `validate_refs.py` | Validate manifest, embedded image references, and basic geometry values. |

## Testing

Run the test suite:

```bash
python -m unittest discover -s tests
```

The tests create minimal ODT, ODP, ODS, and ODG files, then exercise extraction, validation, editing, media insertion, and export helpers.

LibreOffice integration tests are included. They render ODT/ODP/ODG files and recalculate ODS files when `soffice` is available. If LibreOffice is not available, those tests are skipped.

GitHub Actions runs the same suite on every push and pull request. The workflow installs LibreOffice and Poppler with `apt` on Ubuntu so the LibreOffice integration tests run in CI instead of being skipped.

Reusable example inputs live in `tests/fixtures/`:

- `odt_document.json`
- `odp_slides.json`
- `ods_workbook.json`
- `odg_drawing.json`
- `image.svg`

## Examples

Runnable examples live in `examples/`. They are meant as a practical first test layer for users of the skills:

```bash
python examples/build_examples.py
```

This creates ODT, ODP, ODS, and ODG files in `examples/output/`, then validates their package references. The generated output directory is ignored by Git.

For optional LibreOffice QA:

```bash
python examples/build_examples.py --render
```

On macOS, add `--png` when Poppler is installed with Homebrew and PNG page previews are useful:

```bash
python examples/build_examples.py --render --png
```

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development and release checklist.

## Release Status

Current release: `v0.1.1`.

This version is intended as a practical starting point: useful for direct ODF generation and inspection, with conservative scripts and growing test coverage. More advanced ODF features should be added incrementally with fixtures and tests.

## License

MIT. See [LICENSE](LICENSE).
