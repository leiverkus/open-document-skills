# Contributing

Thanks for helping improve the Open Document Skills repository.

## Development Setup

The scripts use only the Python standard library. Optional QA workflows require LibreOffice and, for PNG page previews, Poppler.

```bash
# Create a virtual environment and install dev dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

On macOS:

```bash
brew install poppler
```

LibreOffice is normally discovered at:

```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice
```

On Ubuntu CI, the workflow installs:

```bash
sudo apt-get install -y libreoffice poppler-utils
```

## Local Checks

Run the full test suite with coverage:

```bash
pytest tests/ --cov=odf_lib
```

Lint and format:

```bash
ruff check .
ruff format --check .
```

Pre-commit hooks run both automatically on every commit.

Type-check `odf_lib/` and the four skills. The skills hold same-named
modules (`validate_refs.py` etc.) and are not packages, so mypy runs
per directory:

```bash
mypy odf_lib
for d in odt odp ods odg; do mypy skills/$d/scripts; done
```

Build the runnable examples:

```bash
python3 examples/build_examples.py
```

Run optional visual/recalculation QA:

```bash
python3 examples/build_examples.py --render --png
```

Generated example outputs are written to `examples/output/` and are ignored by Git.

## Real-World Corpus

`tests/fixtures/corpus/` holds LibreOffice-native ODF fixtures that `tests/test_corpus.py`
runs every helper against. The fixtures are committed, so the tests run anywhere without
LibreOffice. If you change anything structural — the flat-ODF pack/unpack format, the
`validate_refs` checks, or the shared XML helpers in `lib/odf_common.py` — regenerate the
corpus so it reflects current output, then re-run the suite:

```bash
python3 tests/fixtures/corpus/build_corpus.py   # requires LibreOffice (soffice)
python3 -m unittest discover -s tests
```

`build_corpus.py` is a maintainer tool, not part of CI.

## Adding or Changing Scripts

Keep scripts small, deterministic, and standard-library-only unless there is a strong reason to add a dependency.

When adding behavior:

1. Update the relevant skill's `SKILL.md` if the workflow changes.
2. Add or update a focused test in `tests/`.
3. Add an example fixture if the behavior is useful for users to copy.
4. Run local tests and example builds.
5. Update the README script reference when adding or renaming a script.

## Skill Installation Check

From a checkout, verify that the installer can copy the skills into Codex/OpenCode-style skills directories:

```bash
tmpdir="$(mktemp -d)"
python3 scripts/install_skills.py --dest "$tmpdir/skills"
python3 scripts/install_skills.py --target opencode --dest "$tmpdir/opencode/skills"
find "$tmpdir/skills" -maxdepth 2 -name SKILL.md
rm -rf "$tmpdir"
```

Verify the Claude Code plugin bundle path:

```bash
tmpdir="$(mktemp -d)"
python3 scripts/install_skills.py --target claude --dest "$tmpdir/open-document-skills"
test -f "$tmpdir/open-document-skills/.claude-plugin/plugin.json"
rm -rf "$tmpdir"
```

Each skill directory should contain:

- `SKILL.md`
- `LICENSE.txt`
- `scripts/`

## Release Checklist

1. Ensure `main` is clean.
2. Run `pytest tests/ --cov=odf_lib --cov-fail-under=30`.
3. Run `ruff check . && ruff format --check .`.
4. Run `mypy odf_lib` and `mypy skills/<fmt>/scripts` for each of `odt`, `odp`, `ods`, `odg`.
5. Run `python3 examples/build_examples.py --render --png` when LibreOffice and Poppler are available.
6. Update `CHANGELOG.md` and the `version` in `pyproject.toml`.
7. Update `VERSION` in [odf_lib/odf_common.py](odf_lib/odf_common.py) to match `pyproject.toml` (used as the `meta:generator` string written into edited documents).
8. Update `version:` in all four `SKILL.md` files and `version` in [.claude-plugin/plugin.json](.claude-plugin/plugin.json).
9. Commit the release notes.
10. Create an annotated tag, for example:

    ```bash
    git tag -a v1.0.0 -m "v1.0.0"
    ```

11. Push `main` and the tag.
12. Create the GitHub release. Publishing the release triggers
    `.github/workflows/publish.yml`, which builds the `open-document-lib`
    distribution and uploads it to PyPI.
13. Confirm GitHub Actions is green for `main`, the tag, and the publish run.

### One-time PyPI setup

The publish workflow uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC) — no API token is stored. Before the first release, register a
trusted publisher on PyPI for the `open-document-lib` project: owner/repo
`leiverkus/open-document-skills`, workflow `publish.yml`, environment
`pypi`. For the very first upload, register it as a *pending* publisher.

## License

By contributing, you agree that your contribution is licensed under the MIT License.
