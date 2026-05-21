from __future__ import annotations

# SPDX-License-Identifier: MIT

import re
import unittest
from pathlib import Path

from helpers import ROOT


DOC_FILES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")


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


if __name__ == "__main__":
    unittest.main()
