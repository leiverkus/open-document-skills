# Open Document Skills

[![Tests](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/open-document-lib)](https://pypi.org/project/open-document-lib/)
[![Python](https://img.shields.io/pypi/pyversions/open-document-lib)](https://pypi.org/project/open-document-lib/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Native ODT / ODP / ODS / ODG generation and editing for agents — no DOCX round-trips, no LibreOffice dependency for the core path.**

Four self-contained skills for Codex, Claude Code, and OpenCode that teach an agent to create, inspect, and edit OpenDocument files directly via Python (stdlib only). Edits preserve inline structure (`text:span`, `text:note`, `text:bookmark`, `text:a`), `meta.xml` is updated on every save, and flat single-XML formats (`.fodt`/`.fodp`/`.fods`/`.fodg`) give you Git-friendly diffs. LibreOffice is optional and only needed for rendering, recalculation, and PDF export.

<p align="center">
  <img src="docs/assets/hero.png" alt="A branded presentation title slide generated from a JSON spec — deep-blue theme, white typography, logo" width="640">
  <br>
  <em>A branded title slide generated from a JSON spec and rendered with LibreOffice — a curated theme injected as <code>styles.xml</code>, in pure Python. See <a href="examples/deck/">examples/deck</a>.</em>
</p>

```bash
# Generate, edit, validate, version — all from the agent shell:
python skills/odt/scripts/create_from_markdown.py article.md doc.odt   # rich text from Markdown
python skills/odt/scripts/replace_text.py doc.odt "{{NAME}}" "Patrick" -o out.odt
python skills/odt/scripts/pack_fodt.py out.odt -o out.fodt   # diff-friendly XML
python skills/odt/scripts/validate_refs.py out.odt
```

## Skills at a glance

| Skill | LibreOffice app | Smithery | Triggers |
| --- | --- | --- | --- |
| [`odt`](skills/odt) | Writer | [smithery.ai/skills/leiverkus/odt](https://smithery.ai/skills/leiverkus/odt) | author from Markdown, edit ODT, footnotes, citations (BibTeX/CSL-JSON), bookmarks, cross-references, figure/table sequences, MathML formulas, render to PDF |
| [`odp`](skills/odp) | Impress | [smithery.ai/skills/leiverkus/odp](https://smithery.ai/skills/leiverkus/odp) | clone slide, edit notes, add image, animations (entrance/exit/emphasis/motion), slide transitions, master-page customization (background, header/footer, logo), render deck |
| [`ods`](skills/ods) | Calc | [smithery.ai/skills/leiverkus/ods](https://smithery.ai/skills/leiverkus/ods) | set cells/formulas, named ranges, dropdowns + data validation, embedded charts (bar/line/pie/scatter), conditional formatting, pivot tables, export CSV, recalculate |
| [`odg`](skills/odg) | Draw | [smithery.ai/skills/leiverkus/odg](https://smithery.ai/skills/leiverkus/odg) | edit labels, add shape image, glue points, connectors with shape binding, groups, flowcharts, org charts, export SVG/PNG |

## Why use these

- **Native ODF, not converted from DOCX.** No font drift, no lost styles, no PDF round-trips.
- **Stdlib-only core.** Every generator, validator, and edit script runs without `pip install` — `xml.etree.ElementTree` and `zipfile` only. LibreOffice is needed only for rendering and recalculation.
- **Structure-preserving edits.** `replace_text` keeps footnotes, hyperlinks, and inline formatting intact. `add_image` updates the manifest and `meta.xml`. `replace_cells` handles typed values and formulas.
- **Audit-friendly.** Every edit writes `meta:modification-date`, `meta:generator`, and increments `meta:editing-cycles`. Pack to `.fodt` and `git diff` works.
- **Tested.** Over 200 unit and integration tests run on every push across Python 3.10–3.13; CI installs LibreOffice so the render/recalc paths are exercised too.

## What this is not

Not a LibreOffice replacement, and not a substitute for full ODF feature coverage. Generated tables of contents and DOCX/PPTX/XLSX import-and-edit are explicit non-goals. See [Current Limits](#current-limits). The goal is to make the 80% of ODF automation that agents need safe, repeatable, and dependency-light.

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
- [Library API](docs/library-api.md)

## Installation

The skills are available through three channels — pick what fits your setup:

### Smithery (recommended for individual skills)

Browse and install via [smithery.ai](https://smithery.ai). Install one or more skills directly through the Smithery UI: [odt](https://smithery.ai/skills/leiverkus/odt), [odp](https://smithery.ai/skills/leiverkus/odp), [ods](https://smithery.ai/skills/leiverkus/ods), [odg](https://smithery.ai/skills/leiverkus/odg).

### Claude Code plugin marketplace

The repository is also a Claude Code plugin marketplace. Add it once, then install the plugin — all four skills come bundled:

```text
/plugin marketplace add leiverkus/open-document-skills
/plugin install open-document-skills@leiverkus-skills
```

`/plugin marketplace update` pulls later releases.

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

## Python library

The shared library behind the four skills is published to PyPI as
[`open-document-lib`](https://pypi.org/project/open-document-lib/). Use it
directly in any Python project — no skill bundling required:

```bash
pip install open-document-lib
```

```python
from odf_lib import pack_flat_odf, replace_text_in_element, validate_against_schema
```

The core has no dependencies beyond the standard library; `[validate]`
pulls in `lxml` for RelaxNG validation and `[scholarly]` pulls in
`bibtexparser`. See [docs/library-api.md](docs/library-api.md) for the
full public API.

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

The scripts are intentionally small and conservative, but production-deep
across all four formats.

They cover:

- direct generation, template-based editing, and Markdown → ODT authoring with inline rich text, links, tables, and footnotes
- package validation, including optional RelaxNG validation against the
  OASIS ODF 1.3 schema (`validate_refs.py --strict`, all four formats)
- text/formula/shape extraction
- XML-safe replacements that preserve inline `text:span`, `text:note`, `text:bookmark`, and `text:a`
- scholarly authoring — footnotes, endnotes, citations (BibTeX/CSL-JSON), cross-references, MathML
- document review — comments and tracked changes (record edits, then accept or reject)
- structural editing — bulk restyle, insert/delete blocks, table editing (rows, columns, cells)
- spreadsheets — named ranges, data validation, embedded charts, conditional formatting, pivot tables
- presentations — designed default styling, branded-theme injection, animations, slide transitions, master-page customization
- drawings — designed styling with per-shape colours, connectors with shape binding, glue points, shape groups
- rendering to PDF, per-page PNG, or a single contact sheet — a visual design loop, not just final QA
- image embedding with magic-byte MIME detection
- `meta.xml` lifecycle updates on every edit (`modification-date`, `generator`, `editing-cycles`)
- flat ODF (`.fodt`/`.fodp`/`.fods`/`.fodg`) roundtrip

They intentionally do **not** model every OpenDocument feature.
Some gaps stay out of scope — use LibreOffice for these:

- generated indexes and tables of contents (LibreOffice builds these from the markers the skills set)
- full Impress slide-master hierarchies beyond simple page layouts
- DOCX/PPTX/XLSX import-and-edit — use `pandoc` if you need those round-trips

See [ROADMAP.md](ROADMAP.md) for what is planned next.

## Contributing & releases

Development setup, the test loop, and the release checklist live in
[CONTRIBUTING.md](CONTRIBUTING.md). Version history is in
[CHANGELOG.md](CHANGELOG.md); planned work is in [ROADMAP.md](ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).
