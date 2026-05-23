"""Shared helpers for OpenDocument Format scripts.

All four ODF skills (ODT, ODP, ODS, ODG) use these functions.
Format-specific *_common.py modules import from here and add their
own NS dict, MIMETYPE constant, and format-specific helpers.
"""

from __future__ import annotations

import base64
import mimetypes
import posixpath
import re
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Mapping, Set
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

VERSION = "1.13.0"  # keep in sync with pyproject.toml (see CONTRIBUTING.md)

ODF_NAMESPACES: dict[str, str] = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "smil": "urn:oasis:names:tc:opendocument:xmlns:smil-compatible:1.0",
    "anim": "urn:oasis:names:tc:opendocument:xmlns:animation:1.0",
    "chart": "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
    "form": "urn:oasis:names:tc:opendocument:xmlns:form:1.0",
    "script": "urn:oasis:names:tc:opendocument:xmlns:script:1.0",
    "math": "http://www.w3.org/1998/Math/MathML",
    "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    "of": "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
}

FLAT_EXTENSIONS: dict[str, str] = {
    "application/vnd.oasis.opendocument.text": ".fodt",
    "application/vnd.oasis.opendocument.presentation": ".fodp",
    "application/vnd.oasis.opendocument.spreadsheet": ".fods",
    "application/vnd.oasis.opendocument.graphics": ".fodg",
}


def parse_xml_from_zip(path: Path, member: str) -> ET.Element:
    """Parse an XML member from a ZIP-based ODF file.

    Args:
        path: Path to the ODF ZIP file.
        member: Internal ZIP member name (e.g. ``"content.xml"``).

    Returns:
        The root XML element of the parsed member.
    """
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as handle:
            return ET.parse(handle).getroot()


def xml_bytes(root: ET.Element) -> bytes:
    """Serialize an XML element to UTF-8 bytes with XML declaration.

    Args:
        root: The XML element to serialize.

    Returns:
        UTF-8 encoded bytes including the ``<?xml ...?>`` declaration.
    """
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_odf_with_replacements(
    input_path: Path,
    output_path: Path,
    replacements: Mapping[str, bytes],
    mimetype_value: str,
) -> None:
    """Copy an ODF ZIP, replacing specified members with new content.

    The mimetype entry is always written first and uncompressed.

    Args:
        input_path: Source ODF file.
        output_path: Destination ODF file (overwritten).
        replacements: Mapping of member names to replacement bytes.
        mimetype_value: The mimetype string to write if not in *replacements*.
    """
    with zipfile.ZipFile(input_path) as src:
        names: list[str] = src.namelist()
        with zipfile.ZipFile(output_path, "w") as dst:
            if "mimetype" in names:
                dst.writestr(
                    "mimetype",
                    replacements.get("mimetype", mimetype_value.encode()),
                    compress_type=zipfile.ZIP_STORED,
                )
            for name in names:
                if name == "mimetype":
                    continue
                dst.writestr(
                    name,
                    replacements.get(name, src.read(name)),
                    compress_type=zipfile.ZIP_DEFLATED,
                )


def pack_dir_as_odf(source_dir: Path, output_path: Path, mimetype_value: str) -> None:
    """Repack an extracted ODF directory into a valid ODF file.

    The mimetype file must exist in *source_dir* and is written first
    and uncompressed, as required by the ODF specification.

    Args:
        source_dir: Directory containing extracted ODF contents.
        output_path: Destination ODF file (overwritten).
        mimetype_value: The mimetype string (written to ``mimetype`` member).
    """
    mimetype: Path = source_dir / "mimetype"
    if not mimetype.exists():
        raise SystemExit(f"Missing mimetype file in {source_dir}")
    with zipfile.ZipFile(output_path, "w") as archive:
        archive.write(mimetype, "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir() or path == mimetype:
                continue
            archive.write(
                path,
                path.relative_to(source_dir).as_posix(),
                compress_type=zipfile.ZIP_DEFLATED,
            )


def ensure_manifest_entry(
    manifest_root: ET.Element,
    full_path: str,
    media_type: str,
    ns: Mapping[str, str],
    q_fn: Callable[[str, str], str],
) -> None:
    """Add or update a manifest file-entry.

    If an entry for *full_path* already exists, its media-type is updated.
    Otherwise a new file-entry is appended.

    Args:
        manifest_root: The ``<manifest:manifest>`` element.
        full_path: The ``manifest:full-path`` attribute value.
        media_type: The ``manifest:media-type`` attribute value.
        ns: Namespace prefix-to-URI mapping.
        q_fn: Qualified-name builder (e.g. ``q("manifest", "full-path")``).
    """
    manifest_ns: str = ns.get("manifest", "")
    entry_tag: str = f"{{{manifest_ns}}}file-entry"
    for entry in manifest_root.findall(f".//{entry_tag}"):
        if entry.attrib.get(q_fn("manifest", "full-path")) == full_path:
            entry.set(q_fn("manifest", "media-type"), media_type)
            return
    ET.SubElement(
        manifest_root,
        entry_tag,
        {
            q_fn("manifest", "full-path"): full_path,
            q_fn("manifest", "media-type"): media_type,
        },
    )


def inject_styles_from_file(
    input_path: Path,
    styles_path: Path,
    output_path: Path,
    mimetype_value: str,
) -> list[str]:
    """Replace the ``styles.xml`` member of an ODF file with the contents of *styles_path*.

    Returns a list of style-name references in content.xml that do NOT appear
    in the new styles.xml — these are dangling and indicate the injection
    swapped out styles that were still referenced by the content.

    Args:
        input_path: Source ODF file.
        styles_path: Local styles.xml replacement to inject.
        output_path: Destination ODF file (overwritten).
        mimetype_value: The mimetype string to preserve.

    Returns:
        List of style names referenced in content but missing in the new styles.
    """
    new_styles_bytes: bytes = styles_path.read_bytes()
    # Validate cross-references: collect style names defined in new styles
    new_styles_root: ET.Element = ET.fromstring(new_styles_bytes)
    style_ns: str = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    text_ns: str = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    defined_names: set[str] = set()
    for style_el in new_styles_root.iter(f"{{{style_ns}}}style"):
        name = style_el.attrib.get(f"{{{style_ns}}}name")
        if name:
            defined_names.add(name)
    # Also include parent-style-name targets (so we resolve a chain)
    parent_names: set[str] = set()
    for style_el in new_styles_root.iter(f"{{{style_ns}}}style"):
        parent = style_el.attrib.get(f"{{{style_ns}}}parent-style-name")
        if parent:
            parent_names.add(parent)
    # Style names used by content.xml's text:style-name attributes
    content_root: ET.Element = parse_xml_from_zip(input_path, "content.xml")
    used: set[str] = set()
    for node in content_root.iter():
        v = node.attrib.get(f"{{{text_ns}}}style-name")
        if v:
            used.add(v)
    # Styles defined in content.xml's own automatic-styles satisfy a reference
    # too — only swapping styles.xml never touches them.
    content_defined: set[str] = set()
    for style_el in content_root.iter(f"{{{style_ns}}}style"):
        name = style_el.attrib.get(f"{{{style_ns}}}name")
        if name:
            content_defined.add(name)
    missing: list[str] = sorted(used - defined_names - parent_names - content_defined)

    write_odf_with_replacements(
        input_path,
        output_path,
        {"styles.xml": new_styles_bytes},
        mimetype_value,
    )
    return missing


def embed_pictures(
    input_path: Path,
    pictures: Mapping[str, Path],
    output_path: Path,
    mimetype_value: str,
    ns: Mapping[str, str],
    q_fn: Callable[[str, str], str],
) -> None:
    """Embed multiple local pictures into the ODF at given package paths.

    Each picture is added as a new ZIP member and registered in
    ``META-INF/manifest.xml``. The content.xml is **not** modified — callers
    typically reference the pictures from their own draw:frame markup.

    Args:
        input_path: Source ODF file.
        pictures: Mapping of package paths (e.g. ``"Pictures/logo.png"``) to local file paths.
        output_path: Destination ODF file.
        mimetype_value: The mimetype string to preserve.
        ns: Namespace map (must contain ``manifest``).
        q_fn: Qualified-name builder.
    """
    manifest: ET.Element = parse_xml_from_zip(input_path, "META-INF/manifest.xml")
    new_members: dict[str, bytes] = {}
    for package_path, source in pictures.items():
        new_members[package_path] = source.read_bytes()
        ensure_manifest_entry(manifest, package_path, sniff_image_mime(source), ns, q_fn)

    copy_with_multiple_members(
        input_path,
        output_path,
        new_members,
        {"META-INF/manifest.xml": xml_bytes(manifest)},
        mimetype_value,
    )


def update_meta_for_edit(
    meta_root: ET.Element,
    ns: Mapping[str, str],
    q_fn: Callable[[str, str], str],
) -> None:
    """Mark an edit in ``meta.xml``: modification-date, generator, editing-cycles.

    Locates or creates the ``<meta:modification-date>``, ``<meta:generator>``,
    and ``<meta:editing-cycles>`` elements under the document's ``<office:meta>``
    node. Modification-date is set to the current UTC ISO timestamp.
    Generator is set to ``open-document-skills/<VERSION>``. Editing-cycles is
    incremented (or initialised to ``1`` if absent or unparseable).

    Args:
        meta_root: The root of ``meta.xml`` (typically ``office:document-meta``).
        ns: Namespace prefix-to-URI mapping; must contain ``office`` and ``meta``.
        q_fn: Qualified-name builder, e.g. ``q("meta", "generator")``.

    Raises:
        SystemExit: If no ``office:meta`` element can be located or created.
    """
    office_ns: str = ns.get("office", "")
    meta_tag: str = f"{{{office_ns}}}meta"
    meta_el: ET.Element | None = meta_root.find(meta_tag)
    if meta_el is None:
        if local_name(meta_root.tag) == "meta":
            meta_el = meta_root
        else:
            raise SystemExit("office:meta element not found in meta.xml")

    def _find_or_create(tag: str) -> ET.Element:
        el: ET.Element | None = meta_el.find(tag)
        if el is None:
            el = ET.SubElement(meta_el, tag)
        return el

    mod_tag: str = q_fn("meta", "modification-date")
    mod_el: ET.Element = _find_or_create(mod_tag)
    mod_el.text = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    gen_tag: str = q_fn("meta", "generator")
    gen_el: ET.Element = _find_or_create(gen_tag)
    gen_el.text = f"open-document-skills/{VERSION}"

    cycles_tag: str = q_fn("meta", "editing-cycles")
    cycles_el: ET.Element = _find_or_create(cycles_tag)
    current: int
    try:
        current = int((cycles_el.text or "0").strip())
    except ValueError:
        current = 0
    cycles_el.text = str(current + 1)


_IMAGE_MIME_BY_MAGIC: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"<?xml", "image/svg+xml"),  # requires <svg> later in header
    (b"<svg", "image/svg+xml"),
    (b"BM", "image/bmp"),
    (b"RIFF", "image/webp"),  # requires bytes 8:12 == b"WEBP"
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
]


