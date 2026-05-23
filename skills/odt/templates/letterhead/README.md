# letterhead

An institutional letterhead template: DIN-5008-inspired layout, single
font (Lato), header with institution placeholders, footer with contact
line.

## What this template offers

- **Page layout**: `LH-A4` (A4, asymmetric margins — 2.5 cm left for the
  Lochrand, 2 cm right; 2.5 cm top, 2 cm bottom; 2 cm header, 1 cm footer)
- **Master page**: `Standard` — header with `[Your Institution]` +
  address placeholders; footer with contact-line placeholder
- **Paragraph styles**:
  - `Title` (14 pt bold — institution name in header)
  - `Address` (recipient address block with 3 cm top margin for envelope alignment)
  - `Date` (right-aligned)
  - `Subject` (bold subject line)
  - `Body` (11 pt, 1.25 line-height)
  - `Heading1`, `Heading2` (rare in letters but available)
  - `Closing` (extra top + bottom margin around the signature)
  - `Signature` (signatory's name, bold)
- **Text styles**: `Emphasis`, `Strong`
- **Fonts**: Lato

## How to apply

```bash
python3 skills/odt/scripts/create_minimal_odt.py spec.json letter.odt
python3 skills/odt/scripts/apply_template.py letter.odt \
    --template-name letterhead -o branded.odt
```

## Customising for your institution

1. **Replace the header placeholders** — open `styles.xml` and edit the
   `<style:header>` `<text:p>` content to your institution name + address.
2. **Add a logo** — drop a `Pictures/logo.png` into your template
   directory (e.g. by copying this template first), insert a
   `<draw:frame>` in `<style:header>` referencing it. `apply_template.py`
   embeds the picture automatically.
3. **Customise the footer** — edit `<style:footer>` for your contact line.

Typical content order in a letter:

```
Address → Date → Subject → Body (multiple paragraphs) → Closing → Signature
```
