# dao-conference

A conference-deck template: deep-blue background (`#02416C`), Nunito Sans
typography, light type on dark ground. Logo in the lower-right corner of
every slide. Suited to academic, non-profit, or grant presentations.

## What this template offers

- **Master pages**: `Default`
- **Slide layouts**: `pl-title-slide`, `pl-title-content`, `pl-two-content`,
  `pl-section-header`, `pl-title-only`, `pl-blank` (the v1.8 standard set)
- **Paragraph styles**: `Title`, `Body`, `Notes`
- **Graphic styles**: `gr-title`, `gr-body`, `gr-notes`, `gr-image`
- **Fonts**: Nunito Sans (with implicit `swiss`-generic Liberation fallback)

## How to apply

```bash
# Build a deck from a spec
python3 skills/odp/scripts/create_minimal_odp.py spec.json deck.odp

# Apply this template
python3 skills/odp/scripts/apply_template.py deck.odp \
    --template-name dao-conference -o branded.odp

# Inspect what the template offers (agent-facing)
python3 skills/odp/scripts/inspect_template.py \
    skills/odp/templates/dao-conference/styles.xml --json
```

## Customising

Replace `Pictures/logo.png` with your own 300×100 (or any 16:5 ratio) logo
at the same path; the master-page frame at `24.2cm × 13.9cm` (lower-right
corner) renders it on every slide. To change the background colour, edit
the `dp-default` drawing-page style in `styles.xml`.
