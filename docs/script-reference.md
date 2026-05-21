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
| `pack_odt.py` | Repack an unpacked ODT directory with correct `mimetype` handling. |
| `render.py` | Render ODT to PDF, optionally PNG pages, through LibreOffice/Poppler. |
| `validate_refs.py` | Validate manifest and embedded image references. |

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
| `pack_ods.py` | Repack an unpacked ODS directory with correct `mimetype` handling. |
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
| `render.py` | Export ODG to PDF, SVG, and/or PNG through LibreOffice. |
| `validate_refs.py` | Validate manifest, embedded image references, and basic geometry values. |

