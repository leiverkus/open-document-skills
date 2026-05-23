# minimalist-mono

A technical-talk template: near-white background, monospace headings,
clean sans-serif body. No default logo. Lots of whitespace. Aesthetic:
engineering retrospectives, dev talks, post-mortems.

## What this template offers

- **Master pages**: `Default` (slate-50 `#F8FAFC` background)
- **Slide layouts**: the v1.8 standard set (title-slide, title-content,
  two-content, section-header, title-only, blank)
- **Paragraph styles**: `Title`, `Body`, `Notes`
- **Graphic styles**: `gr-title`, `gr-body`, `gr-notes`, `gr-image`
- **Fonts**: JetBrains Mono (headings), Inter (body), with Liberation Mono
  and Liberation Sans fallbacks

## How to apply

```bash
python3 skills/odp/scripts/create_minimal_odp.py spec.json deck.odp
python3 skills/odp/scripts/apply_template.py deck.odp \
    --template-name minimalist-mono -o branded.odp
```
