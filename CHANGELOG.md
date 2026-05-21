# Changelog

## v0.1.1 - 2026-05-21

Maintenance and examples release.

### Added

- Runnable `examples/` directory with JSON specs for ODT, ODP, ODS, and ODG.
- Shared example SVG asset and `examples/build_examples.py` helper.
- Example test coverage to ensure all generated example files remain valid ODF packages.
- README documentation for building examples and optional LibreOffice/Poppler QA.

### Changed

- GitHub Actions now installs LibreOffice and Poppler on Ubuntu so integration tests run in CI.
- Updated GitHub Actions to `actions/checkout@v6.0.2` and `actions/setup-python@v6.2.0`.
- Example QA output is written per format below `examples/output/qa/`.

## v0.1.0 - 2026-05-21

Initial public release.

### Added

- `odt` skill for OpenDocument Text / LibreOffice Writer workflows.
- `odp` skill for OpenDocument Presentation / LibreOffice Impress workflows.
- `ods` skill for OpenDocument Spreadsheet / LibreOffice Calc workflows.
- `odg` skill for OpenDocument Graphics / LibreOffice Draw workflows.
- Direct ODF package/XML generation scripts for all four formats.
- XML-safe edit helpers for text, cells, images, slides, and drawings.
- Package inspection and reference validation scripts.
- Optional LibreOffice render/recalc helpers.
- Reusable test fixtures.
- Smoke, edge-case, and optional LibreOffice integration tests.
- GitHub Actions CI.
