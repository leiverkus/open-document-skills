# Agent Compatibility

The repository keeps one canonical source:

```text
skills/
  odt/
    SKILL.md
    LICENSE.txt
    scripts/
  odp/
  ods/
  odg/
```

Each `SKILL.md` uses YAML frontmatter:

```yaml
---
name: odt
description: "Use this skill whenever ..."
license: MIT
version: "0.1.2"
---
```

## Codex

Codex reads skills from a skills directory such as `~/.codex/skills` or another configured skill root. The installer copies each format directory directly into that destination.

## Claude Code

Claude Code plugin skills use a plugin wrapper:

```text
open-document-skills/
  .claude-plugin/
    plugin.json
  skills/
    odt/
      SKILL.md
```

The repository already matches this layout at the root. The installer can also create a clean plugin bundle in another directory.

## OpenCode

OpenCode-compatible skills are discovered from skills directories such as:

```text
~/.config/opencode/skills/
~/.opencode/skills/
.opencode/skills/
```

The installer copies the same `skills/odt`, `skills/odp`, `skills/ods`, and `skills/odg` folders into the chosen OpenCode destination.

## Compatibility Rules

- Keep `name` equal to the directory name.
- Keep `description` explicit about when the skill should trigger.
- Keep helper scripts relative to the skill directory.
- Avoid agent-specific instructions inside `SKILL.md` unless they are necessary for the file format workflow.
- Put runtime-specific installation behavior in `scripts/install_skills.py` or docs, not in the skills themselves.

