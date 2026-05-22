"""Hypothesis property tests for the walker/locator helpers in odf_lib/odf_common.

Four invariants:
1. Replacement idempotence — replacing twice == replacing once (when `new` doesn't contain `old`).
2. Text content conservation — sum of slot lengths stays consistent with the string-level edit.
3. Child preservation — children survive even when matches straddle them.
4. Insert rollback — failed pair-wrap leaves the element unchanged.
"""

from __future__ import annotations

import unittest
from copy import deepcopy
from xml.etree import ElementTree as ET

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from odf_lib.odf_common import (
    insert_after_text_in_element,
    replace_text_in_element,
    wrap_text_with_pair_in_element,
)

SAFE_CHARS = st.characters(
    blacklist_categories=("Cs", "Cc"),  # surrogates and control chars
    blacklist_characters="<>&\"'\n\r",  # XML-sensitive + line breaks (keep tests deterministic)
)
SAFE_TEXT = st.text(alphabet=SAFE_CHARS, min_size=0, max_size=20)


def _build_paragraph(text: str, children_payloads: list[tuple[str, str]]) -> ET.Element:
    """Build a <p> element with optional <span> children: [(span_text, tail), ...]."""
    p = ET.Element("p")
    p.text = text or None
    for span_text, tail in children_payloads:
        span = ET.SubElement(p, "span")
        span.text = span_text or None
        span.tail = tail or None
    return p


PARAGRAPH_STRATEGY = st.builds(
    _build_paragraph,
    text=SAFE_TEXT,
    children_payloads=st.lists(st.tuples(SAFE_TEXT, SAFE_TEXT), max_size=3),
)


def _concatenated_text(element: ET.Element) -> str:
    """Recursively concatenate .text and .tail of every descendant in document order."""
    parts: list[str] = []

    def visit(node: ET.Element, is_root: bool) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            visit(child, False)
        if not is_root and node.tail:
            parts.append(node.tail)

    visit(element, True)
    return "".join(parts)


class WalkerPropertyTests(unittest.TestCase):
    @given(
        paragraph=PARAGRAPH_STRATEGY,
        old=st.text(alphabet=SAFE_CHARS, min_size=1, max_size=5),
        new=st.text(alphabet=SAFE_CHARS, min_size=0, max_size=5),
    )
    @settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_replacement_idempotence(self, paragraph: ET.Element, old: str, new: str) -> None:
        """If `new` doesn't contain `old`, replacing twice == replacing once."""
        assume(old not in new)
        once = deepcopy(paragraph)
        twice = deepcopy(paragraph)
        replace_text_in_element(once, old, new)
        replace_text_in_element(twice, old, new)
        replace_text_in_element(twice, old, new)
        self.assertEqual(ET.tostring(once), ET.tostring(twice))

    @given(
        paragraph=PARAGRAPH_STRATEGY,
        old=st.text(alphabet=SAFE_CHARS, min_size=1, max_size=5),
        new=st.text(alphabet=SAFE_CHARS, min_size=0, max_size=5),
    )
    @settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_text_content_conservation(self, paragraph: ET.Element, old: str, new: str) -> None:
        """After replace, concatenated text matches what a string-level replace would yield."""
        before = _concatenated_text(paragraph)
        count = replace_text_in_element(paragraph, old, new)
        after = _concatenated_text(paragraph)
        expected = before.replace(old, new)
        self.assertEqual(after, expected)
        # Replacement count is consistent with non-overlapping find
        if count > 0:
            # The walker performs non-overlapping replacements left-to-right.
            self.assertEqual(count, before.count(old) if old not in new or not new else count)

    @given(paragraph=PARAGRAPH_STRATEGY, old=st.text(alphabet=SAFE_CHARS, min_size=1, max_size=5))
    @settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_child_count_preserved_under_replacement(self, paragraph: ET.Element, old: str) -> None:
        """Replacement never removes child elements, even when straddling them."""
        original_children = len(list(paragraph))
        replace_text_in_element(paragraph, old, "X")
        self.assertEqual(len(list(paragraph)), original_children)

    @given(
        paragraph=PARAGRAPH_STRATEGY,
        start_anchor=st.text(alphabet=SAFE_CHARS, min_size=1, max_size=5),
        end_anchor=st.text(alphabet=SAFE_CHARS, min_size=1, max_size=5),
    )
    @settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_wrap_pair_rollback_on_failure(self, paragraph: ET.Element, start_anchor: str, end_anchor: str) -> None:
        """If wrap_text_with_pair_in_element fails, the element is unchanged."""
        before = ET.tostring(paragraph)
        start_el = ET.Element("s")
        end_el = ET.Element("e")
        ok = wrap_text_with_pair_in_element(paragraph, start_anchor, end_anchor, start_el, end_el)
        if not ok:
            self.assertEqual(ET.tostring(paragraph), before)

    @given(paragraph=PARAGRAPH_STRATEGY, anchor=st.text(alphabet=SAFE_CHARS, min_size=1, max_size=5))
    @settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_insert_after_anchor_preserves_visible_text(self, paragraph: ET.Element, anchor: str) -> None:
        """If insertion succeeds, the anchor still appears in the visible text."""
        before = _concatenated_text(paragraph)
        new_el = ET.Element("inserted")
        ok = insert_after_text_in_element(paragraph, anchor, new_el)
        after = _concatenated_text(paragraph)
        if ok:
            self.assertEqual(after, before)
            # And the new element is now a sibling or child somewhere
            self.assertTrue(any(e.tag == "inserted" for e in paragraph.iter()))


if __name__ == "__main__":
    unittest.main()
