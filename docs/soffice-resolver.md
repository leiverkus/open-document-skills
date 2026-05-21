# LibreOffice / soffice Resolver

All ODF skills need to locate the LibreOffice executable for render, recalc, and conversion workflows. Use the snippets below before running any LibreOffice-dependent command.

## Bash / sh / zsh / Git Bash / WSL

```bash
SOFFICE="$(command -v soffice || command -v libreoffice || true)"
if [ -z "$SOFFICE" ]; then
  for candidate in \
    "/Applications/LibreOffice.app/Contents/MacOS/soffice" \
    "/usr/bin/libreoffice" \
    "/usr/local/bin/libreoffice" \
    "/snap/bin/libreoffice" \
    "/c/Program Files/LibreOffice/program/soffice.exe" \
    "/mnt/c/Program Files/LibreOffice/program/soffice.exe"; do
    if [ -x "$candidate" ]; then SOFFICE="$candidate"; break; fi
  done
fi
test -n "$SOFFICE" || { echo "LibreOffice/soffice not found"; exit 1; }
```

## Windows PowerShell

```powershell
$Soffice = (Get-Command soffice -ErrorAction SilentlyContinue).Source
if (-not $Soffice) { $Soffice = "C:\Program Files\LibreOffice\program\soffice.exe" }
if (-not (Test-Path $Soffice)) { throw "LibreOffice/soffice not found" }
```

## Python

The bundled `lib/odf_common.py` provides a `find_soffice()` function that performs the same lookup programmatically:

```python
from lib.odf_common import find_soffice

soffice = find_soffice()  # raises SystemExit if not found
```

Each skill's `*_common.py` module also re-exports `find_soffice` for convenience.
