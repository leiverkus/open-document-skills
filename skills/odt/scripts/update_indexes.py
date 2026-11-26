#!/usr/bin/env python3
"""Refresh generated indexes (TOC, bibliography, illustration index, alphabetical
index) in an ODT via headless LibreOffice.

The ``add_*_index.py`` scripts insert each index container with a
``text:<kind>-source`` (configuration) plus an empty ``text:index-body``
placeholder. LibreOffice fills the body when a Basic macro dispatches an
index-refresh on the loaded document. This script automates that:

1. Copies the input ODT to ``--outdir``.
2. Creates an isolated ``-env:UserInstallation`` temp profile.
3. Writes a tiny ``Standard/Module1.RefreshIndexes`` Basic library + permissive
   ``MacroSecurityLevel=0`` into the temp profile (the real user profile is
   never touched). ``ooSetupInstCompleted=true`` is set as well: without it a
   fresh profile runs LibreOffice's first-start setup, which silently drops
   the macro URL, so nothing is refreshed.
4. Invokes ``soffice`` headless with a macro URL that carries the document
   URL as its argument. The macro loads the document itself (hidden), walks
   ``DocumentIndexes`` and calls ``.update()`` on each, then stores and closes
   it. (Passing the document on the command line and relying on
   ``ThisComponent`` is racy: the macro can run before the document is loaded,
   exit without closing anything, and leave soffice running forever.)
5. Cleans up the temp profile.

Mirrors the ``recalc.py`` (ODS, v0.6) pattern for Calc formulas. On
platforms where headless-CLI macro execution is blocked the script reports a
warning and the index bodies remain at their placeholder state — open the
document once in LibreOffice GUI and run **Tools → Update → Update All
Indexes** (or press F9) as a manual fallback.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from odt_common import NS, find_soffice, parse_xml_from_zip

_XLB_SCRIPT_LIBRARY = """<?xml version="1.0" encoding="UTF-8"?>
<library:library xmlns:library="http://openoffice.org/2000/library" library:name="Standard" library:readonly="false" library:passwordprotected="false">
 <library:element library:name="Module1"/>
</library:library>
"""

_XLB_SCRIPT_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<library:libraries xmlns:library="http://openoffice.org/2000/library" xmlns:xlink="http://www.w3.org/1999/xlink">
 <library:library library:name="Standard" library:link="false"/>
</library:libraries>
"""

_XLB_DIALOG_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<library:libraries xmlns:library="http://openoffice.org/2000/library" xmlns:xlink="http://www.w3.org/1999/xlink"/>
"""

_MODULE_XBA = """<?xml version="1.0" encoding="UTF-8"?>
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
Sub RefreshIndexes(sUrl As String)
    Dim oDoc As Object
    On Error GoTo Failed
    Dim aProps(0) As New com.sun.star.beans.PropertyValue
    aProps(0).Name = &quot;Hidden&quot;
    aProps(0).Value = True
    oDoc = StarDesktop.loadComponentFromURL(sUrl, &quot;_blank&quot;, 0, aProps())
    If IsNull(oDoc) Then
        Exit Sub
    End If
    Dim oIndexes As Object
    oIndexes = oDoc.DocumentIndexes
    Dim i As Integer
    For i = 0 To oIndexes.Count - 1
        oIndexes.getByIndex(i).update()
    Next i
    oDoc.store()
    oDoc.close(True)
    Exit Sub
Failed:
    If Not IsNull(oDoc) Then
        oDoc.close(True)
    End If
End Sub
</script:module>
"""

_REGISTRY_XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
 <item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>0</value></prop></item>
 <item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="FirstRun" oor:op="fuse"><value>false</value></prop></item>
 <item oor:path="/org.openoffice.Setup/Office"><prop oor:name="ooSetupInstCompleted" oor:op="fuse"><value>true</value></prop></item>
</oor:items>
"""


def _write_basic_module(profile_root: Path) -> None:
    mod_dir = profile_root / "user" / "basic" / "Standard"
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "script.xlb").write_text(_XLB_SCRIPT_LIBRARY, encoding="utf-8")
    (mod_dir / "Module1.xba").write_text(_MODULE_XBA, encoding="utf-8")
    basic_dir = profile_root / "user" / "basic"
    (basic_dir / "script.xlc").write_text(_XLB_SCRIPT_INDEX, encoding="utf-8")
    (basic_dir / "dialog.xlc").write_text(_XLB_DIALOG_INDEX, encoding="utf-8")
    (profile_root / "user" / "registrymodifications.xcu").write_text(_REGISTRY_XCU, encoding="utf-8")


def _count_index_body_children(odt: Path) -> int:
    """Return the total number of children across all text:index-body elements."""
    try:
        content = parse_xml_from_zip(odt, "content.xml")
    except (KeyError, OSError):
        return 0
    body_tag = f"{{{NS['text']}}}index-body"
    return sum(len(list(b)) for b in content.iter(body_tag))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odt", type=Path)
    parser.add_argument("--outdir", type=Path, default=Path("qa"))
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="soffice run timeout in seconds (default: %(default)s)"
    )
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    target = args.outdir / args.odt.name
    shutil.copyfile(args.odt, target)

    before = _count_index_body_children(target)

    soffice = find_soffice()
    profile = Path(tempfile.mkdtemp(prefix="odf-soffice-"))
    try:
        _write_basic_module(profile)
        # as_uri() percent-encodes quotes, commas and parentheses, so the
        # URL is safe inside the Basic string literal and the macro URL.
        target_url = target.resolve().as_uri()
        cmd = [
            soffice,
            f"-env:UserInstallation={profile.as_uri()}",
            "--headless",
            "--norestore",
            "--nologo",
            "--nofirststartwizard",
            f'macro:///Standard.Module1.RefreshIndexes("{target_url}")',
        ]
        # Own process group: the soffice launcher forks soffice.bin, and on
        # timeout the whole group must go — otherwise soffice.bin survives
        # with its profile deleted underneath it.
        proc = subprocess.Popen(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
        )
        try:
            output, _ = proc.communicate(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            print(
                f"soffice timed out after {args.timeout}s — indexes may not be refreshed",
                file=sys.stderr,
            )
            raise SystemExit(2)
        if proc.returncode != 0:
            print(output, file=sys.stderr)
            raise SystemExit(proc.returncode)
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    after = _count_index_body_children(target)
    if after <= before:
        print(
            "warning: index bodies did not grow — your platform's headless macro execution\n"
            "may be blocked. Workaround: open the document in LibreOffice GUI and run\n"
            "Tools → Update → Update All Indexes (or press F9), then save.",
            file=sys.stderr,
        )
    print(target)


if __name__ == "__main__":
    main()
