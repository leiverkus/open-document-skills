# Branded Flowchart Example

An end-to-end demonstration of ODG drawing styling: a flowchart is
generated from a JSON spec with per-shape colours, its nodes are
connected, and a curated branded `styles.xml` is injected to re-theme the
default-styled shapes.

## What this builds

A one-page ODG (`output/diagram.odg`) with:

- a light-grey page background — no stray generic-blue boxes
- five connected nodes: a `Draft` start, three review steps, a `Publish` end
- per-shape colours from the spec (dark-blue start, amber "Revise", green
  end) layered over a clean white-card theme

## Run it

```bash
python3 examples/diagram/build_diagram.py
```

The script writes `01-base.odg`, the connected stages, and the final
`diagram.odg` into `examples/diagram/output/`. If LibreOffice is
available, it also renders `diagram.pdf`.

## Files

- `spec.json` — shapes for `create_minimal_odg.py`. Each item may carry
  per-shape styling keys: `fill`, `stroke`, `stroke-width`, `text-color`,
  `font-size`, and `corner-radius` (rectangles).
- `styles.xml` — the branded theme. It redefines the **same named styles**
  the generator emits (`standard`, `gr-shape`, `gr-text`, `gr-line`,
  `gr-image`, `dp-default`, master `Default`, layout `Screen`), so
  injecting it re-themes every default-styled shape.
- `build_diagram.py` — the end-to-end build pipeline.

## How the styling works

`create_minimal_odg.py` already produces a presentable drawing: a designed
`standard` graphic style (so even a styleless shape inherits a sensible
look, not LibreOffice's generic blue), role styles for shapes/text/lines/
images, and a `drawing-page` page background.

Two layers of control:

1. **Per-shape keys** — `fill`, `stroke`, `text-color`, etc. in `spec.json`
   produce per-shape automatic styles in `content.xml`. The amber `Revise`
   box and the coloured start/end nodes come from here.
2. **Theme swap** — `inject_styles_from_file` replaces `styles.xml` with a
   branded theme. Because it reuses the generator's style names, every
   shape that did *not* set per-shape keys picks up the new look, while the
   per-shape overrides (which live in `content.xml`) survive untouched.

## Adapting for your project

1. Edit `spec.json` with your own shapes and per-shape colours.
2. Edit `styles.xml` to change the theme (page background, default card
   look, fonts).
3. Adjust the `EDGES` list in `build_diagram.py` to match your node names.
4. Re-run `build_diagram.py`.
