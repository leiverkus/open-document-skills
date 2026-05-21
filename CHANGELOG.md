# Changelog

## v0.1.3 - 2026-05-21

Multi-agent and documentation release.

### Added

- Claude Code plugin metadata via `.claude-plugin/plugin.json`.
- OpenCode and Claude Code installation targets in `scripts/install_skills.py`.
- Agent compatibility documentation for Codex, Claude Code, and OpenCode.
- Dedicated docs pages for installation, workflows, and script reference.
- Documentation link tests.

### Changed

- Skill frontmatter now uses portable `license: MIT` and `version` metadata.
- README now presents the repository as an agent skill pack for Codex, Claude Code, and OpenCode.
- `pyproject.toml` metadata now describes the package as agent skills for OpenDocument files.

## v0.1.2 - 2026-05-21

Documentation and installation release.

### Added

- `scripts/install_skills.py` to install the ODT, ODP, ODS, and ODG skills into `$CODEX_HOME/skills`, `~/.codex/skills`, or a custom destination.
- Installer test coverage for custom destinations and existing-skill skip behavior.
- `CONTRIBUTING.md` with local checks, example QA, installation checks, and release checklist.
- README script-reference tables for all four skills.

### Changed

- README installation instructions now prefer the installer script and document `~/.agents/skills` as an explicit legacy/custom destination.
- README release status updated to `v0.1.2`.

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
