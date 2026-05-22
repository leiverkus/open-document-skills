# Branded Presentation Deck Example

An end-to-end demonstration of ODP presentation styling: a base deck is
generated from a JSON spec, then a curated branded `styles.xml` is injected
to swap the whole theme — dark brand-blue slides, light typography, a logo
on every slide — without touching the slide content.

## What this builds

A three-slide ODP (`output/deck.odp`) with:

- a deep-blue (`#02416C`) slide background
- a white bold title and light-blue body text — no stray blue boxes
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

## Files

- `spec.json` — slide content for `create_minimal_odp.py`.
- `styles.xml` — the branded theme. It redefines the **same named styles**
  the generator emits (`dp-default`, `gr-title`, `gr-body`, `gr-image`,
  `Title`, `Body`, master `Default`, layout `Screen`), so injecting it
  replaces the look while `content.xml` keeps referencing styles by name.
- `logo-placeholder.png` — a stand-in logo; swap in your own.
- `build_deck.py` — the end-to-end build pipeline.

## How the styling works

`create_minimal_odp.py` already produces a presentable deck: a real
`drawing-page` background style, `graphic` frame styles with
`draw:fill="none"` (so frames are not blue boxes), and coloured text. This
example goes one step further and shows the **branding** path:

1. Generate the base ODP.
2. `inject_styles_from_file` swaps in `styles.xml` — a complete branded
   theme defined with the same style names.
3. `embed_pictures` adds the logo file the branded master page references.

Because the branded `styles.xml` reuses the generator's style names, the
injection is a clean drop-in: no edits to `content.xml` are needed.

## Adapting for your project

1. Edit `spec.json` with your own slides.
2. Edit `styles.xml` colours, fonts, and the logo frame position.
3. Replace `logo-placeholder.png` with your brand mark.
4. Re-run `build_deck.py`.

For per-master tweaks instead of a full theme swap, see
`skills/odp/scripts/customize_master.py` (background colour, header/footer,
page numbers, logo).
