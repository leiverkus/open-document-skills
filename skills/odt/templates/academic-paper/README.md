# academic-paper

An IMRaD academic-paper template: centred title, Lato headings, Source
Serif body with paragraph-indent. Pairs with `add_citation.py` /
`fill_citations.py` for BibTeX/CSL-JSON-driven citations.

## What this template offers

- **Page layout**: `AP-A4` (A4, 2.5 cm margins, page-numbered footer)
- **Master page**: `Standard` (no header, footer with page number)
- **Paragraph styles**:
  - `Title` (22 pt, centred)
  - `Author` (12 pt, centred)
  - `Affiliation` (10 pt italic, centred)
  - `Heading1`/`Heading2`/`Heading3` (Lato bold)
  - `Body` (Source Serif 11 pt, 1.15 line-height, 0.5 cm paragraph indent)
  - `Abstract` (small, indented)
  - `Quote` (small, block-indented)
  - `Caption` (italic, centred)
  - `References` (10 pt with hanging indent)
- **Text styles**: `Emphasis`, `Strong`
- **Fonts**: Lato (headings), Source Serif (body)

## How to apply

```bash
python3 skills/odt/scripts/create_minimal_odt.py spec.json paper.odt
python3 skills/odt/scripts/apply_template.py paper.odt \
    --template-name academic-paper -o branded.odt

# Add citations + bibliography
python3 skills/odt/scripts/fill_citations.py branded.odt \
    --source refs.bib -o branded.odt
python3 skills/odt/scripts/add_bibliography.py branded.odt \
    --at end --title "References" -o branded.odt
python3 skills/odt/scripts/update_indexes.py branded.odt --outdir qa
```

## Notes

- Body has a paragraph indent (0.5 cm) per journal convention. To change
  to block-style (no indent + paragraph spacing), edit `Body`'s
  `fo:text-indent`.
- For double-column layouts, the page-layout would need columns set on
  `style:page-layout-properties` — out of scope for this template.
