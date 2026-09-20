"""
Stage 3 tests: bilingual registry pure logic (standalone, no site).

Run with: python3 construction/tests/test_bilingual_service.py
(no Frappe import required).
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# The `construction` package imports frappe in __init__, so the pure module
# is loaded directly by path (stdlib-only) for standalone runs.
_spec = importlib.util.spec_from_file_location(
    "bilingual_registry_pure",
    ROOT / "construction" / "services" / "bilingual_registry.py",
)
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


class TestRegistryLoadAndValidate(unittest.TestCase):
    def test_real_registry_loads_clean(self):
        data, errors = br.load_registry()
        self.assertEqual(errors, [], errors)
        self.assertEqual(data["schema"], br.REGISTRY_SCHEMA)
        self.assertIn("Account", data["doctypes"])
        self.assertEqual(data["doctypes"]["Account"]["state"], "active")
        self.assertEqual(data["doctypes"]["Item"]["state"], "schema_installed")

    def test_registry_sha256_is_stable(self):
        self.assertEqual(br.registry_sha256(), br.registry_sha256())
        self.assertTrue(br.registry_sha256())

    def test_bad_state_rejected(self):
        data, _ = br.load_registry()
        data["doctypes"]["Account"]["state"] = "wild"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reg.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            _, errors = br.load_registry(path=p)
        self.assertTrue(any("registry-state" in e for e in errors), errors)

    def test_missing_fields_rejected(self):
        data, _ = br.load_registry()
        del data["doctypes"]["Account"]["arabic_field"]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reg.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            _, errors = br.load_registry(path=p)
        self.assertTrue(any("registry-field" in e for e in errors), errors)

    def test_bad_fallback_chain_rejected(self):
        data, _ = br.load_registry()
        data["display"]["ar_fallback"] = ["english", "identity"]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reg.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            _, errors = br.load_registry(path=p)
        self.assertTrue(any("registry-fallback" in e for e in errors), errors)

    def test_unknown_direction_mark_rejected(self):
        data, _ = br.load_registry()
        data["unicode_policy"]["narrative_allowed_direction_marks"] = [
            {"name": "BAD", "escape": "\\u202a", "codepoint": "U+202A"}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reg.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            _, errors = br.load_registry(path=p)
        self.assertTrue(any("registry-unicode" in e for e in errors), errors)

    def test_identity_policy_documented_in_registry(self):
        data, errors = br.load_registry()
        self.assertEqual(errors, [])
        policy = data["unicode_policy"]
        self.assertIn("LRM_U+200E", policy["identity_rejected"])
        self.assertIn("BIDI_EMBEDDING_OVERRIDE_ISOLATE_U+202A-U+202E_U+2066-U+2069", policy["narrative_rejected"])

    def test_unparseable_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reg.json"
            p.write_text("{not json", encoding="utf-8")
            data, errors = br.load_registry(path=p)
        self.assertIsNone(data)
        self.assertTrue(any("registry-parse" in e for e in errors), errors)

    def test_absent_registry_fails_closed(self):
        data, errors = br.load_registry(path=Path("/nonexistent/reg.json"))
        self.assertIsNone(data)
        self.assertTrue(any("registry-parse" in e for e in errors), errors)


class TestFallbackChains(unittest.TestCase):
    def test_arabic_chain(self):
        self.assertEqual(br.fallback_chain("ar"), ["arabic", "english", "identity"])
        self.assertEqual(br.fallback_chain("ar-EG"), ["arabic", "english", "identity"])

    def test_english_chain_is_reverse(self):
        self.assertEqual(br.fallback_chain("en"), ["english", "arabic", "identity"])

    def test_unknown_language_defaults_to_english_chain(self):
        self.assertEqual(br.fallback_chain("fr"), ["english", "arabic", "identity"])


class TestUnicodePolicy(unittest.TestCase):
    def test_plain_arabic_allowed(self):
        self.assertTrue(br.is_safe_identity_text("حساب اختبار"))

    def test_nul_rejected(self):
        self.assertFalse(br.is_safe_identity_text("bad\x00name"))

    def test_c0_controls_rejected(self):
        for ch in ("\x01", "\x1f", "\x7f", "\x85"):
            self.assertFalse(br.is_safe_identity_text("bad" + ch + "name"), repr(ch))

    def test_c1_controls_rejected(self):
        self.assertFalse(br.is_safe_identity_text("bad\x9fname"))

    def test_all_bidi_controls_rejected_in_identity(self):
        # Canonical C1: U+202A–U+202E, U+2066–U+2069, U+200E, U+200F, U+061C
        for ch in ("\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
                   "\u2066", "\u2067", "\u2068", "\u2069",
                   "\u200e", "\u200f", "\u061c"):
            self.assertFalse(br.is_safe_identity_text("\u062d\u0633\u0627\u0628" + ch), "U+%04X must be rejected" % ord(ch))

    def test_narrative_allows_documented_direction_marks(self):
        # Section 8.6 documented policy: LRM/RLM/ALM allowed in narrative
        self.assertTrue(br.is_safe_narrative_text("reason \u200e note"))
        self.assertTrue(br.is_safe_narrative_text("سبب \u200f إدخالي"))
        self.assertTrue(br.is_safe_narrative_text("\u061csabab"))

    def test_narrative_rejects_embeddings_overrides_isolates(self):
        for ch in ("\u202a", "\u202e", "\u2066", "\u2069"):
            self.assertFalse(br.is_safe_narrative_text("reason" + ch))

    def test_narrative_rejects_nul_and_controls(self):
        self.assertFalse(br.is_safe_narrative_text("bad\x00reason"))
        self.assertFalse(br.is_safe_narrative_text("bad\x1freason"))

    def test_identity_policy_stricter_than_narrative(self):
        text = "value \u200e with mark"
        self.assertFalse(br.is_safe_identity_text(text))
        self.assertTrue(br.is_safe_narrative_text(text))

    def test_none_and_non_str_rejected(self):
        self.assertFalse(br.is_safe_identity_text(None))
        self.assertFalse(br.is_safe_identity_text(5))
        self.assertFalse(br.is_safe_narrative_text(None))


class TestArabicNormalization(unittest.TestCase):
    def test_alef_variants_unify(self):
        base = br.normalize_arabic("\u0627\u062d\u0645\u062f")
        self.assertEqual(br.normalize_arabic("\u0623\u062d\u0645\u062f"), base)
        self.assertEqual(br.normalize_arabic("\u0625\u062d\u0645\u062f"), base)
        self.assertEqual(br.normalize_arabic("\u0622\u062d\u0645\u062f"), base)
        self.assertEqual(br.normalize_arabic("\u0671\u062d\u0645\u062f"), base)

    def test_tatweel_and_diacritics_stripped(self):
        diacritic = "\u0623\u064e\u062d\u0652\u0645\u064e\u062f"  # أَحْمَد
        bare = "\u0627\u062d\u0645\u062f"
        self.assertEqual(br.normalize_arabic(diacritic), bare)
        self.assertEqual(br.normalize_arabic("\u0627\u0640\u062d\u0640\u0645\u0640\u062f"), bare)

    def test_normalized_query_matches_stored_form(self):
        stored = "\u0623\u064e\u062d\u0652\u0645\u064e\u062f"  # diacritized with hamza alef
        query = "\u0627\u062d\u0645\u062f"  # bare
        self.assertEqual(br.normalize_arabic(stored), br.normalize_arabic(query))

    def test_empty_and_none(self):
        self.assertEqual(br.normalize_arabic(""), "")
        self.assertEqual(br.normalize_arabic(None), "")


class TestDisplayLabel(unittest.TestCase):
    def test_arabic_session_prefers_arabic(self):
        label, mode = br.display_label({"arabic": "عربي", "english": "Cash"}, "ar", identity="x")
        self.assertEqual((label, mode), ("عربي", "arabic"))

    def test_arabic_session_falls_back_to_english(self):
        label, mode = br.display_label({"arabic": "", "english": "Cash"}, "ar", identity="x")
        self.assertEqual((label, mode), ("Cash", "english"))

    def test_arabic_session_falls_back_to_identity(self):
        label, mode = br.display_label({"arabic": None, "english": None}, "ar", identity="1100 - Cash")
        self.assertEqual((label, mode), ("1100 - Cash", "identity"))

    def test_english_session_prefers_english_then_arabic(self):
        label, mode = br.display_label({"arabic": "عربي", "english": ""}, "en", identity="x")
        self.assertEqual((label, mode), ("عربي", "arabic"))
        label, mode = br.display_label({"arabic": "عربي", "english": "Cash"}, "en", identity="x")
        self.assertEqual((label, mode), ("Cash", "english"))

    def test_whitespace_only_values_skipped(self):
        label, mode = br.display_label({"arabic": "  ", "english": "Cash"}, "ar", identity="x")
        self.assertEqual((label, mode), ("Cash", "english"))


class TestCompleteness(unittest.TestCase):
    def test_complete(self):
        result = br.completeness({"arabic": "عربي", "english": "Cash"})
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_missing_arabic(self):
        result = br.completeness({"arabic": "", "english": "Cash"})
        self.assertFalse(result["complete"])
        self.assertIn("arabic", result["missing"])

    def test_code_included_when_required(self):
        result = br.completeness(
            {"arabic": "عربي", "english": "Cash", "code": "1100"}, required=("arabic", "english", "code")
        )
        self.assertTrue(result["complete"])
        result = br.completeness(
            {"arabic": "عربي", "english": "Cash", "code": ""}, required=("arabic", "english", "code")
        )
        self.assertFalse(result["complete"])
        self.assertIn("code", result["missing"])


class TestRelevanceRank(unittest.TestCase):
    def test_exact_beats_prefix_beats_substring(self):
        self.assertLess(
            br.relevance_rank(["CT-T3-0001"], "CT-T3-0001"),
            br.relevance_rank(["CT-T3-0002"], "CT-T3-0001"),
        )
        self.assertLess(
            br.relevance_rank(["CT-T3-x"], "CT-T3"),
            br.relevance_rank(["x-CT-T3"], "CT-T3"),
        )

    def test_empty_query_ranks_last(self):
        self.assertEqual(br.relevance_rank(["anything"], ""), 3)
        self.assertEqual(br.relevance_rank(["anything"], None), 3)

    def test_best_of_multiple_strings(self):
        self.assertEqual(br.relevance_rank(["zzz", "CT"], "CT"), 0)

    def test_case_insensitive_and_whitespace_insensitive(self):
        self.assertEqual(br.relevance_rank(["CT Bilingual Pilot"], "ct bilingual "), 1)


if __name__ == "__main__":
    unittest.main()
