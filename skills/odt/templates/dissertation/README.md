# dissertation

A long-form scholarly monograph template — PhD / Habilitation / scholarly
book. 5-level outline numbering, chapter-per-page, dense body line-height,
hanging-indent bibliography. Designed to consume the v1.10 index pipeline
(TOC, bibliography, illustration index, alphabetical index).

## What this template offers

- **Page layout**: `Diss-A4` (A4, 3 cm margins per DIN convention,
  1.5 cm header, 1.5 cm footer)
- **Master page**: `Standard` — header with chapter-title placeholder;
  footer with page number
- **Outline numbering**: `Outline` — 5 levels deep (1. / 1.1. / 1.1.1. /
  1.1.1.1. / 1.1.1.1.1.)
- **Paragraph styles**:
  - `Title` (28 pt centred — title-page title)
  - `Subtitle` (14 pt italic centred — dissertation type)
  - `Dedication` (italic centred — for dedications/epigraphs)
  - `Heading1` (22 pt, page-break-before — Chapter)
  - `Heading2`/`Heading3`/`Heading4`/`Heading5`
  - `Body` (Source Serif 11 pt, 1.4 line-height, 0.5 cm paragraph indent)
  - `Abstract` (italic, indented — front-matter abstract)
  - `Quote` (smaller, italic, indented — block quotes)
  - `Caption` (italic centred grey — figures/tables/equations)
  - `BibliographyEntry` (hanging indent, 10 pt — back-matter bibliography)
- **Text styles**: `Emphasis`, `Strong`
- **Fonts**: Lato (headings), Source Serif (body)

## How to apply (full scholarly pipeline)

```bash
# 1. Author the manuscript
python3 skills/odt/scripts/create_minimal_odt.py spec.json diss.odt

# 2. Apply the template
python3 skills/odt/scripts/apply_template.py diss.odt \
    --template-name dissertation -o branded.odt

# 3. Add scholarly apparatus — pairs naturally with v1.10 indexes
python3 skills/odt/scripts/fill_citations.py branded.odt \
    --source refs.bib -o branded.odt
python3 skills/odt/scripts/add_sequence.py branded.odt \
    --sequence Figure --name fig1 --anchor "Map of …" -o branded.odt
python3 skills/odt/scripts/add_index_mark.py branded.odt \
    --anchor "…term…" --key1 "Topics" -o branded.odt

python3 skills/odt/scripts/add_toc.py branded.odt \
    --at start --title "Table of Contents" --levels 4 -o branded.odt
python3 skills/odt/scripts/add_bibliography.py branded.odt \
    --at end --title "Bibliography" -o branded.odt
python3 skills/odt/scripts/add_illustration_index.py branded.odt \
    --at end --sequence Figure -o branded.odt
python3 skills/odt/scripts/add_alphabetical_index.py branded.odt \
    --at end --title "Index" -o branded.odt

# 4. Refresh all index bodies
python3 skills/odt/scripts/update_indexes.py branded.odt --outdir qa
```

## Notes

- `Heading1` includes `fo:break-before="page"` so each chapter starts on a
  new page. If you don't want that for a particular Heading1 paragraph,
  override locally.
- The `Outline` style is configured but **does not assign chapter numbers
  to `Heading1` automatically** in this template — Heading1 paragraphs
  show only the chapter title. To enable hierarchical numbering visible in
  the body, link `Heading1`–`Heading5` to the outline-style. Most
  dissertation conventions favour explicit "Chapter 3" prefixes anyway.
- For Front-Matter (with Roman page numbers) / Main-Matter (Arabic) /
  Back-Matter sectioning, wrap blocks in `<text:section>` with
  per-section page styles. The template ships one master page; richer
  per-section page styling is a follow-on.
