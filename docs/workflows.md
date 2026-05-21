# OpenDocument Workflows

The skills prefer native OpenDocument package/XML workflows. LibreOffice is treated as an interoperability and visual QA tool.

## Common Loop

1. Create or modify the ODF package with the relevant script.
2. Inspect package structure.
3. Extract text, sheets, formulas, shapes, or slide content.
4. Validate package references.
5. Render or recalculate with LibreOffice when visual or formula QA matters.

## ODT

Create:

```bash
python3 skills/odt/scripts/create_minimal_odt.py examples/odt_document.json example.odt
```

Check:

```bash
python3 skills/odt/scripts/inspect_package.py example.odt
python3 skills/odt/scripts/extract_text.py example.odt
python3 skills/odt/scripts/validate_refs.py example.odt
```

Render:

```bash
python3 skills/odt/scripts/render.py example.odt --outdir qa --png
```

## ODP

Create:

```bash
python3 skills/odp/scripts/create_minimal_odp.py examples/odp_slides.json example.odp
```

Check:

```bash
python3 skills/odp/scripts/inspect_package.py example.odp
python3 skills/odp/scripts/extract_text.py example.odp
python3 skills/odp/scripts/list_masters.py example.odp
python3 skills/odp/scripts/validate_refs.py example.odp
```

Render:

```bash
python3 skills/odp/scripts/render.py example.odp --outdir qa --png
```

## ODS

Create:

```bash
python3 skills/ods/scripts/create_minimal_ods.py examples/ods_workbook.json example.ods
```

Check:

```bash
python3 skills/ods/scripts/inspect_package.py example.ods
python3 skills/ods/scripts/extract_sheets.py example.ods
python3 skills/ods/scripts/extract_formulas.py example.ods
python3 skills/ods/scripts/validate_refs.py example.ods
```

Recalculate:

```bash
python3 skills/ods/scripts/recalc.py example.ods --outdir qa
```

## ODG

Create:

```bash
python3 skills/odg/scripts/create_minimal_odg.py examples/odg_drawing.json example.odg
```

Check:

```bash
python3 skills/odg/scripts/inspect_package.py example.odg
python3 skills/odg/scripts/extract_text.py example.odg
python3 skills/odg/scripts/extract_shapes.py example.odg
python3 skills/odg/scripts/validate_refs.py example.odg
```

Export:

```bash
python3 skills/odg/scripts/render.py example.odg --outdir qa --formats pdf,svg,png
```

## Examples

Build all example files:

```bash
python3 examples/build_examples.py
```

Build and run optional QA:

```bash
python3 examples/build_examples.py --render --png
```