def sniff_image_mime(path: Path) -> str:
    """Return the MIME type of an image file by inspecting its magic bytes.

    Reads the first 64 bytes (enough for all checks including the SVG-via-XML
    case and the WebP four-CC validation) and falls back to extension-based
    detection via :func:`media_type_for` when no magic matches.

    Args:
        path: Local file path.

    Returns:
        MIME type string (e.g. ``"image/png"``); falls back to the extension
        guess if the file is unreadable or no magic matches.
    """
    try:
        with open(path, "rb") as handle:
            header: bytes = handle.read(64)
    except OSError:
        return media_type_for(path)
    for magic, mime in _IMAGE_MIME_BY_MAGIC:
        if not header.startswith(magic):
            continue
        if mime == "image/svg+xml" and magic == b"<?xml":
            # Confirm it's actually SVG, not arbitrary XML.
            if b"<svg" not in header:
                continue
        if mime == "image/webp":
            if len(header) < 12 or header[8:12] != b"WEBP":
                continue
        return mime
    return media_type_for(path)


def media_type_for(path: Path) -> str:
    """Guess the MIME type for a file path, falling back to octet-stream.

    Args:
        path: File path (only the extension is used for guessing).

    Returns:
        MIME type string, e.g. ``"image/png"`` or ``"application/octet-stream"``.
    """
    guessed: str | None
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def unique_picture_name(existing: Set[str], image: Path) -> str:
    """Return a unique ``Pictures/…`` path that does not clash with *existing*.

    Args:
        existing: Set of already-used package paths.
        image: Source image file path.

    Returns:
        A ``Pictures/<filename>`` path, with ``-N`` suffix if needed.
    """
    base: str = image.name.replace("\\", "_").replace("/", "_")
    candidate: str = posixpath.join("Pictures", base)
    stem: str = image.stem
    suffix: str = image.suffix
    counter: int = 1
    while candidate in existing:
        candidate = posixpath.join("Pictures", f"{stem}-{counter}{suffix}")
        counter += 1
    return candidate


def copy_into_package(
    input_path: Path,
    output_path: Path,
    package_path: str,
    source: Path,
    replacements: Mapping[str, bytes],
    mimetype_value: str,
) -> None:
    """Copy an ODF ZIP, replacing members and adding *source* at *package_path*.

    Args:
        input_path: Source ODF file.
        output_path: Destination ODF file (overwritten).
        package_path: Internal ZIP path for the new file.
        source: Local file to insert.
        replacements: Mapping of member names to replacement bytes.
        mimetype_value: The mimetype string to write if not in *replacements*.
    """
    with zipfile.ZipFile(input_path) as src:
        names: list[str] = src.namelist()
        with zipfile.ZipFile(output_path, "w") as dst:
            if "mimetype" in names:
                dst.writestr(
                    "mimetype",
                    replacements.get("mimetype", mimetype_value.encode()),
                    compress_type=zipfile.ZIP_STORED,
                )
            for name in names:
                if name == "mimetype" or name == package_path:
                    continue
                dst.writestr(
                    name,
                    replacements.get(name, src.read(name)),
                    compress_type=zipfile.ZIP_DEFLATED,
                )
            dst.write(source, package_path, compress_type=zipfile.ZIP_DEFLATED)


def copy_with_multiple_members(
    input_path: Path,
    output_path: Path,
    new_members: Mapping[str, bytes],
    replacements: Mapping[str, bytes],
    mimetype_value: str,
) -> None:
    """Copy an ODF ZIP with both replacements and arbitrary new members.

    Like :func:`copy_into_package` but for adding *several* new internal files
    (e.g. ``Object 1/content.xml`` plus its directory entry) in one pass.

    Args:
        input_path: Source ODF file.
        output_path: Destination ODF file (overwritten).
        new_members: Mapping ``{package_path: bytes}`` of files to add.
        replacements: Mapping of existing member names to replacement bytes.
        mimetype_value: The mimetype string to write if not in *replacements*.
    """
    with zipfile.ZipFile(input_path) as src:
        names: list[str] = src.namelist()
        with zipfile.ZipFile(output_path, "w") as dst:
            if "mimetype" in names:
                dst.writestr(
                    "mimetype",
                    replacements.get("mimetype", mimetype_value.encode()),
                    compress_type=zipfile.ZIP_STORED,
                )
            for name in names:
                if name == "mimetype" or name in new_members:
                    continue
                dst.writestr(
                    name,
                    replacements.get(name, src.read(name)),
                    compress_type=zipfile.ZIP_DEFLATED,
                )
            for path, payload in new_members.items():
                dst.writestr(path, payload, compress_type=zipfile.ZIP_DEFLATED)


def unique_object_name(existing: Set[str]) -> str:
    """Return the first ``Object N`` (N=1,2,3,...) that is not present in *existing*.

    Used for MathML/formula sub-packages. Match is on prefix — an existing
    ``Object 3/content.xml`` causes ``Object 3`` to be considered taken.

    Args:
        existing: Set of already-used package paths.

    Returns:
        The chosen ``Object N`` (no trailing slash).
    """
    counter: int = 1
    while True:
        candidate: str = f"Object {counter}"
        if not any(name == candidate or name.startswith(candidate + "/") for name in existing):
            return candidate
        counter += 1


def find_pandoc() -> str | None:
    """Locate the pandoc executable on PATH. Returns None if not found."""
    return shutil.which("pandoc")


SCHEMA_URLS: dict[str, str] = {
    "content": "https://docs.oasis-open.org/office/OpenDocument/v1.3/os/schemas/OpenDocument-v1.3-schema.rng",
    "manifest": "https://docs.oasis-open.org/office/OpenDocument/v1.3/os/schemas/OpenDocument-v1.3-manifest-schema.rng",
}


