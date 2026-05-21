from __future__ import annotations

# SPDX-License-Identifier: MIT
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from helpers import ROOT, SKILLS, assert_mimetype_first, run_script

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


class ExampleTests(unittest.TestCase):
    def test_build_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp) / "examples"
            subprocess.run(
                [sys.executable, str(ROOT / "examples" / "build_examples.py"), "--outdir", str(outdir)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for filename in ["example.odt", "example.odp", "example.ods", "example.odg"]:
                path = outdir / filename
                self.assertTrue(path.exists(), filename)
                assert_mimetype_first(self, path)

    def test_dao_build_grant_proposal_runs_end_to_end(self) -> None:
        """The examples/dao/build_grant_proposal.py pipeline must complete and validate."""
        subprocess.run(
            [sys.executable, str(ROOT / "examples" / "dao" / "build_grant_proposal.py")],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        final = ROOT / "examples" / "dao" / "output" / "grant_proposal.odt"
        self.assertTrue(final.exists())
        assert_mimetype_first(self, final)
        # validate_refs must pass cleanly
        result = run_script(SKILLS / "odt" / "scripts" / "validate_refs.py", final)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")
        # Inspect: at least 3 citations, 1 footnote, 1 bookmark, 1 sequence
        with zipfile.ZipFile(final) as archive:
            content = ET.fromstring(archive.read("content.xml"))
        citations = [e for e in content.iter() if e.tag == f"{{{NS['text']}}}bibliography-mark"]
        notes = [e for e in content.iter() if e.tag == f"{{{NS['text']}}}note"]
        bookmarks = [e for e in content.iter() if e.tag == f"{{{NS['text']}}}bookmark"]
        sequences = [e for e in content.iter() if e.tag == f"{{{NS['text']}}}sequence"]
        self.assertGreaterEqual(len(citations), 3)
        self.assertGreaterEqual(len(notes), 1)
        self.assertGreaterEqual(len(bookmarks), 1)
        self.assertGreaterEqual(len(sequences), 1)


if __name__ == "__main__":
    unittest.main()
