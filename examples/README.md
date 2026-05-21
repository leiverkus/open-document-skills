# Examples

This directory contains small, reproducible example inputs for the four OpenDocument skills.

## Build

From the repository root:

```bash
python examples/build_examples.py
```

This creates:

```text
examples/output/example.odt
examples/output/example.odp
examples/output/example.ods
examples/output/example.odg
```

The generated files are ignored by Git. The source JSON files and shared SVG asset are tracked.

## Optional QA

Render or recalculate the generated files with LibreOffice:

```bash
python examples/build_examples.py --render
```

QA output is written below `examples/output/qa/`, with one subdirectory per format.

On macOS, install Poppler first if you also want PNG page images:

```bash
brew install poppler
python examples/build_examples.py --render --png
```

LibreOffice is discovered automatically from common locations, including:

```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice
```

## Files

- `odt_document.json` demonstrates headings, paragraphs, lists, tables, images, and footnotes.
- `odp_slides.json` demonstrates slides, images, speaker notes, and a simple QA checklist.
- `ods_workbook.json` demonstrates typed cell content and formulas.
- `odg_drawing.json` demonstrates text boxes, shapes, connectors, and images.

## License

MIT. See the repository `LICENSE`.
