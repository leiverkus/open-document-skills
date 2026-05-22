#!/usr/bin/env python3
"""Performance benchmarks for the open-document-skills helpers.

Generates large documents and times the core operations end-to-end
(create, edit, validate, flat-ODF round-trip) by invoking the actual CLI
scripts — the same path a user takes. This is a maintainer tool: it is
not part of CI (runner variance makes hard thresholds unreliable).

    python3 benchmarks/run_benchmarks.py            # full sizes
    python3 benchmarks/run_benchmarks.py --quick    # tiny sizes (smoke)
    python3 benchmarks/run_benchmarks.py --save     # also write results.md

Numbers are indicative and machine-dependent — compare relative cost and
scaling, not absolute milliseconds.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

# (full, quick) sizes for each dimension.
SIZES = {
    "odt_paragraphs": (2000, 20),
    "ods_rows": (1000, 10),
    "ods_cols": (100, 5),
    "odp_slides": (100, 3),
    "odg_shapes": (500, 10),
}


def run(script: Path, *args: object) -> None:
    """Invoke a CLI script, raising on failure."""
    proc = subprocess.run(
        [sys.executable, "-B", str(script), *map(str, args)],
        cwd=script.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{script.name} failed:\n{proc.stdout}")


def timed(rows: list[tuple[str, str, str, float]], fmt: str, op: str, detail: str, fn) -> None:
    """Run *fn*, record elapsed seconds into *rows*."""
    start = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - start
    rows.append((fmt, op, detail, elapsed))
    print(f"  {op:<22} {detail:<18} {elapsed * 1000:8.1f} ms")


def write_spec(path: Path, spec: object) -> Path:
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def bench_odt(rows: list, tmp: Path, quick: bool) -> None:
    n = SIZES["odt_paragraphs"][1 if quick else 0]
    scripts = SKILLS / "odt" / "scripts"
    print(f"ODT — {n} paragraphs")
    spec = write_spec(
        tmp / "odt.json",
        {
            "title": "Benchmark",
            "blocks": [{"type": "paragraph", "text": f"Paragraph {i} with the marker WORD here."} for i in range(n)],
        },
    )
    odt = tmp / "doc.odt"
    flat = tmp / "doc.fodt"
    back = tmp / "round.odt"
    edited = tmp / "edited.odt"
    timed(rows, "ODT", "create_minimal", f"{n} paragraphs", lambda: run(scripts / "create_minimal_odt.py", spec, odt))
    timed(rows, "ODT", "replace_text", f"{n} paragraphs", lambda: run(scripts / "replace_text.py", odt, "WORD", "TERM", "-o", edited))
    timed(rows, "ODT", "validate_refs", f"{n} paragraphs", lambda: run(scripts / "validate_refs.py", odt))
    timed(rows, "ODT", "pack_fodt", f"{n} paragraphs", lambda: run(scripts / "pack_fodt.py", odt, "-o", flat))
    timed(rows, "ODT", "unpack_fodt", f"{n} paragraphs", lambda: run(scripts / "unpack_fodt.py", flat, "-o", back))


def bench_ods(rows: list, tmp: Path, quick: bool) -> None:
    nrows = SIZES["ods_rows"][1 if quick else 0]
    ncols = SIZES["ods_cols"][1 if quick else 0]
    scripts = SKILLS / "ods" / "scripts"
    cells = nrows * ncols
    print(f"ODS — {nrows}×{ncols} = {cells} cells")
    spec = write_spec(
        tmp / "ods.json",
        {"sheets": [{"name": "Data", "rows": [[f"r{r}c{c}" for c in range(ncols)] for r in range(nrows)]}]},
    )
    ods = tmp / "book.ods"
    edited = tmp / "edited.ods"
    timed(rows, "ODS", "create_minimal", f"{cells} cells", lambda: run(scripts / "create_minimal_ods.py", spec, ods))
    timed(rows, "ODS", "replace_cells", f"{cells} cells", lambda: run(scripts / "replace_cells.py", ods, "Data!A1=changed", "-o", edited))
    timed(rows, "ODS", "validate_refs", f"{cells} cells", lambda: run(scripts / "validate_refs.py", ods))


def bench_odp(rows: list, tmp: Path, quick: bool) -> None:
    n = SIZES["odp_slides"][1 if quick else 0]
    scripts = SKILLS / "odp" / "scripts"
    print(f"ODP — {n} slides")
    spec = write_spec(
        tmp / "odp.json",
        {"slides": [{"name": f"Slide{i}", "title": f"Title {i}"} for i in range(n)]},
    )
    odp = tmp / "deck.odp"
    cloned = tmp / "cloned.odp"
    timed(rows, "ODP", "create_minimal", f"{n} slides", lambda: run(scripts / "create_minimal_odp.py", spec, odp))
    timed(rows, "ODP", "clone_slide", f"{n} slides", lambda: run(scripts / "clone_slide.py", odp, "-o", cloned, "--source-slide", "1"))
    timed(rows, "ODP", "validate_refs", f"{n} slides", lambda: run(scripts / "validate_refs.py", odp))


def bench_odg(rows: list, tmp: Path, quick: bool) -> None:
    n = SIZES["odg_shapes"][1 if quick else 0]
    scripts = SKILLS / "odg" / "scripts"
    print(f"ODG — {n} shapes")
    items = [
        {"type": "rect", "x": f"{i % 20}cm", "y": f"{i // 20}cm", "width": "2cm", "height": "1cm", "name": f"shape{i}"}
        for i in range(n)
    ]
    spec = write_spec(tmp / "odg.json", {"pages": [{"name": "Page", "items": items}]})
    odg = tmp / "drawing.odg"
    timed(rows, "ODG", "create_minimal", f"{n} shapes", lambda: run(scripts / "create_minimal_odg.py", spec, odg))
    timed(rows, "ODG", "validate_refs", f"{n} shapes", lambda: run(scripts / "validate_refs.py", odg))


def render_table(rows: list[tuple[str, str, str, float]]) -> str:
    lines = [
        "| Format | Operation | Size | Time |",
        "|--------|-----------|------|------|",
    ]
    for fmt, op, detail, elapsed in rows:
        lines.append(f"| {fmt} | `{op}` | {detail} | {elapsed * 1000:.0f} ms |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="tiny sizes — fast smoke run")
    parser.add_argument("--save", action="store_true", help="write benchmarks/results.md")
    args = parser.parse_args()

    rows: list[tuple[str, str, str, float]] = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        bench_odt(rows, tmp, args.quick)
        bench_ods(rows, tmp, args.quick)
        bench_odp(rows, tmp, args.quick)
        bench_odg(rows, tmp, args.quick)

    print("\n" + render_table(rows))

    if args.save:
        results = Path(__file__).resolve().parent / "results.md"
        mode = "quick" if args.quick else "full"
        results.write_text(
            f"# Benchmark results ({mode} sizes)\n\n"
            f"Generated by `benchmarks/run_benchmarks.py`. Indicative, machine-dependent.\n\n"
            + render_table(rows)
            + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {results}")


if __name__ == "__main__":
    main()
