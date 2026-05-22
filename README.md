# Open Document Skills

[![Tests](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/leiverkus/open-document-skills)](https://github.com/leiverkus/open-document-skills/releases)

**Native ODT / ODP / ODS / ODG generation and editing for agents — no DOCX round-trips, no LibreOffice dependency for the core path.**

Four self-contained skills for Codex, Claude Code, and OpenCode that teach an agent to create, inspect, and edit OpenDocument files directly via Python (stdlib only). Edits preserve inline structure (`text:span`, `text:note`, `text:bookmark`, `text:a`), `meta.xml` is updated on every save, and flat single-XML formats (`.fodt`/`.fodp`/`.fods`/`.fodg`) give you Git-friendly diffs. LibreOffice is optional and only needed for rendering, recalculation, and PDF export.

```bash
# Generate, edit, validate, version — all from the agent shell:
python skills/odt/scripts/create_minimal_odt.py spec.json doc.odt
python skills/odt/scripts/replace_text.py doc.odt "{{NAME}}" "Patrick" -o out.odt
python skills/odt/scripts/pack_fodt.py out.odt -o out.fodt   # diff-friendly XML
python skills/odt/scripts/validate_refs.py out.odt
```

## Skills at a glance

| Skill | LibreOffice app | Smithery | Triggers |
| --- | --- | --- | --- |
| [`odt`](skills/odt) | Writer | [smithery.ai/skills/leiverkus/odt](https://smithery.ai/skills/leiverkus/odt) | edit ODT, footnotes, citations (BibTeX/CSL-JSON), bookmarks, cross-references, figure/table sequences, MathML formulas, render to PDF |
| [`odp`](skills/odp) | Impress | [smithery.ai/skills/leiverkus/odp](https://smithery.ai/skills/leiverkus/odp) | clone slide, edit notes, add image, animations (entrance/exit/emphasis/motion), slide transitions, master-page customization (background, header/footer, logo), render deck |
| [`ods`](skills/ods) | Calc | [smithery.ai/skills/leiverkus/ods](https://smithery.ai/skills/leiverkus/ods) | set cells/formulas, named ranges, dropdowns + data validation, embedded charts (bar/line/pie/scatter), export CSV, recalculate |
| [`odg`](skills/odg) | Draw | [smithery.ai/skills/leiverkus/odg](https://smithery.ai/skills/leiverkus/odg) | edit labels, add shape image, glue points, connectors with shape binding, groups, flowcharts, org charts, export SVG/PNG |

## Why use these

- **Native ODF, not converted from DOCX.** No font drift, no lost styles, no PDF round-trips.
- **Stdlib-only core.** Every generator, validator, and edit script runs without `pip install` — `xml.etree.ElementTree` and `zipfile` only. LibreOffice is needed only for rendering and recalculation.
- **Structure-preserving edits.** `replace_text` keeps footnotes, hyperlinks, and inline formatting intact. `add_image` updates the manifest and `meta.xml`. `replace_cells` handles typed values and formulas.
- **Audit-friendly.** Every edit writes `meta:modification-date`, `meta:generator`, and increments `meta:editing-cycles`. Pack to `.fodt` and `git diff` works.
- **Tested.** 76 unit + integration tests run on every push; CI installs LibreOffice so the render/recalc paths are exercised too.

## What this is not

Not a LibreOffice replacement. Not a substitute for full ODF feature coverage (tracked changes, complex TOCs, Impress animations, Calc pivots, Draw glue points, RelaxNG schema validation are explicit non-goals — see [Current Limits](#current-limits)). The goal is to make the 80% of ODF automation that agents need safe, repeatable, and dependency-light.

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
.claude-plugin/
  plugin.json
examples/
  README.md
  build_examples.py
  *.json
docs/
  index.md
```

Each skill is MIT-licensed and also contains its own `LICENSE.txt`.

## Documentation

Detailed documentation lives in [docs/index.md](docs/index.md):

- [Installation](docs/installation.md)
- [Agent Compatibility](docs/agent-compatibility.md)
- [OpenDocument Workflows](docs/workflows.md)
- [Script Reference](docs/script-reference.md)

## Installation

The skills are available through three channels — pick what fits your setup:

### Smithery (recommended for individual skills)

Browse and install via [smithery.ai](https://smithery.ai). Install one or more skills directly through the Smithery UI: [odt](https://smithery.ai/skills/leiverkus/odt), [odp](https://smithery.ai/skills/leiverkus/odp), [ods](https://smithery.ai/skills/leiverkus/ods), [odg](https://smithery.ai/skills/leiverkus/odg).

### Open Agent Skills CLI

The [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI installs across Claude Code, Codex, Cursor, OpenCode, and 50+ other agents:

```bash
# List skills in the repo
npx skills add leiverkus/open-document-skills --list

# Install all four globally for Claude Code
npx skills add leiverkus/open-document-skills --skill '*' -a claude-code -g

# Install only ODT into your project
npx skills add leiverkus/open-document-skills --skill odt
```

### Bundled installer (Codex / OpenCode / Claude Code)

Install all four skills at once via the bundled Python installer:

```bash
python3 scripts/install_skills.py
```

By default, the installer writes to `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise to:

```bash
~/.codex/skills
```

If your setup uses the older `.agents` directory, install there explicitly:

```bash
python3 scripts/install_skills.py --target agents
```

Existing skill directories are skipped by default. To intentionally overwrite the installed copies:

```bash
python3 scripts/install_skills.py --target agents --replace
```

For OpenCode global skills:

```bash
python3 scripts/install_skills.py --target opencode
```

To install project-local OpenCode skills:

```bash
python3 scripts/install_skills.py --target opencode --dest .opencode/skills
```

For Claude Code, this repository can be used as a skill-focused plugin because it contains `.claude-plugin/plugin.json` and a top-level `skills/` directory. To create a plugin bundle at a chosen destination:

```bash
python3 scripts/install_skills.py --target claude --dest ./dist/open-document-skills
```

Then add or install that plugin directory in Claude Code.

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

Install all optional tools on macOS with Homebrew:

```bash
brew install --cask libreoffice
brew install poppler pandoc
```

Install all optional tools on Windows with winget:

```powershell
winget install --id TheDocumentFoundation.LibreOffice -e
winget install --id oschwartz10612.Poppler -e
winget install --id JohnMacFarlane.Pandoc -e
```

Install all optional tools on Ubuntu with apt:

```bash
sudo apt-get update
sudo apt-get install -y libreoffice poppler-utils pandoc
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
python skills/odt/scripts/add_footnote.py input.odt --anchor "claim" --body "Source: ..." -o output.odt
python skills/odt/scripts/fill_citations.py template.odt --source refs.bib -o output.odt
python skills/odt/scripts/add_bookmark.py input.odt --name K1 --anchor "Chapter 1" -o output.odt
python skills/odt/scripts/add_math.py input.odt --latex 'E = mc^2' --anchor "Equation" -o output.odt
python skills/odt/scripts/pack_fodt.py output.odt -o output.fodt
python skills/odt/scripts/validate_refs.py output.odt
```

Script reference: see [docs/script-reference.md](docs/script-reference.md).

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

Script reference: see [docs/script-reference.md](docs/script-reference.md).

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

Script reference: see [docs/script-reference.md](docs/script-reference.md).

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

Script reference: see [docs/script-reference.md](docs/script-reference.md).

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

## Flat ODF (Git-friendly)

Every format has `pack_*` and `unpack_*` scripts that convert between the zipped ODF package and a flat single-XML file (`.fodt`, `.fodp`, `.fods`, `.fodg`). The flat form is part of the OASIS specification, opens directly in LibreOffice, and produces readable diffs under Git. Embedded images are inlined as base64 on pack and extracted back to `Pictures/` on unpack.

```bash
python skills/odt/scripts/pack_fodt.py document.odt -o document.fodt
git diff document.fodt
python skills/odt/scripts/unpack_fodt.py document.fodt -o document.odt
```

See [docs/workflows.md](docs/workflows.md#flat-odf-git-friendly) for details.

## Performance

The helpers are pure-Python and stream through ZIP packages without loading
LibreOffice. End-to-end CLI latency on a representative laptop:

| Format | Document | Create | Edit | Validate |
|--------|----------|--------|------|----------|
| ODT | 2000 paragraphs | 55 ms | 54 ms (`replace_text`) | 48 ms |
| ODS | 100 000 cells (1000×100) | 398 ms | 428 ms (`replace_cells`) | 689 ms |
| ODP | 100 slides | 45 ms | 42 ms (`clone_slide`) | 42 ms |
| ODG | 500 shapes | 47 ms | — | 44 ms |

Every timing includes Python interpreter startup (~40 ms), so small
documents are startup-bound; large spreadsheets are the heaviest case and
still finish well under a second. Reproduce or re-measure with
[`benchmarks/run_benchmarks.py`](benchmarks/README.md). Numbers are
indicative and machine-dependent.

## Current Limits

The scripts are intentionally small and conservative.

They currently cover:

- minimal direct generation
- basic package validation
- text/formula/shape extraction
- XML-safe replacements that preserve inline `text:span`, `text:note`, `text:bookmark`, and `text:a`
- image embedding
- repacking with `mimetype` first and uncompressed
- `meta.xml` lifecycle updates on every edit (`modification-date`, `generator`, `editing-cycles`)
- flat ODF (`.fodt`/`.fodp`/`.fods`/`.fodg`) roundtrip

They do not yet attempt to fully model every OpenDocument feature, such as:

- tracked changes and comments
- complex indexes and generated tables of contents
- advanced Impress animations
- complex Calc charts, named ranges, protection, and pivot tables
- advanced Draw glue points, groups, and custom path editing
- RelaxNG validation against the OASIS ODF 1.3 schema

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

Current release: `v0.9.0` — a robustness release. Every helper is now exercised against a committed corpus of 17 LibreOffice-native ODF fixtures (`tests/test_corpus.py`), which uncovered and fixed two foreign-ODF bugs in `validate_refs` and the flat-ODF roundtrip. No new features — all four skills (ODT/ODP/ODS/ODG) remain at production-level depth. See [ROADMAP.md](ROADMAP.md) for v1.0 (PyPI publication + final polish + ecosystem maturity).

## License

MIT. See [LICENSE](LICENSE).
