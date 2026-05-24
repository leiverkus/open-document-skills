# Open Document Skills

[![Tests](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/leiverkus/open-document-skills/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/open-document-lib)](https://pypi.org/project/open-document-lib/)
[![Python](https://img.shields.io/pypi/pyversions/open-document-lib)](https://pypi.org/project/open-document-lib/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A complete native-ODF skill set for agents — generate, edit, validate, brand, and convert all four OpenDocument formats (ODT / ODP / ODS / ODG) without a DOCX detour.**

Four self-contained skills for Codex, Claude Code, OpenCode, and any agent runtime that supports the `SKILL.md` convention. Production-deep across all four OpenDocument formats: generation, structure-preserving edits, scholarly authoring (footnotes, citations, MathML, generated indexes), curated templates and themes, RelaxNG validation, bidirectional bridges to DOCX / XLSX / PPTX, and PDF rendering — all driven from stdlib-only Python with LibreOffice as an optional QA companion.

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
| [`odt`](skills/odt) | Writer | [smithery.ai/skills/leiverkus/odt](https://smithery.ai/skills/leiverkus/odt) | author from Markdown, edit ODT, footnotes, citations (BibTeX/CSL-JSON), bookmarks, cross-references, figure/table sequences, MathML formulas, generated indexes, tracked changes, **5 shipped templates** (grant proposal, academic paper, letterhead, CV, dissertation), DOCX bridge, render to PDF |
| [`odp`](skills/odp) | Impress | [smithery.ai/skills/leiverkus/odp](https://smithery.ai/skills/leiverkus/odp) | clone slide, edit notes, add image, named slide layouts, multiple master pages, animations (entrance/exit/emphasis/motion), slide transitions, master-page customization, **3 shipped templates** (dao-conference, academic-blue, minimalist-mono), PPTX bridge, render deck |
| [`ods`](skills/ods) | Calc | [smithery.ai/skills/leiverkus/ods](https://smithery.ai/skills/leiverkus/ods) | set cells/formulas, named ranges, dropdowns + data validation, embedded charts (bar/line/pie/scatter), conditional formatting, pivot tables, XLSX bridge, export CSV, recalculate |
| [`odg`](skills/odg) | Draw | [smithery.ai/skills/leiverkus/odg](https://smithery.ai/skills/leiverkus/odg) | edit labels, add shape image, glue points, connectors with shape binding, groups, flowcharts, org charts, export SVG/PNG |

## What makes this different

- **Native ODF — with an OOXML bridge.** Generation and editing stay native (no font drift, no lost styles); when interop demands it, `convert.py` per skill round-trips through Microsoft Office formats (DOCX / XLSX / PPTX, plus legacy DOC / XLS / PPT) via headless LibreOffice. No tool in the agent ecosystem covers both directions natively.
- **Stdlib-only core.** Every generator, validator, and edit script runs without `pip install` — `xml.etree.ElementTree` and `zipfile` only. LibreOffice is optional, needed for rendering, formula recalculation, generated-index refresh, and the OOXML bridge.
- **Structure-preserving edits.** `replace_text` keeps inline children (`text:span`, `text:note`, `text:bookmark`, `text:a`) intact; `add_image` updates the manifest and `meta.xml`; `replace_cells` handles typed values and formulas. No tool flattens your formatting.
- **Scholarly authoring, end-to-end.** Footnotes, endnotes, citations (BibTeX or CSL-JSON), cross-references, MathML formulas (LaTeX→MathML via Pandoc), and generated indexes (table of contents, bibliography, illustration/table index, alphabetical index) — refreshed via headless LibreOffice. The only ODF-agent suite with this depth.
- **Curated template ecosystem.** Five English-first ODT templates (grant proposal, academic paper, letterhead, CV, dissertation) and three branded ODP templates ship in-box; an `inspect_template` / `extract_template` / `apply_template` toolchain lets users bring their own from any `.odt` / `.ott` / `.docx` / `.odp` / `.otp` / `.pptx`. Templates are bundled into every Smithery / skills.sh / Claude Code plugin install.
- **Audit- and Git-friendly.** Every edit writes `meta:modification-date`, `meta:generator`, and increments `meta:editing-cycles`. Pack to flat ODF (`.fodt` / `.fodp` / `.fods` / `.fodg`) and `git diff` shows real, reviewable changes — embedded images and all.
- **Tested.** 403 unit, integration, and property-based tests on every push across Python 3.10–3.13. CI installs LibreOffice so the render / recalc / convert / index-refresh paths are exercised, validates against the OASIS ODF 1.3 RelaxNG schema with `--strict`, and runs `tests/test_corpus.py` against LibreOffice-roundtripped real-world fixtures to catch regressions native-LO files would surface.

## What the four skills cover

| Skill | Generation | Editing | Format-specific |
|---|---|---|---|
| **ODT** | spec-driven; Markdown → ODT with rich inline (`text:span`, links, GFM tables, footnotes); **5 shipped templates** | structure-preserving text/image edits; bulk restyle; block insert/delete; table editing (rows, columns, cells); tracked changes; comments | footnotes, citations (BibTeX/CSL-JSON), cross-references, MathML, generated indexes (TOC, bibliography, illustration/alphabetical index) |
| **ODP** | spec-driven with six standard slide layouts and multiple master pages; **3 shipped templates** | per-slide layout/master reassignment; clone slide; add image; master-page customization (background, header/footer, logo) | animations (entrance/exit/emphasis/motion paths), slide transitions, contact-sheet visual design loop |
| **ODS** | spec-driven, themed header rows | typed cells, formulas, named ranges, data validation (dropdowns + range constraints) | embedded charts (bar/line/pie/scatter), conditional formatting, pivot tables (computed + refreshable), formula recalc via soffice |
| **ODG** | spec-driven with role-styled shapes; per-shape styling keys | edit labels; add shape image; per-shape colours | connectors with shape binding, glue points, groups; flowcharts, org charts; PDF/SVG/PNG export |

**Shared by all four**: `--theme NAME` (5 curated palette + font pairings); RelaxNG `--strict` validation against the OASIS ODF 1.3 schema; flat-ODF roundtrip; `render.py` to PDF / per-page PNG / contact sheet; MIME-byte-detected image embedding; `meta.xml` lifecycle on every edit; bidirectional `convert.py` to/from the matching Microsoft Office format (ODT ↔ DOCX/DOC, ODS ↔ XLSX/XLS, ODP ↔ PPTX/PPT).

## Out of scope

- **In-place native-OOXML editing** (open `.docx`/`.xlsx`/`.pptx`, edit as DOCX/XLSX/PPTX, save back as DOCX/XLSX/PPTX) — use `python-docx`, `openpyxl`, `python-pptx`, or `pandoc`. One-shot conversion in either direction ships via `convert.py`; for sustained DOCX work the natural pattern is `convert.py → edit as ODF → convert.py` back.
- **Master-page inheritance chains** — ODF has no such concept; slides reference a master page and a slide layout independently, both supported.

See [ROADMAP.md](ROADMAP.md) for the trajectory across the v0.2 – v1.13 releases.

## Documentation

Detailed documentation lives in [docs/index.md](docs/index.md):

- [Installation](docs/installation.md)
- [Agent Compatibility](docs/agent-compatibility.md)
- [OpenDocument Workflows](docs/workflows.md)
- [Script Reference](docs/script-reference.md)
- [Library API](docs/library-api.md)
- [Repository Layout](docs/repository-layout.md)

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
- refresh generated indexes in ODT (table of contents, bibliography, alphabetical index)
- convert between ODF and Microsoft Office formats (DOCX/XLSX/PPTX, and legacy DOC/XLS/PPT)
- round-trip conversions from Markdown/HTML

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

## Contributing & releases

Development setup, the test loop, and the release checklist live in
[CONTRIBUTING.md](CONTRIBUTING.md). Version history is in
[CHANGELOG.md](CHANGELOG.md); planned work is in [ROADMAP.md](ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).
