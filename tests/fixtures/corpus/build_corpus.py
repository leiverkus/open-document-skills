#!/usr/bin/env python3
"""Build the real-world test corpus by round-tripping through LibreOffice.

Each fixture is: (1) generated with create_minimal_*, (2) enriched with the
relevant add_* skills, (3) round-tripped through ``soffice --convert-to`` so it
gains LibreOffice-native structure (extra automatic-styles, full settings.xml,
loext: extensions, different element ordering). Round-tripped files expose bugs
where helpers implicitly assume our own generator's output shape.

The committed corpus is the round-tripped result. This script is a maintainer
tool — it requires LibreOffice and is NOT run in CI.

Usage:
    python3 tests/fixtures/corpus/build_corpus.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"
CORPUS = ROOT / "tests" / "fixtures" / "corpus"

sys.path.insert(0, str(ROOT))
from lib.odf_common import find_soffice  # noqa: E402


def run(script: Path, *args: object) -> None:
    subprocess.run(
        [sys.executable, "-B", str(script), *map(str, args)],
        check=True,
        capture_output=True,
        text=True,
    )


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def soffice_roundtrip(soffice: str, src: Path, fmt: str, outdir: Path) -> Path:
    """Convert src through LibreOffice to gain native structure."""
    subprocess.run(
        [soffice, "--headless", "--convert-to", fmt, "--outdir", str(outdir), str(src)],
        check=True,
        capture_output=True,
    )
    result = outdir / (src.stem + "." + fmt)
    if not result.exists():
        raise SystemExit(f"soffice did not produce {result}")
    return result


# --- ODT fixtures ---------------------------------------------------------


def build_odt(tmp: Path, soffice: str) -> None:
    odt = SKILLS / "odt" / "scripts"

    # odt-minimal
    spec = write_json(tmp / "odt_min.json", {
        "title": "Minimal Document",
        "blocks": [
            {"type": "heading", "level": 1, "text": "Introduction"},
            {"type": "paragraph", "text": "A simple paragraph with plain text."},
            {"type": "list", "items": ["First", "Second", "Third"]},
        ],
    })
    base = tmp / "odt_min.odt"
    run(odt / "create_minimal_odt.py", spec, base)
    _emit(soffice, base, "odt", "odt-minimal.odt")

    # odt-footnotes
    spec = write_json(tmp / "odt_fn.json", {
        "title": "Document with Footnotes",
        "blocks": [{"type": "paragraph", "text": "Claims need evidence and support."}],
    })
    base = tmp / "odt_fn.odt"
    run(odt / "create_minimal_odt.py", spec, base)
    noted = tmp / "odt_fn_noted.odt"
    run(odt / "add_footnote.py", base, "--anchor", "evidence",
        "--body", "See Mueller 2020.", "-o", noted)
    _emit(soffice, noted, "odt", "odt-footnotes.odt")

    # odt-citations
    spec = write_json(tmp / "odt_cit.json", {
        "title": "Document with Citations",
        "blocks": [{"type": "paragraph",
                    "text": "Earlier studies [@Mueller2020] established the baseline."}],
    })
    base = tmp / "odt_cit.odt"
    run(odt / "create_minimal_odt.py", spec, base)
    cited = tmp / "odt_cit_filled.odt"
    run(odt / "fill_citations.py", base, "--source",
        ROOT / "tests" / "fixtures" / "refs.csl.json", "-o", cited)
    _emit(soffice, cited, "odt", "odt-citations.odt")

    # odt-crossrefs
    spec = write_json(tmp / "odt_xr.json", {
        "title": "Document with Cross-References",
        "blocks": [
            {"type": "heading", "level": 1, "text": "Methods"},
            {"type": "paragraph", "text": "As discussed in the methods section earlier."},
        ],
    })
    base = tmp / "odt_xr.odt"
    run(odt / "create_minimal_odt.py", spec, base)
    bm = tmp / "odt_xr_bm.odt"
    run(odt / "add_bookmark.py", base, "--name", "MethodsSec",
        "--anchor", "Methods", "-o", bm)
    ref = tmp / "odt_xr_ref.odt"
    run(odt / "add_reference.py", bm, "--ref-to", "MethodsSec", "--kind", "bookmark",
        "--anchor", "methods section", "--display", "chapter", "-o", ref)
    _emit(soffice, ref, "odt", "odt-crossrefs.odt")

    # odt-math
    spec = write_json(tmp / "odt_math.json", {
        "title": "Document with Math",
        "blocks": [{"type": "paragraph", "text": "The decay equation governs dating."}],
    })
    base = tmp / "odt_math.odt"
    run(odt / "create_minimal_odt.py", spec, base)
    mathed = tmp / "odt_math_eq.odt"
    run(odt / "add_math.py", base, "--mathml",
        ROOT / "tests" / "fixtures" / "sample_formula.mml",
        "--anchor", "decay equation", "-o", mathed)
    _emit(soffice, mathed, "odt", "odt-math.odt")


# --- ODS fixtures ---------------------------------------------------------


def build_ods(tmp: Path, soffice: str) -> None:
    ods = SKILLS / "ods" / "scripts"

    spec = write_json(tmp / "ods_min.json", {
        "sheets": [{"name": "Data", "rows": [["Name", "Value"], ["Alpha", "10"], ["Beta", "20"]]}]
    })
    base = tmp / "ods_min.ods"
    run(ods / "create_minimal_ods.py", spec, base)
    _emit(soffice, base, "ods", "ods-minimal.ods")

    spec = write_json(tmp / "ods_f.json", {
        "sheets": [{"name": "Calc", "rows": [["A", "B"], ["3", "4"]]}]
    })
    base = tmp / "ods_f.ods"
    run(ods / "create_minimal_ods.py", spec, base)
    cells = tmp / "ods_f_cells.ods"
    run(ods / "replace_cells.py", base, "Calc!C2=formula:of:=[.A2]+[.B2]", "-o", cells)
    _emit(soffice, cells, "ods", "ods-formulas.ods")

    spec = write_json(tmp / "ods_nr.json", {
        "sheets": [{"name": "Sales", "rows": [["Month", "Revenue"],
                                              ["Jan", "1000"], ["Feb", "1500"]]}]
    })
    base = tmp / "ods_nr.ods"
    run(ods / "create_minimal_ods.py", spec, base)
    nr = tmp / "ods_nr_named.ods"
    run(ods / "add_named_range.py", base, "--name", "Revenue",
        "--range", "Sales.B2:B3", "-o", nr)
    _emit(soffice, nr, "ods", "ods-named-ranges.ods")

    spec = write_json(tmp / "ods_ch.json", {
        "sheets": [{"name": "Chart", "rows": [["Q", "Sales"],
                                              ["Q1", "100"], ["Q2", "150"], ["Q3", "120"]]}]
    })
    base = tmp / "ods_ch.ods"
    run(ods / "create_minimal_ods.py", spec, base)
    charted = tmp / "ods_ch_bar.ods"
    run(ods / "add_chart.py", base, "--type", "bar", "--data", "Chart.A1:B4",
        "--cell", "Chart.D1", "--title", "Quarterly Sales", "-o", charted)
    _emit(soffice, charted, "ods", "ods-chart.ods")


# --- ODP fixtures ---------------------------------------------------------


def build_odp(tmp: Path, soffice: str) -> None:
    odp = SKILLS / "odp" / "scripts"

    spec = write_json(tmp / "odp_min.json", {
        "slides": [{"name": "Intro", "title": "Hello"}, {"name": "Body", "title": "Content"}]
    })
    base = tmp / "odp_min.odp"
    run(odp / "create_minimal_odp.py", spec, base)
    _emit(soffice, base, "odp", "odp-minimal.odp")

    spec = write_json(tmp / "odp_an.json", {
        "slides": [{"name": "Animated", "title": "Title"}]
    })
    base = tmp / "odp_an.odp"
    run(odp / "create_minimal_odp.py", spec, base)
    animated = tmp / "odp_an_fx.odp"
    run(odp / "add_animation.py", base, "--slide", "1", "--shape", "Animated",
        "--effect", "entrance:fade-in", "-o", animated)
    _emit(soffice, animated, "odp", "odp-animation.odp")

    spec = write_json(tmp / "odp_tr.json", {
        "slides": [{"name": "A", "title": "First"}, {"name": "B", "title": "Second"}]
    })
    base = tmp / "odp_tr.odp"
    run(odp / "create_minimal_odp.py", spec, base)
    trans = tmp / "odp_tr_wipe.odp"
    run(odp / "add_transition.py", base, "--slide", "all", "--type", "wipe", "-o", trans)
    _emit(soffice, trans, "odp", "odp-transition.odp")

    spec = write_json(tmp / "odp_ma.json", {
        "slides": [{"name": "Slide", "title": "Branded"}]
    })
    base = tmp / "odp_ma.odp"
    run(odp / "create_minimal_odp.py", spec, base)
    master = tmp / "odp_ma_bg.odp"
    run(odp / "customize_master.py", base, "--master", "Default",
        "--background-color", "#02416C", "-o", master)
    _emit(soffice, master, "odp", "odp-master.odp")


# --- ODG fixtures ---------------------------------------------------------


def build_odg(tmp: Path, soffice: str) -> None:
    odg = SKILLS / "odg" / "scripts"

    def three_rects(name: str) -> Path:
        spec = write_json(tmp / f"{name}.json", {
            "pages": [{"name": "Flow", "items": [
                {"type": "rect", "x": "1cm", "y": "1cm", "width": "3cm", "height": "1.5cm", "name": "A"},
                {"type": "rect", "x": "6cm", "y": "1cm", "width": "3cm", "height": "1.5cm", "name": "B"},
                {"type": "rect", "x": "11cm", "y": "1cm", "width": "3cm", "height": "1.5cm", "name": "C"},
            ]}]
        })
        out = tmp / f"{name}.odg"
        run(odg / "create_minimal_odg.py", spec, out)
        return out

    base = three_rects("odg_min")
    _emit(soffice, base, "odg", "odg-minimal.odg")

    base = three_rects("odg_conn")
    c1 = tmp / "odg_conn_1.odg"
    run(odg / "connect_shapes.py", base, "--from", "A", "--to", "B", "-o", c1)
    c2 = tmp / "odg_conn_2.odg"
    run(odg / "connect_shapes.py", c1, "--from", "B", "--to", "C", "-o", c2)
    _emit(soffice, c2, "odg", "odg-connectors.odg")

    base = three_rects("odg_grp")
    grouped = tmp / "odg_grp_g.odg"
    run(odg / "group_shapes.py", base, "--shapes", "A,B,C", "--name", "Block", "-o", grouped)
    _emit(soffice, grouped, "odg", "odg-groups.odg")

    base = three_rects("odg_gp")
    gp = tmp / "odg_gp_pts.odg"
    run(odg / "add_gluepoint.py", base, "--shape", "A", "--position", "0.5,0",
        "--escape", "up", "-o", gp)
    _emit(soffice, gp, "odg", "odg-gluepoints.odg")


_SOFFICE: str = ""
_TMP: Path = Path()


def _emit(soffice: str, src: Path, fmt: str, final_name: str) -> None:
    """Round-trip src through soffice and copy the result into the corpus dir."""
    with tempfile.TemporaryDirectory() as conv_tmp:
        converted = soffice_roundtrip(soffice, src, fmt, Path(conv_tmp))
        shutil.copy(converted, CORPUS / final_name)
    print(f"  {final_name}")


def main() -> None:
    soffice = find_soffice()
    CORPUS.mkdir(parents=True, exist_ok=True)
    print(f"Building corpus into {CORPUS} (soffice: {soffice})")
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        print("ODT fixtures:")
        build_odt(tmp, soffice)
        print("ODS fixtures:")
        build_ods(tmp, soffice)
        print("ODP fixtures:")
        build_odp(tmp, soffice)
        print("ODG fixtures:")
        build_odg(tmp, soffice)
    count = len(list(CORPUS.glob("*.od[tpsg]")))
    print(f"Done — {count} fixtures.")


if __name__ == "__main__":
    main()
