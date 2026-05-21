# Contributing

Thanks for helping improve the Open Document Skills repository.

## Development Setup

The scripts use only the Python standard library. Optional QA workflows require LibreOffice and, for PNG page previews, Poppler.

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

Run the full test suite:

```bash
python3 -m unittest discover -s tests
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
2. Run `python3 -m unittest discover -s tests`.
3. Run `python3 examples/build_examples.py --render --png` when LibreOffice and Poppler are available.
4. Update `CHANGELOG.md`.
5. Commit the release notes.
6. Create an annotated tag, for example:

```bash
git tag -a v0.1.2 -m "v0.1.2"
```

7. Push `main` and the tag.
8. Create the GitHub release.
9. Confirm GitHub Actions is green for both `main` and the tag.

## License

By contributing, you agree that your contribution is licensed under the MIT License.
