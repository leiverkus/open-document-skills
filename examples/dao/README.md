# DAO Grant Proposal Example

An end-to-end demonstration of the v0.4 scholarly-authoring stack: citations, footnotes, cross-references, sequences (figure numbering), and LaTeX formulas — all combined in a realistic German-language grant-proposal workflow.

## What this builds

A short ODT (eventually `output/grant_proposal.odt`) with:

- five sections (Zusammenfassung, Forschungsstand, Methodik, Arbeitsprogramm, Literatur)
- three citations from `refs.bib` (filled from pandoc-style `[@bibkey]` placeholders)
- one footnote on the methodology
- a bookmark + cross-reference linking back to the Methodik chapter
- a figure sequence (`Figure 1`) plus a sequence-ref to it
- a LaTeX formula (Carbon-14 decay, `N(t) = N_0 e^{-\lambda t}`) embedded as MathML

## Run it

```bash
python3 examples/dao/build_grant_proposal.py
```

The script writes intermediate stages (`01-base.odt` … `08-with-math.odt`) plus the final `grant_proposal.odt` into `examples/dao/output/`. If LibreOffice is available, it also renders `grant_proposal.pdf`.

## Files

- `spec.json` — block-level content spec for `create_minimal_odt.py`. Contains the placeholder text including `[@bibkey]` markers and the anchors that later scripts target.
- `refs.bib` — BibTeX bibliography with three Theologie-/Archäologie-Beispieleinträge.
- `build_grant_proposal.py` — the end-to-end build pipeline; each step calls one of the ODT skill scripts.

## What this is not

- Not a real DAO/Solearis Antrag template. The styling layer (Nunito Sans, `#02416C`, official page geometry) is a v0.5 follow-up — for now the ODT uses the default `create_minimal_odt.py` styles.
- Not a substitute for a proper Antrags-Software wie GEPRIS, DRUM, oder Antragsdatenbank. This shows what the **skills** can produce; the workflow with a real Verwaltung läuft anders.
- Not the entire DFG-Antragsformular — kein Tabellenwerk, kein Personalkostenrechner, keine institutionellen Stempel.

## Adapting for your project

1. Replace `spec.json` content with your own block list.
2. Replace `refs.bib` with your bibliography (or use a `.csl.json` and adjust `--source`).
3. Tweak anchors in `build_grant_proposal.py` so they match new spec text.
4. Add or remove pipeline steps to suit (e.g. drop the math step if no formulas).

The pipeline is intentionally linear and idempotent — every step takes one ODT and produces another, so you can stop after any step and inspect the intermediate result.
