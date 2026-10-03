"""Tests for transactional link resolution sidecar.

Validates construction/services/transaction_link_search.py against the design
stipulated in docs/ai/work-items/transactional-link-resolution/RFC.md and SCOPE.md.

Covers:
- Server-authoritative allow-list validation (rejecting unregistered doctypes like Journal Entry)
- Client filter sanitization and link-field collision prevention
- Empty/whitespace query recency fast-path
- Assertion of the RFC §4.2 `txt=""` correctness trap on Arabic queries
- Latin/ASCII query passthrough and native search fields derivation
- End-to-end Arabic query resolution and bilingual label enrichment
- The four directional properties (no phantoms, bounded recall, native agreement, determinism)
- Invariant preservation across the triad
"""

import re
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.desk.search import search_link

from construction.services.transaction_link_search import (
    TOP_K_MASTER_MATCHES,
    TRANSACTION_LINK_CONFIG,
    _contains_arabic,
    _native_search_fields,
    _resolve_master_ids,
    _sanitize_client_filters,
    search_transactions,
    seed_required_targets,
)


class TestAllowListValidation(unittest.TestCase):
    def test_unregistered_doctype_returns_empty(self):
        """Unregistered doctypes (including Journal Entry per D2) return empty list."""
        for dt in ["Journal Entry", "Item", "User", "Role", "NonExistentDocType", "", None]:
            res = search_transactions(dt, txt="anything")
            self.assertEqual(res, [], f"Expected empty list for unregistered doctype: {dt}")

    def test_registered_doctypes_accepted(self):
        """All 7 registered targets exist and declare required keys."""
        expected_targets = {
            "Sales Order",
            "Sales Invoice",
            "Material Request",
            "Purchase Order",
            "Purchase Invoice",
            "Purchase Receipt",
            "Stock Entry",
        }
        self.assertEqual(set(TRANSACTION_LINK_CONFIG.keys()), expected_targets)
        for dt, cfg in TRANSACTION_LINK_CONFIG.items():
            self.assertIn("link_field", cfg)
            self.assertIn("master_doctype", cfg)

    def test_seed_required_targets(self):
        """Purchase Order is identified as requiring seed data before verification."""
        self.assertEqual(seed_required_targets(), ["Purchase Order"])


class TestClientFilterSanitization(unittest.TestCase):
    def test_meta_and_link_field_stripped(self):
        """Client-supplied structural keys and the link field itself are stripped."""
        raw = {
            "doctype": "HACK",
            "search_fields": ["evil"],
            "display_format": "{evil}",
            "searchfield": "name",
            "query": "evil.query",
            "customer": "EVIL_CUSTOMER",
            "company": "Valid Company",
            "status": "Draft",
        }
        sanitized = _sanitize_client_filters(raw, link_field="customer")
        self.assertNotIn("doctype", sanitized)
        self.assertNotIn("search_fields", sanitized)
        self.assertNotIn("display_format", sanitized)
        self.assertNotIn("searchfield", sanitized)
        self.assertNotIn("query", sanitized)
        self.assertNotIn("customer", sanitized)
        self.assertEqual(sanitized.get("company"), "Valid Company")
        self.assertEqual(sanitized.get("status"), "Draft")

    def test_json_string_filters_parsed_and_sanitized(self):
        """JSON-formatted string filter inputs are parsed and sanitized cleanly."""
        raw_json = '{"customer": "COLLISION", "status": "Submitted"}'
        sanitized = _sanitize_client_filters(raw_json, link_field="customer")
        self.assertNotIn("customer", sanitized)
        self.assertEqual(sanitized.get("status"), "Submitted")


