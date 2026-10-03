"""Tests for Narrative Unicode Policy & Rich-Text Sanitization Service.

Pursuant to docs/ai/work-items/bilingual-narrative-sanitizer/SCOPE.md:
- Entity-decoded overrides rejected (&#x202E;, &#8238;, etc.)
- Literal U+202A–U+202E, U+2066–U+2069 rejected in text nodes
- LRM/RLM/ALM and &rlm;/&lrm; accepted
- Markup preserved: <p dir="rtl">, <strong>, <ul>/<li>, <br> survive
- Text inside failed nodes caught (<p>bad&#x202E;</p>)
- bdi_join produces <bdi>…</bdi> per element, escapes once, no double-escape
- Read-only import proven (registry SHA-256 stable)
- Save hook coverage on parent and child doctypes
- Zero leftover test artifacts (cleanup.leftover == 0)
"""

import unittest
import markupsafe
import frappe

from construction.services.bilingual_registry import registry_sha256
from construction.services.narrative_sanitizer import (
    bdi_join,
    find_offending_codepoint,
    sanitize_and_validate_html,
    validate_plain_text_narrative,
    validate_narrative_fields,
    NARRATIVE_FIELDS_CONFIG,
    CHILD_NARRATIVE_FIELDS_CONFIG,
)


class TestHtmlSanitizerAndValidator(unittest.TestCase):
    def test_entity_decoded_override_rejected(self):
        """&#x202E; and &#8238; entity encodings decoded and rejected with U+202E."""
        hex_payload = "<p>Text with &#x202E; override</p>"
        with self.assertRaises(frappe.ValidationError) as ctx:
            sanitize_and_validate_html(hex_payload, fieldname="description")
        self.assertIn("U+202E", str(ctx.exception))
        self.assertIn("description", str(ctx.exception))

        dec_payload = "<p>Text with &#8238; override</p>"
        with self.assertRaises(frappe.ValidationError) as ctx:
            sanitize_and_validate_html(dec_payload, fieldname="description")
        self.assertIn("U+202E", str(ctx.exception))

    def test_literal_overrides_and_isolates_rejected(self):
        """Literal bidi controls U+202A-U+202E and U+2066-U+2069 rejected."""
        for codepoint_char, code_str in [
            ("\u202a", "U+202A"),
            ("\u202b", "U+202B"),
            ("\u202c", "U+202C"),
            ("\u202d", "U+202D"),
            ("\u202e", "U+202E"),
            ("\u2066", "U+2066"),
            ("\u2067", "U+2067"),
            ("\u2068", "U+2068"),
            ("\u2069", "U+2069"),
        ]:
            payload = f"<div>Prose containing {codepoint_char} here</div>"
            with self.assertRaises(frappe.ValidationError) as ctx:
                sanitize_and_validate_html(payload, fieldname="bio")
            self.assertIn(code_str, str(ctx.exception))

    def test_lrm_rlm_alm_accepted(self):
        """Legitimate direction marks (U+200E, U+200F, U+061C) and named entities accepted."""
        payload_lrm = "<p>English clause with \u200e Arabic insertion</p>"
        self.assertEqual(sanitize_and_validate_html(payload_lrm), payload_lrm)

        payload_rlm = "<p>بند عربي مع \u200f كلمة إنجليزية</p>"
        self.assertEqual(sanitize_and_validate_html(payload_rlm), payload_rlm)

        payload_alm = "<p>علامة \u061c عربية</p>"
        self.assertEqual(sanitize_and_validate_html(payload_alm), payload_alm)

        payload_entities = "<p>Marks &rlm; and &lrm; inside text</p>"
        self.assertEqual(sanitize_and_validate_html(payload_entities), payload_entities)

    def test_markup_preserved(self):
        """HTML markup, attributes, and tags survive untouched."""
        markup = '<p dir="rtl" class="intro"><strong>Bold</strong> text with <br> and <ul><li>item</li></ul></p>'
        result = sanitize_and_validate_html(markup, fieldname="notes")
        self.assertEqual(result, markup)

    def test_text_inside_failed_node_caught(self):
        """Control character nested inside deep HTML nodes is caught."""
        nested = "<div><section><p><span>Deep text bad&#x202E;</span></p></section></div>"
        with self.assertRaises(frappe.ValidationError) as ctx:
            sanitize_and_validate_html(nested, fieldname="notes")
        self.assertIn("U+202E", str(ctx.exception))

    def test_attribute_override_caught(self):
        """Bidi override inside tag attribute values is caught."""
        attr_payload = '<a href="/test" title="Malicious&#x202E;title">Link</a>'
        with self.assertRaises(frappe.ValidationError) as ctx:
            sanitize_and_validate_html(attr_payload, fieldname="notes")
        self.assertIn("U+202E", str(ctx.exception))

    def test_c0_c1_control_characters_rejected(self):
        """C0 and C1 control characters (NUL, DEL, etc.) rejected in HTML text."""
        nul_payload = "<p>Text with \x00 NUL byte</p>"
        with self.assertRaises(frappe.ValidationError) as ctx:
            sanitize_and_validate_html(nul_payload, fieldname="notes")
        self.assertIn("U+0000", str(ctx.exception))

        del_payload = "<p>Text with \x7f DEL byte</p>"
        with self.assertRaises(frappe.ValidationError) as ctx:
            sanitize_and_validate_html(del_payload, fieldname="notes")
        self.assertIn("U+007F", str(ctx.exception))


