# Installation

Clone the repository first:

```bash
git clone https://github.com/leiverkus/open-document-skills.git
cd open-document-skills
```

## Codex

Install into the default Codex skills directory:

```bash
python3 scripts/install_skills.py
```

The default destination is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise `~/.codex/skills`.

## Legacy `.agents`

Some setups still load skills from `~/.agents/skills`:

```bash
python3 scripts/install_skills.py --target agents
```

## OpenCode

Install global OpenCode skills:

```bash
python3 scripts/install_skills.py --target opencode
```

The default destination follows OpenCode's common configuration locations:

- `$OPENCODE_CONFIG_DIR/skills` when `OPENCODE_CONFIG_DIR` is set
- `$XDG_CONFIG_HOME/opencode/skills` when `XDG_CONFIG_HOME` is set
- `~/.config/opencode/skills`

For project-local OpenCode skills:

```bash
python3 scripts/install_skills.py --target opencode --dest .opencode/skills
```

## Claude Code

Claude Code discovers skills inside plugins. This repository includes:

```text
.claude-plugin/plugin.json
skills/
```

Create a plugin bundle:

```bash
python3 scripts/install_skills.py --target claude --dest ./dist/open-document-skills
```

Then add or install `./dist/open-document-skills` as a Claude Code plugin.

## Custom Destination

Install to any skills directory:

```bash
python3 scripts/install_skills.py --dest /path/to/skills
```

Existing skill directories are skipped by default. To replace them:

```bash
python3 scripts/install_skills.py --dest /path/to/skills --replace
```

Install a subset:

```bash
python3 scripts/install_skills.py --skills odt odp
```

## Verify

After installation, each installed skill directory should contain:

```text
SKILL.md
LICENSE.txt
scripts/
```

Restart the target agent application after installing or replacing skills.