def ensure_schema(name: str) -> Path:
    """Locate an OASIS ODF 1.3 RelaxNG schema, downloading it on first use.

    Schemas are cached under ``$XDG_CACHE_HOME/open-document-skills/schemas/``
    (defaulting to ``~/.cache/open-document-skills/schemas/``).

    Args:
        name: Either ``"content"`` or ``"manifest"``.

    Returns:
        Local filesystem path to the cached schema.

    Raises:
        SystemExit: If *name* is unknown or download fails.
    """
    import os
    import urllib.request

    if name not in SCHEMA_URLS:
        raise SystemExit(f"unknown schema {name!r}; choose from {sorted(SCHEMA_URLS)}")
    cache_root: Path = (
        Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "open-document-skills" / "schemas"
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    schema_path: Path = cache_root / f"odf-1.3-{name}.rng"
    if not schema_path.exists():
        url: str = SCHEMA_URLS[name]
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                schema_path.write_bytes(resp.read())
        except Exception as exc:
            raise SystemExit(f"failed to download schema {url}: {exc}")
    return schema_path


def validate_against_schema(
    xml_bytes_input: bytes,
    schema_name: str,
    strip_namespaces: tuple[str, ...] = (),
) -> tuple[bool, list[str]]:
    """Validate *xml_bytes_input* against the named OASIS ODF 1.3 RelaxNG schema.

    Lazily imports ``lxml`` and raises ``SystemExit`` with an install hint
    when the optional dependency is missing.

    Args:
        xml_bytes_input: Raw XML bytes to validate.
        schema_name: Schema key, e.g. ``"content"`` or ``"manifest"``.
        strip_namespaces: Namespace URIs whose elements and attributes are
            removed before validation. Use this for documented vendor
            extensions (e.g. ``calcext``) that ODF permits as foreign content
            but the OASIS core schema does not describe.

    Returns:
        ``(is_valid, errors)`` where errors is a list of human-readable strings.
    """
    try:
        from lxml import etree  # type: ignore
    except ImportError:
        raise SystemExit("Schema validation requires lxml. Install with:\n  pip install open-document-lib[validate]")
    schema_path: Path = ensure_schema(schema_name)
    rng_doc = etree.parse(str(schema_path))
    relaxng = etree.RelaxNG(rng_doc)
    try:
        doc = etree.fromstring(xml_bytes_input)
    except etree.XMLSyntaxError as exc:
        return False, [f"XML syntax error: {exc}"]
    for namespace in strip_namespaces:
        etree.strip_elements(doc, f"{{{namespace}}}*")
        etree.strip_attributes(doc, f"{{{namespace}}}*")
    valid = relaxng.validate(doc)
    errors: list[str] = []
    if not valid:
        for err in relaxng.error_log:
            errors.append(f"line {err.line}: {err.message}")
    return valid, errors


# Documented vendor extensions that ODF permits as foreign content but the
# OASIS core schema does not describe. They are excluded from the --strict
# RelaxNG check (and reported as a warning) rather than counted as errors.
KNOWN_EXTENSION_NAMESPACES: dict[str, str] = {
    "calcext": "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0",
}


def apply_strict_schema_check(
    odf_path: Path,
    result: dict[str, object],
    extension_namespaces: dict[str, str] | None = None,
) -> None:
    """Validate an ODF file's content.xml and manifest.xml against the schemas.

    Runs RelaxNG validation against the OASIS ODF 1.3 schemas — the same
    ``content`` schema covers ODT/ODP/ODS/ODG, so this works for every
    format. Mutates *result* in place: schema errors are appended to
    ``result["errors"]`` (prefixed by member name) and ``result["status"]``
    is set to ``"errors_found"`` when any errors are present.

    Args:
        odf_path: Path to the ODF package to validate.
        result: A validation result dict with ``"errors"`` and ``"status"``
            keys, as returned by a ``validate_refs`` ``validate()`` function.
        extension_namespaces: Optional ``label -> URI`` map of documented
            vendor extensions to exclude from the content.xml schema check.
            Each extension actually present is reported in ``result["warnings"]``
            instead of failing the check. Defaults to
            :data:`KNOWN_EXTENSION_NAMESPACES`.
    """
    if extension_namespaces is None:
        extension_namespaces = KNOWN_EXTENSION_NAMESPACES
    with zipfile.ZipFile(odf_path) as archive:
        content_bytes = archive.read("content.xml")
        try:
            manifest_bytes: bytes | None = archive.read("META-INF/manifest.xml")
        except KeyError:
            manifest_bytes = None
    errors = result["errors"]
    if not isinstance(errors, list):  # defensive — validate() always returns a list
        errors = []
        result["errors"] = errors
    present = {label: uri for label, uri in extension_namespaces.items() if uri.encode("utf-8") in content_bytes}
    ok, errs = validate_against_schema(content_bytes, "content", strip_namespaces=tuple(present.values()))
    if not ok:
        errors.extend(f"content.xml: {err}" for err in errs)
    if manifest_bytes is not None:
        ok_m, errs_m = validate_against_schema(manifest_bytes, "manifest")
        if not ok_m:
            errors.extend(f"manifest.xml: {err}" for err in errs_m)
    if present:
        warnings = result.get("warnings")
        if isinstance(warnings, list):
            for label in sorted(present):
                warnings.append(
                    f"content.xml uses the {label!r} extension — excluded from the OASIS "
                    "core-schema check (renders in LibreOffice, valid as ODF foreign content)"
                )
    if errors:
        result["status"] = "errors_found"


def latex_to_mathml(latex: str) -> bytes:
    """Convert a LaTeX snippet to MathML bytes via pandoc.

    Args:
        latex: LaTeX source (without surrounding ``$`` delimiters).

    Returns:
        UTF-8 encoded MathML XML.

    Raises:
        SystemExit: If pandoc is not on PATH, with install hints.
    """
    import subprocess

    pandoc: str | None = find_pandoc()
    if pandoc is None:
        raise SystemExit(
            "LaTeX → MathML requires pandoc.\n"
            "  macOS:  brew install pandoc\n"
            "  Ubuntu: sudo apt-get install pandoc\n"
            "  Windows: winget install JohnMacFarlane.Pandoc\n"
            "Or supply --mathml or --mathml-inline directly."
        )
    # Wrap in math mode so pandoc emits a <math> element.
    wrapped: str = f"${latex}$"
    result = subprocess.run(
        [pandoc, "-f", "latex", "-t", "html5", "--mathml"],
        input=wrapped.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    # Pandoc's html5+mathml output wraps in <p>...</p>; extract the <math>...</math> element.
    html_out: str = result.stdout.decode("utf-8")
    math_start: int = html_out.find("<math")
    math_end: int = html_out.rfind("</math>")
    if math_start < 0 or math_end < 0:
        raise SystemExit(f"pandoc did not emit a <math> element. Output was:\n{html_out}")
    return html_out[math_start : math_end + len("</math>")].encode("utf-8")


def clear_children(element: ET.Element) -> None:
    """Remove all child elements from *element* in-place.

    Args:
        element: The XML element to clear.
    """
    element[:] = []


def _collect_text_slots(element: ET.Element) -> list[tuple[ET.Element, str]]:
    """Collect (node, attr) text-slot pairs in document order.

    Walker and locator helpers share this structure. For *element*, yields
    ``(element, "text")`` first; then for every descendant in DFS order,
    yields ``(node, "text")`` before recursing and ``(node, "tail")`` after.
    The root's ``.tail`` is intentionally not included (it lives outside the
    element's content).

    Args:
        element: Root of the subtree to collect from.

    Returns:
        Ordered list of ``(node, attr)`` pairs where ``attr`` is ``"text"`` or ``"tail"``.
    """
    slots: list[tuple[ET.Element, str]] = []

    def visit(node: ET.Element, is_root: bool) -> None:
        slots.append((node, "text"))
        for child in list(node):
            visit(child, False)
        if not is_root:
            slots.append((node, "tail"))

    visit(element, True)
    return slots


def _build_parent_map(element: ET.Element) -> dict[ET.Element, ET.Element]:
    """Build a descendant → parent mapping for *element*'s subtree.

    The root *element* is not present as a key (it has no parent within the subtree).

    Args:
        element: Root of the subtree.

    Returns:
        Dict mapping each descendant to its direct parent.
    """
    parent_map: dict[ET.Element, ET.Element] = {}
    for parent in element.iter():
        for child in parent:
            parent_map[child] = parent
    return parent_map


def find_text_position_in_element(element: ET.Element, needle: str) -> tuple[ET.Element, str, int] | None:
    """Find the FIRST occurrence of *needle* in *element*'s text content.

    Walks ``.text`` of *element* and every descendant, plus ``.tail`` of every
    descendant, in document order. Returns the slot (node, attr) and local
    offset where the match BEGINS. A match may span multiple slots — only the
    starting slot is reported.

    Args:
        element: The element to search.
        needle: Substring to look for. Empty string returns None.

    Returns:
        ``(node, attr, local_offset)`` where ``attr`` is ``"text"`` or ``"tail"``,
        or ``None`` if not found.
    """
    if not needle:
        return None
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)
    idx: int = combined.find(needle)
    if idx < 0:
        return None
    running: int = 0
    for (node, attr), value in zip(slots, values):
        if running <= idx < running + len(value):
            return node, attr, idx - running
        running += len(value)
    return None


def insert_after_text_in_element(element: ET.Element, anchor: str, new_element: ET.Element) -> bool:
    """Insert *new_element* immediately after the first occurrence of *anchor*.

    Splits the slot containing the END of the match, then inserts *new_element*
    either as a child (when the match ends in a ``.text`` slot) or as a sibling
    (when it ends in a ``.tail`` slot). The remainder of the slot becomes
    *new_element*'s ``.tail``. Other inline children of *element* are preserved.

    Args:
        element: The container in which to search.
        anchor: Substring that locates the insertion point.
        new_element: The element to insert.

    Returns:
        ``True`` if the anchor was found and the element inserted, else ``False``.
    """
    if not anchor:
        return False
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)
    idx: int = combined.find(anchor)
    if idx < 0:
        return False
    end: int = idx + len(anchor)
    running: int = 0
    target_index: int = -1
    for i, value in enumerate(values):
        if running <= end - 1 < running + len(value):
            target_index = i
            break
        running += len(value)
    if target_index < 0:
        return False
    target_node, target_attr = slots[target_index]
    local_end: int = end - running
    current_value: str = values[target_index]
    prefix: str = current_value[:local_end]
    suffix: str = current_value[local_end:]

    if target_attr == "text":
        target_node.text = prefix if prefix else None
        target_node.insert(0, new_element)
        new_element.tail = suffix if suffix else None
        return True

    target_node.tail = prefix if prefix else None
    parent_map: dict[ET.Element, ET.Element] = _build_parent_map(element)
    parent: ET.Element | None = parent_map.get(target_node)
    if parent is None:
        return False
    sibling_index: int = list(parent).index(target_node)
    parent.insert(sibling_index + 1, new_element)
    new_element.tail = suffix if suffix else None
    return True


