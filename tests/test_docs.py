from __future__ import annotations

# SPDX-License-Identifier: MIT
import re
import unittest

from helpers import ROOT

DOC_FILES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")
SKILL_VERSION_RE = re.compile(r'^version:\s*"([^"]+)"', re.MULTILINE)


class DocsTests(unittest.TestCase):
    def test_internal_markdown_links_exist(self) -> None:
        for doc in DOC_FILES:
            text = doc.read_text(encoding="utf-8")
            for link in LINK_RE.findall(text):
                if "://" in link:
                    continue
                target = (doc.parent / link).resolve()
                self.assertTrue(target.exists(), f"{doc.relative_to(ROOT)} links to missing {link}")

    def test_docs_index_lists_core_pages(self) -> None:
        index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
        for name in ["installation.md", "agent-compatibility.md", "workflows.md", "script-reference.md"]:
            self.assertIn(name, index)

    def test_skill_versions_match_pyproject(self) -> None:
        """All SKILL.md version fields must match pyproject.toml version."""
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        pyproject_version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
        assert pyproject_version_match is not None, "No version found in pyproject.toml"
        pyproject_version = pyproject_version_match.group(1)

        for skill_dir in sorted((ROOT / "skills").iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            text = skill_md.read_text(encoding="utf-8")
            version_match = SKILL_VERSION_RE.search(text)
            assert version_match is not None, f"No version found in {skill_md.relative_to(ROOT)}"
            skill_version = version_match.group(1)
            self.assertEqual(
                pyproject_version,
                skill_version,
                f"Version mismatch: {skill_md.relative_to(ROOT)} has {skill_version}, "
                f"pyproject.toml has {pyproject_version}",
            )


if __name__ == "__main__":
    unittest.main()
