# cv

An academic CV template: Lato single-font, navy section headers with
bottom-rule, compact 2 cm margins. Designed for European-style academic
applications.

## What this template offers

- **Page layout**: `CV-A4` (A4, 2 cm margins, footer with name + page)
- **Master page**: `Standard` — footer "[Your Name] · Page N"
- **Paragraph styles**:
  - `Title` (24 pt navy bold — applicant's name)
  - `Contact` (9 pt small grey — email/phone/ORCID/website)
  - `Heading1` (13 pt navy, with bottom rule — section headers)
  - `Heading2` (11 pt bold — sub-sections like "Refereed Publications")
  - `EntryTitle` (11 pt bold — position / degree / publication title)
  - `EntryDetail` (10 pt grey — organisation / institution / co-authors)
  - `Body` (10 pt, 1.25 line-height — for plain prose)
  - `BulletItem` (hanging indent — Languages, Skills, Service lists)
- **Text styles**: `Emphasis`, `Strong`, `DateRange` (small grey — for
  inline date ranges in EntryTitle lines)
- **Fonts**: Lato

## How to apply

```bash
python3 skills/odt/scripts/create_minimal_odt.py spec.json cv.odt
python3 skills/odt/scripts/apply_template.py cv.odt \
    --template-name cv -o branded.odt
```

## Recommended section order

```
[Title: Your Name]
[Contact: email · phone · ORCID · website]

Heading1: Education
  EntryTitle: Degree, Institution        DateRange: 2018–2021
  EntryDetail: Thesis title; advisor

Heading1: Research Positions
  EntryTitle: …                          DateRange: …
  EntryDetail: …

Heading1: Publications              ← use Heading2 sub-sections
  Heading2: Refereed Articles
    Body: full bibliography entry
  Heading2: Book Chapters
    Body: full bibliography entry

Heading1: Third-Party Funding
  EntryTitle: Project title, Agency      DateRange: …
  EntryDetail: amount; role

Heading1: Teaching | Service | Languages
  BulletItem: …
```

## Customising

- Change the accent colour by editing `#1B3A57` in `styles.xml`.
- For US-style CVs with section dates right-aligned in tabular form,
  introduce a two-column table block via `add_table` / `edit_table` —
  the template doesn't impose a tabbed-list layout.
