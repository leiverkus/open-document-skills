# grant-proposal

A research-grant-proposal template for any funding agency — DFG, ERC,
VolkswagenStiftung, Gerda Henkel, Fritz Thyssen, BMBF, EU Horizon, …
English-first, institution-neutral. A4 + 2.5 cm margins, outline-numbered
headings, Lato navy headings + Source Serif body.

## What this template offers

- **Page layout**: `GP-A4` (21 × 29.7 cm, 2.5 cm margins, 1.5 cm header, 1 cm footer)
- **Master page**: `Standard` — header with project-title placeholder; footer with page number
- **Outline numbering**: `Outline` — `1.` / `1.1.` / `1.1.1.` / `1.1.1.1.` (4 levels)
- **Paragraph styles**:
  - `Title` (28 pt, navy, bold — cover-page title)
  - `Heading1`, `Heading2`, `Heading3` (auto-numbered, navy)
  - `Body` (Source Serif 11 pt, justified, 1.2 line-height)
  - `Abstract` (italic, indented — for the cover-page abstract)
  - `Quote` (italic, indented — for block quotes)
  - `Caption` (italic, centred, 10 pt — for figures, tables, equations)
- **Text styles**: `Emphasis`, `Strong`
- **Fonts**: Lato (headings), Source Serif (body), both with Liberation fallbacks

## How to apply

```bash
# 1. Author the content
python3 skills/odt/scripts/create_minimal_odt.py spec.json proposal.odt

# 2. Apply the template (injects styles, runs validate_refs)
python3 skills/odt/scripts/apply_template.py proposal.odt \
    --template-name grant-proposal -o branded.odt

# 3. Add scholarly apparatus (recommended pairing)
python3 skills/odt/scripts/fill_citations.py branded.odt \
    --source refs.bib -o branded.odt
python3 skills/odt/scripts/add_toc.py branded.odt \
    --at start --title "Table of Contents" -o branded.odt
python3 skills/odt/scripts/add_bibliography.py branded.odt \
    --at end --title "References" -o branded.odt
python3 skills/odt/scripts/update_indexes.py branded.odt --outdir qa
```

## Customising

- **Add a logo**: edit `styles.xml` and insert a `<draw:frame>` inside the
  `Standard` master page's `<style:header>`, then put your image at
  `Pictures/logo.png` in the template directory (or use `customize_master.py`
  after applying).
- **Change the accent colour**: search-replace `#1B3A57` in `styles.xml`.
- **Different margins**: edit `GP-A4` page-layout's `fo:margin-*`.
- **More heading levels**: extend the `Outline` text-outline-style.

## Localized variants

`examples/dao/` shows how a German DAO archaeology institute customises a
similar template (German headers, DAO blue, Nunito Sans, additional
DAO-specific paragraph styles).