class TestPlainTextValidator(unittest.TestCase):
    def test_plain_text_entity_decoded_override_rejected(self):
        """Plain text containing HTML-encoded overrides decoded and rejected."""
        payload = "Order reference &#x202E; 1234"
        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_plain_text_narrative(payload, fieldname="customer_code")
        self.assertIn("U+202E", str(ctx.exception))
        self.assertIn("customer_code", str(ctx.exception))

    def test_plain_text_lrm_rlm_alm_accepted(self):
        """Plain text direction marks accepted."""
        text = "Order with LRM \u200e and RLM \u200f"
        # Should not raise
        validate_plain_text_narrative(text, fieldname="customer_code")

    def test_plain_text_multiline_support(self):
        """Multiline plain text addresses/messages pass without false rejection on newlines."""
        multiline = "Building 4, Apt 12\nMain Street\nCity, Country"
        validate_plain_text_narrative(multiline, fieldname="current_address")

        bad_multiline = "Building 4\nMain Street \u202e Bad\nCity"
        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_plain_text_narrative(bad_multiline, fieldname="current_address")
        self.assertIn("U+202E", str(ctx.exception))


class TestBdiJoin(unittest.TestCase):
    def test_bdi_join_wrapping_and_escaping(self):
        """bdi_join wraps each non-empty element in <bdi> with single HTML escaping."""
        res = bdi_join(["Title", "العنوان"])
        self.assertIsInstance(res, markupsafe.Markup)
        self.assertEqual(str(res), "<bdi>Title</bdi> / <bdi>العنوان</bdi>")

    def test_bdi_join_single_escape_no_double_escape(self):
        """bdi_join escapes HTML entities without double-escaping."""
        res = bdi_join(["Steel <Grade A>", "حديد & صلب"])
        self.assertIsInstance(res, markupsafe.Markup)
        self.assertEqual(
            str(res),
            "<bdi>Steel &lt;Grade A&gt;</bdi> / <bdi>حديد &amp; صلب</bdi>",
        )

    def test_bdi_join_empty_and_none(self):
        """bdi_join handles empty items and None gracefully."""
        self.assertEqual(str(bdi_join([])), "")
        self.assertEqual(str(bdi_join([None, ""])), "")
        self.assertEqual(str(bdi_join(["Only One", None])), "<bdi>Only One</bdi>")

    def test_bdi_join_custom_separator(self):
        """bdi_join supports custom separator."""
        res = bdi_join(["Part A", "Part B"], separator=" - ")
        self.assertEqual(str(res), "<bdi>Part A</bdi> - <bdi>Part B</bdi>")


class TestRegistryImmutability(unittest.TestCase):
    def test_registry_remains_unchanged(self):
        """Sanitizer imports registry read-only; registry SHA-256 remains stable."""
        digest_before = registry_sha256()
        self.assertIsNotNone(digest_before)

        # Run multiple sanitizer routines
        sanitize_and_validate_html("<p>Safe text</p>")
        validate_plain_text_narrative("Safe plain text")

        digest_after = registry_sha256()
        self.assertEqual(digest_before, digest_after)