class TestEmptyAndLatinQueries(unittest.TestCase):
    def test_empty_txt_bypasses_preresolution(self):
        """Empty txt returns recent orders without executing pre-resolution."""
        res = search_transactions("Sales Order", txt="", page_length=5)
        self.assertTrue(len(res) > 0)
        self.assertIn("value", res[0])

    def test_whitespace_txt_bypasses_preresolution(self):
        """Whitespace txt is treated identically to empty txt."""
        res = search_transactions("Sales Order", txt="   ", page_length=5)
        self.assertTrue(len(res) > 0)

    def test_native_search_fields_derivation(self):
        """Search fields include name and doctype title/search fields."""
        fields = _native_search_fields("Sales Order")
        self.assertIn("name", fields)
        self.assertIn("customer", fields)
        self.assertIn("customer_name", fields)

    def test_latin_query_passthrough(self):
        """Latin query matches existing sales orders by naming series or fields."""
        res = search_transactions("Sales Order", txt="_T-Sales Order-0000", page_length=5)
        self.assertTrue(len(res) > 0)
        for row in res:
            self.assertTrue(row["value"].startswith("_T-Sales Order-"))


class TestTxtCorrectnessTrap(unittest.TestCase):
    def test_txt_trap_asserted_downstream_receives_empty_txt(self):
        """RFC §4.2: Downstream call to searchable_link_search receives txt='' on Arabic queries."""
        calls = []

        import construction.services.transaction_link_search as mod
        real_func = mod.searchable_link_search

        def mock_search(doctype, txt="", **kwargs):
            calls.append({"doctype": doctype, "txt": txt, "kwargs": kwargs})
            if doctype == "Customer":
                return [{"value": "_Test Customer", "label": "_Test Customer"}]
            return real_func(doctype=doctype, txt=txt, **kwargs)

        with patch.object(mod, "searchable_link_search", side_effect=mock_search):
            res = mod.search_transactions("Sales Order", txt="عميل", page_length=5)

            # Master leg received the Arabic query
            master_calls = [c for c in calls if c["doctype"] == "Customer"]
            self.assertTrue(len(master_calls) >= 1)
            self.assertEqual(master_calls[0]["txt"], "عميل")

            # Transaction leg MUST have received txt="" to avoid the naming-series trap
            tx_calls = [c for c in calls if c["doctype"] == "Sales Order"]
            self.assertTrue(len(tx_calls) >= 1)
            self.assertEqual(tx_calls[0]["txt"], "", "TRAP TRIGGERED: Transaction call received non-empty txt!")
            self.assertIn("customer", tx_calls[0]["kwargs"].get("filters", {}))


class TestSeededArabicEndToEnd(unittest.TestCase):
    def test_arabic_search_matches_and_enriches_labels(self):
        """Seeded Arabic customer enables searching transactions and enriches labels."""
        so = frappe.get_all("Sales Order", fields=["name", "customer"], limit=1)
        self.assertTrue(so, "Sales Order records required for test")
        cust_name = so[0].customer
        cust = frappe.get_doc("Customer", cust_name)
        orig_ar = cust.customer_name_in_arabic
        test_ar = "العميل الهندسي للاختبار"

        try:
            cust.customer_name_in_arabic = test_ar
            cust.save()
            frappe.db.commit()

            res = search_transactions("Sales Order", txt="الهندسي", page_length=10)
            self.assertTrue(len(res) > 0, "Arabic query should match orders for the customer")

            matched_values = [r["value"] for r in res]
            self.assertIn(so[0].name, matched_values)

            # Check label enrichment
            matched_row = next(r for r in res if r["value"] == so[0].name)
            self.assertIn(test_ar, matched_row["label"])
            self.assertEqual(matched_row["description"], test_ar)
        finally:
            clean = frappe.get_doc("Customer", cust_name)
            clean.customer_name_in_arabic = orig_ar
            clean.save()
            frappe.db.commit()

    def test_unmatched_arabic_returns_no_phantoms(self):
        """Arabic query that matches no master yields empty results (RFC §7.1 Property 1)."""
        res = search_transactions("Sales Order", txt="نص_عربي_غير_موجود_قطعا_في_البيانات")
        self.assertEqual(res, [])


