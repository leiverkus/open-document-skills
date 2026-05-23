# academic-blue

An academic-talk template: cream background, deep navy sans-serif headings,
serif body text. Reads well projected over long sessions. No default logo;
add one by editing the `Default` master-page or via `customize_master.py`.

## What this template offers

- **Master pages**: `Default` (cream `#FDFBF6` background)
- **Slide layouts**: `pl-title-slide`, `pl-title-content`, `pl-two-content`,
  `pl-section-header`, `pl-title-only`, `pl-blank` (the v1.8 standard set)
- **Paragraph styles**: `Title`, `Body`, `Notes`
- **Graphic styles**: `gr-title`, `gr-body`, `gr-notes`, `gr-image`
- **Fonts**: Lato (headings), Source Serif (body), both with Liberation
  fallback so a CI-rendered PDF still ships even where the first-choice
  fonts are absent

## How to apply

```bash
python3 skills/odp/scripts/create_minimal_odp.py spec.json deck.odp
python3 skills/odp/scripts/apply_template.py deck.odp \
    --template-name academic-blue -o branded.odp
```

## Customising

To add a logo, edit `styles.xml` and add a `<draw:frame>` inside the
`Default` master-page (see `dao-conference` for an example), or use:

```bash
python3 skills/odp/scripts/customize_master.py branded.odp \
    --master Default --logo my-logo.png -o branded.odp
```

To change the background colour, edit the `dp-default` drawing-page style.