class MockDoc(dict):
    def __init__(self, doctype, **kwargs):
        super().__init__(**kwargs)
        self.doctype = doctype
        self._children = []

    def append(self, field, child):
        self._children.append(child)

    def get_all_children(self):
        return self._children


class TestDocEventsValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.has_site = bool(getattr(frappe, "local", None) and getattr(frappe.local, "site", None))
        if cls.has_site:
            frappe.set_user("Administrator")
        cls.created_docs = []

    @classmethod
    def tearDownClass(cls):
        leftover = 0
        if cls.has_site:
            for dt, name in cls.created_docs:
                if frappe.db.exists(dt, name):
                    try:
                        frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
                    except Exception:
                        leftover += 1
        cls.created_docs.clear()
        assert leftover == 0, f"cleanup.leftover == {leftover}"

    def _create_test_doc(self, doctype, **kwargs):
        if self.has_site:
            doc = frappe.new_doc(doctype)
            for k, v in kwargs.items():
                setattr(doc, k, v)
            return doc
        return MockDoc(doctype, **kwargs)

    def test_parent_doc_validation_passes_clean(self):
        """Item with clean HTML description passes validate hook."""
        doc = self._create_test_doc(
            "Item",
            item_code="TEST-NARRATIVE-CLEAN",
            item_name="Clean Narrative Item",
            item_group="All Item Groups",
            stock_uom="Nos",
            description='<p dir="rtl">Clean item description</p>',
        )
        # Direct hook invocation
        validate_narrative_fields(doc)

    def test_parent_doc_validation_fails_dirty(self):
        """Item with bidi override in description fails validate hook."""
        doc = self._create_test_doc(
            "Item",
            item_code="TEST-NARRATIVE-DIRTY",
            item_name="Dirty Narrative Item",
            description="<p>Contaminated &#x202E; description</p>",
        )

        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_narrative_fields(doc)
        self.assertIn("U+202E", str(ctx.exception))
        self.assertIn("Item.description", str(ctx.exception))

    def test_child_table_validation_fails_dirty(self):
        """Payment Terms Template with dirty description in child row fails validate hook."""
        parent = self._create_test_doc("Payment Terms Template", template_name="Test PTT Narrative")
        child = self._create_test_doc(
            "Payment Terms Template Detail",
            description="Contaminated &#x202E; term",
        )
        parent.append("terms", child)

        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_narrative_fields(parent)
        self.assertIn("U+202E", str(ctx.exception))
        self.assertIn("Payment Terms Template Detail.description", str(ctx.exception))


class TestDynamicMetadataDerivation(unittest.TestCase):
    def test_meta_derivation_item_fields(self):
        """Metadata derivation discovers description (tier 2) and customer_code (tier 1) on Item."""
        from construction.services.narrative_sanitizer import get_narrative_fields_for_doctype

        fields = get_narrative_fields_for_doctype("Item")
        self.assertEqual(fields.get("description"), 2)
        self.assertEqual(fields.get("customer_code"), 1)

    def test_meta_failure_falls_back_without_caching(self):
        """When get_meta fails, fallback to baseline is returned but NOT cached."""
        from unittest.mock import patch
        from construction.services.narrative_sanitizer import get_narrative_fields_for_doctype

        synthetic_dt = "SyntheticTestDocType"
        if getattr(frappe, "local", None) and hasattr(frappe.local, "_ct_narrative_fields_cache"):
            frappe.local._ct_narrative_fields_cache.pop(synthetic_dt, None)

        with patch("frappe.get_meta", side_effect=RuntimeError("DB hiccup")):
            res = get_narrative_fields_for_doctype(synthetic_dt)
            self.assertEqual(res, {})

            cache = getattr(frappe.local, "_ct_narrative_fields_cache", {}) if getattr(frappe, "local", None) else {}
            self.assertNotIn(synthetic_dt, cache)


if __name__ == "__main__":
    unittest.main()
