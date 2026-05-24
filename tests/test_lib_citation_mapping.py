"""Direct unit tests for ``odf_lib.citation_mapping``.

The module is dependency-light by design (no ``bibtexparser`` import),
so all tests run against the stdlib. They cover the three public
functions plus the lookup tables, including edge cases the bulk
citation pipeline relies on: missing CSL date parts, BibTeX
``ENTRYTYPE`` casing, brace-stripped field values, multi-author lists,
literal-name authors, list-form ISSN, and the unknown-type fallback to
``misc``.
"""

from __future__ import annotations

import unittest

from odf_lib.citation_mapping import (
    BIBTEX_FIELD_TO_ODF,
    BIBTEX_TYPE_TO_ODF,
    CSL_TYPE_TO_ODF,
    ODF_BIBLIOGRAPHY_FIELDS,
    ODF_BIBLIOGRAPHY_TYPES,
    REQUIRED_FIELDS,
    bibtex_entry_to_odf_fields,
    csl_authors_to_string,
    csl_date_to_year,
    csl_entry_to_odf_fields,
)


class CslAuthorsToStringTests(unittest.TestCase):
    def test_family_and_given(self) -> None:
        authors = [{"family": "Mueller", "given": "Klaus"}]
        self.assertEqual(csl_authors_to_string(authors), "Mueller, Klaus")

    def test_multiple_authors_joined_with_semicolon(self) -> None:
        authors = [
            {"family": "Mueller", "given": "Klaus"},
            {"family": "Schmidt", "given": "Eva"},
        ]
        self.assertEqual(
            csl_authors_to_string(authors),
            "Mueller, Klaus; Schmidt, Eva",
        )

    def test_family_only(self) -> None:
        self.assertEqual(csl_authors_to_string([{"family": "Plato"}]), "Plato")

    def test_given_only(self) -> None:
        self.assertEqual(csl_authors_to_string([{"given": "Aristotle"}]), "Aristotle")

    def test_literal_name_takes_precedence(self) -> None:
        # CSL `literal` is for corporate/anonymous authors; it overrides family/given.
        authors = [{"literal": "World Health Organization", "family": "ignored"}]
        self.assertEqual(csl_authors_to_string(authors), "World Health Organization")

    def test_skips_non_dict_entries(self) -> None:
        authors = [{"family": "Mueller"}, "not-a-dict", None, {"family": "Schmidt"}]
        self.assertEqual(csl_authors_to_string(authors), "Mueller; Schmidt")  # type: ignore[list-item]

    def test_empty_list(self) -> None:
        self.assertEqual(csl_authors_to_string([]), "")

    def test_entry_with_no_usable_fields_is_skipped(self) -> None:
        # No family, no given, no literal → nothing to emit.
        self.assertEqual(csl_authors_to_string([{}, {"family": "Mueller"}]), "Mueller")


class CslDateToYearTests(unittest.TestCase):
    def test_typical_issued_with_full_date(self) -> None:
        date = {"date-parts": [[2020, 5, 14]]}
        self.assertEqual(csl_date_to_year(date), "2020")

    def test_year_only(self) -> None:
        date = {"date-parts": [[1999]]}
        self.assertEqual(csl_date_to_year(date), "1999")

    def test_returns_none_for_non_dict(self) -> None:
        self.assertIsNone(csl_date_to_year("2020"))
        self.assertIsNone(csl_date_to_year(None))
        self.assertIsNone(csl_date_to_year([2020]))

    def test_returns_none_when_date_parts_missing(self) -> None:
        self.assertIsNone(csl_date_to_year({}))
        self.assertIsNone(csl_date_to_year({"raw": "circa 1850"}))

    def test_returns_none_when_date_parts_not_a_list(self) -> None:
        self.assertIsNone(csl_date_to_year({"date-parts": "2020"}))

    def test_returns_none_for_empty_date_parts(self) -> None:
        self.assertIsNone(csl_date_to_year({"date-parts": []}))

    def test_returns_none_when_first_part_not_a_list(self) -> None:
        self.assertIsNone(csl_date_to_year({"date-parts": ["2020"]}))

    def test_returns_none_for_empty_first_part(self) -> None:
        self.assertIsNone(csl_date_to_year({"date-parts": [[]]}))