class TestDirectionalProperties(unittest.TestCase):
    def test_property_2_bounded_recall(self):
        """RFC §7.1 Property 2: Result count is bounded by page_length and TOP_K."""
        res = search_transactions("Sales Order", txt="", page_length=7)
        self.assertTrue(len(res) <= 7)
        self.assertTrue(len(res) <= TOP_K_MASTER_MATCHES)

    def test_property_3_native_agreement_on_latin_vocabulary(self):
        """RFC §7.1 Property 3: Governed search agrees with native search on Latin naming series."""
        query = "_T-Sales Order-0000"
        governed = search_transactions("Sales Order", txt=query, page_length=10)
        native = search_link("Sales Order", txt=query, page_length=10)

        gov_names = {r["value"] for r in (governed or [])}
        nat_names = {r["value"] for r in (native or [])}

        # Shared matches within page length window
        self.assertTrue(len(gov_names & nat_names) > 0)

    def test_property_4_determinism(self):
        """RFC §7.1 Property 4: Consecutive identical queries return identical results."""
        res1 = search_transactions("Sales Order", txt="_T-Sales Order-0000", page_length=10)
        res2 = search_transactions("Sales Order", txt="_T-Sales Order-0000", page_length=10)
        self.assertEqual(res1, res2)


class TestTriadInvariantGuard(unittest.TestCase):
    def test_triad_remains_unmodified(self):
        """Assert zero diff lines on the invariant triad across reference commits."""
        commits = [
            "38beb35d31026e0afc70dd43e0ccf8de7dc1a222",
            "cbc8d5b",
            "46aa201",
            "0f5be0d",
            "87e88cd",
            "a7086ef",
            "2f74193",
        ]
        files = [
            "construction/services/bilingual_service.py",
            "construction/searchable_dropdown/api/search.py",
            "construction/data/bilingual/bilingual_registry.json",
        ]
        import os
        repo_dir = Path(__file__).resolve().parents[2]
        for c in commits:
            for f in files:
                diff = subprocess.check_output(
                    ["git", "diff", c, "--", f], cwd=repo_dir
                ).decode()
                self.assertFalse(diff.strip(), f"Invariant diff found vs {c} on {f}")


class TestTopKBoundary(unittest.TestCase):
    def test_preresolution_requests_and_caps_at_top_k(self):
        """RFC §7.2: pre-resolution requests exactly TOP_K and never returns more."""
        import construction.services.transaction_link_search as mod

        seen = {}

        def fake_search(*, doctype, txt, page_length=None, **kwargs):
            seen[doctype] = page_length
            return [{"value": f"CUST-{i:04d}"} for i in range(TOP_K_MASTER_MATCHES + 5)]

        with patch.object(mod, "searchable_link_search", side_effect=fake_search):
            ids = mod._resolve_master_ids("Customer", "عميل")

        self.assertEqual(seen.get("Customer"), TOP_K_MASTER_MATCHES)
        self.assertEqual(len(ids), TOP_K_MASTER_MATCHES, "Over-returning callee not capped")


class TestClientServerAllowListDrift(unittest.TestCase):
    def test_js_transactional_targets_match_server_config(self):
        """The client routing list must equal the server-authoritative allow-list."""
        repo_dir = Path(__file__).resolve().parents[2]
        src = (
            repo_dir / "construction/public/js/searchable_dropdown/searchable_dropdown.js"
        ).read_text(encoding="utf-8")
        match = re.search(r"const transactionalTargets\s*=\s*\[(.*?)\]", src, re.S)
        self.assertIsNotNone(match, "transactionalTargets array not found in JS")
        js_targets = set(re.findall(r'"([^"]+)"', match.group(1)))
        self.assertEqual(
            js_targets,
            set(TRANSACTION_LINK_CONFIG),
            "JS routing list drifted from TRANSACTION_LINK_CONFIG",
        )


if __name__ == "__main__":
    unittest.main()