def extract_text_range_from_element(element: ET.Element, needle: str, marker: ET.Element) -> str | None:
    """Cut the first occurrence of *needle* out of *element*, leaving *marker*.

    Splits the text slot containing the match into prefix and suffix, removes
    the matched text, and inserts *marker* between them — as a child (text
    slot) or a sibling (tail slot). The matched run must lie within a single
    text slot; if it straddles an inline child (e.g. a ``text:span`` boundary),
    the function returns ``None`` and makes no change. Used to record a tracked
    deletion: the marker is the ``text:change`` placeholder.

    Args:
        element: The paragraph-like container to search.
        needle: The exact text run to remove.
        marker: The element to leave at the cut point.

    Returns:
        The removed text, or ``None`` if *needle* was not found within a
        single text slot.
    """
    if not needle:
        return None
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)
    idx: int = combined.find(needle)
    if idx < 0:
        return None
    end: int = idx + len(needle)
    running: int = 0
    target: int = -1
    local: int = 0
    for i, value in enumerate(values):
        if running <= idx < running + len(value):
            if end <= running + len(value):  # whole run within this one slot
                target = i
                local = idx - running
            break
        running += len(value)
    if target < 0:
        return None  # not found, or the run straddles an inline child
    node, attr = slots[target]
    value = values[target]
    prefix: str = value[:local]
    suffix: str = value[local + len(needle) :]
    if attr == "text":
        node.text = prefix or None
        node.insert(0, marker)
        marker.tail = suffix or None
        return needle
    node.tail = prefix or None
    parent_map: dict[ET.Element, ET.Element] = _build_parent_map(element)
    parent: ET.Element | None = parent_map.get(node)
    if parent is None:
        return None
    pos: int = list(parent).index(node)
    parent.insert(pos + 1, marker)
    marker.tail = suffix or None
    return needle


def replace_pattern_with_element_in_element(
    element: ET.Element,
    pattern: re.Pattern[str],
    factory: Callable[[re.Match[str]], ET.Element],
) -> int:
    """Replace every regex match in *element*'s text content with a built element.

    For each non-overlapping match of *pattern* against the concatenated text
    content (``.text`` of *element* and descendants, plus ``.tail`` of every
    descendant), the match is removed and replaced with the element returned
    by ``factory(match)``. The element is inserted either as a child (when
    the match falls in a ``.text`` slot) or as a sibling (when in a ``.tail``
    slot). The new element's ``.tail`` carries the remainder of the original
    slot.

    Matches that straddle multiple slots are silently skipped — short
    placeholder patterns like ``[@bibkey]`` virtually never straddle inline
    children, and skipping is safer than corrupting structure.

    Args:
        element: Container to scan.
        pattern: Compiled regex.
        factory: Callable returning a new ET.Element per match.

    Returns:
        Number of replacements performed.
    """
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    offsets: list[int] = []
    running: int = 0
    for v in values:
        offsets.append(running)
        running += len(v)
    combined: str = "".join(values)

    matches: list[re.Match[str]] = list(pattern.finditer(combined))
    if not matches:
        return 0

    def slot_for(global_offset: int) -> int:
        lo, hi = 0, len(values) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offsets[mid] <= global_offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    parent_map: dict[ET.Element, ET.Element] = _build_parent_map(element)
    replaced: int = 0

    # Work right-to-left so earlier modifications don't shift later positions
    # within the paragraph structure.
    for match in reversed(matches):
        start, end = match.start(), match.end()
        i_slot = slot_for(start)
        j_slot = slot_for(end - 1) if end > start else i_slot
        if i_slot != j_slot:
            # Straddle — skip silently.
            continue
        target_node, target_attr = slots[i_slot]
        local_start = start - offsets[i_slot]
        local_end = end - offsets[i_slot]
        current = values[i_slot]
        prefix = current[:local_start]
        suffix = current[local_end:]
        new_element = factory(match)

        if target_attr == "text":
            target_node.text = prefix if prefix else None
            target_node.insert(0, new_element)
            new_element.tail = suffix if suffix else None
        else:
            target_node.tail = prefix if prefix else None
            parent = parent_map.get(target_node)
            if parent is None:
                continue
            sibling_index = list(parent).index(target_node)
            parent.insert(sibling_index + 1, new_element)
            new_element.tail = suffix if suffix else None

        # Update tracking so subsequent (earlier) matches see the new state.
        # We pessimistically rebuild slots; simpler than incremental updates.
        slots = _collect_text_slots(element)
        values = [getattr(n, a) or "" for n, a in slots]
        offsets = []
        running = 0
        for v in values:
            offsets.append(running)
            running += len(v)
        parent_map = _build_parent_map(element)
        replaced += 1

    return replaced


def insert_in_paragraph(paragraph: ET.Element, position: str, new_element: ET.Element) -> None:
    """Insert *new_element* at the start or end of *paragraph*.

    ``"end"`` appends; ``"start"`` inserts as first child and pushes any
    existing ``paragraph.text`` to ``new_element.tail``.

    Args:
        paragraph: The container element (typically ``text:p`` or ``text:h``).
        position: Either ``"start"`` or ``"end"``.
        new_element: Element to insert.

    Raises:
        ValueError: If *position* is not ``"start"`` or ``"end"``.
    """
    if position == "end":
        paragraph.append(new_element)
        new_element.tail = None
    elif position == "start":
        old_text: str | None = paragraph.text
        paragraph.text = None
        paragraph.insert(0, new_element)
        new_element.tail = old_text
    else:
        raise ValueError(f"position must be 'start' or 'end', got {position!r}")


def wrap_text_with_pair_in_element(
    element: ET.Element,
    start_anchor: str,
    end_anchor: str,
    start_element: ET.Element,
    end_element: ET.Element,
) -> bool:
    """Bracket a text region with two empty marker elements (e.g. range bookmarks).

    Finds *start_anchor* and *end_anchor* in *element*'s text content; inserts
    *start_element* immediately after the start anchor and *end_element*
    immediately after the end anchor. The end anchor must occur after the
    start anchor in document order. Rolls back on failure: nothing is inserted
    unless both anchors were found and the order is correct.

    Args:
        element: The paragraph (or similar) to search.
        start_anchor: Substring marking the start of the bracketed region.
        end_anchor: Substring marking the end. Must come after *start_anchor*.
        start_element: Element to insert after the start anchor (e.g. ``text:bookmark-start``).
        end_element: Element to insert after the end anchor (e.g. ``text:bookmark-end``).

    Returns:
        ``True`` if both insertions succeeded, ``False`` otherwise (and no
        change is made to *element*).
    """
    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)
    start_idx: int = combined.find(start_anchor)
    if start_idx < 0:
        return False
    end_idx: int = combined.find(end_anchor, start_idx + len(start_anchor))
    if end_idx < 0:
        return False
    # Insert end first so positions of start_anchor remain stable.
    if not insert_after_text_in_element(element, end_anchor, end_element):
        return False
    if not insert_after_text_in_element(element, start_anchor, start_element):
        # Rollback end insertion.
        parent_map: dict[ET.Element, ET.Element] = _build_parent_map(element)
        parent: ET.Element | None = parent_map.get(end_element)
        if parent is not None:
            # Restore the tail before removing.
            siblings: list[ET.Element] = list(parent)
            idx: int = siblings.index(end_element)
            preceding_tail: str | None = end_element.tail
            if idx == 0:
                parent.text = (parent.text or "") + (preceding_tail or "") or None
            else:
                prev: ET.Element = siblings[idx - 1]
                prev.tail = (prev.tail or "") + (preceding_tail or "") or None
            parent.remove(end_element)
        return False
    return True


