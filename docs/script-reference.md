# Script Reference

All scripts use the Python standard library.

## ODT

| Script | Purpose |
| --- | --- |
| `create_minimal_odt.py` | Build a minimal ODT from a JSON document spec. |
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
| `pack_odt.py` | Repack an unpacked ODT directory with correct `mimetype` handling. |
| `pack_fodt.py` | Convert a zipped ODT to a flat `.fodt` (single XML, Git-friendly). |
| `unpack_fodt.py` | Convert a flat `.fodt` back to a zipped `.odt` package. |
| `render.py` | Render ODT to PDF, optionally PNG pages, through LibreOffice/Poppler. |
| `validate_refs.py` | Validate manifest, embedded image references, note id consistency, citation field completeness, leftover citation placeholders, cross-reference targets. Use `--strict` for OASIS RelaxNG schema validation (requires `pip install open-document-skills[validate]`). |

## ODP

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
| `pack_fodp.py` | Convert a zipped ODP to a flat `.fodp` (single XML, Git-friendly). |
| `unpack_fodp.py` | Convert a flat `.fodp` back to a zipped `.odp` package. |
| `render.py` | Render ODP to PDF, optionally PNG pages, through LibreOffice/Poppler. |
| `validate_refs.py` | Validate manifest and embedded image references. |

## ODS

| Script | Purpose |
| --- | --- |
| `create_minimal_ods.py` | Build a minimal ODS workbook from a JSON spec. |
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
| `pack_ods.py` | Repack an unpacked ODS directory with correct `mimetype` handling. |
| `pack_fods.py` | Convert a zipped ODS to a flat `.fods` (single XML, Git-friendly). |
| `unpack_fods.py` | Convert a flat `.fods` back to a zipped `.ods` package. |
| `recalc.py` | Recalculate a workbook through LibreOffice and validate references. |
| `validate_refs.py` | Validate manifest/package references and basic formula errors. |

## ODG

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
| `pack_fodg.py` | Convert a zipped ODG to a flat `.fodg` (single XML, Git-friendly). |
| `unpack_fodg.py` | Convert a flat `.fodg` back to a zipped `.odg` package. |
| `render.py` | Export ODG to PDF, SVG, and/or PNG through LibreOffice. |
| `validate_refs.py` | Validate manifest, embedded image references, and basic geometry values. |

