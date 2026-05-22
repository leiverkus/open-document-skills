# Markdown → ODT Example

`create_from_markdown.py` turns a Markdown file into a styled ODT document —
the high-level authoring path for the ODT skill. An agent writes ordinary
Markdown; the script parses it (standard library only, no Pandoc) and emits
rich-text ODT with `text:span` runs, links, lists, tables, and footnotes.

## Run it

```bash
python3 skills/odt/scripts/create_from_markdown.py \
    examples/article/sample.md article.odt
```

Add `--title "..."` to override the document title (the default is the
first `# H1`). Render to PDF for a visual check:

```bash
python3 skills/odt/scripts/render.py article.odt --outdir qa
```

## What `sample.md` demonstrates

- Headings (`#`–`######`) → `text:h` with outline levels
- Inline **bold**, *italic*, ***both***, `code`, and links
- Bullet and ordered lists, including nesting
- Blockquotes and fenced code blocks
- GFM tables with column alignment
- Markdown footnotes (`[^id]` + `[^id]:`) → `text:note`
- Thematic breaks (`---`)

Images (`![alt](path.png)`) are also supported — local files are embedded
into the package, remote URLs are linked.

## Supported Markdown

A pragmatic CommonMark subset plus GFM tables and footnotes. Not supported:
indented (4-space) code blocks, setext headings, raw HTML, autolinks
(`<url>`), and task-list checkboxes — use fenced code blocks and ATX
headings instead.

## Branding

`create_from_markdown.py` uses fixed style names (`Heading1`–`Heading6`,
`Body`, `Quote`, `CodeBlock`, `Strong`, `Emphasis`, `Code`, …). A curated
`styles.xml` that redefines those same names can be injected with
`inject_styles_from_file` to re-theme the whole document.
