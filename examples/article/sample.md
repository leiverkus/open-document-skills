# Renewable Energy: A Short Briefing

This article is a sample for the **Markdown → ODT** authoring path. Every
construct below is parsed by a standard-library Markdown parser and emitted
as a styled OpenDocument text document — no `LibreOffice` required for the
conversion itself.

## Why Markdown

Authoring in Markdown means an agent can write *naturally* — with **bold**,
*italic*, `inline code`, and [links](https://www.oasis-open.org/) — instead
of hand-assembling a block-level JSON structure. The structure is the prose.

## Key Points

Unordered lists, including nested items:

- Solar and wind now lead new capacity additions
- Storage is the remaining bottleneck
  - Grid-scale batteries
  - Pumped hydro
- Policy still drives the pace

Ordered lists work too:

1. Measure the baseline
2. Model the trend
3. Report the projection

## A Note on Method

> Capacity figures are normalised to a common baseline so regions of
> differing size can be compared directly.

The model itself is a short script:

```python
def projected_capacity(p0, rate, years):
    return p0 * (1 + rate) ** years
```

## Results

| Region   | 2020 | 2025 | Growth |
|:---------|-----:|-----:|:------:|
| Europe   |  420 |  610 |  high  |
| Americas |  380 |  500 | medium |
| Asia     |  510 |  890 |  high  |

Adoption broadly follows an exponential curve.[^model]

---

Generated from `sample.md` — see this directory's README for the command.

[^model]: The exponential model is a deliberate simplification; real
adoption is shaped by policy, supply chains, and grid capacity.
