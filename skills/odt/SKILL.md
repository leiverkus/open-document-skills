---
name: odt
description: "Create, read, edit, convert, repair, or inspect OpenDocument Text files (.odt)."
triggers: [".odt", "ODT", "OpenDocument Text", "Open Office document", "LibreOffice Writer", "Writer document", "odt-Datei", "OpenDocument-Text"]
dont_use_for: ["spreadsheets (.ods)", "presentations (.odp)", "PDFs as primary deliverable", "general prose editing"]
license: MIT
version: "0.1.3"
---

# ODT creation, editing, and analysis

## Overview

An `.odt` file is an OpenDocument ZIP package. Important package files:

- `mimetype` - should be the first ZIP entry and stored uncompressed as `application/vnd.oasis.opendocument.text`
- `content.xml` - document body
- `styles.xml` - named styles and page layout
- `meta.xml` - document metadata
- `settings.xml` - application settings
- `META-INF/manifest.xml` - package manifest

## Quick Reference

| Task | Preferred approach |
|------|--------------------|
| Extract text and structure | Use `scripts/extract_text.py` or parse `content.xml` |
| Create styled/template document | Start from an `.odt` template, preserve styles/page layout, edit XML |
| Create simple structured document | Generate ODT package XML directly |
| Convert Markdown/HTML/DOCX to ODT | Use Pandoc/LibreOffice only when the source already exists or interoperability requires it |
| Preserve complex formatting | Unpack the ODT, edit XML with a structured XML parser, then repack carefully |
| Inspect raw structure | `unzip -l file.odt`; `python -m zipfile -e file.odt unpacked/` |

## Tool Checks

Before starting a real ODT task, check which tools are available:

```bash
which pandoc
python3 -c "import odf; print('odfpy available')"
```

Resolve the LibreOffice command as described in [docs/soffice-resolver.md](../../docs/soffice-resolver.md).

## Reading Content

For plain text and semantic structure:

```bash
pandoc input.odt -t markdown -o output.md
```

For raw package inspection:

```bash
python -m zipfile -e input.odt unpacked_odt
```

Read `content.xml` with an XML parser. Do not use regex for XML edits.

Bundled scripts for common inspection tasks:

```bash
# Extract headings, paragraphs, lists, tables, and footnotes.
python scripts/extract_text.py input.odt
python scripts/extract_text.py input.odt --json

# Inspect package files, media references, styles, tables, and document structure.
python scripts/inspect_package.py input.odt
```

## content.xml Structure

An ODT document normally stores body content in `content.xml` under:

```text
office:document-content
  office:body
    office:text
```

Important body elements:

- `text:h` - real headings; `text:outline-level` controls hierarchy
- `text:p` - paragraphs, including styled body text
- `text:list`, `text:list-item` - real lists
- `table:table`, `table:table-row`, `table:table-cell` - tables
- `text:section` - named document sections
- `text:note` - footnotes/endnotes with citation and body content
- `draw:frame` + `draw:image` - embedded or linked images
- `text:bookmark`, `text:reference-mark`, `text:table-of-content` - references and generated structures when present

Styles are name-based. Common references include:

- `text:style-name` for paragraphs/headings/lists
- `draw:style-name` for image frames or shapes
- `table:style-name` and `table:default-cell-style-name` for tables
- `style:name` in `styles.xml` and automatic styles in `content.xml`

Headers, footers, page styles, and page layout are usually in `styles.xml`, not the main body. When changing page size, margins, headers, footers, or numbering, inspect `style:master-page`, `style:page-layout`, `style:header`, and `style:footer`.

## Creating ODT Files

ODT is an XML package and can be generated directly. Do not default to DOCX/Markdown as an intermediate when the deliverable is natively ODT.

Choose the creation path by fidelity needs:

| Scenario | Use |
|----------|-----|
| Institutional letter/report with exact styles, header/footer, page layout | Template-first ODT |
| Simple generated memo/report/protocol | Direct ODT XML generation |
| Existing Markdown/HTML/DOCX source or explicit cross-format conversion | Pandoc/LibreOffice conversion fallback |

### Template-First ODT

Use this when layout, styles, headers, footers, or institutional formatting matter.

1. Extract the template.
2. Inspect `styles.xml` for paragraph, text, table, page, header, and footer styles.
3. Inspect `content.xml` for placeholder paragraphs, sections, tables, and image frames.
4. Replace placeholders with XML-aware edits.
5. Add images under `Pictures/` and update `META-INF/manifest.xml`.
6. Repack and run the full QA loop.

### Direct ODT XML Generation

Use this for simple structured documents. Generate a minimal package with:

- `mimetype`
- `content.xml`
- `styles.xml`
- `meta.xml`
- `settings.xml`
- `META-INF/manifest.xml`
- optional `Pictures/...`

Minimum body structure:

```text
office:body
  office:text
    text:h text:outline-level="1"
    text:p
    text:list
    table:table
```