class CslEntryToOdfFieldsTests(unittest.TestCase):
    def test_journal_article_full_entry(self) -> None:
        entry = {
            "type": "article-journal",
            "title": "Origins of Bronze Age Trade",
            "container-title": "Archaeology Quarterly",
            "author": [{"family": "Mueller", "given": "K."}],
            "issued": {"date-parts": [[2020]]},
            "publisher": "Anvil Press",
            "publisher-place": "Berlin",
            "page": "23-45",
            "volume": "12",
            "issue": "3",
            "URL": "https://example.org/article",
            "ISSN": "1234-5678",
        }
        result = csl_entry_to_odf_fields(entry)
        self.assertEqual(result["bibliography-type"], "article")
        self.assertEqual(result["title"], "Origins of Bronze Age Trade")
        self.assertEqual(result["journal"], "Archaeology Quarterly")
        self.assertEqual(result["author"], "Mueller, K.")
        self.assertEqual(result["year"], "2020")
        self.assertEqual(result["publisher"], "Anvil Press")
        self.assertEqual(result["address"], "Berlin")
        self.assertEqual(result["pages"], "23-45")
        self.assertEqual(result["volume"], "12")
        self.assertEqual(result["number"], "3")
        self.assertEqual(result["url"], "https://example.org/article")
        self.assertEqual(result["issn"], "1234-5678")

    def test_book_entry(self) -> None:
        entry = {
            "type": "book",
            "title": "Iron Age Communities",
            "author": [{"family": "Schmidt", "given": "E."}],
            "issued": {"date-parts": [[1998]]},
            "publisher": "University Press",
            "ISBN": "978-3-16-148410-0",
            "edition": "2nd",
        }
        result = csl_entry_to_odf_fields(entry)
        self.assertEqual(result["bibliography-type"], "book")
        self.assertEqual(result["isbn"], "978-3-16-148410-0")
        self.assertEqual(result["edition"], "2nd")

    def test_chapter_maps_to_incollection(self) -> None:
        result = csl_entry_to_odf_fields({"type": "chapter", "title": "Chapter X"})
        self.assertEqual(result["bibliography-type"], "incollection")

    def test_paper_conference_maps_to_inproceedings(self) -> None:
        result = csl_entry_to_odf_fields({"type": "paper-conference", "title": "Talk"})
        self.assertEqual(result["bibliography-type"], "inproceedings")

    def test_thesis_maps_to_phdthesis(self) -> None:
        result = csl_entry_to_odf_fields({"type": "thesis", "title": "T"})
        self.assertEqual(result["bibliography-type"], "phdthesis")

    def test_webpage_maps_to_www(self) -> None:
        result = csl_entry_to_odf_fields({"type": "webpage", "title": "Page"})
        self.assertEqual(result["bibliography-type"], "www")

    def test_unknown_type_falls_back_to_misc(self) -> None:
        result = csl_entry_to_odf_fields({"type": "obscure-thing", "title": "X"})
        self.assertEqual(result["bibliography-type"], "misc")

    def test_missing_type_defaults_to_misc(self) -> None:
        result = csl_entry_to_odf_fields({"title": "Untyped"})
        self.assertEqual(result["bibliography-type"], "misc")

    def test_editor_field_handled_like_author(self) -> None:
        entry = {
            "type": "book",
            "title": "Edited Volume",
            "editor": [{"family": "Beck", "given": "Ulrich"}],
        }
        result = csl_entry_to_odf_fields(entry)
        self.assertEqual(result["editor"], "Beck, Ulrich")

    def test_empty_author_list_yields_no_author_field(self) -> None:
        entry = {"type": "book", "title": "Anon", "author": []}
        result = csl_entry_to_odf_fields(entry)
        self.assertNotIn("author", result)

    def test_author_not_a_list_is_treated_as_empty(self) -> None:
        entry = {"type": "book", "title": "T", "author": "Mueller, K."}
        result = csl_entry_to_odf_fields(entry)
        self.assertNotIn("author", result)

    def test_issn_list_form(self) -> None:
        result = csl_entry_to_odf_fields({"type": "article-journal", "title": "X", "ISSN": ["1234-5678", "8765-4321"]})
        self.assertEqual(result["issn"], "1234-5678")

    def test_issn_empty_list_falls_back(self) -> None:
        # When ISSN is an empty list, the implementation falls back to str(issn).
        result = csl_entry_to_odf_fields({"type": "article-journal", "title": "X", "ISSN": []})
        self.assertEqual(result["issn"], "[]")

    def test_missing_issued_yields_no_year(self) -> None:
        result = csl_entry_to_odf_fields({"type": "book", "title": "Undated"})
        self.assertNotIn("year", result)

    def test_note_field_passed_through(self) -> None:
        result = csl_entry_to_odf_fields({"type": "misc", "title": "X", "note": "Cited from secondary source"})
        self.assertEqual(result["note"], "Cited from secondary source")


