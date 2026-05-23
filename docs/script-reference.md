# Script Reference

All scripts use the Python standard library.

## ODT

| Script | Purpose |
| --- | --- |
| `create_minimal_odt.py` | Build a minimal ODT from a JSON document spec. Accepts `--theme` for a curated palette + font pairing. |
| `create_from_markdown.py` | Build a styled ODT from a Markdown file — rich inline text (`text:span`), links, nested lists, GFM tables, footnotes, images. Stdlib-only parser, no Pandoc. Accepts `--theme`. |
| `extract_text.py` | Print visible document text, including footnotes. |
| `inspect_package.py` | Summarize package files, manifest entries, images, and document metadata. |
| `list_styles.py` | List styles found in `styles.xml` and `content.xml`. |
| `replace_text.py` | XML-safe text replacement in document content. |
| `add_image.py` | Add an image to the document package and manifest. |
| `add_footnote.py` | Insert a footnote (or endnote) via text anchor or paragraph index. |
| `list_notes.py` | List all footnotes/endnotes as JSON with id, class, citation, body, anchor context. |
| `add_citation.py` | Insert a `text:bibliography-mark` from BibTeX, CSL-JSON, or inline `--field` arguments. |
| `fill_citations.py` | Bulk-replace pandoc-style `[@bibkey]` placeholders with `text:bibliography-mark`. |
| `list_citations.py` | List all `text:bibliography-mark` entries as JSON. |
| `add_bookmark.py` | Insert `text:bookmark` (point or range) via text anchor or paragraph index. |
| `add_reference.py` | Insert `text:reference-mark` (point/range), `text:bookmark-ref`, or `text:reference-ref`. |
| `add_sequence.py` | Auto-numbered `text:sequence` (Figure/Table/Equation) with on-demand `text:sequence-decls`; also `text:sequence-ref`. |
| `list_refs.py` | List bookmarks, reference-marks, sequences, and references as JSON. |
| `add_math.py` | Embed a MathML formula via LaTeX (Pandoc), MathML file, or inline MathML; uses LibreOffice-native `Object N/` sub-packages. |
| `add_toc.py` | Insert a `text:table-of-content` placeholder with configurable outline level (default 3) and entry templates. |
| `add_bibliography.py` | Insert a `text:bibliography` placeholder with entry templates for the common ODF bibliography types. |
| `add_illustration_index.py` | Insert a `text:illustration-index` (or `text:table-index` when `--sequence Table`); `--sequence Figure`/`Table`/`Equation`/… selects the caption-sequence-name. |
| `add_alphabetical_index.py` | Insert a `text:alphabetical-index` placeholder; pair with `add_index_mark.py`. |
| `add_index_mark.py` | Insert a `text:alphabetical-index-mark` point marker at an anchor with `--key1` / `--key2` headings. |
| `update_indexes.py` | Refresh every `text:index-body` via headless LibreOffice (isolated temp profile + one-off Basic macro). Mirrors `recalc.py` for ODS. |
| `add_comment.py` | Insert an `office:annotation` comment (point or range) with author, date, and body. |
| `list_comments.py` | List all comments as JSON with name, author, date, text, and context. |
| `track_change.py` | Record an edit as a tracked change — `--insert`, `--delete`, or `--replace`. |
| `list_changes.py` | List all tracked changes as JSON with id, kind, author, date, and text. |
| `resolve_changes.py` | Accept or reject tracked changes (`--all` or `--id`). |
| `restyle.py` | Bulk-set `text:style-name` on paragraphs/headings matching `--current-style`, `--headings`/`--paragraphs`, `--level`. |
| `insert_blocks.py` | Insert a JSON `blocks` fragment (heading/paragraph/list/table) after/before an anchor, at a paragraph index, or at body start/end. |
| `delete_block.py` | Delete a whole block (paragraph/heading/list/table) by anchor text or index. |
| `edit_table.py` | Edit a table by name — add/delete rows and columns, set cells. |
| `pack_odt.py` | Repack an unpacked ODT directory with correct `mimetype` handling. |
| `pack_fodt.py` | Convert a zipped ODT to a flat `.fodt` (single XML, Git-friendly). |
| `unpack_fodt.py` | Convert a flat `.fodt` back to a zipped `.odt` package. |
| `render.py` | Render ODT to PDF, per-page PNGs (`--png`), or a single labelled contact sheet (`--contact-sheet`) via LibreOffice/Poppler. |
| `convert.py` | Bidirectional conversion to/from Microsoft Word: ODT ↔ DOCX/DOC via headless LibreOffice. Isolated `-env:UserInstallation` temp profile — your real LibreOffice profile is never touched. |
| `validate_refs.py` | Validate manifest, embedded image references, note id consistency, citation field completeness, leftover citation placeholders, cross-reference targets. Use `--strict` for OASIS RelaxNG schema validation (requires `pip install open-document-lib[validate]`). |

