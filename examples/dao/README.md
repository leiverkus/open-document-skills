# DAO Grant Proposal Example (German localisation)

A **localisation showcase** for the v1.13 ODT template ecosystem: a
German-language DAO-archaeology grant proposal built on the same
`apply_template` pipeline as the shipped generic `grant-proposal`
template, but with German prose, DAO-blue (`#02416C`) branding, and
Nunito Sans typography instead of the generic Lato/Source Serif.

This is also an end-to-end demonstration of the v0.4 scholarly-authoring
stack: citations, footnotes, cross-references, figure sequences, and
LaTeX formulas.

## How it relates to the shipped template

| | `skills/odt/templates/grant-proposal/` | `examples/dao/` |
|---|---|---|
| Language | English | German |
| Accent | Navy `#1B3A57` | DAO blue `#02416C` |
| Typography | Lato + Source Serif | Nunito Sans (+ SemiBold) |
| Style names | `Title`, `Heading1`, … | DAO-prefixed + standard names |
| Logo | none (institution-neutral) | `Pictures/logo.png` (DAO placeholder) |
| Audience | Any agency, any country | German archaeology institutes |

`examples/dao/` is itself a valid template directory (`styles.xml` +
`Pictures/logo.png` + `LICENSE.txt`-style content) that `apply_template`
consumes via the `--template` path argument.

## What this builds

A short ODT (`output/grant_proposal.odt`) with:

- five sections (Zusammenfassung, Forschungsstand, Methodik, Arbeitsprogramm, Literatur)
- DAO-blue styling injected via `apply_template.py`
- DAO logo placeholder embedded in the header
- three citations from `refs.bib` (filled from pandoc-style `[@bibkey]` placeholders)
- one footnote on the methodology
- a bookmark + cross-reference linking back to the Methodik chapter
- a figure sequence (`Figure 1`) plus a sequence-ref to it
- a LaTeX formula (Carbon-14 decay) embedded as MathML

## Run it

```bash
python3 examples/dao/build_grant_proposal.py
```

The script writes intermediate stages (`01-base.odt` … `09-with-math.odt`)
plus the final `grant_proposal.odt` into `examples/dao/output/`. If
LibreOffice is available, it also renders `grant_proposal.pdf`.

## Files in this example

- `spec.json` — German block-level content spec for `create_minimal_odt.py`.
  Contains the placeholder text including `[@bibkey]` markers and the
  German anchors (e.g. "3. Methodik", "siehe Abbildung") that later
  scripts target.
- `styles.xml` — DAO-branded styles (the actual template).
- `Pictures/logo.png` — DAO logo placeholder, referenced by the header
  in `styles.xml`.
- `refs.bib` — BibTeX bibliography with three example archaeology entries.
- `build_grant_proposal.py` — the end-to-end build pipeline.

## Localising for your own institution

Use this directory as a copy-and-adapt starting point:

```bash
cp -r examples/dao my-project/
# Edit my-project/styles.xml — colours, fonts, header text, logo position
# Replace my-project/Pictures/logo.png with your institution's logo
# Edit my-project/spec.json with your project's content
python3 examples/dao/build_grant_proposal.py  # or copy + adapt to your project
```

The English-first generic starting point is
`skills/odt/templates/grant-proposal/` — fork it if you don't need the
DAO/German specifics.