class BibtexEntryToOdfFieldsTests(unittest.TestCase):
    def test_article_full_entry(self) -> None:
        entry = {
            "ENTRYTYPE": "article",
            "author": "Mueller, Klaus",
            "title": "{Origins of Bronze Age Trade}",
            "journal": "Archaeology Quarterly",
            "year": "2020",
            "volume": "12",
            "number": "3",
            "pages": "23-45",
            "publisher": "Anvil Press",
        }
        result = bibtex_entry_to_odf_fields(entry)
        self.assertEqual(result["bibliography-type"], "article")
        self.assertEqual(result["author"], "Mueller, Klaus")
        # Braces are stripped.
        self.assertEqual(result["title"], "Origins of Bronze Age Trade")
        self.assertEqual(result["journal"], "Archaeology Quarterly")
        self.assertEqual(result["year"], "2020")
        self.assertEqual(result["volume"], "12")
        self.assertEqual(result["number"], "3")
        self.assertEqual(result["pages"], "23-45")

    def test_uppercase_entrytype_lowercased(self) -> None:
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "ARTICLE", "title": "T", "author": "A"})
        self.assertEqual(result["bibliography-type"], "article")

    def test_type_key_fallback(self) -> None:
        # Some BibTeX parsers use lowercase `type` instead of `ENTRYTYPE`.
        result = bibtex_entry_to_odf_fields({"type": "book", "title": "T"})
        self.assertEqual(result["bibliography-type"], "book")

    def test_online_maps_to_www(self) -> None:
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "online", "title": "Page"})
        self.assertEqual(result["bibliography-type"], "www")

    def test_electronic_maps_to_www(self) -> None:
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "electronic", "title": "Page"})
        self.assertEqual(result["bibliography-type"], "www")

    def test_unknown_entrytype_falls_back_to_misc(self) -> None:
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "obscure", "title": "X"})
        self.assertEqual(result["bibliography-type"], "misc")

    def test_missing_entrytype_defaults_to_misc(self) -> None:
        result = bibtex_entry_to_odf_fields({"title": "Untyped"})
        self.assertEqual(result["bibliography-type"], "misc")

    def test_organization_field_renamed_to_organizations(self) -> None:
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "manual", "title": "M", "organization": "ACME Corp"})
        self.assertEqual(result["organizations"], "ACME Corp")
        self.assertNotIn("organization", result)

    def test_type_field_renamed_to_report_type(self) -> None:
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "techreport", "title": "T", "type": "Technical report"})
        # In `bibtex_entry_to_odf_fields`, the `type` field maps via
        # BIBTEX_FIELD_TO_ODF to `report-type`. Note: `entry.get("type")`
        # is also consulted as a fallback for ENTRYTYPE — but ENTRYTYPE is
        # set here, so `type` survives as a field.
        self.assertEqual(result["report-type"], "Technical report")

    def test_empty_field_values_skipped(self) -> None:
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "article", "title": "T", "author": "", "journal": "J"})
        self.assertNotIn("author", result)
        self.assertIn("journal", result)

    def test_braces_stripped_from_value_edges_only(self) -> None:
        # The implementation only strips leading/trailing braces, not interior ones.
        result = bibtex_entry_to_odf_fields({"ENTRYTYPE": "book", "title": "{Title with {Inner} braces}"})
        self.assertEqual(result["title"], "Title with {Inner} braces")


class LookupTableInvariantsTests(unittest.TestCase):
    """Spec-level invariants: every mapped value must be in the ODF vocabulary."""

    def test_csl_types_all_map_to_valid_odf_types(self) -> None:
        for odf_type in CSL_TYPE_TO_ODF.values():
            self.assertIn(
                odf_type,
                ODF_BIBLIOGRAPHY_TYPES,
                f"CSL→ODF map emits {odf_type!r} which is not a valid bibliography-type",
            )

    def test_bibtex_types_all_map_to_valid_odf_types(self) -> None:
        for odf_type in BIBTEX_TYPE_TO_ODF.values():
            self.assertIn(
                odf_type,
                ODF_BIBLIOGRAPHY_TYPES,
                f"BibTeX→ODF map emits {odf_type!r} which is not a valid bibliography-type",
            )

    def test_bibtex_fields_all_map_to_valid_odf_fields(self) -> None:
        for odf_field in BIBTEX_FIELD_TO_ODF.values():
            self.assertIn(
                odf_field,
                ODF_BIBLIOGRAPHY_FIELDS,
                f"BibTeX→ODF map emits {odf_field!r} which is not a valid bibliography field",
            )

    def test_required_field_keys_are_valid_odf_types(self) -> None:
        for odf_type in REQUIRED_FIELDS:
            self.assertIn(odf_type, ODF_BIBLIOGRAPHY_TYPES)

    def test_required_fields_are_valid_odf_fields(self) -> None:
        for odf_type, fields in REQUIRED_FIELDS.items():
            for field in fields:
                self.assertIn(
                    field,
                    ODF_BIBLIOGRAPHY_FIELDS,
                    f"REQUIRED_FIELDS[{odf_type!r}] names {field!r} which is not a valid field",
                )


if __name__ == "__main__":
    unittest.main()