## ODP

| Script | Purpose |
| --- | --- |
| `create_minimal_odp.py` | Build a minimal ODP from a JSON slide spec — designed default theme, six named slide layouts (`title-slide`/`title-content`/`two-content`/`section-header`/`title-only`/`blank`), optional extra master pages, and a `--theme` flag. |
| `extract_text.py` | Print slide text and speaker notes. |
| `inspect_package.py` | Summarize slides, notes, images, package files, and manifest entries. |
| `list_masters.py` | List master pages, slide layouts (`presentation-page-layout` + placeholders), and per-slide usage as JSON. |
| `set_layout.py` | Reassign the slide layout and/or master page on one or more slides, repositioning placeholder frames to the new layout's zones. |
| `inspect_template.py` | Inspect a template (`.odp`/`.otp`/standalone `styles.xml`) as JSON: master pages with backgrounds, slide layouts with placeholder zones, named graphic/paragraph styles, font declarations. The agent's per-slide layout-picking input. |
| `extract_template.py` | Distil any `.odp`/`.otp`/`.pptx` (PPTX auto-converted via v1.11 bridge) into a reusable template directory: filtered `styles.xml`, master-page-referenced `Pictures/`, plus `LICENSE.txt`/`PROVENANCE.md`/`README.md`. |
| `apply_template.py` | Apply a template directory (shipped or user-curated) to an ODP in one call: inject styles, embed master pictures, validate references. Replaces hand-rolled inject+embed orchestrations. |
| `clone_slide.py` | Clone a slide from a template deck with optional text replacements. |
| `replace_text.py` | XML-safe text replacement in slides and notes. |
| `add_image.py` | Add an image to a slide and update package references. |
| `add_animation.py` | Add a shape-level animation (entrance/exit/emphasis/motion path). |
| `list_animations.py` | List all animations as JSON. |
| `add_transition.py` | Add or remove a slide transition (fade/wipe/cover/uncover/push/dissolve/random). |
| `list_transitions.py` | List all slide transitions as JSON. |
| `customize_master.py` | Customize a master page: background colour (written into the master's `drawing-page` style so it renders), header/footer, page numbers, logo, clone-to. |
| `pack_odp.py` | Repack an unpacked ODP directory with correct `mimetype` handling. |
| `pack_fodp.py` | Convert a zipped ODP to a flat `.fodp` (single XML, Git-friendly). |
| `unpack_fodp.py` | Convert a flat `.fodp` back to a zipped `.odp` package. |
| `render.py` | Render ODP to PDF, per-slide PNGs (`--png`), or a single labelled contact sheet (`--contact-sheet`) via LibreOffice/Poppler. |
| `convert.py` | Bidirectional conversion to/from Microsoft PowerPoint: ODP ↔ PPTX/PPT via headless LibreOffice. |
| `validate_refs.py` | Validate manifest, embedded image references, animation/transition/master-page/slide-layout targets. Use `--strict` for OASIS RelaxNG schema validation. |

## ODS

| Script | Purpose |
| --- | --- |
| `create_minimal_ods.py` | Build a minimal ODS workbook from a JSON spec. Accepts `--theme` (themed header row + body font). |
| `extract_sheets.py` | Print sheet cell values and formulas. |
| `extract_formulas.py` | Emit formulas as structured JSON. |
| `inspect_package.py` | Summarize package files, sheets, manifest entries, and metadata. |
| `list_styles.py` | List spreadsheet styles. |
| `replace_cells.py` | Set values or formulas by sheet and A1 address. |
| `export_csv.py` | Export one sheet to CSV. |
| `add_named_range.py` | Add a `table:named-range` (cell-range alias) or `table:named-expression` (formula/constant), global or sheet-scoped. |
| `list_named_ranges.py` | List all named ranges and named expressions as JSON. |
| `add_data_validation.py` | Add a data-validation rule (list/number/date/text) and apply it to a cell range. |
| `add_chart.py` | Embed a chart object (bar/line/pie/scatter) into a cell via LibreOffice-native `Object N/` sub-package. |
| `list_charts.py` | List all embedded chart objects as JSON. |
| `add_conditional_format.py` | Highlight a cell range by value/formula condition — `calcext:conditional-format` (LibreOffice-rendered) plus ODF-core `style:map`; stackable. |
| `add_pivot_table.py` | Compute a pivot (group-by + aggregation) and write the result grid plus a refreshable `table:data-pilot-table`. |
| `list_pivot_tables.py` | List all `table:data-pilot-table` definitions as JSON — name, source/target range, fields. |
| `pack_ods.py` | Repack an unpacked ODS directory with correct `mimetype` handling. |
| `pack_fods.py` | Convert a zipped ODS to a flat `.fods` (single XML, Git-friendly). |
| `unpack_fods.py` | Convert a flat `.fods` back to a zipped `.ods` package. |
| `recalc.py` | Recalculate a workbook through LibreOffice and validate references. |
| `render.py` | Render ODS to PDF, per-page PNGs (`--png`), or a single labelled contact sheet (`--contact-sheet`) via LibreOffice/Poppler. |
| `convert.py` | Bidirectional conversion to/from Microsoft Excel: ODS ↔ XLSX/XLS via headless LibreOffice. |
| `validate_refs.py` | Validate manifest/package references, formula errors, named ranges, data validation, and chart targets. Use `--strict` for OASIS RelaxNG schema validation. |

## ODG

| Script | Purpose |
| --- | --- |
| `create_minimal_odg.py` | Build a minimal ODG drawing from a JSON spec, with a designed default theme (no generic-blue shapes), optional per-shape styling keys (`fill`, `stroke`, `stroke-width`, `text-color`, `font-size`, `corner-radius`), and a `--theme` flag. |
| `extract_text.py` | Print text from drawing pages and shapes. |
| `extract_shapes.py` | Emit drawing shapes, frames, geometry, and text as structured JSON. |
| `inspect_package.py` | Summarize pages, shapes, images, package files, and manifest entries. |
| `list_styles.py` | List Draw styles and page layouts. |
| `replace_text.py` | XML-safe text replacement in drawing content. |
| `add_image.py` | Add an image to a drawing page and update package references. |
| `add_gluepoint.py` | Add a `draw:glue-point` (anchor for connectors) to a shape. |
| `connect_shapes.py` | Connect two shapes with a `draw:connector` (standard/line/curve). |
| `group_shapes.py` | Wrap shapes into a `draw:g` group container. |
| `ungroup.py` | Dissolve groups (by name or all) on a page. |
| `list_structure.py` | List groups, connectors, and glue points as JSON. |
| `pack_odg.py` | Repack an unpacked ODG directory with correct `mimetype` handling. |
| `pack_fodg.py` | Convert a zipped ODG to a flat `.fodg` (single XML, Git-friendly). |
| `unpack_fodg.py` | Convert a flat `.fodg` back to a zipped `.odg` package. |
| `render.py` | Export ODG to PDF/SVG/PNG (`--formats`), or a single labelled contact sheet (`--contact-sheet`). |
| `validate_refs.py` | Validate manifest, embedded image references, geometry values, connector/glue-point targets, and groups. Use `--strict` for OASIS RelaxNG schema validation. |

