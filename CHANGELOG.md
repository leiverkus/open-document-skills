# Changelog

## v0.8.0 - 2026-05-21

ODG depth: glue points, connectors with shape-to-shape binding, group/ungroup. Final format-depth release before the v0.9 corpus tests + v1.0 polish.

### Added

- **Glue points (ODG)**:
  - `add_gluepoint.py` — `<draw:glue-point>` with `--position X,Y` (relative to shape size), `--escape direction` (up/down/left/right/auto/horizontal/vertical), `--id` (auto from 4; 0-3 are LibreOffice's built-in edge midpoints).
- **Connectors (ODG)**:
  - `connect_shapes.py` with `--from` / `--to` shape names, optional `--from-glue` / `--to-glue` glue-point IDs, types `standard`, `line`, `curve`, `--line-width`, `--page`.
  - Auto-assigns unique `draw:id` to source/target shapes when missing.
- **Groups (ODG)**:
  - `group_shapes.py` — wraps named shapes into `<draw:g>` preserving document order.
  - `ungroup.py` — dissolves a group by name or all groups on a page (`--all`).
- **`list_structure.py` (ODG)** — combined JSON inventory of groups, connectors, and glue points per page.
- **`validate_refs.py` (ODG)** extended: detects duplicate glue-point IDs per shape, dangling connector shape targets, dangling glue-point references on connectors, and empty groups.
- **`odg_common.py`** helpers: `ensure_shape_id`, `find_shape_by_name`, `iter_glue_points`.
- 14 new tests across `tests/test_odg_gluepoints.py`, `tests/test_odg_connectors.py`, `tests/test_odg_groups.py`. Total: 209 (was 197).

### Changed

- ODG `SKILL.md` description + triggers extended with glue point, Klebepunkt, connector, Verbinder, group, Gruppe, flowchart, Flussdiagramm, org chart, Organigramm, Mindmap.

## v0.7.0 - 2026-05-21

ODP depth: animations, slide transitions, master-page customization.

### Added

- **Animations (ODP)**:
  - `add_animation.py` with four effect categories — entrance (`appear`, `fade-in`, `fly-in`, `wipe-in`), exit (`disappear`, `fade-out`, `fly-out`, `wipe-out`), emphasis (`pulse`, `spin`, `grow-shrink`, `color-change`), and motion paths (`linear`, `arc`, `curve`).
  - `--direction`, `--duration`, `--delay`, `--trigger` flags for fine control.
  - Auto-assigns unique `draw:id` to target shapes when missing.
  - LibreOffice-compatible `ooo-*` preset-id mapping.
  - `list_animations.py` for JSON inventory.
- **Slide transitions (ODP)**:
  - `add_transition.py` with `--slide N|all|NAME`, types `fade`, `wipe`, `cover`, `uncover`, `push`, `dissolve`, `random`, plus `--direction`, `--duration`, and `--remove`.
  - `list_transitions.py` for inventory.
  - Auto-creates `style:style style:family="drawing-page"` under `office:automatic-styles`.
- **Master-page customization (ODP)**:
  - `customize_master.py` for background color/image, header/footer text, page-number visibility, logo embedding.
  - `--clone-to NEW_NAME` to create a derived master.
  - Reuses v0.5 `embed_pictures` for image embedding.
- **`odp_common.py`** helpers: `find_shape_by_name`, `ensure_shape_id`, `ensure_timing_root`.
- **`validate_refs.py` (ODP)** extended: detects duplicate `draw:id`, dangling `smil:targetElement` animation references.
- 15 new tests across `tests/test_odp_animations.py`, `tests/test_odp_transitions.py`, `tests/test_odp_master.py`. Total: 197 (was 182).

### Changed

- ODP `SKILL.md` description + triggers extended with animation, Animation, Effekt, transition, Übergang, Folienübergang, master page, Folienmaster, background, Hintergrund, fade-in, fly-in, wipe, motion path.

## v0.6.0 - 2026-05-21

ODS depth: named ranges, data validation, and embedded charts.

### Added

- **Named ranges (ODS)**:
  - `add_named_range.py` — emits `table:named-range` (cell-range alias) or `table:named-expression` (formula/constant alias). Supports global or sheet-scoped names. Idempotent: re-adding the same name replaces the entry.
  - `list_named_ranges.py` — JSON listing of all named ranges + expressions, with scope.
- **Data validation (ODS)**:
  - `add_data_validation.py` — types `list` (dropdown), `number`, `date`, `text`. Applies to a cell range via `table:content-validation-name`. Supports help/error messages.
- **Charts (ODS)**: embedded chart objects via `add_chart.py` with `--type bar|line|pie|scatter`. Charts live as `Object N/` sub-packages with MIME `application/vnd.oasis.opendocument.chart`, parallel to v0.4 MathML structure. Two manifest entries per chart. `list_charts.py` for inspection.
- **`validate_refs.py` (ODS)** extended: detects unknown sheet names in named-range targets, duplicate named-range/expression names, dangling `table:content-validation-name` references, and missing chart `Object N/` package targets.
- New `ods_common.py` helpers: `build_chart_content` (chart XML payload builder for all four types), re-exports of `unique_object_name`, `copy_with_multiple_members`, `ensure_manifest_entry` from `lib/odf_common`.
- ODS `NS` map extended with `chart`, `draw`, `svg` for chart object handling.
- 19 new tests across `tests/test_ods_named_ranges.py`, `tests/test_ods_validation.py`, `tests/test_ods_charts.py`. Total: 182 (was 163).

### Changed

- ODS `SKILL.md` description and trigger list extended with named-range, dropdown, chart, Diagramm, Balkendiagramm, Liniendiagramm, Kreisdiagramm keywords.
- `tests/test_property.py` `_concatenated_text` helper made recursive (Hypothesis caught a non-recursive bug in the test, not the production code).

## v0.5.0 - 2026-05-21

DAO-branded template, cross-paragraph ranges, RelaxNG schema validation, magic-byte MIME, Hypothesis property tests.

### Added

- **DAO-branded template** in `examples/dao/`:
  - `styles.xml` — Nunito Sans, `#02416C`, A4 with 2.5 cm DFG-Antrag margins, master page with logo header + footer with page number, 7 named paragraph styles (`DAO-Title`, `DAO-Heading-1..3`, `DAO-Body`, `DAO-Quote`, `DAO-Caption`), outline numbering for 3 levels.
  - `logo-placeholder.png` — 300×100 PNG with `#02416C`-bordered transparent placeholder; user replaces with the real DAO logo.
  - `build_grant_proposal.py` — new Step 1b injects DAO styles + embeds logo.
  - `spec.json` — all block specs reference DAO-* style names.
  - Resulting PDF: ~115 KB (up from ~50 KB) reflecting the elaborated styling.
- **Cross-paragraph range bookmarks/refs**: new `wrap_text_across_elements` helper; `add_bookmark.py` and `add_reference.py` now fall back to cross-paragraph when intra-paragraph fails.
- **RelaxNG schema validation**: optional `[validate] = ["lxml>=4.9"]` extra. `ensure_schema` downloads OASIS ODF 1.3 schemas on first use to `~/.cache/open-document-skills/schemas/`. `validate_refs.py --strict` activates content.xml + manifest.xml RelaxNG validation.
- **Magic-byte MIME detection**: new public `sniff_image_mime(path)` reading file headers (PNG/JPEG/GIF/SVG/BMP/WebP/TIFF) with `media_type_for` fallback. Wired into `add_image.py` for ODT/ODP/ODG — PNG-with-`.jpg`-extension and similar mislabels now land with the correct manifest MIME.
- **Hypothesis property tests** in `tests/test_property.py` — 5 invariants for the walker/locator (idempotence, content conservation, child preservation, rollback, anchor-preservation under insert). 80 examples per invariant.
- **Library helpers in `lib/odf_common.py`**:
  - `wrap_text_across_elements`
  - `inject_styles_from_file` (with cross-reference validation against content.xml)
  - `embed_pictures` (bulk Pictures/ + manifest insertion)
  - `ensure_schema`, `validate_against_schema`
  - `sniff_image_mime` + `_IMAGE_MIME_BY_MAGIC` table
- **`create_minimal_odt.py`** now reads an optional `style` field on block specs (heading/paragraph) and emits `text:style-name` accordingly — prerequisite for DAO style injection.
- 27 new tests across `tests/test_dao_template.py`, `tests/test_property.py`, `tests/test_schema_validation.py`, plus cross-paragraph and magic-byte tests in existing files. Total: 163 (was 136).

### Changed

- `pyproject.toml`: new `[validate]` extra; `hypothesis` added to `[dev]`.
- CI workflow installs `lxml` and `hypothesis` (and `pandoc` from v0.4) so all paths are exercised.

## v0.4.0 - 2026-05-21

Cross-references, MathML, and an end-to-end DAO grant-proposal example.

### Added

- **Cross-references (ODT)** — five new scripts:
  - `add_bookmark.py` — `text:bookmark` (point) and `text:bookmark-start`/`text:bookmark-end` (intra-paragraph range) via text anchor or paragraph index.
  - `add_reference.py` — `text:reference-mark` (point/range), `text:bookmark-ref` (to a bookmark), `text:reference-ref` (to a reference-mark). Supports `--display page|chapter|number|direction|text`.
  - `add_sequence.py` — auto-numbered `text:sequence` (Figure/Table/Equation/…) with on-demand `text:sequence-decls` injection; `text:sequence-ref` for references.
  - `list_refs.py` — JSON inventory of bookmarks, reference-marks, sequences, and all kinds of refs with paragraph index and context.
- **MathML embedding (ODT)** — `add_math.py` accepting `--latex` (via optional `pandoc`), `--mathml PATH`, or `--mathml-inline XML`. Formulas are embedded as `Object N/` sub-packages (LibreOffice-native convention) with proper manifest entries.
- **DAO grant-proposal example** — `examples/dao/{spec.json, refs.bib, build_grant_proposal.py, README.md}`. End-to-end pipeline that produces a German grant proposal with citations, footnote, bookmark+ref, figure sequence, and a Carbon-14 LaTeX formula. ~50 KB PDF when LibreOffice is present.
- **Library helpers in `lib/odf_common.py`**:
  - `wrap_text_with_pair_in_element` — bracket a text region with a start/end element pair, with rollback on failure.
  - `ensure_sequence_declarations` — idempotent insertion of `text:sequence-decls`/`text:sequence-decl` under `office:text`.
  - `unique_object_name` — `Object 1`, `Object 2`, … picker, parallel to `unique_picture_name`.
  - `copy_with_multiple_members` — ZIP-write helper accepting an arbitrary `{path: bytes}` mapping of new members plus replacements.
  - `find_pandoc`, `latex_to_mathml` — LaTeX → MathML conversion via pandoc subprocess.
- **`validate_refs.py` (ODT)** extended with 8 new checks: duplicate bookmark/reference-mark/sequence names, unmatched range pairs, dangling refs (bookmark-ref/reference-ref/sequence-ref), missing draw:object package targets.
- 26 new tests across `tests/test_cross_refs.py`, `tests/test_math.py`, `tests/test_examples.py` extension, and unit tests in `tests/test_lib_odf_common.py`. Total: 136 tests (was 110).

### Changed

- CI workflow installs `pandoc` so the LaTeX→MathML code path is exercised in tests.
- ODT `SKILL.md` description and trigger list extended with cross-reference, figure, equation, MathML, LaTeX, Querverweis, Lesezeichen, Abbildung, Gleichung keywords.

## v0.3.0 - 2026-05-21

Scholarly authoring: footnote/endnote API + BibTeX/CSL-JSON citation API.

### Added

- `add_footnote.py` (ODT): insert `text:note` via text-anchor or paragraph index, auto-increments ids (`ftn0`/`edn0`...), supports footnote and endnote classes.
- `list_notes.py` (ODT): JSON output of every note with id, class, citation marker, body text, paragraph index, and ±40-char anchor context.
- `add_citation.py` (ODT): insert `text:bibliography-mark` from a CSL-JSON file, BibTeX file (via optional `bibtexparser`), or inline `--field` arguments. Auto-detects source format by file extension.
- `fill_citations.py` (ODT): bulk-replace pandoc-style `[@bibkey]` placeholders throughout a template ODT. Idempotent; unknown keys stay with a warning.
- `list_citations.py` (ODT): JSON output of every `text:bibliography-mark` with all its attribute fields.
- New optional dependency group `[scholarly] = ["bibtexparser>=1.4,<2"]`.
- `lib/citation_mapping.py`: BibTeX/CSL-JSON → ODF field mapping tables, plus author/date normalisation helpers.
- New `lib/odf_common.py` helpers reused across the new scripts:
  - `find_text_position_in_element` — locator returning slot + offset for the first occurrence of a substring.
  - `insert_after_text_in_element` — splice an element in immediately after a text anchor (anchor preserved).
  - `replace_pattern_with_element_in_element` — regex-driven replacement of placeholders with elements.
  - `insert_in_paragraph` — start/end insertion helper.
  - Internal `_collect_text_slots` extracted from the v0.2.0 walker for reuse.
- `validate_refs.py` (ODT) extended: duplicate `text:note` id detection (error), duplicate `text:bibliography-mark` identifier detection (warning), leftover `[@key]` placeholder detection (warning), missing `text:note-body` (error), empty `text:note-citation` (warning).
- `extract_text.py` (ODT) JSON output for notes now includes `id` and `citation` fields (non-breaking).
- 33 new tests across `tests/test_footnotes.py`, `tests/test_citations.py`, and unit tests in `tests/test_lib_odf_common.py`. Total: 110 tests (was 76); CI installs `bibtexparser` so the BibTeX path is exercised.

### Changed

- ODT `SKILL.md` triggers expanded with citation/footnote/bibliography keywords in English and German.
- CI workflow installs `bibtexparser` in the smoke and coverage jobs.

## v0.2.1 - 2026-05-21

Documentation polish for skill-registry listings (skills.sh).

### Changed

- README hero rewritten: one-line pitch lead, four-line code sample showing the create/edit/pack/validate loop, "Skills at a glance" table with trigger keywords, "Why use these" bullets (stdlib core, structure-preserving, audit-friendly, tested), explicit "What this is not" non-goals section.
- Added release badge to README.

## v0.2.0 - 2026-05-21

Inline-preserving text edits, meta lifecycle, and flat ODF (Git-friendly) support.

### Added

- `replace_text_in_element()` in `lib/odf_common.py`: slot-based walker that preserves `text:span`, `text:note`, `text:bookmark`, `text:a`, and handles matches straddling child boundaries.
- `update_meta_for_edit()` in `lib/odf_common.py`: writes `meta:modification-date`, `meta:generator` (`open-document-skills/<VERSION>`), and increments `meta:editing-cycles` on every edit operation.
- `pack_flat_odf()` and `unpack_flat_odf()` in `lib/odf_common.py`: convert between zipped ODF packages and flat single-XML `.fodt`/`.fodp`/`.fods`/`.fodg` files. Pictures are embedded as base64 inside `<office:binary-data>` when packing, extracted back to `Pictures/` on unpack, manifest rebuilt.
- Eight new CLI scripts (`pack_fodt.py`/`unpack_fodt.py` and the equivalents for ODP/ODS/ODG).
- `VERSION` constant in `lib/odf_common.py` (kept in sync with `pyproject.toml` via release checklist).
- Twelve new tests: walker structure preservation (inline span, straddle, footnote), `update_meta_for_edit` unit tests, meta lifecycle across all 8 edit scripts, flat-ODF roundtrips for all four formats, embedded-image base64 verification, manifest rebuild, LibreOffice opens `.fodt` integration test.

### Changed

- `replace_text.py` for ODT/ODP/ODG: switched from destructive `set_plain_text` (which called `clear_children`) to `replace_text_in_element`. Inline children are now preserved.
- All eight edit scripts (`replace_text` ×3, `add_image` ×3, `clone_slide`, `replace_cells`) now update `meta.xml` on save.
- `CONTRIBUTING.md` release checklist now requires bumping `VERSION` in `lib/odf_common.py` alongside `pyproject.toml`.
- `README.md` and `docs/script-reference.md`: added the 8 flat-ODF scripts.
- `docs/workflows.md`: added "Flat ODF (Git-friendly)" section.

## v0.1.6 - 2026-05-21

Type hints, test coverage, and documentation slimming.

### Added

- Full type hints and expanded docstrings for all 12 functions in `lib/odf_common.py`.
- `tests/test_lib_odf_common.py` — 18 direct unit tests for library functions, achieving 100% coverage on `lib/`.
- `unittest.mock`-based tests for `find_soffice()` (PATH-found and not-found paths).

### Changed

- All four `SKILL.md` files: script tables and example blocks replaced with links to `docs/script-reference.md` (~74 lines removed).
- Coverage CI job fixed: LibreOffice installed to satisfy `find_soffice()` import-time call.

## v0.1.5 - 2026-05-21

Dev dependencies and pre-commit hooks.

### Added

- `dev` optional dependency group in `pyproject.toml` (`pytest>=8.0`, `ruff>=0.9`).
- `.pre-commit-config.yaml` with `ruff-check --fix` and `ruff-format` hooks.

## v0.1.4 - 2026-05-21

Refactoring, shared library, and CI improvements.

### Added

- `lib/odf_common.py` shared library with 13 reusable functions (ZIP packing, XML parsing, manifest handling, `find_soffice`, media-type detection, picture-name deduplication).
- `docs/soffice-resolver.md` documenting the LibreOffice discovery strategy.
- Version synchronization test between `pyproject.toml` and all four `SKILL.md` files.
- Ruff configuration (`E`, `F`, `W`, `I`, `UP` selected; `E501` ignored).
- Lint job in GitHub Actions CI.
- JSON error handling (file existence check, `JSONDecodeError` catch) in all four `create_minimal_*.py` scripts.
- `odfpy` as optional dependency (`[odf]` extra) in `pyproject.toml`.
- Edge case tests for XML special characters, missing spec files, and invalid JSON.
- Docstrings on all helper functions in `create_minimal_*.py` scripts.

### Changed

- `skills/odt/scripts/odt_common.py`, `skills/odp/scripts/odp_common.py`, `skills/ods/scripts/ods_common.py`, `skills/odg/scripts/odg_common.py` refactored to import from `lib.odf_common` via thin format-specific wrappers.
- Test files updated to use shared imports.
- All four `SKILL.md` files: frontmatter split into `description`, `triggers`, and `dont_use_for`; tool check references `docs/soffice-resolver.md`.
- README shortened: script tables replaced with links to `docs/script-reference.md`.

## v0.1.3 - 2026-05-21

Multi-agent and documentation release.

### Added

- Claude Code plugin metadata via `.claude-plugin/plugin.json`.
- OpenCode and Claude Code installation targets in `scripts/install_skills.py`.
- Agent compatibility documentation for Codex, Claude Code, and OpenCode.
- Dedicated docs pages for installation, workflows, and script reference.
- Documentation link tests.

### Changed

- Skill frontmatter now uses portable `license: MIT` and `version` metadata.
- README now presents the repository as an agent skill pack for Codex, Claude Code, and OpenCode.
- `pyproject.toml` metadata now describes the package as agent skills for OpenDocument files.

## v0.1.2 - 2026-05-21

Documentation and installation release.

### Added

- `scripts/install_skills.py` to install the ODT, ODP, ODS, and ODG skills into `$CODEX_HOME/skills`, `~/.codex/skills`, or a custom destination.
- Installer test coverage for custom destinations and existing-skill skip behavior.
- `CONTRIBUTING.md` with local checks, example QA, installation checks, and release checklist.
- README script-reference tables for all four skills.

### Changed

- README installation instructions now prefer the installer script and document `~/.agents/skills` as an explicit legacy/custom destination.
- README release status updated to `v0.1.2`.

## v0.1.1 - 2026-05-21

Maintenance and examples release.

### Added

- Runnable `examples/` directory with JSON specs for ODT, ODP, ODS, and ODG.
- Shared example SVG asset and `examples/build_examples.py` helper.
- Example test coverage to ensure all generated example files remain valid ODF packages.
- README documentation for building examples and optional LibreOffice/Poppler QA.

### Changed

- GitHub Actions now installs LibreOffice and Poppler on Ubuntu so integration tests run in CI.
- Updated GitHub Actions to `actions/checkout@v6.0.2` and `actions/setup-python@v6.2.0`.
- Example QA output is written per format below `examples/output/qa/`.

## v0.1.0 - 2026-05-21

Initial public release.

### Added

- `odt` skill for OpenDocument Text / LibreOffice Writer workflows.
- `odp` skill for OpenDocument Presentation / LibreOffice Impress workflows.
- `ods` skill for OpenDocument Spreadsheet / LibreOffice Calc workflows.
- `odg` skill for OpenDocument Graphics / LibreOffice Draw workflows.
- Direct ODF package/XML generation scripts for all four formats.
- XML-safe edit helpers for text, cells, images, slides, and drawings.
- Package inspection and reference validation scripts.
- Optional LibreOffice render/recalc helpers.
- Reusable test fixtures.
- Smoke, edge-case, and optional LibreOffice integration tests.
- GitHub Actions CI.