def wrap_text_across_elements(
    elements: list[ET.Element],
    start_anchor: str,
    end_anchor: str,
    start_element: ET.Element,
    end_element: ET.Element,
) -> bool:
    """Bracket a text region with a start/end marker pair across multiple paragraphs.

    Searches *elements* in document order for *start_anchor*; in the first
    matching element, then searches the remainder (and the same element after
    the start position) for *end_anchor*. Inserts *start_element* immediately
    after the start anchor and *end_element* immediately after the end anchor.

    If start and end fall in the same element, falls back to
    :func:`wrap_text_with_pair_in_element`. Otherwise, inserts the end first
    (in a later element, so positions stay stable) and the start second.
    Rolls back on failure.

    Args:
        elements: Container elements to search (typically all paragraphs).
        start_anchor: Substring marking the range start.
        end_anchor: Substring marking the range end (must come after start).
        start_element: Element inserted after the start anchor.
        end_element: Element inserted after the end anchor.

    Returns:
        ``True`` if both markers were inserted, ``False`` otherwise.
    """
    if not start_anchor or not end_anchor:
        return False

    # Locate start
    start_idx: int = -1
    for i, element in enumerate(elements):
        if find_text_position_in_element(element, start_anchor) is not None:
            start_idx = i
            break
    if start_idx < 0:
        return False

    # Locate end: in the same element after the start, or in any subsequent element.
    end_idx: int = -1
    start_element_combined: str = "".join(getattr(n, a) or "" for n, a in _collect_text_slots(elements[start_idx]))
    s_pos: int = start_element_combined.find(start_anchor)
    e_pos: int = start_element_combined.find(end_anchor, s_pos + len(start_anchor))
    if e_pos >= 0:
        # Both in same element.
        return wrap_text_with_pair_in_element(elements[start_idx], start_anchor, end_anchor, start_element, end_element)

    for j in range(start_idx + 1, len(elements)):
        if find_text_position_in_element(elements[j], end_anchor) is not None:
            end_idx = j
            break
    if end_idx < 0:
        return False

    # Insert end first (later element); positions in start element remain stable.
    if not insert_after_text_in_element(elements[end_idx], end_anchor, end_element):
        return False
    if not insert_after_text_in_element(elements[start_idx], start_anchor, start_element):
        # Rollback end insertion.
        parent_map: dict[ET.Element, ET.Element] = _build_parent_map(elements[end_idx])
        parent: ET.Element | None = parent_map.get(end_element)
        if parent is not None:
            siblings: list[ET.Element] = list(parent)
            idx: int = siblings.index(end_element)
            preceding_tail: str | None = end_element.tail
            if idx == 0:
                parent.text = (parent.text or "") + (preceding_tail or "") or None
            else:
                prev: ET.Element = siblings[idx - 1]
                prev.tail = (prev.tail or "") + (preceding_tail or "") or None
            parent.remove(end_element)
        return False
    return True


def ensure_sequence_declarations(text_root: ET.Element, names: list[str], ns: Mapping[str, str]) -> None:
    """Ensure ``text:sequence-decls`` exists under *text_root* and contains *names*.

    *text_root* is typically the ``office:text`` element. If a
    ``text:sequence-decls`` block is missing, it is prepended as the first
    child. Missing ``text:sequence-decl`` entries for each ``NAME`` in *names*
    are appended.

    Args:
        text_root: The ``office:text`` element (parent of body content).
        names: Sequence names (e.g. ``["Figure", "Table", "Illustration"]``).
        ns: Namespace map (must contain ``text``).
    """
    text_ns: str = ns["text"]
    decls_tag: str = f"{{{text_ns}}}sequence-decls"
    decl_tag: str = f"{{{text_ns}}}sequence-decl"
    name_attr: str = f"{{{text_ns}}}name"
    display_attr: str = f"{{{text_ns}}}display-outline-level"

    decls: ET.Element | None = text_root.find(decls_tag)
    if decls is None:
        decls = ET.Element(decls_tag)
        text_root.insert(0, decls)

    existing: set[str] = {child.attrib.get(name_attr, "") for child in decls.findall(decl_tag)}
    for name in names:
        if name in existing:
            continue
        ET.SubElement(decls, decl_tag, {name_attr: name, display_attr: "0"})


def build_index_body_placeholder(
    title: str,
    container_name: str,
    section_style: str = "Sect1",
    title_paragraph_style: str = "Contents_20_Heading",
) -> ET.Element:
    """Build an empty ``text:index-body`` placeholder for a generated index.

    The body contains only the title paragraph. The actual index entries are
    filled in later by LibreOffice when ``update_indexes.py`` opens the document
    and dispatches the index-refresh action. Until then, opening the file in
    LibreOffice GUI shows the empty index — pressing F9 (or Tools → Update →
    Update All Indexes) fills it.

    Args:
        title: Title text rendered in the placeholder (e.g. ``"Table of Contents"``).
        container_name: ``text:name`` of the enclosing index element
            (e.g. ``"Table of Contents1"``); the title element's ``text:name``
            is set to ``f"{container_name}_Head"`` per the LibreOffice convention.
        section_style: ``text:style-name`` for the ``text:index-title`` element.
        title_paragraph_style: ``text:style-name`` for the title paragraph.

    Returns:
        A ``text:index-body`` element with one ``text:index-title`` child.
    """
    text_ns: str = ODF_NAMESPACES["text"]
    name_attr: str = f"{{{text_ns}}}name"
    style_attr: str = f"{{{text_ns}}}style-name"
    body: ET.Element = ET.Element(f"{{{text_ns}}}index-body")
    title_el: ET.Element = ET.SubElement(body, f"{{{text_ns}}}index-title")
    title_el.set(style_attr, section_style)
    title_el.set(name_attr, f"{container_name}_Head")
    p: ET.Element = ET.SubElement(title_el, f"{{{text_ns}}}p")
    p.set(style_attr, title_paragraph_style)
    p.text = title
    return body


def replace_text_in_element(element: ET.Element, old: str, new: str) -> int:
    """Replace ``old`` with ``new`` in *element*'s text, preserving children.

    Walks all text nodes (``.text`` of *element* and every descendant, plus
    ``.tail`` of every descendant) in document order. Inline children such as
    ``text:span``, ``text:note``, ``text:bookmark``, ``text:a`` keep their
    identity. Matches that straddle child boundaries are still replaced — the
    new content is placed in the first containing slot, intermediate slots are
    cleared, and the trailing slot keeps only the suffix after the match.

    Args:
        element: The element whose textual content should be searched.
        old: Substring to search for. Empty string is a no-op.
        new: Replacement string.

    Returns:
        Number of non-overlapping replacements performed.
    """
    if not old:
        return 0

    slots: list[tuple[ET.Element, str]] = _collect_text_slots(element)
    values: list[str] = [getattr(n, a) or "" for n, a in slots]
    combined: str = "".join(values)

    matches: list[tuple[int, int]] = []
    pos: int = 0
    while True:
        i: int = combined.find(old, pos)
        if i < 0:
            break
        matches.append((i, i + len(old)))
        pos = i + len(old)
    if not matches:
        return 0

    offsets: list[int] = []
    running: int = 0
    for v in values:
        offsets.append(running)
        running += len(v)

    def slot_for(offset: int) -> int:
        lo: int = 0
        hi: int = len(values) - 1
        while lo < hi:
            mid: int = (lo + hi + 1) // 2
            if offsets[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    for match_start, match_end in reversed(matches):
        i_slot: int = slot_for(match_start)
        j_slot: int = slot_for(match_end - 1) if match_end > match_start else i_slot
        local_i: int = match_start - offsets[i_slot]
        local_j: int = match_end - offsets[j_slot]
        if i_slot == j_slot:
            v = values[i_slot]
            values[i_slot] = v[:local_i] + new + v[local_j:]
        else:
            values[i_slot] = values[i_slot][:local_i] + new
            for k in range(i_slot + 1, j_slot):
                values[k] = ""
            values[j_slot] = values[j_slot][local_j:]

    for (node, attr), value in zip(slots, values):
        setattr(node, attr, value if value else None)

    return len(matches)


def find_soffice() -> str:
    """Locate the LibreOffice/soffice executable.

    Checks PATH first, then common installation directories on macOS,
    Linux (including snap), and Windows (including WSL).

    Returns:
        Absolute path to the ``soffice`` or ``libreoffice`` executable.

    Raises:
        SystemExit: If no executable is found.
    """
    candidates: list[str] = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "/usr/local/bin/libreoffice",
        "/snap/bin/libreoffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        "/c/Program Files/LibreOffice/program/soffice.exe",
        "/mnt/c/Program Files/LibreOffice/program/soffice.exe",
    ]
    for name in ("soffice", "libreoffice"):
        found: str | None = shutil.which(name)
        if found:
            return found
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise SystemExit("LibreOffice/soffice not found")


