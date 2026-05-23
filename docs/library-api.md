# open-document-lib

A standard-library toolkit for reading, editing, and writing **OpenDocument
Format** files — text documents (`.odt`), presentations (`.odp`),
spreadsheets (`.ods`), and drawings (`.odg`) — plus their flat (single-XML)
variants.

`open-document-lib` is the shared library behind the
[open-document-skills](https://github.com/leiverkus/open-document-skills)
agent skills. The core has **no dependencies** beyond the Python standard
library; a few helpers opt into `lxml` or `bibtexparser` when present.

## Install

```bash
pip install open-document-lib

# optional extras
pip install open-document-lib[validate]    # lxml — RelaxNG schema validation
pip install open-document-lib[scholarly]   # bibtexparser — BibTeX citation ingest
```

Requires Python 3.10+. The package ships `py.typed`, so type checkers see
its annotations.

## Quick start

```python
from pathlib import Path
from xml.etree import ElementTree as ET
from odf_lib import (
    parse_xml_from_zip, xml_bytes, write_odf_with_replacements,
    replace_text_in_element, update_meta_for_edit,
)

src = Path("report.odt")
content = parse_xml_from_zip(src, "content.xml")

# Structure-preserving find/replace across the document body.
text_ns = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
for para in content.iter(f"{{{text_ns}}}p"):
    replace_text_in_element(para, "{{CLIENT}}", "ACME GmbH")

# Stamp the edit into meta.xml (modification date, generator, cycle count).
meta = parse_xml_from_zip(src, "meta.xml")
# update_meta_for_edit needs a namespace map + qualified-name helper;
# the skills' *_common.py wrappers supply these.

write_odf_with_replacements(
    src, Path("report-out.odt"),
    {"content.xml": xml_bytes(content)},
    "application/vnd.oasis.opendocument.text",
)
```

Flat-ODF round-trip:

```python
from odf_lib import pack_flat_odf, unpack_flat_odf

pack_flat_odf(Path("deck.odp"), Path("deck.fodp"))    # ZIP  → single XML
unpack_flat_odf(Path("deck.fodp"), Path("deck.odp"))  # XML  → ZIP package
```

## API reference

Everything below is exported directly from the `odf_lib` package and is
covered by semantic versioning from 1.0 onward. Anything in
`odf_lib.odf_common` that is **not** listed here (notably `_`-prefixed
helpers) is internal and may change without notice.

### Constants

| Name | Description |
|---|---|
| `VERSION` | Library version string (also `odf_lib.__version__`). |
| `ODF_NAMESPACES` | `dict[str, str]` of ODF namespace prefixes → URIs. |
| `FLAT_EXTENSIONS` | Mapping of ODF mimetype → flat-file extension (`.fodt`, …). |

### ZIP / XML core

| Signature | Description |
|---|---|
| `parse_xml_from_zip(path, member) -> ET.Element` | Parse one XML member of an ODF ZIP. |
| `xml_bytes(root) -> bytes` | Serialize an element to UTF-8 bytes with XML declaration. |
| `write_odf_with_replacements(input_path, output_path, replacements, mimetype_value) -> None` | Copy an ODF package, swapping named members; `mimetype` stays first and stored. |
| `pack_dir_as_odf(source_dir, output_path, mimetype_value) -> None` | Repack an extracted directory into a valid ODF file. |
| `copy_into_package(input_path, output_path, package_path, source, replacements, mimetype_value) -> None` | Add a single file to a package plus member replacements. |
| `copy_with_multiple_members(input_path, output_path, new_members, replacements, mimetype_value) -> None` | Add several new members in one pass (e.g. `Object N/` sub-packages). |
| `unpack_to_temp(path) -> tempfile.TemporaryDirectory` | Extract a package to a managed temp directory. |

### Manifest and media

| Signature | Description |
|---|---|
| `ensure_manifest_entry(manifest_root, full_path, media_type, ns, q_fn) -> None` | Add or update a `manifest:file-entry`. |
| `media_type_for(path) -> str` | MIME type from a file extension. |
| `sniff_image_mime(path) -> str` | MIME type from magic bytes, with extension fallback. |
| `unique_picture_name(existing, image) -> str` | Collision-free `Pictures/` filename. |
| `unique_object_name(existing) -> str` | Next free `Object N` sub-package name. |

### Metadata

| Signature | Description |
|---|---|
| `update_meta_for_edit(meta_root, ns, q_fn) -> None` | Refresh `meta:modification-date`/`generator` and bump `editing-cycles`. |

### Flat ODF

| Signature | Description |
|---|---|
| `pack_flat_odf(input_zip, output_flat) -> None` | Convert a zipped ODF to flat single-XML form (pictures and `Object N/` sub-packages inlined). |
| `unpack_flat_odf(input_flat, output_zip) -> None` | Convert a flat ODF back to a zipped package and rebuild the manifest. |

### Text walker, locator, insertion

| Signature | Description |
|---|---|
| `replace_text_in_element(element, old, new) -> int` | Structure-preserving find/replace across text and child tails. |
| `replace_pattern_with_element_in_element(element, pattern, factory) -> int` | Replace regex matches with generated elements. |
| `find_text_position_in_element(element, needle) -> tuple \| None` | Locate `needle`, returning `(node, "text"\|"tail", offset)`. |
| `insert_after_text_in_element(element, anchor, new_element) -> bool` | Splice an element in right after an anchor string. |
| `insert_in_paragraph(paragraph, position, new_element) -> None` | Insert at the `start` or `end` of a paragraph. |
| `wrap_text_with_pair_in_element(element, start_anchor, end_anchor, start_element, end_element) -> bool` | Wrap an intra-paragraph text range with a start/end pair. |
| `wrap_text_across_elements(elements, start_anchor, end_anchor, start_element, end_element) -> bool` | Same, spanning multiple paragraphs. |
| `ensure_sequence_declarations(text_root, names, ns) -> None` | Ensure `text:sequence-decl` entries exist. |
| `build_index_body_placeholder(title, container_name, section_style="Sect1", title_paragraph_style="Contents_20_Heading") -> ET.Element` | Build an empty `text:index-body` placeholder used by the ODT index inserters; LibreOffice fills it on refresh. |
| `clear_children(element) -> None` | Remove all children of an element. |
| `local_name(tag) -> str` | Local name from a Clark-notation tag. |

### Styles and pictures

| Signature | Description |
|---|---|
| `inject_styles_from_file(input_path, styles_path, output_path, mimetype_value) -> list[str]` | Replace `styles.xml`; returns dangling style references. |
| `embed_pictures(input_path, pictures, output_path, mimetype_value, ns, q_fn) -> None` | Bulk-add images to `Pictures/` and the manifest. |

### Schema validation

| Signature | Description |
|---|---|
| `ensure_schema(name) -> Path` | Download and cache an OASIS ODF 1.3 RelaxNG schema (`content`/`manifest`). |
| `validate_against_schema(xml_bytes_input, schema_name) -> tuple[bool, list[str]]` | Validate XML bytes against a cached schema (requires `lxml`). |

### External tooling

| Signature | Description |
|---|---|
| `find_soffice() -> str` | Locate the LibreOffice `soffice` binary; raises if absent. |
| `find_pandoc() -> str \| None` | Locate the `pandoc` binary. |
| `latex_to_mathml(latex) -> bytes` | Convert a LaTeX snippet to MathML via Pandoc. |

### Rendering / Conversion

| Signature | Description |
|---|---|
| `convert_with_soffice(input_path, target_format, outdir, filter_name=None) -> Path` | Convert via headless LibreOffice with an isolated temp profile. Used for OOXML conversion (`docx`/`xlsx`/`pptx` and the legacy `doc`/`xls`/`ppt`), PDF rendering, and same-format re-saves. |
| `render_to_pdf(odf_path, outdir) -> Path` | Render an ODF file to PDF via LibreOffice (thin wrapper around `convert_with_soffice`). |
| `pdf_to_pngs(pdf_path, outdir, dpi=150) -> list[Path]` | Render each PDF page to a PNG via `pdftoppm` (Poppler). |
| `build_contact_sheet(images, output_path, columns=0) -> Path` | Compose page thumbnails into one labelled grid image. Requires Pillow (`pip install open-document-lib[render]`). |

### Themes

| Signature | Description |
|---|---|
| `THEMES: dict[str, Theme]` | The five curated themes (`corporate-blue`, `warm-editorial`, `high-contrast`, `slate-mono`, `forest`). |
| `Theme` | Dataclass: `background`, `accent`, `text`, `muted`, `shape_fill`, `heading_font`, `body_font`. |
| `get_theme(name) -> Theme` | Look up a theme by name; exits with the valid-name list on a miss. |
| `theme_font_faces(theme) -> list[tuple[str, str, str]]` | The `(face_name, font_family, family_generic)` triples for a theme's `style:font-face` declarations. |

## License

MIT. See [LICENSE](https://github.com/leiverkus/open-document-skills/blob/main/LICENSE).
