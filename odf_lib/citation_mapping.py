"""Field mappings between CSL-JSON, BibTeX, and ODF text:bibliography-mark.

Keep this module dependency-light so it imports without pulling bibtexparser.
"""

from __future__ import annotations

from typing import Any

# ODF text:bibliography-type attribute values (per OASIS ODF 1.3 spec, §6.1.10).
ODF_BIBLIOGRAPHY_TYPES: set[str] = {
    "article",
    "book",
    "booklet",
    "conference",
    "custom1",
    "custom2",
    "custom3",
    "custom4",
    "custom5",
    "email",
    "inbook",
    "incollection",
    "inproceedings",
    "journal",
    "manual",
    "mastersthesis",
    "misc",
    "phdthesis",
    "proceedings",
    "techreport",
    "unpublished",
    "www",
}

# Field names that ODF accepts as attributes of text:bibliography-mark.
ODF_BIBLIOGRAPHY_FIELDS: set[str] = {
    "address",
    "annote",
    "author",
    "bibliography-type",
    "booktitle",
    "chapter",
    "custom1",
    "custom2",
    "custom3",
    "custom4",
    "custom5",
    "edition",
    "editor",
    "howpublished",
    "identifier",
    "institution",
    "isbn",
    "issn",
    "journal",
    "month",
    "note",
    "number",
    "organizations",
    "pages",
    "publisher",
    "report-type",
    "school",
    "series",
    "title",
    "url",
    "volume",
    "year",
}

# CSL type → ODF bibliography-type
CSL_TYPE_TO_ODF: dict[str, str] = {
    "article-journal": "article",
    "article-magazine": "article",
    "article-newspaper": "article",
    "article": "article",
    "book": "book",
    "chapter": "incollection",
    "paper-conference": "inproceedings",
    "thesis": "phdthesis",
    "report": "techreport",
    "manuscript": "unpublished",
    "webpage": "www",
    "post": "www",
    "post-weblog": "www",
    "personal_communication": "email",
}

# BibTeX entry type → ODF bibliography-type (identity for most)
BIBTEX_TYPE_TO_ODF: dict[str, str] = {
    "article": "article",
    "book": "book",
    "booklet": "booklet",
    "conference": "conference",
    "inbook": "inbook",
    "incollection": "incollection",
    "inproceedings": "inproceedings",
    "manual": "manual",
    "mastersthesis": "mastersthesis",
    "misc": "misc",
    "phdthesis": "phdthesis",
    "proceedings": "proceedings",
    "techreport": "techreport",
    "unpublished": "unpublished",
    "online": "www",
    "electronic": "www",
}

# BibTeX field name → ODF field name
BIBTEX_FIELD_TO_ODF: dict[str, str] = {
    "address": "address",
    "annote": "annote",
    "author": "author",
    "booktitle": "booktitle",
    "chapter": "chapter",
    "edition": "edition",
    "editor": "editor",
    "howpublished": "howpublished",
    "institution": "institution",
    "isbn": "isbn",
    "issn": "issn",
    "journal": "journal",
    "month": "month",
    "note": "note",
    "number": "number",
    "organization": "organizations",
    "pages": "pages",
    "publisher": "publisher",
    "school": "school",
    "series": "series",
    "title": "title",
    "type": "report-type",
    "url": "url",
    "volume": "volume",
    "year": "year",
}


def csl_authors_to_string(authors: list[dict[str, Any]]) -> str:
    """CSL `author` list (dicts with `family`/`given`) → 'Family, Given; Family, Given'."""
    parts: list[str] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        family = author.get("family", "")
        given = author.get("given", "")
        literal = author.get("literal")
        if literal:
            parts.append(str(literal))
        elif family and given:
            parts.append(f"{family}, {given}")
        elif family:
            parts.append(family)
        elif given:
            parts.append(given)
    return "; ".join(parts)


def csl_date_to_year(date_field: Any) -> str | None:
    """Extract a year from CSL-JSON's `issued` (or similar) field."""
    if not isinstance(date_field, dict):
        return None
    parts = date_field.get("date-parts")
    if not isinstance(parts, list) or not parts:
        return None
    first = parts[0]
    if not isinstance(first, list) or not first:
        return None
    return str(first[0])


def csl_entry_to_odf_fields(entry: dict[str, Any]) -> dict[str, str]:
    """Map a CSL-JSON entry to ODF text:bibliography-mark attribute values."""
    result: dict[str, str] = {}
    csl_type = entry.get("type", "misc")
    result["bibliography-type"] = CSL_TYPE_TO_ODF.get(csl_type, "misc")
    if "title" in entry:
        result["title"] = str(entry["title"])
    if "container-title" in entry:
        result["journal"] = str(entry["container-title"])
    if "author" in entry:
        authors = entry["author"] if isinstance(entry["author"], list) else []
        if authors:
            result["author"] = csl_authors_to_string(authors)
    if "editor" in entry:
        editors = entry["editor"] if isinstance(entry["editor"], list) else []
        if editors:
            result["editor"] = csl_authors_to_string(editors)
    year = csl_date_to_year(entry.get("issued"))
    if year:
        result["year"] = year
    if "publisher" in entry:
        result["publisher"] = str(entry["publisher"])
    if "publisher-place" in entry:
        result["address"] = str(entry["publisher-place"])
    if "page" in entry:
        result["pages"] = str(entry["page"])
    if "volume" in entry:
        result["volume"] = str(entry["volume"])
    if "issue" in entry:
        result["number"] = str(entry["issue"])
    if "edition" in entry:
        result["edition"] = str(entry["edition"])
    if "URL" in entry:
        result["url"] = str(entry["URL"])
    if "ISBN" in entry:
        result["isbn"] = str(entry["ISBN"])
    if "ISSN" in entry:
        issn = entry["ISSN"]
        result["issn"] = str(issn[0] if isinstance(issn, list) and issn else issn)
    if "note" in entry:
        result["note"] = str(entry["note"])
    return result


def bibtex_entry_to_odf_fields(entry: dict[str, Any]) -> dict[str, str]:
    """Map a parsed BibTeX entry (dict with ENTRYTYPE + fields) to ODF fields."""
    result: dict[str, str] = {}
    entry_type = str(entry.get("ENTRYTYPE", entry.get("type", "misc"))).lower()
    result["bibliography-type"] = BIBTEX_TYPE_TO_ODF.get(entry_type, "misc")
    for bib_field, odf_field in BIBTEX_FIELD_TO_ODF.items():
        if bib_field in entry and entry[bib_field]:
            result[odf_field] = str(entry[bib_field]).strip("{}")
    return result


# Required fields per ODF bibliography-type (subset; pragmatic for validation).
REQUIRED_FIELDS: dict[str, set[str]] = {
    "article": {"author", "title", "journal", "year"},
    "book": {"author", "title", "year"},
    "incollection": {"author", "title", "booktitle", "year"},
    "inproceedings": {"author", "title", "booktitle", "year"},
    "techreport": {"author", "title", "institution", "year"},
    "mastersthesis": {"author", "title", "school", "year"},
    "phdthesis": {"author", "title", "school", "year"},
    "manual": {"title", "year"},
    "misc": set(),
    "www": {"url"},
}
