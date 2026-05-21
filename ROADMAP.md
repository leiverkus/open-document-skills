# Roadmap

Living document. Subject to revision based on adoption signals from [Smithery](https://smithery.ai/skills/leiverkus/odt) and [skills.sh](https://skills.sh) and on real-world usage feedback. Updated when each milestone ships.

Current release: **v0.2.1** — see [CHANGELOG.md](CHANGELOG.md).

## Guiding principles

1. **Stdlib-only core stays stdlib-only.** Optional features (`lxml` for schema validation, `Pillow` for image probing) are opt-in dependencies. The base install must continue to work with nothing but Python's standard library.
2. **Template-first beats XML-from-scratch.** Direct generation is for minimal docs and tests. Real work uses a curated template; helpers edit it.
3. **Structure-preserving edits are non-negotiable.** Any new edit script must preserve inline children (`text:span`, `text:note`, `text:bookmark`, `text:a`) the way `replace_text_in_element` does.
4. **Audit-friendly by default.** Every edit operation updates `meta.xml`; every helper that touches the manifest stays idempotent.
5. **LibreOffice stays optional.** It is a render/QA/recalc helper, never a hard runtime dependency.

## v0.3 — Scholarly authoring (priority for academic/DAO workflows)

The largest current gap relative to general-purpose tools (pandoc, docx skills) is academic authoring with a proper apparatus. v0.3 closes it.

- **`text:bibliography-mark` API** — read/write/list helpers; BibTeX and CSL-JSON ingestion; `add_citation.py`, `list_citations.py`, `validate_citations.py`.
- **`text:reference-ref` / `text:bookmark-ref`** — programmatic cross-references; `add_reference.py`, `list_bookmarks.py`, link validation in `validate_refs.py`.
- **MathML embedding** — `draw:object` with Math content; LaTeX-to-MathML via optional Pandoc fallback; round-trip with LibreOffice math formula objects.
- **Footnote/endnote API** — `add_footnote.py` producing correct `text:note` structure (citation, body, numbering); `list_notes.py` extracting structured citations.
- **DAO example** — `examples/dao/` with a Nunito Sans / `#02416C` template, a grant-proposal snippet, and an end-to-end walkthrough demonstrating citation insertion, cross-references, and footnote-rich prose. Becomes the canonical "is this useful for me?" demo in the README.

Estimated scope: ~6 new CLI scripts + ~3 new lib helpers + 10–15 tests per skill.

## v0.4 — Robustness

Polish the existing surface before adding new format depth.

- **RelaxNG schema validation** against OASIS ODF 1.3 — opt-in `--strict` flag on `validate_refs.py`, depends on `lxml` (optional). Schemas bundled or downloaded from the OASIS registry on demand.
- **Property-based tests** (`hypothesis`) for `replace_text_in_element` — random paragraph trees with mixed inline children; invariants: structure preserved, total text length conserved (modulo replacements), no orphaned tail text.
- **Real-world corpus tests** — ~20 ODF fixtures harvested from LibreOffice/Collabora/AbiWord/Calligra exports (different versions). Round-trip each through pack/unpack and verify content equivalence.
- **Image probing** — magic-byte MIME sniffing in `add_image.py` (so `.png` with `.jpg` extension lands correctly in the manifest); optional Pillow-based aspect-ratio detection so `--width`/`--height` can be inferred.

## v0.5 — Format depth

Adds the most-requested features inside each format. Driven by what users actually ask for after v0.3 ships.

- **ODS** — named ranges (`table:named-range`), basic chart objects (line, bar), data validation (`table:content-validation`).
- **ODP** — animation primitives (entrance/exit on shape level), slide transitions.
- **ODG** — glue points, connector routing, group/ungroup operations.

## v1.0 — Ecosystem maturity

- **PyPI publication of the library** — extract `lib/odf_common.py` as the standalone `open-document-lib` package; the skill scripts continue to depend on it. Third-party Python projects can `pip install open-document-lib` and use the helpers without skill bundling.
- **Companion template repository** — DAO/Solearis branded templates (grant proposal, handout, conference poster) published as separate Smithery listings, depending on the core skills.
- **Performance benchmarks** — measured edit latency on 1000+ page documents, 100k+ cell spreadsheets, 100+ slide decks. Published in the README so consumers know the limits.
- **CI schema gate** — every generated test output passes ODF 1.3 validation as a CI hard requirement.

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
- Pull requests welcome, especially for v0.4 (robustness) and v0.5 (format depth). See [CONTRIBUTING.md](CONTRIBUTING.md).

## Pace

Adoption signals (Smithery `totalActivations`, GitHub stars, issue volume) drive timing:

- **Strong pull**: v0.3 ships within 4–6 weeks of v0.2.1.
- **Moderate pull**: v0.4 first (polish makes the project look professional for later submissions/integrations), v0.3 follows.
- **Weak pull**: maintenance-mode releases; v0.3 work shifts to the personal DAO branch until usage materializes.

No specific release dates promised. Each milestone is a coherent unit; releases happen when the milestone is feature-complete and tested.
