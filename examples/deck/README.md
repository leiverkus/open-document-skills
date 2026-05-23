# Branded Presentation Deck Example

An end-to-end demonstration of the v1.12 ODP template stack: generate a
base deck from a JSON spec, then apply the `dao-conference` template
(curated branded `styles.xml` + logo) in a single call.

## What this builds

A branded ODP (`output/deck.odp`) with:

- a deep-blue (`#02416C`) slide background
- white bold titles, light-blue body text — no stray blue boxes
- a logo placeholder anchored bottom-right of every slide
- a title slide plus two content slides

The first slide is also the source of the README hero image.

## Run it

```bash
python3 examples/deck/build_deck.py
```

The script writes `01-base.odp` and the final `deck.odp` into
`examples/deck/output/`. If LibreOffice is available, it also renders
`deck.pdf`.

## Files in this example

- `spec.json` — slide content for `create_minimal_odp.py`.
- `build_deck.py` — the end-to-end build pipeline (now a thin wrapper).
- `output/` — generated artifacts.

## Files in the template (now upstream)

The branded `styles.xml` and the logo placeholder used to live here; in v1.12
they were migrated to `skills/odp/templates/dao-conference/` so any user can
apply the same branding without copying files. That template directory has:

- `styles.xml` — the branded theme (same named styles the generator emits)
- `Pictures/logo.png` — the logo placeholder
- `LICENSE.txt`, `PROVENANCE.md`, `README.md`

## How the pipeline works (v1.12)

```text
spec.json ──┬─▶ create_minimal_odp.py ──▶ base.odp
            │                              │
            │                              ▼
            │                    apply_template.py
            │                    --template-name dao-conference
            │                              │
            ▼                              ▼
   templates/dao-conference/  ──────▶ branded.odp
       styles.xml                          │
       Pictures/logo.png                   ▼
                                      render.py
                                          │
                                          ▼
                                       deck.pdf
```

`apply_template.py` wraps the three steps that this example used to do by
hand (inject styles → embed pictures → validate). The branded `styles.xml`
reuses the generator's style names (`dp-default`, `gr-title`, `gr-body`,
`gr-image`, `Title`, `Body`, master `Default`, layout `Screen`), so the
injection is a clean drop-in: no edits to `content.xml`.

## Adapting for your project

1. Edit `spec.json` with your own slides.
2. Copy `skills/odp/templates/dao-conference/` to a new template directory
   (e.g. `skills/odp/templates/my-brand/`) and customise the colours, fonts,
   and the logo frame position.
3. Replace `Pictures/logo.png` with your brand mark.
4. Rebuild with `--template-name my-brand`.

For per-master tweaks instead of a full theme swap, see
`skills/odp/scripts/customize_master.py`. To see what a template offers
before applying it, use `inspect_template.py` (new in v1.12).