def unpack_to_temp(path: Path) -> tempfile.TemporaryDirectory[str]:
    """Extract an ODF ZIP to a temporary directory.

    The caller is responsible for cleaning up the returned
    TemporaryDirectory (e.g. via a context manager or ``.cleanup()``).

    Args:
        path: Path to the ODF ZIP file.

    Returns:
        A ``tempfile.TemporaryDirectory`` containing the extracted contents.
    """
    temp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(path) as archive:
        archive.extractall(temp.name)
    return temp


_IMAGE_MAGIC: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"<?xml", ".svg"),
    (b"<svg", ".svg"),
    (b"BM", ".bmp"),
    (b"RIFF", ".webp"),
]


def _sniff_image_extension(data: bytes) -> str:
    for magic, ext in _IMAGE_MAGIC:
        if data.startswith(magic):
            return ext
    return ".bin"


def _object_media_types(manifest_bytes: bytes | None) -> dict[str, str]:
    """Map ``Object N`` directory names to their manifest media-types."""
    if not manifest_bytes:
        return {}
    manifest_ns: str = ODF_NAMESPACES["manifest"]
    result: dict[str, str] = {}
    try:
        root = ET.fromstring(manifest_bytes)
    except ET.ParseError:
        return {}
    for entry in root.findall(f".//{{{manifest_ns}}}file-entry"):
        path = entry.attrib.get(f"{{{manifest_ns}}}full-path", "")
        media = entry.attrib.get(f"{{{manifest_ns}}}media-type", "")
        if path.startswith("Object ") and path.endswith("/") and media:
            result[path.rstrip("/")] = media
    return result


def _flatten_object(members: dict[str, bytes], mimetype: str | None) -> ET.Element:
    """Merge an embedded object's sub-package members into one flat document.

    Args:
        members: Mapping of member filename (e.g. ``"content.xml"``) to bytes.
        mimetype: Object media-type for the ``office:mimetype`` attribute.

    Returns:
        A nested ``<office:document>`` element ready to inline inside
        ``<draw:object>``.
    """
    office_ns: str = ODF_NAMESPACES["office"]
    doc: ET.Element = ET.Element(f"{{{office_ns}}}document", {f"{{{office_ns}}}version": "1.3"})
    if mimetype:
        doc.set(f"{{{office_ns}}}mimetype", mimetype)
    roots: dict[str, ET.Element] = {}
    for name, data in members.items():
        try:
            roots[name] = ET.fromstring(data)
        except ET.ParseError:
            continue

    def pick(member: str, names: set[str]) -> list[ET.Element]:
        root = roots.get(member)
        return [] if root is None else [c for c in root if local_name(c.tag) in names]

    for child in pick("meta.xml", {"meta"}):
        doc.append(child)
    for child in pick("settings.xml", {"settings"}):
        doc.append(child)
    for child in pick("content.xml", {"scripts"}):
        doc.append(child)
    for child in pick("styles.xml", {"font-face-decls"}):
        doc.append(child)
    for child in pick("styles.xml", {"styles"}):
        doc.append(child)
    merged_auto: ET.Element = ET.SubElement(doc, f"{{{office_ns}}}automatic-styles")
    for member in ("styles.xml", "content.xml"):
        for auto in pick(member, {"automatic-styles"}):
            for grandchild in list(auto):
                merged_auto.append(grandchild)
    for child in pick("styles.xml", {"master-styles"}):
        doc.append(child)
    for child in pick("content.xml", {"body"}):
        doc.append(child)
    return doc


def _split_object_flat(doc: ET.Element) -> tuple[dict[str, bytes], str | None]:
    """Split a flat object ``<office:document>`` back into sub-package members.

    Args:
        doc: The nested ``<office:document>`` inlined inside ``<draw:object>``.

    Returns:
        A ``(members, mimetype)`` pair where ``members`` maps member filenames
        to serialized bytes.
    """
    office_ns: str = ODF_NAMESPACES["office"]
    mimetype: str | None = doc.attrib.get(f"{{{office_ns}}}mimetype")
    content_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-content", {f"{{{office_ns}}}version": "1.3"})
    styles_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-styles", {f"{{{office_ns}}}version": "1.3"})
    meta_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-meta", {f"{{{office_ns}}}version": "1.3"})
    settings_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-settings", {f"{{{office_ns}}}version": "1.3"})
    content_auto: ET.Element = ET.SubElement(content_doc, f"{{{office_ns}}}automatic-styles")
    has_styles = has_meta = has_settings = False
    for child in list(doc):
        name: str = local_name(child.tag)
        if name == "meta":
            meta_doc.append(child)
            has_meta = True
        elif name == "settings":
            settings_doc.append(child)
            has_settings = True
        elif name == "scripts":
            content_doc.insert(0, child)
        elif name in {"font-face-decls", "styles", "master-styles"}:
            styles_doc.append(child)
            has_styles = True
        elif name == "automatic-styles":
            for grandchild in list(child):
                content_auto.append(grandchild)
        elif name == "body":
            content_doc.append(child)
    members: dict[str, bytes] = {"content.xml": xml_bytes(content_doc)}
    if has_styles:
        members["styles.xml"] = xml_bytes(styles_doc)
    if has_meta:
        members["meta.xml"] = xml_bytes(meta_doc)
    if has_settings:
        members["settings.xml"] = xml_bytes(settings_doc)
    return members, mimetype


def pack_flat_odf(input_zip: Path, output_flat: Path) -> None:
    """Convert a zipped ODF package to flat (single-XML) ODF.

    The resulting file has a single ``<office:document>`` root with merged
    content, styles, meta, and settings, plus all embedded pictures encoded
    inline as ``<office:binary-data>`` children of their ``<draw:image>``.

    Args:
        input_zip: Source ODF file (``.odt``/``.odp``/``.ods``/``.odg``).
        output_flat: Destination flat ODF file (``.fodt``/``.fodp``/...).
    """
    for prefix, uri in ODF_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    office_ns: str = ODF_NAMESPACES["office"]
    xlink_ns: str = ODF_NAMESPACES["xlink"]
    draw_ns: str = ODF_NAMESPACES["draw"]

    with zipfile.ZipFile(input_zip) as archive:
        mimetype: str = archive.read("mimetype").decode("ascii").strip()
        meta_root: ET.Element = ET.fromstring(archive.read("meta.xml"))
        settings_root: ET.Element = ET.fromstring(archive.read("settings.xml"))
        styles_root: ET.Element = ET.fromstring(archive.read("styles.xml"))
        content_root: ET.Element = ET.fromstring(archive.read("content.xml"))
        pictures: dict[str, bytes] = {
            name: archive.read(name) for name in archive.namelist() if name.startswith("Pictures/")
        }
        # Embedded objects (charts, formulas) live under 'Object N/' as full
        # sub-packages (content.xml plus optional styles.xml/meta.xml).
        object_members: dict[str, bytes] = {
            name: archive.read(name)
            for name in archive.namelist()
            if name.startswith("Object ") and not name.endswith("/")
        }
        try:
            object_manifest: bytes | None = archive.read("META-INF/manifest.xml")
        except KeyError:
            object_manifest = None

    flat_root: ET.Element = ET.Element(
        f"{{{office_ns}}}document",
        {
            f"{{{office_ns}}}version": "1.3",
            f"{{{office_ns}}}mimetype": mimetype,
        },
    )

    def _children_matching(source: ET.Element, names: set[str]) -> list[ET.Element]:
        return [child for child in source if local_name(child.tag) in names]

    for child in _children_matching(meta_root, {"meta"}):
        flat_root.append(child)
    for child in _children_matching(settings_root, {"settings"}):
        flat_root.append(child)
    for child in _children_matching(content_root, {"scripts"}):
        flat_root.append(child)
    for child in _children_matching(styles_root, {"font-face-decls"}):
        flat_root.append(child)
    for child in _children_matching(styles_root, {"styles"}):
        flat_root.append(child)

    merged_auto: ET.Element = ET.SubElement(flat_root, f"{{{office_ns}}}automatic-styles")
    for source in (styles_root, content_root):
        for auto in _children_matching(source, {"automatic-styles"}):
            for grandchild in list(auto):
                merged_auto.append(grandchild)

    for child in _children_matching(styles_root, {"master-styles"}):
        flat_root.append(child)
    for child in _children_matching(content_root, {"body"}):
        flat_root.append(child)

    for image in flat_root.iter(f"{{{draw_ns}}}image"):
        href: str | None = image.attrib.get(f"{{{xlink_ns}}}href")
        if href and href in pictures:
            for attr in (
                f"{{{xlink_ns}}}href",
                f"{{{xlink_ns}}}type",
                f"{{{xlink_ns}}}show",
                f"{{{xlink_ns}}}actuate",
            ):
                image.attrib.pop(attr, None)
            binary: ET.Element = ET.SubElement(image, f"{{{office_ns}}}binary-data")
            binary.text = base64.b64encode(pictures[href]).decode("ascii")

    # Embed object sub-packages (charts, formulas): inline the object's
    # full sub-package as a nested <office:document> inside its <draw:object>.
    object_media: dict[str, str] = _object_media_types(object_manifest)
    for obj in list(flat_root.iter(f"{{{draw_ns}}}object")):
        href_obj: str | None = obj.attrib.get(f"{{{xlink_ns}}}href")
        if not href_obj:
            continue
        obj_dir: str = href_obj.lstrip("./").rstrip("/")
        members: dict[str, bytes] = {
            name[len(obj_dir) + 1 :]: data for name, data in object_members.items() if name.startswith(obj_dir + "/")
        }
        if "content.xml" not in members:
            continue
        for attr in (
            f"{{{xlink_ns}}}href",
            f"{{{xlink_ns}}}type",
            f"{{{xlink_ns}}}show",
            f"{{{xlink_ns}}}actuate",
        ):
            obj.attrib.pop(attr, None)
        obj.append(_flatten_object(members, object_media.get(obj_dir)))

    output_flat.write_bytes(xml_bytes(flat_root))


