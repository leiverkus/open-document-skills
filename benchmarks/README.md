# Benchmarks

`run_benchmarks.py` measures the end-to-end latency of the core helpers by
invoking the actual CLI scripts on large generated documents — the same
path a user takes.

```bash
python3 benchmarks/run_benchmarks.py            # full sizes
python3 benchmarks/run_benchmarks.py --quick    # tiny sizes (fast smoke run)
python3 benchmarks/run_benchmarks.py --save     # also write results.md
```

## What it measures

| Format | Document | Operations timed |
|--------|----------|------------------|
| ODT | 2000 paragraphs | create, replace_text, validate_refs, pack/unpack flat ODF |
| ODS | 100 000 cells (1000×100) | create, replace_cells, validate_refs |
| ODP | 100 slides | create, clone_slide, validate_refs |
| ODG | 500 shapes | create, validate_refs |

Each timing includes Python interpreter startup, since that is part of the
real per-invocation cost. At small sizes that startup (~40 ms) dominates;
at large sizes the actual work dominates.

## Reading the numbers

The figures are **indicative and machine-dependent**. Use them to compare
relative cost and to watch scaling behaviour across releases — not as an
absolute guarantee. They are deliberately **not** run in CI: shared CI
runners vary too much for hard latency thresholds to be meaningful.

`tests/test_benchmarks.py` runs `--quick` on every CI build so the script
itself cannot rot, but it asserts only that the run succeeds.

A representative full run is published in the project
[README](../README.md#performance).
