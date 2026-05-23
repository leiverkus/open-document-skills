# Repository Layout

The repository keeps one canonical skill source under `skills/` and one
shared library under `odf_lib/`. Installers and plugin metadata adapt that
source to each target runtime.

```text
open-document-skills/
├── .claude-plugin/        # Claude Code plugin manifest + marketplace
│   ├── plugin.json
│   └── marketplace.json
├── .github/workflows/     # CI: tests.yml + publish.yml (PyPI on release)
├── benchmarks/            # Maintainer benchmarks (run_benchmarks.py)
├── docs/                  # Long-form documentation
│   ├── index.md
│   ├── installation.md
│   ├── agent-compatibility.md
│   ├── workflows.md
│   ├── script-reference.md
│   ├── library-api.md
│   ├── repository-layout.md
│   └── soffice-resolver.md
├── examples/              # Curated end-to-end examples
│   ├── dao/               # DAO grant proposal (ODT, branded inject + DFG style)
│   ├── deck/              # Branded ODP deck
│   ├── diagram/           # Branded ODG flowchart
│   ├── article/           # Markdown → ODT showcase
│   └── build_examples.py  # Build all four examples in one shot
├── odf_lib/               # Shared library — published to PyPI as `open-document-lib`
│   ├── __init__.py        # Curated public API (re-exports)
│   ├── odf_common.py      # ZIP/XML, walker, manifest, render, schema, …
│   ├── themes.py          # Curated theme registry (palette + font pairing)
│   └── py.typed           # PEP 561 marker
├── scripts/               # Maintainer scripts (install_skills.py)
├── skills/                # Four agent skills — each MIT-licensed and standalone
│   ├── odt/               # OpenDocument Text (Writer)
│   ├── odp/               # OpenDocument Presentation (Impress)
│   ├── ods/               # OpenDocument Spreadsheet (Calc)
│   └── odg/               # OpenDocument Graphics (Draw)
│       ├── SKILL.md       # Skill metadata + agent-facing guidance
│       ├── LICENSE.txt
│       └── scripts/       # Stdlib-only CLI scripts, one per task
├── tests/                 # Unittest suite (~350 tests)
│   ├── fixtures/
│   │   └── corpus/        # LibreOffice-roundtripped real-world ODFs
│   ├── helpers.py
│   └── test_*.py
├── AGENTS.md              # Conventions for agents working *on* the repo
├── CHANGELOG.md
├── CLAUDE.md              # Re-exports AGENTS.md for Claude Code
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── pyproject.toml         # `open-document-lib` package + dev/scholarly/validate/render extras
```

Each `skills/<format>/` directory is a self-contained skill: it ships with its
own `SKILL.md`, `LICENSE.txt`, and `scripts/`. The `install_skills.py`
maintainer script also bundles a copy of `odf_lib/` into each installed skill
so the scripts run standalone without an editable repo.
