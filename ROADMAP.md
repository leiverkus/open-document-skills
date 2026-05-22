# Roadmap

Living document. Subject to revision based on adoption signals from [Smithery](https://smithery.ai/skills/leiverkus/odt) and [skills.sh](https://skills.sh) and on real-world usage feedback. Updated when each milestone ships.

Current release: **v1.0.0** — see [CHANGELOG.md](CHANGELOG.md).

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

## v1.x — Future

Direction beyond 1.0, driven by adoption signals and real-world use:

- **Companion template repository** — DAO/Solearis branded templates (grant proposal, handout, conference poster) as separate Smithery listings depending on the core skills.
- **CI typecheck** — `mypy`/`pyright` gate (the library already ships `py.typed`).
- **Deeper format coverage** as concrete use cases arrive — e.g. Calc pivot tables, richer chart styling, generated indexes — added incrementally with fixtures and tests.

## Explicit non-goals (stays in Current Limits)

These are intentionally out of scope. If you need them, use LibreOffice or another tool:

- **Tracked changes** (`text:tracked-changes`) — preservation is hard across tools; recommend round-tripping through LibreOffice for this.
- **Complex Calc pivots and conditional formatting** — build in LibreOffice, then read with our skills.
- **Full Impress slide-master hierarchies** beyond simple page-layouts.
- **Full LibreOffice/Word-processor replacement.**
- **DOCX/PPTX/XLSX import-and-edit** — the whole point of this project is to avoid those round-trips. Use `pandoc` if you need DOCX in/out.

## How to influence the roadmap

- Open a GitHub issue with a concrete use case ("I need to do X with format Y, current scripts don't handle Z").
- Open a discussion if your use case overlaps multiple milestones — order may shift.
- Pull requests welcome, especially toward v1.0 (PyPI packaging, performance benchmarks). See [CONTRIBUTING.md](CONTRIBUTING.md).

## Pace

Adoption signals (Smithery `totalActivations`, GitHub stars, issue volume) drive timing:

- **Strong pull**: v0.3 ships within 4–6 weeks of v0.2.1.
- **Moderate pull**: v0.4 first (polish makes the project look professional for later submissions/integrations), v0.3 follows.
- **Weak pull**: maintenance-mode releases; v0.3 work shifts to the personal DAO branch until usage materializes.

No specific release dates promised. Each milestone is a coherent unit; releases happen when the milestone is feature-complete and tested.