def unpack_flat_odf(input_flat: Path, output_zip: Path) -> None:
    """Convert a flat ODF file back to a zipped ODF package.

    Splits the single ``<office:document>`` root into the standard four
    XML files (content/styles/meta/settings), extracts inline pictures
    from ``<office:binary-data>`` blobs into ``Pictures/`` entries, and
    rebuilds ``META-INF/manifest.xml``.

    Args:
        input_flat: Source flat ODF file.
        output_zip: Destination zipped ODF file.
    """
    for prefix, uri in ODF_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    office_ns: str = ODF_NAMESPACES["office"]
    xlink_ns: str = ODF_NAMESPACES["xlink"]
    draw_ns: str = ODF_NAMESPACES["draw"]
    style_ns: str = ODF_NAMESPACES["style"]
    manifest_ns: str = ODF_NAMESPACES["manifest"]

    flat_root: ET.Element = ET.parse(input_flat).getroot()
    mimetype: str | None = flat_root.attrib.get(f"{{{office_ns}}}mimetype")
    if not mimetype:
        raise SystemExit("flat ODF root missing office:mimetype attribute")

    meta_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-meta", {f"{{{office_ns}}}version": "1.3"})
    settings_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-settings", {f"{{{office_ns}}}version": "1.3"})
    styles_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-styles", {f"{{{office_ns}}}version": "1.3"})
    content_doc: ET.Element = ET.Element(f"{{{office_ns}}}document-content", {f"{{{office_ns}}}version": "1.3"})

    styles_auto: ET.Element = ET.SubElement(styles_doc, f"{{{office_ns}}}automatic-styles")
    content_auto: ET.Element = ET.SubElement(content_doc, f"{{{office_ns}}}automatic-styles")

    for child in list(flat_root):
        name: str = local_name(child.tag)
        if name == "meta":
            meta_doc.append(child)
        elif name == "settings":
            settings_doc.append(child)
        elif name == "scripts":
            content_doc.append(child)
        elif name == "font-face-decls":
            styles_doc.append(child)
        elif name == "styles":
            styles_doc.append(child)
        elif name == "automatic-styles":
            for grandchild in list(child):
                if grandchild.tag == f"{{{style_ns}}}page-layout":
                    styles_auto.append(grandchild)
                else:
                    content_auto.append(grandchild)
        elif name == "master-styles":
            styles_doc.append(child)
        elif name == "body":
            content_doc.append(child)

    pictures: dict[str, bytes] = {}
    existing_names: set[str] = set()
    for image in content_doc.iter(f"{{{draw_ns}}}image"):
        binary: ET.Element | None = image.find(f"{{{office_ns}}}binary-data")
        if binary is None or not binary.text:
            continue
        data: bytes = base64.b64decode(binary.text.strip())
        ext: str = _sniff_image_extension(data)
        candidate: str = unique_picture_name(existing_names, Path(f"image{len(pictures) + 1}{ext}"))
        existing_names.add(candidate)
        pictures[candidate] = data
        image.remove(binary)
        image.set(f"{{{xlink_ns}}}href", candidate)
        image.set(f"{{{xlink_ns}}}type", "simple")
        image.set(f"{{{xlink_ns}}}show", "embed")
        image.set(f"{{{xlink_ns}}}actuate", "onLoad")

    # Extract inlined object sub-packages (charts, formulas) back to Object N/.
    math_ns: str = ODF_NAMESPACES["math"]
    chart_ns: str = ODF_NAMESPACES["chart"]
    objects: dict[str, bytes] = {}
    object_media: dict[str, str] = {}
    object_count = 0
    for obj in content_doc.iter(f"{{{draw_ns}}}object"):
        doc_child: ET.Element | None = obj.find(f"{{{office_ns}}}document")
        if doc_child is None:
            continue
        object_count += 1
        obj_dir = f"Object {object_count}"
        members, declared_mime = _split_object_flat(doc_child)
        for member_name, member_bytes in members.items():
            objects[f"{obj_dir}/{member_name}"] = member_bytes
        if declared_mime:
            object_media[obj_dir] = declared_mime
        elif doc_child.find(f".//{{{math_ns}}}math") is not None:
            object_media[obj_dir] = "application/vnd.oasis.opendocument.formula"
        elif doc_child.find(f".//{{{chart_ns}}}chart") is not None:
            object_media[obj_dir] = "application/vnd.oasis.opendocument.chart"
        else:
            object_media[obj_dir] = "application/vnd.oasis.opendocument.text"
        obj.remove(doc_child)
        obj.set(f"{{{xlink_ns}}}href", f"./{obj_dir}/")
        obj.set(f"{{{xlink_ns}}}type", "simple")
        obj.set(f"{{{xlink_ns}}}show", "embed")
        obj.set(f"{{{xlink_ns}}}actuate", "onLoad")

    manifest_doc: ET.Element = ET.Element(
        f"{{{manifest_ns}}}manifest",
        {f"{{{manifest_ns}}}version": "1.3"},
    )
    ET.SubElement(
        manifest_doc,
        f"{{{manifest_ns}}}file-entry",
        {
            f"{{{manifest_ns}}}full-path": "/",
            f"{{{manifest_ns}}}media-type": mimetype,
            f"{{{manifest_ns}}}version": "1.3",
        },
    )
    for name in ("content.xml", "styles.xml", "meta.xml", "settings.xml"):
        ET.SubElement(
            manifest_doc,
            f"{{{manifest_ns}}}file-entry",
            {
                f"{{{manifest_ns}}}full-path": name,
                f"{{{manifest_ns}}}media-type": "text/xml",
            },
        )
    for picture_path in pictures:
        ET.SubElement(
            manifest_doc,
            f"{{{manifest_ns}}}file-entry",
            {
                f"{{{manifest_ns}}}full-path": picture_path,
                f"{{{manifest_ns}}}media-type": media_type_for(Path(picture_path)),
            },
        )
    for obj_dir, media in object_media.items():
        ET.SubElement(
            manifest_doc,
            f"{{{manifest_ns}}}file-entry",
            {f"{{{manifest_ns}}}full-path": f"{obj_dir}/", f"{{{manifest_ns}}}media-type": media},
        )
    for object_path in objects:
        ET.SubElement(
            manifest_doc,
            f"{{{manifest_ns}}}file-entry",
            {f"{{{manifest_ns}}}full-path": object_path, f"{{{manifest_ns}}}media-type": "text/xml"},
        )

    with zipfile.ZipFile(output_zip, "w") as archive:
        archive.writestr("mimetype", mimetype, compress_type=zipfile.ZIP_STORED)
        archive.writestr("content.xml", xml_bytes(content_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("styles.xml", xml_bytes(styles_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("meta.xml", xml_bytes(meta_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("settings.xml", xml_bytes(settings_doc), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", xml_bytes(manifest_doc), compress_type=zipfile.ZIP_DEFLATED)
        for path, data in pictures.items():
            archive.writestr(path, data, compress_type=zipfile.ZIP_DEFLATED)
        for path, data in objects.items():
            archive.writestr(path, data, compress_type=zipfile.ZIP_DEFLATED)


def local_name(tag: str) -> str:
    """Extract the local name from a Clark-notation tag ``'{ns}local'``.

    Args:
        tag: XML tag in Clark notation (e.g. ``"{urn:...}text"``) or plain name.

    Returns:
        The local name part (e.g. ``"text"``).
    """
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def convert_with_soffice(
    input_path: Path,
    target_format: str,
    outdir: Path,
    filter_name: str | None = None,
) -> Path:
    """Convert *input_path* to *target_format* via headless LibreOffice.

    Spawns soffice with an isolated ``-env:UserInstallation`` temp profile
    (so concurrent calls do not clash, and the real user profile is never
    touched), runs ``--convert-to``, and returns the output file path.

    Used for PDF rendering (see :func:`render_to_pdf`), OOXML conversion
    (``docx``/``xlsx``/``pptx`` and the legacy ``doc``/``xls``/``ppt``), and
    same-format re-saves (e.g. ``--convert-to ods`` to refresh formulas as
    in :file:`skills/ods/scripts/recalc.py`).

    Args:
        input_path: Source file.
        target_format: soffice format identifier (e.g. ``"pdf"``, ``"docx"``,
            ``"ods"``). Determines the output extension.
        outdir: Directory for the output (created if absent).
        filter_name: Optional explicit LibreOffice filter name. When set,
            soffice receives ``f"{target_format}:{filter_name}"`` — useful
            to pin a specific filter version where soffice's default would
            be ambiguous (rare).

    Returns:
        Path to the converted file (``outdir / f"{input_path.stem}.{target_format}"``).

    Raises:
        SystemExit: If LibreOffice fails or the output file is not produced.
    """
    import subprocess

    outdir.mkdir(parents=True, exist_ok=True)
    soffice: str = find_soffice()
    convert_arg: str = f"{target_format}:{filter_name}" if filter_name else target_format
    profile: str = tempfile.mkdtemp(prefix="odf-soffice-")
    try:
        result = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation=file://{profile}",
                "--headless",
                "--convert-to",
                convert_arg,
                "--outdir",
                str(outdir),
                str(input_path),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    output: Path = outdir / f"{input_path.stem}.{target_format}"
    if result.returncode != 0 or not output.exists():
        raise SystemExit(f"LibreOffice failed to convert {input_path.name} to {target_format}:\n{result.stdout}")
    return output


def render_to_pdf(odf_path: Path, outdir: Path) -> Path:
    """Render an ODF file to PDF with LibreOffice.

    Thin wrapper around :func:`convert_with_soffice` with ``target_format="pdf"``;
    retained for backward compatibility and as the dedicated PDF entry point.

    Args:
        odf_path: Source ODF file.
        outdir: Directory for the PDF (created if absent).

    Returns:
        Path to the rendered PDF.

    Raises:
        SystemExit: If LibreOffice fails or the PDF is not produced.
    """
    return convert_with_soffice(odf_path, "pdf", outdir)


def render_impress_to_pdf(
    odp_path: Path,
    outdir: Path,
    *,
    notes: bool = False,
    notes_only: bool = False,
) -> Path:
    """Render an ODP deck to PDF with optional speaker-notes pages.

    Uses LibreOffice's ``impress_pdf_Export`` filter to control whether the
    PDF includes notes pages. The output filename varies with the mode so
    callers can keep slide-only, slide+notes, and notes-only PDFs side by
    side:

    - default (neither flag): ``<stem>.pdf`` — slides only (same as
      :func:`render_to_pdf`).
    - ``notes=True``: ``<stem>-with-notes.pdf`` — slides interleaved with
      notes pages.
    - ``notes_only=True``: ``<stem>-notes.pdf`` — notes pages only.

    Args:
        odp_path: Source ODP file.
        outdir: Directory for the PDF (created if absent).
        notes: Include speaker-notes pages alongside the slide pages.
        notes_only: Export only the notes pages (implies ``notes=True``).
            Mutually exclusive with the slide-only default.

    Returns:
        Path to the rendered PDF (renamed per mode, see above).

    Raises:
        ValueError: If both ``notes`` and ``notes_only`` are ``False`` but
            the caller expected a notes-flavoured output (i.e. nothing to do
            here that ``render_to_pdf`` would not already cover). The
            default mode is still supported for symmetry.
        SystemExit: If LibreOffice fails or the PDF is not produced.
    """
    if notes_only:
        # ``ExportOnlyNotesPages=True`` requires ``ExportNotesPages=True``
        # in LibreOffice's filter — both must be set together.
        filter_name: str | None = (
            'impress_pdf_Export:{"ExportNotesPages":{"type":"boolean","value":"true"},'
            '"ExportOnlyNotesPages":{"type":"boolean","value":"true"}}'
        )
        suffix = "-notes"
    elif notes:
        filter_name = 'impress_pdf_Export:{"ExportNotesPages":{"type":"boolean","value":"true"}}'
        suffix = "-with-notes"
    else:
        filter_name = None
        suffix = ""

    outdir.mkdir(parents=True, exist_ok=True)
    if not suffix:
        return convert_with_soffice(odp_path, "pdf", outdir, filter_name=filter_name)

    # Render into a private temp dir so the rename target does not clobber
    # an existing ``<stem>.pdf`` (e.g. a slide-only PDF rendered first).
    staging = Path(tempfile.mkdtemp(prefix="odf-render-notes-"))
    try:
        rendered = convert_with_soffice(odp_path, "pdf", staging, filter_name=filter_name)
        target = outdir / f"{odp_path.stem}{suffix}.pdf"
        if target.exists():
            target.unlink()
        rendered.replace(target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def pdf_to_pngs(pdf_path: Path, outdir: Path, dpi: int = 150) -> list[Path]:
    """Render every page of a PDF to a PNG with ``pdftoppm`` (Poppler).

    Args:
        pdf_path: Source PDF.
        outdir: Directory for the page PNGs (created if absent).
        dpi: Render resolution.

    Returns:
        Sorted list of ``<stem>-N.png`` page images.

    Raises:
        SystemExit: If ``pdftoppm`` is not installed or rendering fails.
    """
    import subprocess

    pdftoppm: str | None = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise SystemExit(
            "pdftoppm not found — install Poppler (e.g. 'brew install poppler' or 'apt install poppler-utils')"
        )
    outdir.mkdir(parents=True, exist_ok=True)
    prefix: Path = outdir / pdf_path.stem
    result = subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise SystemExit(f"pdftoppm failed for {pdf_path.name}:\n{result.stdout}")
    return sorted(outdir.glob(f"{pdf_path.stem}-*.png"))


def build_contact_sheet(images: list[Path], output_path: Path, columns: int = 0) -> Path:
    """Compose page thumbnails into a single labelled grid image.

    A contact sheet shows every page of a document at once, so layout and
    cross-page consistency can be judged in a single glance. Requires Pillow.

    Args:
        images: Page images, in order.
        output_path: Destination PNG.
        columns: Grid columns; 0 picks 2 for landscape pages, 3 for portrait.

    Returns:
        Path to the contact sheet PNG.

    Raises:
        SystemExit: If Pillow is not installed or *images* is empty.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise SystemExit(
            "Contact sheet rendering requires Pillow. Install with:\n"
            "  pip install open-document-lib[render]\n"
            "Or render per-page PNGs with --png and inspect them individually."
        ) from None

    if not images:
        raise SystemExit("build_contact_sheet: no page images to compose")

    thumb_w = 480
    pad = 16
    label_h = 22
    bg = (245, 245, 247)

    thumbs: list[Image.Image] = []
    for path in images:
        img = Image.open(path).convert("RGB")
        ratio = thumb_w / img.width
        thumbs.append(img.resize((thumb_w, max(1, round(img.height * ratio))), Image.LANCZOS))

    if columns <= 0:
        columns = 2 if thumbs[0].width >= thumbs[0].height else 3
    columns = min(columns, len(thumbs))
    rows = (len(thumbs) + columns - 1) // columns

    cell_w = thumb_w + pad
    cell_h = max(t.height for t in thumbs) + pad + label_h
    sheet = Image.new("RGB", (columns * cell_w + pad, rows * cell_h + pad), bg)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()

    for index, thumb in enumerate(thumbs):
        col = index % columns
        row = index // columns
        x = pad + col * cell_w
        y = pad + row * cell_h
        draw.text((x, y), f"Page {index + 1}", fill=(60, 60, 70), font=font)
        sheet.paste(thumb, (x, y + label_h))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path
