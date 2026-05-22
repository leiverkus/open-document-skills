# Roadmap

Living document. Subject to revision based on adoption signals from [Smithery](https://smithery.ai/skills/leiverkus/odt) and [skills.sh](https://skills.sh) and on real-world usage feedback. Updated when each milestone ships.

Current release: **v1.6.0** — see [CHANGELOG.md](CHANGELOG.md).

## Guiding principles

1. **Stdlib-only core stays stdlib-only.** Optional features (`lxml` for schema validation, `Pillow` for image probing) are opt-in dependencies. The base install must continue to work with nothing but Python's standard library.
2. **Template-first beats XML-from-scratch.** Direct generation is for minimal docs and tests. Real work uses a curated template; helpers edit it.
3. **Structure-preserving edits are non-negotiable.** Any new edit script must preserve inline children (`text:span`, `text:note`, `text:bookmark`, `text:a`) the way `replace_text_in_element` does.
4. **Audit-friendly by default.** Every edit operation updates `meta.xml`; every helper that touches the manifest stays idempotent.
5. **LibreOffice stays optional.** It is a render/QA/recalc helper, never a hard runtime dependency.

## v0.3 — Scholarly authoring ✅ shipped (2026-05-21)

Closed the largest gap relative to general-purpose tools (pandoc, docx skills): academic authoring with a proper apparatus.

- ✅ **`text:bibliography-mark` API** — `add_citation.py`, `list_citations.py`, `validate_refs.py` extension. BibTeX (via optional `bibtexparser`) and CSL-JSON (stdlib) ingestion.
- ✅ **Bulk citation flow** — `fill_citations.py` replaces pandoc-style `[@bibkey]` placeholders.
- ✅ **Footnote/endnote API** — `add_footnote.py`, `list_notes.py`, validate-refs duplicate-id check.
- ⏳ **`text:reference-ref` / `text:bookmark-ref`** — deferred to v0.4.
- ⏳ **MathML embedding** — deferred to v0.4.
- ⏳ **DAO example template** — deferred to v0.4.

## v0.4 — Authoring depth + DAO example ✅ shipped (2026-05-21)

- ✅ **Cross-references** — `add_bookmark.py`, `add_reference.py`, `add_sequence.py`, `list_refs.py`. Bookmarks (point + range), reference-marks, sequence numbering (Figure/Table/Equation), refs in all three flavors with display modes.
- ✅ **MathML embedding** — `add_math.py` with LaTeX (via optional Pandoc), raw MathML, or inline MathML; Object N/ sub-package convention.
- ✅ **DAO grant-proposal example** — `examples/dao/build_grant_proposal.py` end-to-end pipeline combining all v0.3 + v0.4 features.
- ⏳ **DAO branded template** (Nunito Sans, `#02416C`, master pages) — deferred to v0.5; the DAO example currently uses default styles.

## v0.5 — DAO branding + Robustness ✅ shipped (2026-05-21)

- ✅ DAO-branded template (Nunito Sans, `#02416C`, logo placeholder, DFG-standard margins, outline numbering)
- ✅ Cross-paragraph range bookmarks/refs via new `wrap_text_across_elements`
- ✅ RelaxNG schema validation (opt-in via `[validate]` extra; OASIS schemas downloaded on first use)
- ✅ Hypothesis property tests for walker/locator (5 invariants)
- ✅ Magic-byte MIME detection in `add_image.py` for all three formats

- **RelaxNG schema validation** against OASIS ODF 1.3 — opt-in `--strict` flag on `validate_refs.py`, depends on `lxml` (optional). Schemas bundled or downloaded from the OASIS registry on demand.
- **Property-based tests** (`hypothesis`) for `replace_text_in_element` — random paragraph trees with mixed inline children; invariants: structure preserved, total text length conserved (modulo replacements), no orphaned tail text.
- **Real-world corpus tests** — ~20 ODF fixtures harvested from LibreOffice/Collabora/AbiWord/Calligra exports (different versions). Round-trip each through pack/unpack and verify content equivalence.
- **Image probing** — magic-byte MIME sniffing in `add_image.py` (so `.png` with `.jpg` extension lands correctly in the manifest); optional Pillow-based aspect-ratio detection so `--width`/`--height` can be inferred.

## v0.6 — ODS depth ✅ shipped (2026-05-21)

- ✅ `add_named_range.py` (point + expression), `list_named_ranges.py`
- ✅ `add_data_validation.py` (list/number/date/text)
- ✅ `add_chart.py` with four types: bar, line, pie, scatter
- ✅ `list_charts.py`, validate_refs extended for ODS-specific checks

## v0.7 — ODP depth ✅ shipped (2026-05-21)

- ✅ Shape-level animations (entrance, exit, emphasis, motion paths)
- ✅ Slide transitions with all standard types
- ✅ Master-page customization (background, header, footer, logo, clone-to)
- ✅ validate_refs extended for animation target consistency

## v0.8 — ODG depth ✅ shipped (2026-05-21)

- ✅ Glue points (`add_gluepoint.py`)
- ✅ Connectors with shape-to-shape binding (`connect_shapes.py`)
- ✅ Group / ungroup (`group_shapes.py`, `ungroup.py`)
- ✅ Combined `list_structure.py` + validate_refs extensions

## v0.9 — Real-world corpus tests ✅ shipped (2026-05-22)

A pure robustness release — no new features. Closed the blind spot where helpers
implicitly assumed our own generators' output structure.

- ✅ **Corpus build pipeline** (`tests/fixtures/corpus/build_corpus.py`) — generates base files, enriches with the `add_*` skills, round-trips each through `soffice --convert-to` for LibreOffice-native structure.
- ✅ **17 committed corpus fixtures** spanning all four formats and every depth feature, MIT-licensed (content is ours).
- ✅ **`tests/test_corpus.py`** — roundtrip tests for every v0.2–v0.8 helper against each fixture; skips cleanly when the corpus is absent.
- ✅ **Two foreign-ODF bugs fixed**: `validate_refs.py` handling of trailing-slash-free `draw:object` refs and dangling `ObjectReplacements/` previews; `pack_flat_odf`/`unpack_flat_odf` preservation of full `Object N/` sub-packages (charts, formulas).

## v1.0 — Ecosystem maturity ✅ shipped (2026-05-22)

The maturity release: no new format features, just the steps that make the
project a dependable 1.0.

- ✅ **PyPI publication** — the shared library ships as `open-document-lib` (`pip install open-document-lib`). `lib/` was renamed to the PyPI-safe `odf_lib/`; `pyproject.toml` gained a build system and packaging metadata; a curated public API is documented in `docs/library-api.md`. `.github/workflows/publish.yml` uploads on release via Trusted Publishing.
- ✅ **Schema validation for all four formats** — `validate_refs.py --strict` (OASIS ODF 1.3 RelaxNG) extended from ODT to ODP/ODS/ODG via a shared `apply_strict_schema_check` helper. The test suite is the CI schema gate.
- ✅ **Performance benchmarks** — `benchmarks/run_benchmarks.py` measures large-document latency; representative numbers published in the README.
- ✅ **Final polish** — skill-trigger audit, README "Current Limits" refresh, CONTRIBUTING release-checklist fixes. Plus two robustness fixes: schema-clean table generation and per-invocation LibreOffice profiles.

## v1.1 — ODP presentation styling ✅ shipped (2026-05-22)

The first user-facing post-1.0 release. The ODP generator produced decks
LibreOffice rendered poorly — styleless frames showed as blue boxes,
text colour was uncontrollable, master backgrounds did not render.

- ✅ **`create_minimal_odp.py` designed default theme** — real `drawing-page`
  background style, no-fill `graphic` frame styles, text styled through the
  graphic style; no more blue boxes.
- ✅ **`customize_master.py --background-color` renders** — written into the
  `drawing-page` style the master references, in `office:automatic-styles`.
- ✅ **ODP `inject_styles_from_file` / `embed_pictures`** wrappers — a branded
  presentation `styles.xml` can be swapped in by name.
- ✅ **Branded deck example** — `examples/deck/`; the README hero is now a
  real ODP title slide. (Track C, partially delivered.)

## v1.2 — ODG drawing styling ✅ shipped (2026-05-22)

A review of all four formats after v1.1 found ODG carried the same
styling bug ODP had — and only ODG. ODT and ODS render plainly but
correctly.

- ✅ **`create_minimal_odg.py` designed default theme** — a designed
  `standard` graphic style, role styles, and a `drawing-page` background;
  no more generic-blue shapes.
- ✅ **Per-shape styling keys** — `fill`, `stroke`, `stroke-width`,
  `text-color`, `font-size`, `corner-radius` per spec item.
- ✅ **ODG `inject_styles_from_file` / `embed_pictures`** wrappers.
- ✅ **Branded flowchart example** — `examples/diagram/`. (Track C, further
  delivery.)

## Beyond 1.0 — three tracks

The format-feature roadmap is complete: four formats at production depth, a
published library, a real-world corpus. Further format depth has diminishing
returns without users pulling for it. Post-1.0 work is organised as three
tracks — **not** a fixed `vX.Y` schedule — pursued as time and adoption allow.

### Track A — Adoption

The project has strong code and few users; that is the real constraint.

- Follow the community plugin-directory submission through to listing.
- A flagship example: a realistic DFG/DAI-style research proposal — footnotes, BibTeX citations, cross-references, MathML, DAO branding — rendered to PDF and screenshotted in the README. The scholarly-German workflow is the differentiation against generic document tools.
- A README hero GIF/screenshot: JSON spec → rendered PDF.
- Watch the adoption signals (Smithery activations, PyPI downloads, GitHub stars) that this document says drive the pace.

### Track B — Packaging and quality hardening

The v1.0.1 `odf_lib`-bundling bug existed because CI only exercised the full
repo checkout, never an installed skill.

- CI matrix across Python 3.10–3.13 (the library declares `>=3.10`; CI runs only 3.12).
- A CI job that exercises the **installed** form — the single-skill / `npx skills` scenario — building on the `tests/test_install.py` regression tests.
- A `mypy`/`pyright` typecheck gate; the library already ships `py.typed`.

### Track C — Companion templates

Branded, ready-to-use templates (grant proposal, conference handout, poster)
for the academic niche — a separate repository depending on the core skills.
This is what turns the toolkit into something a non-technical researcher can
pick up directly; the highest-value piece of genuinely new work.

### Track D — Authoring ergonomics

Benchmarked against Anthropic's `docx`/`xlsx`/`pptx` skills. Those target
OOXML (Microsoft formats) while this project targets ODF, so they are
complements rather than competitors — but they set the bar for *how an
agent produces a good document with little friction*. Gaps found, ranked
by leverage:

1. **Authoring expressiveness — the biggest gap.** The Anthropic skills let
   the model author at a high level (`docx`: Markdown → docx via Pandoc;
   `pptx`: HTML → pptx). This project's JSON spec is low-level — it cannot
   express "a paragraph with one bold word and a link". A first-class
   **Markdown → ODT** path is the single highest-leverage change. → **v1.3.**
2. **Visual feedback loop.** The `pptx` skill *designs against rendered
   thumbnails*. `render.py` and the QA-loop docs exist here, but rendering
   is framed as QA, not as the primary design mechanism. A contact-sheet
   render mode + sharper SKILL.md guidance would close most of this. → **v1.4.**
3. **Tracked changes + comments (ODT).** The `docx` skill does redlining —
   a top review use case. ODF supports `text:tracked-changes` and
   `office:annotation`. → **v1.5.**
4. **Richer editing primitives.** Bulk restyle ("apply this style to every
   heading"), insert-section, table editing are thinner than the `docx`
   skill's formatting-preserving edits. → **v1.6.**
5. **ODS depth.** Conditional formatting and pivot tables — handled by
   `xlsx`, currently non-goals here.
6. **Polished template library.** Overlaps Track C.

Already at parity or ahead: stdlib-only with zero install friction; the
scholarly apparatus (footnotes, BibTeX citations, cross-references, MathML)
that the `docx` skill lacks first-class; flat-ODF Git diffs; RelaxNG schema
validation across all four formats; the real-world corpus tests.

## v1.3 — Markdown → ODT authoring ✅ shipped (2026-05-22)

Track D item 1: a first-class Markdown authoring path for ODT, so an agent
writes rich prose without hand-assembling block JSON.

- ✅ **`create_from_markdown.py`** — Markdown → styled ODT with a
  standard-library parser (`md_parser.py`, no Pandoc).
- ✅ **Inline rich text** — `text:span` runs, `text:a` links, `text:note`
  footnotes, GFM tables, embedded/linked images.
- ✅ **`examples/article/`** — a sample Markdown document.

## v1.4 — Visual feedback loop ✅ shipped (2026-05-22)

Track D item 2: make rendering the primary design mechanism, not only a
final check.

- ✅ **Contact-sheet render mode** — `render.py --contact-sheet` composes
  every page/slide into one labelled grid image (Pillow, optional `[render]`
  extra).
- ✅ **ODS `render.py`** — every format now renders through the skill tooling.
- ✅ **Consolidated render helpers** in `odf_lib` (`render_to_pdf`,
  `pdf_to_pngs`, `build_contact_sheet`); the four `render.py` are thin CLIs.
- ✅ **SKILL.md** reframed: render-early-and-iterate, not render-once-at-the-end.

## v1.5 — Tracked changes & comments (ODT) ✅ shipped (2026-05-22)

Track D item 3: redlining — record edits as tracked changes a human can
accept or reject, and attach comments.

- ✅ **Comments** — `add_comment.py` (point + range), `list_comments.py`;
  `office:annotation` with author, date, body.
- ✅ **Tracked changes** — `track_change.py` (`--insert`/`--delete`/
  `--replace`), `list_changes.py`; `text:tracked-changes` with
  `change-start`/`change-end`/`change` markers. New walker helper
  `extract_text_range_from_element` cuts a run out of the body for a
  tracked deletion.
- ✅ **Resolve** — `resolve_changes.py` accepts or rejects changes (`--all`
  or `--id`).

## v1.6 — Richer editing primitives (ODT) ✅ shipped (2026-05-22)

Track D item 4: structural editing of an existing document, matching the
`docx` skill's formatting-preserving edits.

- ✅ **`restyle.py`** — bulk-set `text:style-name` on paragraphs/headings
  matching `--current-style`, `--headings`/`--paragraphs`, `--level`.
- ✅ **`insert_blocks.py`** — splice a JSON `blocks` fragment in after/before
  an anchor, at a paragraph index, or at body start/end; shares the
  `build_block` dispatch with `create_minimal_odt.py`.
- ✅ **`delete_block.py`** — remove a paragraph/heading/list/table.
- ✅ **`edit_table.py`** — add/delete rows and columns, set cells, by table
  name; expands repeated-cell/row shorthands first.

### Versioning

`1.0.x` for bug fixes, shipped promptly; a `1.x` minor when something
user-facing lands (as v1.1/v1.2 did). A `2.0` only for a breaking change to
the published `open-document-lib` API — avoided unless clearly necessary.

## Explicit non-goals (stays in Current Limits)

These are intentionally out of scope. If you need them, use LibreOffice or another tool:

- **Whole-paragraph / cross-paragraph tracked deletions** — `track_change.py` records tracked deletions of a text run within one paragraph; deleting across paragraph boundaries is deferred. Tracked insertions and comments work anywhere.
- **Complex Calc pivots and conditional formatting** — build in LibreOffice for now, then read with our skills. Under reconsideration as Track D item 5.
- **Full Impress slide-master hierarchies** beyond simple page-layouts.
- **Full LibreOffice/Word-processor replacement.**
- **DOCX/PPTX/XLSX import-and-edit** — the whole point of this project is to avoid those round-trips. Use `pandoc` if you need DOCX in/out.

## How to influence the roadmap

- Open a GitHub issue with a concrete use case ("I need to do X with format Y, current scripts don't handle Z").
- Open a discussion if your use case overlaps multiple milestones — order may shift.
- Pull requests welcome — bug fixes, fixtures for under-tested cases, and the tracks above. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Pace

The v0.1–v1.0 roadmap is complete: all four formats have production depth, the library is published to PyPI, and the test suite plus real-world corpus guard against regressions. The project is now in **stable maintenance** — bug fixes ship promptly, and the three tracks above advance as adoption (Smithery activations, PyPI downloads, GitHub stars, issue volume) and time allow. Pausing to gather real-world usage is itself a valid state.

No specific release dates promised. Each release is a coherent unit and ships when it is feature-complete and tested.