Keep direct generation deliberately small: headings, paragraphs, lists, simple tables, images, and footnotes. Add advanced fields, tracked changes, indexes, or generated tables of contents only when the task requires them and QA confirms they survive LibreOffice rendering.

### Conversion Fallback

Use Pandoc or LibreOffice conversion when the source already exists in another format or when interoperability is the task:

```bash
pandoc input.md -o output.odt
```

When a reference template is available, use it to carry page styles, fonts, headers, footers, and bibliography styling:

```bash
pandoc input.md --reference-doc=template.odt -o output.odt
```

Set explicit heading hierarchy in the source. Avoid manually faking headings with bold text.

## Bundled Creation and Editing Scripts

These scripts support direct ODT generation and XML-safe template workflows:

| Script | Purpose |
|--------|---------|
| `create_minimal_odt.py` | Generate a valid minimal ODT from a JSON document spec with title, sections, paragraphs, lists, tables, images, and footnotes |
| `replace_text.py` | XML-safe find/replace, optionally scoped to `content.xml`, `styles.xml`, or both |
| `add_image.py` | Copy an image into `Pictures/`, update manifest entries, and insert a `draw:image` frame |
| `list_styles.py` | Print paragraph, text, table, graphic, page, and master-page styles |
| `validate_refs.py` | Check style, image, and manifest references for broken links |
| `pack_odt.py` | Repack an extracted ODT with `mimetype` first and uncompressed |

Examples:

```bash
python scripts/create_minimal_odt.py document.json output.odt
python scripts/replace_text.py input.odt "{{NAME}}" "Patrick Leiverkus" -o output.odt
python scripts/add_image.py input.odt figure.png --width 8cm --height 5cm -o output.odt
python scripts/list_styles.py output.odt
python scripts/validate_refs.py output.odt
python scripts/pack_odt.py unpacked_odt output.odt
```

## ODT Layout Checklist

- Use real `text:h` headings with outline levels; do not fake headings with bold paragraphs.
- Use real `text:list` lists; avoid manually typed bullets when generating XML.
- Use real `table:table` structures; check table widths, cell padding, and page breaks in PDF output.
- Put repeated headers/footers/page numbers in page styles, not copied body paragraphs.
- Preserve template style names unless intentionally changing the design system.
- Anchor images deliberately and leave enough surrounding text space for LibreOffice layout.
- Keep page size and margins explicit for generated documents.
- Verify long words, German compounds, footnotes, and bibliography-like paragraphs in PDF render.

## Editing Existing ODT Files

For content-only edits:

1. Convert to Markdown with Pandoc.
2. Make the content changes.
3. Convert back to ODT, using the original as `--reference-doc` when layout matters.
4. Render or convert to PDF and visually check the result.

For precise edits that must preserve layout:

1. Extract the package.
2. Parse and modify `content.xml` / `styles.xml` with an XML library.
3. Keep namespace prefixes valid.
4. Update `META-INF/manifest.xml` if adding or removing embedded files.
5. Repack with `mimetype` first and uncompressed.

Repack pattern:

```bash
cd unpacked_odt
zip -0 -X ../output.odt mimetype
zip -r -X ../output.odt . -x mimetype
```

## QA (Required)

Assume generated or edited ODT files have problems until proven otherwise. Writer layout can change because of fonts, page styles, table widths, image anchoring, footnotes, and conversion filters.

### Content QA

Extract structure:

```bash
python scripts/extract_text.py output.odt
python scripts/extract_text.py output.odt --json > qa/text.json
```

Check headings, paragraph order, lists, tables, image references, footnotes/endnotes, and leftover placeholders such as `Lorem`, `TODO`, `XXXX`, or template instructions.

### Package QA

Inspect and validate:

```bash
python scripts/inspect_package.py output.odt > qa/package.json
python scripts/validate_refs.py output.odt
```

Check that `mimetype` is first, required XML files exist, media targets exist, manifest entries are present, and style references are not broken.

### Visual QA

Render to PDF:

```bash
python scripts/render.py output.odt --outdir qa
```

If only Pandoc is available, use Markdown as a partial content check:

```bash
pandoc output.odt -t markdown -o qa.md
```

Inspect page breaks, headers/footers, table overflow, footnote placement, missing images, changed fonts, and unexpected style loss.

### Verification Loop

1. Extract content and package summaries.
2. Render to PDF.
3. List concrete issues found.
4. Fix the ODT source, package XML, or template edits.
5. Re-run the relevant extraction/inspection/rendering steps.
6. Do not deliver until a final pass shows no unresolved content, package, or visual issues relevant to the user's request.

## ODT Notes

- ODF styles are style-name based. Preserve existing style names when editing templates.
- Embedded images live under package paths such as `Pictures/...`; the manifest must include them.
- OpenDocument comments and tracked changes are not uniformly preserved across tools. When those matter, prefer LibreOffice round-trips and verify manually.
- Avoid creating minimal XML by hand unless the file is simple; ODT consumers are forgiving, but style and manifest mistakes cause subtle rendering problems.
