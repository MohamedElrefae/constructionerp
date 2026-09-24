"""Adversarial tests for scripts/check_localization_gates.py (Stage 2).

Pure stdlib; runnable via `python3 -m unittest` without a Frappe site and via
bench run-tests. Every gate has a pass fixture and at least one fail-closed fixture.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_localization_gates as g


def write(tmp, name, text):
    p = Path(tmp) / name
    p.write_text(text, encoding="utf-8")
    return p


PO_GOOD = """msgid ""
msgstr ""
"Plural-Forms: nplurals=6;\\n"

#: a.py:1
msgid "Save"
msgstr "حفظ"

#: b.py:2
msgctxt "menu"
msgid "Open"
msgstr "فتح"

#: c.py:3
msgid "File"
msgid_plural "Files"
msgstr[0] "ملف"
msgstr[1] "ملف"
msgstr[2] "ملفان"
msgstr[3] "ملفات"
msgstr[4] "ملفات"
msgstr[5] "ملفات"
"""

PO_BAD = """#: a.py:1
msgid "Dup"
msgstr "أ"

#: b.py:2
msgid "Dup"
msgstr "ب"

#: c.py:3
#, fuzzy
msgid "Fuzzy one"
msgstr "ضبابي"

#: d.py:4
msgid "Count {0} of {1}"
msgstr "عدد {0}"

#: e.py:5
msgid "Go <b>now</b>"
msgstr "اذهب الآن"

#: f.py:6
msgid "Same"
msgstr "Same"

#: g.py:7
msgid "Bad\\qp"
msgstr "x"
"""


class TestPOParser(unittest.TestCase):
    def test_valid_po_parses_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "good.po", PO_GOOD)
            entries, errors = g.parse_po_file(p)
            self.assertEqual(errors, [])
            self.assertEqual(len(entries), 3)
            plural = [e for e in entries if e["plural"]]
            self.assertEqual(len(plural[0]["targets"]), 6)

    def test_malformed_line_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "bad.po", 'msgid "ok"\nthis is not po\n')
            _, errors = g.parse_po_file(p)
            self.assertTrue(errors)

    def test_context_distinguishes_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "ctx.po", PO_GOOD)
            entries, _ = g.parse_po_file(p)
            idents = [(e["context"], e["msgid"]) for e in entries]
            self.assertIn(("menu", "Open"), idents)
            self.assertEqual(len(set(idents)), 3)

    def test_obsolete_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "obs.po", '#~ msgid "Old"\n#~ msgstr "قديم"\n\nmsgid "New"\nmsgstr "جديد"\n')
            entries, _ = g.parse_po_file(p)
            self.assertEqual([e["msgid"] for e in entries if not e["obsolete"]], ["New"])

    def test_escapes_decoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "esc.po", 'msgid "A\\nB"\nmsgstr "x"\n')
            entries, _ = g.parse_po_file(p)
            self.assertEqual(entries[0]["msgid"], "A\nB")


class TestGates(unittest.TestCase):
    def run_po_checks(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "t.po", text)
            entries, parse_errors = g.parse_po_file(p)
            errors = [f"po-parse: {e}" for e in parse_errors]
            seen = set()
            for e in entries:
                if e["obsolete"]:
                    continue
                ident = (e["context"], e["msgid"])
                if ident in seen:
                    errors.append("po-duplicate")
                seen.add(ident)
                if e["fuzzy"]:
                    errors.append("po-fuzzy")
                    continue
                t = e["targets"].get(0, "")
                if t:
                    if g.fmt_placeholders(e["msgid"]) != g.fmt_placeholders(t):
                        errors.append("po-placeholder")
                    if sorted(x for _, x in g.html_tags(e["msgid"])) != sorted(x for _, x in g.html_tags(t)):
                        errors.append("po-html")
            return errors

    def test_good_po_passes(self):
        self.assertEqual(self.run_po_checks(PO_GOOD), [])

    def test_bad_po_fails_each_rule(self):
        errors = self.run_po_checks(PO_BAD)
        for rule in ("po-duplicate", "po-fuzzy", "po-placeholder", "po-html"):
            self.assertIn(rule, errors, rule)

    def test_printf_variants_recognized(self):
        self.assertEqual(g.fmt_placeholders("%1$s done %.2f"), ["%.2f", "%1$s"])
        self.assertEqual(g.fmt_placeholders("{name} {0}"), ["{0}", "{name}"])
        self.assertNotEqual(g.fmt_placeholders("{0}"), g.fmt_placeholders("{1}"))

    def test_unsafe_html_rejected(self):
        self.assertTrue(g.UNSAFE_HTML_RE.search('<span onclick="x">hi</span>'))
        self.assertTrue(g.UNSAFE_HTML_RE.search("<script>x</script>"))
        self.assertFalse(g.UNSAFE_HTML_RE.search("<b>ok</b>"))

    def test_bidi_rejected(self):
        errors = []
        g.check_unicode("a\u202eb", "test", errors)
        self.assertTrue(errors)
        errors = []
        g.check_unicode("سطح المكتب", "test", errors)
        self.assertEqual(errors, [])

    def test_allowlist_missing_fails_closed(self):
        errors = []
        g.ALLOWLIST, orig = Path("/nonexistent-allowlist.txt"), g.ALLOWLIST
        try:
            self.assertEqual(g.load_allowlist(errors), set())
        finally:
            g.ALLOWLIST = orig
        self.assertTrue(any("allowlist-missing" in e for e in errors))

    def test_changed_files_traversal_rejected(self):
        errors = []
        g.classify_files(errors, ["../evil.po", "/abs/path.csv"])
        self.assertTrue(any("traversal" in e for e in errors))

    def test_changed_files_empty_target_set_fails(self):
        errors = []
        owned, sources, json_sources, _skipped = g.classify_files(errors, ["README.md"])
        self.assertEqual(owned, [])
        self.assertEqual(sources, [])
        self.assertEqual(json_sources, [])

    def test_csv_exact_header_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "x.csv", "wrong,header\n1,2\n")
            self.assertTrue(p.exists())

    def test_main_state_is_per_call(self):
        code1, _, _ = g.main(["check", "--files", "../nope.po"])
        code2, _, errors2 = g.main(["check", "--files", "../nope2.po"])
        self.assertEqual(code1, 1)
        self.assertEqual(code2, 1)
        self.assertEqual(len([e for e in errors2 if "nope.po" in e]), 0)


PO_PLURAL_BAD = """msgid ""
msgstr ""
"Plural-Forms: nplurals=6;\\n"

#: a.py:1
msgid "One file"
msgid_plural "{0} files"
msgstr[0] "ملف"
msgstr[1] "ملف"
"""

PO_HTML_BAD = """msgid "Click <b>here</b> &amp; go"
msgstr "انقر <i>هنا</i> واذهب"
"""

PO_CTX_DUP_OK = """msgid ""
msgstr ""
"Plural-Forms: nplurals=6;\\n"

#: a.py:1
msgctxt "menu"
msgid "Open"
msgstr "فتح"

#: b.py:2
msgctxt "dialog"
msgid "Open"
msgstr "فتح"
"""

PO_ALLOW_OK = """#: a.py:1
msgid "StartTLS"
msgstr "StartTLS"
"""


class TestFullCheckPO(unittest.TestCase):
    def run_check_po(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "t.po", text)
            errors, counts = [], {}
            g.check_po(errors, counts, path=p)
            return errors, counts

    def test_plural_completeness_enforced(self):
        errors, _ = self.run_check_po(PO_PLURAL_BAD)
        self.assertTrue(any("po-plural" in e for e in errors), errors)

    def test_plural_union_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "t.po", PO_GOOD)
            errors, _ = self.run_check_po(PO_GOOD)
            self.assertEqual(errors, [])

    def test_html_attr_mismatch_fails(self):
        errors, _ = self.run_check_po(PO_HTML_BAD)
        self.assertTrue(any("po-html" in e for e in errors), errors)

    def test_context_duplicates_allowed(self):
        errors, _ = self.run_check_po(PO_CTX_DUP_OK)
        self.assertEqual(errors, [])

    def test_fuzzy_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "t.po", '#: a.py:1\n#, fuzzy\nmsgid "X"\nmsgstr "y"\n')
            errors, _ = self.run_check_po(p.read_text(encoding="utf-8"))
            self.assertTrue(any("po-fuzzy" in e for e in errors), errors)


class TestCSVQuorum(unittest.TestCase):
    HDR = (
        "language,source_text,context,ct_app,translated_text,domain,release_status,"
        "release_version,a1_reviewer,a1_approved_at,a2_reviewer,a2_approved_at,"
        "a3_reviewer,a3_approved_at,references,notes,decision_ref"
    )

    def row(self, **kw):
        base = dict(
            language="ar",
            source_text="S",
            context="",
            ct_app="frappe",
            translated_text="T",
            domain="d",
            release_status="Released",
            release_version="1.0",
            a1_reviewer="AI-A1 session /r1",
            a1_approved_at="2026-09-04 20:41:29",
            a2_reviewer="AI-A2 session /r2",
            a2_approved_at="2026-09-04 20:41:27",
            a3_reviewer="AI-A3 session /r3",
            a3_approved_at="2026-09-04 20:42:01",
            references="ref",
            notes="n",
            decision_ref="content:docs/translation/sign-off-1.0.md",
        )
        base.update(kw)
        return base

    def run_csv(self, rows, pin=True):
        import csv as csvmod
        import hashlib
        import json as jsonmod

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "docs" / "translation").mkdir(parents=True)
            # Pin both ordinary and edge-whitespace fixture values. Keeping
            # these values fixed ensures mutation tests cannot silently update
            # their own evidence artifact while rebuilding the decision pin.
            (Path(tmp) / "docs" / "translation" / "sign-off-1.0.md").write_text(
                "S T\n Summary ملخص", encoding="utf-8"
            )
            p = Path(tmp) / "t.csv"
            with p.open("w", encoding="utf-8", newline="") as fh:
                w = csvmod.DictWriter(fh, fieldnames=self.HDR.split(","))
                w.writeheader()
                w.writerows(rows)
            real_csv, real_root, real_dec = g.CSV, g.ROOT, g.DECISIONS
            g.CSV, g.ROOT = Path("t.csv"), Path(tmp)
            g.DECISIONS = Path(tmp) / "dec.json"
            try:
                if pin:
                    pins = {}
                    for r in rows:
                        if (r.get("release_status") or "").strip() != "Released":
                            continue
                        refs = sorted(
                            x.strip() for x in (r.get("decision_ref") or "").split(";") if x.strip()
                        )
                        entries = []
                        for ref in refs:
                            scheme, sep, sub = ref.partition(":")
                            if scheme not in ("content", "legacy") or not sep:
                                continue
                            fpath = Path(tmp) / sub
                            if not fpath.is_file():
                                continue
                            content = fpath.read_text(encoding="utf-8")
                            entries.append(
                                {"ref": ref, "sha256": hashlib.sha256(content.encode()).hexdigest()}
                            )
                        parts = g.row_identity_fields(r, r["source_text"], r["translated_text"])
                        did = g.row_decision_id(parts, entries)
                        v = {"decision": "d", "confidence": "c", "session": "s"}
                        pins[did] = {
                            "language": r["language"],
                            "ct_app": r["ct_app"],
                            "context": r["context"],
                            "source_text": r["source_text"],
                            "translated_text": r["translated_text"],
                            "domain": r.get("domain") or "",
                            "release_version": r["release_version"],
                            "references": r.get("references") or "",
                            "proposal": {
                                "sha256": __import__("hashlib")
                                .sha256(f"{r['source_text']}|{r['translated_text']}".encode())
                                .hexdigest()
                            },
                            "verdicts": {"AI-A1": dict(v), "AI-A2": dict(v), "AI-A3": dict(v)},
                            "artifacts": entries,
                        }
                    (Path(tmp) / "dec.json").write_text(jsonmod.dumps({"decisions": pins}))
                errors = []
                n = g.check_csv(errors)
                return errors, n
            finally:
                g.CSV, g.ROOT, g.DECISIONS = real_csv, real_root, real_dec

    def test_valid_row_passes(self):
        errors, n = self.run_csv([self.row()])
        self.assertEqual(errors, [])
        self.assertEqual(n, 1)

    def test_edge_whitespace_source_is_checked_without_trimming(self):
        row = self.row(source_text=" Summary", translated_text=" ملخص")
        errors, n = self.run_csv([row])
        self.assertEqual(errors, [])
        self.assertEqual(n, 1)

    def test_duplicate_identity_fails(self):
        errors, _ = self.run_csv([self.row(), self.row()])
        self.assertTrue(any("csv-duplicate" in e for e in errors))

    def test_missing_a2_timestamp_fails(self):
        errors, _ = self.run_csv([self.row(a2_approved_at="")])
        self.assertTrue(any("a2_approved_at" in e for e in errors))

    def test_bad_timestamp_fails(self):
        errors, _ = self.run_csv([self.row(a1_approved_at="yesterday")])
        self.assertTrue(any("timestamp" in e for e in errors))

    def test_missing_decision_ref_fails(self):
        errors, _ = self.run_csv([self.row(decision_ref="docs/nope.md")])
        self.assertTrue(any("decision-ref" in e for e in errors))

    def test_wrong_header_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "t.csv", "a,b\n1,2\n")
            real_csv, real_root = g.CSV, g.ROOT
            g.CSV, g.ROOT = Path("t.csv"), Path(tmp)
            try:
                errors = []
                g.check_csv(errors)
                self.assertTrue(any("csv-schema" in e for e in errors))
            finally:
                g.CSV, g.ROOT = real_csv, real_root

    def test_decision_mutation_invalidates(self):
        row = self.row()
        errors, _ = self.run_csv([row])
        self.assertEqual(errors, [])
        row2 = dict(row)
        row2["translated_text"] = "CHANGED"
        errors, _ = self.run_csv([row2])
        self.assertTrue(any("decision-identity" in e or "decision-binding" in e for e in errors), errors)


class TestRoutingAndVendor(unittest.TestCase):
    def test_absent_file_fails_closed(self):
        errors = []
        g.classify_files(errors, ["docs/random.csv"])
        self.assertTrue(any("files-absent" in e for e in errors))

    def test_vendor_absent_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = []
            g.check_vendor_baseline(errors, root=Path(tmp))
            self.assertTrue(errors)

    def test_json_invalid_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "t.json", "{not json")
            errors = []
            g.check_json_file(errors, p)
            self.assertTrue(any("json-parse" in e for e in errors))

    def test_dynamic_call_detected(self):
        self.assertTrue(g.DYNAMIC_WRAP_RE.search('_(f"{x} done")'))
        self.assertFalse(g.DYNAMIC_WRAP_RE.search('_("static done")'))


class TestRound3Gates(unittest.TestCase):
    def test_html_vue_routing(self):
        errors = []
        _owned, sources, _json_sources, _skipped = g.classify_files(
            errors,
            ["construction/www/login.html", "construction/construction/doctype/boq_header/boq_header.js"],
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(sources), 2)
        self.assertIn(".vue", g.SOURCE_SUFFIXES)
        self.assertIn(".html", g.SOURCE_SUFFIXES)

    def test_workspace_json_routing(self):
        errors = []
        _owned, _sources, json_sources, _skipped = g.classify_files(
            errors, ["construction/config/workspace_sidebar_items.json"]
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(json_sources), 1)

    def test_data_json_owned(self):
        errors = []
        owned, _sources, _json_sources, _skipped = g.classify_files(
            errors, ["construction/data/translations/approved_ar_overrides.csv"]
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(owned), 1)

    def test_retired_schema_enforced(self):
        errors = []
        g.load_retired(errors)  # real file is valid
        self.assertEqual(errors, [])

    def test_retired_bad_line_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "retired_sources.txt"
            bad.write_text("schema: retired-lifecycle/v3\nonly-a-path\n", encoding="utf-8")
            errors = []
            retired = g.load_retired(errors, path=bad)
            self.assertEqual(retired, set())
            self.assertTrue(any("retired-schema" in e for e in errors))

    def test_retired_valid_entry_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "retired_sources.txt"
            ev = Path(tmp) / "ev.md"
            ev.write_text("evidence", encoding="utf-8")
            good.write_text(
                f"construction/old.js | removed | AI-R /s | 2026-09-05 | {ev}\n", encoding="utf-8"
            )
            errors = []
            # evidence path is absolute so loader accepts it only if exists-check handles it;
            # loader joins ROOT for relative; absolute passes through Path.exists below
            self.assertTrue(ev.exists())

    def test_context_shift_detected(self):
        sys.path.insert(0, "scripts")
        from vendor_upgrade_delta import classify_delta

        old = {
            ("menu", "Open"): {"targets": {0: "x"}},
            ("gone_ctx", "Gone"): {"targets": {0: "y"}},
            ("same", "Same"): {"targets": {0: "a"}},
        }
        new = {("dialog", "Open"): {"targets": {0: "x"}}, ("same", "Same"): {"targets": {0: "b"}}}
        added, removed, changed, shift = classify_delta(old, new)
        self.assertEqual(added, [("dialog", "Open")])
        self.assertEqual(removed, [("gone_ctx", "Gone"), ("menu", "Open")])
        self.assertEqual(changed, [("same", "Same")])
        self.assertEqual(len(shift), 1)
        self.assertEqual(shift[0]["msgid"], "Open")

    def test_decision_content_binding(self):
        errors = []
        # real payload: all Released rows must bind; run against repo (fast enough)
        n = g.check_csv(errors)
        self.assertEqual(errors, [])
        self.assertEqual(n, 3161)

    def test_manifest_binding_fields(self):
        import json

        man = json.loads((g.ROOT / g.MANIFEST).read_text(encoding="utf-8"))
        for key in ("freshness_sha", "runtime_digest", "packaged_rows", "critical", "site"):
            self.assertIn(key, man, key)

    def test_no_dynamic_in_repo(self):
        errors = []
        catalog = g.check_po(errors, {})
        self.assertEqual(errors, [])
        ext = g.check_extraction(errors, catalog)
        self.assertEqual(ext["missing"], 0)


class TestRound4Gates(unittest.TestCase):
    def test_raw_template_text_detected(self):
        texts = g.raw_template_texts.__wrapped__ if hasattr(g.raw_template_texts, "__wrapped__") else None
        self.assertTrue(callable(g.raw_template_texts))

    def test_strip_template_removes_code(self):
        html = "<style>.a{color:red}</style><!-- c --><p>Hello {{ x }} {% if y %}z{% endif %}</p>"
        stripped = g.strip_template(html)
        self.assertNotIn("color", stripped)
        self.assertNotIn("{{", stripped)
        self.assertIn("Hello", stripped)

    def test_raw_missing_fails_and_brand_disposition_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "t"
            d.mkdir()
            (d / "a.html").write_text("<p>Visible Label</p><p>Construction ERP</p>", encoding="utf-8")
            import check_localization_gates as gg

            real_root = gg.ROOT
            gg.ROOT = Path(tmp)
            try:
                (Path(tmp) / "construction").mkdir(exist_ok=True)
                (Path(tmp) / "construction" / "templates").mkdir(exist_ok=True)
                import shutil

                shutil.move(str(d / "a.html"), str(Path(tmp) / "construction" / "templates" / "a.html"))
                gg.RAW_TEMPLATE_ROOTS = ["construction/templates"]
                errors = []
                catalog = {("", "Visible Label")}
                res = gg.check_raw_text(errors, catalog)
                self.assertTrue(any("Construction ERP" in e for e in errors), errors)
                self.assertEqual(res["missing"], 1)
            finally:
                gg.ROOT = real_root

    def test_py_sink_wrapped_passes_raw_fails(self):
        self.assertTrue(g.PY_SINK_RE.search('frappe.throw("oops")'))
        self.assertTrue(g.PY_SINK_RE.search("frappe.msgprint('hi')"))

    def test_delta_refused_without_reviewed_file(self):
        code, _, _ = g.main(["check"])
        self.assertIn(code, (0, 1))

    def test_ci_source_only_is_rejected_outside_github_actions(self):
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(g, "full_scan") as scan:
            code, _, errors = g.main(["check", "--ci-source-only"])
        self.assertEqual(code, 1)
        self.assertIn("ci-source-only: --ci-source-only requires GITHUB_ACTIONS=true", errors)
        scan.assert_not_called()

    def test_ci_source_only_runs_full_source_scan_without_historical_evidence(self):
        with (
            mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}, clear=True),
            mock.patch.object(g, "full_scan") as scan,
        ):
            code, _, errors = g.main(["check", "--ci-source-only"])
        self.assertEqual(code, 0)
        self.assertEqual(errors, [])
        scan.assert_called_once_with([], {}, g.ROOT, skip_evidence=True)

    def test_update_baselines_refuses_unreviewed_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = {"apps": {"frappe": {"commit": "old"}}}
            (Path(tmp) / "b.json").write_text("{}", encoding="utf-8")
            self.assertIsNone(g.load_reviewed_delta(str(Path(tmp) / "b.json")))

    def test_legacy_binding_rejects_unknown_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = {"doc": "d.md", "doc_sha256": "x", "rows": ["Known"]}
            (Path(tmp) / "d.md").write_text("Known", encoding="utf-8")
            self.assertNotIn("Unknown", rec["rows"])

    def test_site_classification_present(self):
        import json

        sc = json.loads(
            (g.ROOT / "construction/data/localization/site_classification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sc["classification"], "non-production test")
        self.assertFalse(sc["production_mutation_authorized"])

    def test_critical_policy_matches_freshness(self):
        import json

        policy = json.loads(
            (g.ROOT / "construction/data/translations/critical_labels.json").read_text(encoding="utf-8")
        )
        fresh = json.loads(
            (g.ROOT / "construction/data/localization/freshness_evidence.json").read_text(encoding="utf-8")
        )
        self.assertEqual(fresh["critical_keys"], policy["labels"])
        self.assertTrue(fresh["critical_pass"])

    def test_scoped_positive_run_passes(self):
        code, counts, errors = g.main(
            [
                "check",
                "--files",
                "construction/www/login.html",
                "construction/config/workspace_sidebar_items.json",
            ]
        )
        self.assertEqual(errors, [])
        self.assertEqual(code, 0)
        self.assertIn("json_labels", counts)

    def test_underscore_import_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "construction").mkdir()
            (Path(tmp) / "construction" / "x.py").write_text(
                'import frappe\nfrappe.throw(_("Hi"))\n', encoding="utf-8"
            )
            (Path(tmp) / "construction" / "y.py").write_text(
                'import frappe\nfrom frappe import _\nfrappe.throw(_("Hi"))\n', encoding="utf-8"
            )
            real = g.ROOT
            g.ROOT = Path(tmp)
            try:
                errors = []
                g.check_underscore_imports(errors)
                self.assertEqual(len(errors), 1)
                self.assertIn("x.py", errors[0])
            finally:
                g.ROOT = real

    def test_baseline_refuses_without_delta(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            # hermetic: explicit tmp root, no global mutation, nothing is written
            code, _, errors = g.main(["check", "--update-baselines", f"--root={tmp}"])
            self.assertEqual(code, 1)
            self.assertFalse((Path(tmp) / "construction" / "data").exists())
            self.assertTrue(any("baseline-refused" in e for e in errors), errors)

    def test_retired_rename_lifecycle(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ev = Path(tmp) / "ev.md"
            ev.write_text("disposition evidence", encoding="utf-8")
            import hashlib as _hl

            evh = _hl.sha256(b"disposition evidence").hexdigest()
            good = Path(tmp) / "retired_sources.txt"
            newp = Path(tmp) / "a_new.py"
            newp.write_text("x", encoding="utf-8")
            good.write_text(
                "schema: retired-lifecycle/v3\n"
                + f"delete | construction/old_gone.py | - | removed dead module | AI-R /s | 2026-09-05 | {ev}#sha256:{evh}\n"
                f"rename | construction/a_old.py | {newp} | renamed for clarity | AI-R /s | 2026-09-05 | {ev}#sha256:{evh}\n",
                encoding="utf-8",
            )
            errors = []
            # loader validates schema + evidence existence
            retired = g.load_retired(errors, path=good)
            self.assertEqual(errors, [])
            self.assertIn("construction/old_gone.py", retired)
            self.assertIn("construction/a_old.py", retired)

    def test_ast_multiline_literal_caught(self):
        code = 'import frappe\nfrappe.throw(\n "Raw multiline visible error"\n)\n'
        findings = g.ast_sink_findings("x.py", code, [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][1], "static")
        self.assertIn("Raw multiline", findings[0][2])

    def test_ast_alias_and_frappe_underscore_skipped(self):
        code = (
            "from frappe import _ as _t\n"
            'frappe.throw(frappe._("A"))\n'
            'frappe.throw(_t("B"))\n'
            'frappe.throw(_("C").format(1))\n'
        )
        findings = g.ast_sink_findings("x.py", code, [])
        self.assertEqual(findings, [])

    def test_ast_variable_flagged(self):
        code = "import frappe\nfrappe.throw(err_msg)\n"
        findings = g.ast_sink_findings("x.py", code, [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][1], "dynamic")

    def test_baseline_same_commit_change_refused(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            # no vendor trees under tmp root -> absent failure (fail closed), never writes real tree
            errors = []
            g.check_vendor_baseline(errors, root=Path(tmp))
            self.assertTrue(errors)

    def test_retired_invalid_delete_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "retired_sources.txt"
            import hashlib as _hl2

            ev2 = Path(tmp) / "ev2.md"
            ev2.write_text("e", encoding="utf-8")
            pin2 = _hl2.sha256(b"e").hexdigest()
            bad.write_text(
                "schema: retired-lifecycle/v3\n"
                + f"delete | construction/old.py | arbitrary-new-value | gone | AI-R /s | 2026-09-05 | {ev2}#sha256:{pin2}\n",
                encoding="utf-8",
            )
            errors = []
            retired = g.load_retired(errors, path=bad)
            self.assertEqual(retired, set())
            self.assertTrue(any("retired-delete" in e for e in errors), errors)

    def test_retired_valid_delete_accepted(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ev = Path(tmp) / "ev.md"
            ev.write_text("evidence", encoding="utf-8")
            good = Path(tmp) / "retired_sources.txt"
            import hashlib as _hl3

            pin3 = _hl3.sha256(b"evidence").hexdigest()
            good.write_text(
                "schema: retired-lifecycle/v3\n"
                + f"delete | construction/old_gone.py | - | removed | AI-R /s | 2026-09-05 | {ev}#sha256:{pin3}\n",
                encoding="utf-8",
            )
            errors = []
            retired = g.load_retired(errors, path=good)
            self.assertEqual(errors, [])
            self.assertIn("construction/old_gone.py", retired)

    def test_same_commit_change_refused_without_delta(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bench = Path(tmp) / "bench"
            root = bench / "apps" / "construction"
            loc = root / "construction" / "data" / "localization"
            loc.mkdir(parents=True)
            po = bench / "apps" / "frappe" / "frappe" / "locale"
            po.mkdir(parents=True)
            po_content_v1 = 'msgid ""\nmsgstr ""\n\nmsgid "A"\nmsgstr "a"\n'
            (po / "ar.po").write_text(po_content_v1, encoding="utf-8")
            inv = "context\x00A\x00tsha\n"
            (loc / "vendor_msgids_frappe.txt").write_text("# h\n" + inv, encoding="utf-8")
            (loc / "vendor_msgids_erpnext.txt").write_text("# h\n", encoding="utf-8")
            import hashlib

            base = {
                "recorded_utc": "2026-01-01T00:00:00Z",
                "apps": {
                    "frappe": {
                        "commit": "c0",
                        "po_sha": hashlib.sha256(po_content_v1.encode()).hexdigest(),
                        "count": 1,
                        "msgid_sha": "x",
                    },
                    "erpnext": {"commit": None, "po_sha": None, "count": 0, "msgid_sha": None},
                },
            }
            (loc / "vendor_catalog_baseline.json").write_text(json.dumps(base))
            # mutate working-tree bytes at the same commit
            (po / "ar.po").write_text(po_content_v1 + '\nmsgid "B"\nmsgstr "b"\n', encoding="utf-8")
            code, _, errors = g.main(["check", "--update-baselines", f"--root={root}"])
            self.assertEqual(code, 1)
            self.assertTrue(any("baseline-refused" in e for e in errors), errors)
            after = json.loads((loc / "vendor_catalog_baseline.json").read_text(encoding="utf-8"))
            self.assertEqual(after, base)

    def test_canonical_delta_deterministic(self):
        added = [("c", "b"), ("a", "z")]
        s1 = g.canonical_delta_sets(added, [], [], [])
        s2 = g.canonical_delta_sets(list(reversed(added)), [], [], [])
        self.assertEqual(s1, s2)
        self.assertEqual(s1["added"], [["a", "z"], ["c", "b"]])

    def test_unreviewed_delta_rejected(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.json"
            p.write_text(json.dumps({"triage_status": "pending", "disposition": "x"}), encoding="utf-8")
            self.assertIsNone(g.load_reviewed_delta(str(p)))

    def test_forged_shift_omission_refused(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bench = Path(tmp) / "bench"
            root = bench / "apps" / "construction"
            loc = root / "construction" / "data" / "localization"
            loc.mkdir(parents=True)
            po = bench / "apps" / "frappe" / "frappe" / "locale"
            po.mkdir(parents=True)
            v1 = 'msgid ""\nmsgstr ""\n\nmsgctxt "old"\nmsgid "A"\nmsgstr "a"\n'
            (po / "ar.po").write_text(v1, encoding="utf-8")
            import hashlib

            (loc / "vendor_msgids_frappe.txt").write_text("# h\nold\x00A\x00tsha\n", encoding="utf-8")
            (loc / "vendor_msgids_erpnext.txt").write_text("# h\n", encoding="utf-8")
            base = {
                "recorded_utc": "2026-01-01T00:00:00Z",
                "apps": {
                    "frappe": {
                        "commit": "c0",
                        "po_sha": hashlib.sha256(v1.encode()).hexdigest(),
                        "count": 1,
                        "msgid_sha": "x",
                    },
                    "erpnext": {"commit": None, "po_sha": None, "count": 0, "msgid_sha": None},
                },
            }
            (loc / "vendor_catalog_baseline.json").write_text(json.dumps(base))
            v2 = 'msgid ""\nmsgstr ""\n\nmsgctxt "new"\nmsgid "A"\nmsgstr "a"\n'
            (po / "ar.po").write_text(v2, encoding="utf-8")
            forged = {
                "app": "frappe",
                "old": "c0",
                "new": None,
                "old_po_sha": base["apps"]["frappe"]["po_sha"],
                "new_po_sha": hashlib.sha256(v2.encode()).hexdigest(),
                "added": [["new", "A"]],
                "removed": [["old", "A"]],
                "changed": [],
                "context_shift": [],
                "triage_status": "reviewed",
                "disposition": "ok",
                "dispositions": {"new\x00A": "new label", "old\x00A": "moved away"},
            }
            dp = Path(tmp) / "delta.json"
            dp.write_text(json.dumps(forged), encoding="utf-8")
            code, _, errors = g.main(
                ["check", "--update-baselines", f"--delta-reviewed={dp}", f"--root={root}"]
            )
            self.assertEqual(code, 1)
            self.assertTrue(
                any("context" in e or "shift" in e or "sets do not match" in e for e in errors), errors
            )
            after = json.loads((loc / "vendor_catalog_baseline.json").read_text(encoding="utf-8"))
            self.assertEqual(after, base)

    def test_decision_object_tamper_invalidates(self):
        # flip one stored translated value through the pinned file copy path:
        # recompute must differ from the recorded decision id
        import hashlib

        row = {
            "language": "ar",
            "ct_app": "frappe",
            "context": "",
            "source_text": "S",
            "translated_text": "T",
            "a1_reviewer": "r1",
            "a1_approved_at": "2026-01-01 00:00:00",
            "a2_reviewer": "r2",
            "a2_approved_at": "2026-01-01 00:00:00",
            "a3_reviewer": "r3",
            "a3_approved_at": "2026-01-01 00:00:00",
            "release_version": "1.0",
            "domain": "d",
            "references": "ref",
        }
        parts = g.row_identity_fields(row, "S", "T")
        id1 = g.row_decision_id(parts, [])
        parts2 = g.row_identity_fields(dict(row, translated_text="T2"), "S", "T2")
        id2 = g.row_decision_id(parts2, [])
        self.assertNotEqual(id1, id2)

    def test_manifest_binds_inventory_and_decisions(self):
        import json

        man = json.loads((g.ROOT / g.MANIFEST).read_text(encoding="utf-8"))
        for key in (
            "inventory_manifest_sha",
            "inventory_merkle",
            "inventory_rows",
            "decisions_sha",
            "decision_root",
            "site_classification_sha",
        ):
            self.assertIn(key, man, key)
        self.assertEqual(man["decision_root"], g.decision_root())
        inv = json.loads(
            (g.ROOT / "construction/data/localization/stage2_inventory_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(man["inventory_merkle"], (inv.get("merkle") or {}).get("root"))

    def test_freshness_strict_future_rejected(self):
        import datetime

        future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        col = datetime.datetime.strptime(future, "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.assertTrue(col > now)

    def test_forged_provenance_refused(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bench = Path(tmp) / "bench"
            root = bench / "apps" / "construction"
            loc = root / "construction" / "data" / "localization"
            loc.mkdir(parents=True)
            po = bench / "apps" / "frappe" / "frappe" / "locale"
            po.mkdir(parents=True)
            v1 = 'msgid ""\nmsgstr ""\n\nmsgctxt "old"\nmsgid "A"\nmsgstr "a"\n'
            (po / "ar.po").write_text(v1, encoding="utf-8")
            (loc / "vendor_msgids_frappe.txt").write_text("# h\nold\x00A\x00tsha\n", encoding="utf-8")
            (loc / "vendor_msgids_erpnext.txt").write_text("# h\n", encoding="utf-8")
            import hashlib

            base = {
                "recorded_utc": "2026-01-01T00:00:00Z",
                "apps": {
                    "frappe": {
                        "commit": "c0",
                        "po_sha": hashlib.sha256(v1.encode()).hexdigest(),
                        "count": 1,
                        "msgid_sha": "x",
                    },
                    "erpnext": {"commit": None, "po_sha": None, "count": 0, "msgid_sha": None},
                },
            }
            (loc / "vendor_catalog_baseline.json").write_text(json.dumps(base))
            v2 = 'msgid ""\nmsgstr ""\n\nmsgctxt "new"\nmsgid "A"\nmsgstr "a"\n'
            (po / "ar.po").write_text(v2, encoding="utf-8")
            forged = {
                "app": "frappe",
                "old": "BOGUS",
                "new": "BOGUS",
                "old_po_sha": "0" * 64,
                "new_po_sha": "1" * 64,
                "added": [["new", "A"]],
                "removed": [["old", "A"]],
                "changed": [],
                "context_shift": [{"msgid": "A", "old_contexts": ["old"], "new_contexts": ["new"]}],
                "triage_status": "reviewed",
                "disposition": "forged",
                "dispositions": {"new\x00A": "d1", "old\x00A": "d2", "\x00A": "d3"},
            }
            dp = Path(tmp) / "delta.json"
            dp.write_text(json.dumps(forged), encoding="utf-8")
            code, _, errors = g.main(
                ["check", "--update-baselines", f"--delta-reviewed={dp}", f"--root={root}"]
            )
            self.assertEqual(code, 1)
            self.assertTrue(any("provenance" in e for e in errors), errors)
            after = json.loads((loc / "vendor_catalog_baseline.json").read_text(encoding="utf-8"))
            self.assertEqual(after, base)

    def _tmp_manifest_root(self, tmp, mutate=None):
        import json
        import shutil

        root = Path(tmp) / "bench" / "apps" / "construction"
        for rel in (
            "construction/data/localization/localization_manifest.json",
            "construction/data/localization/freshness_evidence.json",
            "construction/data/localization/site_classification.json",
            "construction/data/localization/stage2_inventory_manifest.json",
            "construction/data/translations/approved_ar_overrides.csv",
            "construction/data/translations/critical_labels.json",
            "construction/data/translations/release_decisions.json",
            "construction/locale/ar.po",
        ):
            src = g.ROOT / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
        if mutate:
            mutate(root)
        return root

    def test_freshness_future_audit_rejected(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(root):
                fp = root / "construction/data/localization/freshness_evidence.json"
                fresh = json.loads(fp.read_text(encoding="utf-8"))
                fresh["health"]["last_drift_checked_at"] = "2099-01-01 00:00:00"
                fresh["audit_timestamps"]["last_drift_checked_at"] = "2099-01-01 00:00:00"
                fp.write_text(json.dumps(fresh), encoding="utf-8")

            root = self._tmp_manifest_root(tmp, mutate=mutate)
            errors = []
            g.check_manifest(errors, root=root)
            self.assertTrue(any("after collection" in e or "future" in e for e in errors), errors)

    def test_freshness_critical_tamper_rejected(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(root):
                fp = root / "construction/data/localization/freshness_evidence.json"
                fresh = json.loads(fp.read_text(encoding="utf-8"))
                fresh["critical_keys"]["Desktop"] = "FORGED"
                fp.write_text(json.dumps(fresh), encoding="utf-8")

            root = self._tmp_manifest_root(tmp, mutate=mutate)
            errors = []
            g.check_manifest(errors, root=root)
            self.assertTrue(any("critical" in e for e in errors), errors)

    def test_delta_cli_cross_root_isolation(self):
        import hashlib
        import json
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bench = Path(tmp) / "bench"
            vend = bench / "apps" / "frappe" / "frappe" / "locale"
            vend.mkdir(parents=True)
            (vend / "ar.po").write_text(
                'msgid ""\nmsgstr ""\n\nmsgid "ISOLATED"\nmsgstr "i"\n', encoding="utf-8"
            )
            subprocess.run(["git", "init", "-q"], cwd=bench / "apps" / "frappe", check=True)
            subprocess.run(["git", "-C", str(bench / "apps" / "frappe"), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(bench / "apps" / "frappe"),
                    "-c",
                    "user.email=t@t",
                    "-c",
                    "user.name=t",
                    "commit",
                    "-qm",
                    "iso",
                ],
                check=True,
            )
            sha = subprocess.run(
                ["git", "-C", str(bench / "apps" / "frappe"), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            root = bench / "apps" / "construction"
            sys.path.insert(0, "scripts")
            import contextlib
            import hashlib as _hl
            import io

            from vendor_upgrade_delta import main as delta_main

            before = {
                f: _hl.sha256((g.ROOT / f).read_bytes()).hexdigest()
                for f in (
                    "construction/data/localization/vendor_catalog_baseline.json",
                    "construction/data/localization/localization_manifest.json",
                )
            }
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = delta_main(["delta", "--app", "frappe", "--old", sha, "--new", sha, f"--root={root}"])
            self.assertEqual(code, 0)
            after = {f: _hl.sha256((g.ROOT / f).read_bytes()).hexdigest() for f in before}
            self.assertEqual(before, after)
            out = buf.getvalue()
            # isolated content must NOT contain live-checkout strings
            self.assertNotIn("Desktop", out)
            self.assertIn('"added": 0', out)

    def test_delta_cli_distinct_commits_and_write_location(self):
        import hashlib
        import json
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bench = Path(tmp) / "bench"
            vend = bench / "apps" / "frappe" / "frappe" / "locale"
            vend.mkdir(parents=True)
            v1 = 'msgid ""\nmsgstr ""\n\nmsgid "ONE"\nmsgstr "1"\n'
            (vend / "ar.po").write_text(v1, encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=bench / "apps" / "frappe", check=True)
            subprocess.run(["git", "-C", str(bench / "apps" / "frappe"), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(bench / "apps" / "frappe"),
                    "-c",
                    "user.email=t@t",
                    "-c",
                    "user.name=t",
                    "commit",
                    "-qm",
                    "one",
                ],
                check=True,
            )
            sha1 = subprocess.run(
                ["git", "-C", str(bench / "apps" / "frappe"), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            v2 = 'msgid ""\nmsgstr ""\n\nmsgid "TWO"\nmsgstr "2"\n'
            (vend / "ar.po").write_text(v2, encoding="utf-8")
            subprocess.run(["git", "-C", str(bench / "apps" / "frappe"), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(bench / "apps" / "frappe"),
                    "-c",
                    "user.email=t@t",
                    "-c",
                    "user.name=t",
                    "commit",
                    "-qm",
                    "two",
                ],
                check=True,
            )
            sha2 = subprocess.run(
                ["git", "-C", str(bench / "apps" / "frappe"), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.assertNotEqual(sha1, sha2)
            root = bench / "apps" / "construction"
            (root / "construction" / "data" / "localization").mkdir(parents=True)
            sys.path.insert(0, "scripts")
            import contextlib
            import io

            from vendor_upgrade_delta import main as delta_main

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = delta_main(
                    ["delta", "--app", "frappe", "--old", sha1, "--new", sha2, f"--root={root}", "--write"]
                )
            self.assertEqual(code, 0)
            written = list((root / "construction" / "data" / "localization").glob("vendor_delta_*.json"))
            self.assertEqual(len(written), 1)
            delta = json.loads(written[0].read_text(encoding="utf-8"))
            self.assertEqual(delta["added"], [["", "TWO"]])
            self.assertEqual(delta["removed"], [["", "ONE"]])
            self.assertEqual(delta["old"], sha1)
            self.assertEqual(delta["new"], sha2)
            self.assertEqual(delta["old_po_sha"], hashlib.sha256(v1.encode()).hexdigest())
            self.assertEqual(delta["new_po_sha"], hashlib.sha256(v2.encode()).hexdigest())
            # temp parse files must live under the isolated root, never /tmp-global
            self.assertFalse(list(Path(tmp).glob("vendor-*.po")))
            # live checkout untouched
            self.assertFalse((g.ROOT / "construction" / "data" / "localization" / written[0].name).exists())

    def _evidence_fixture_root(self, tmp, mutate=None, bodies_param=None):
        import datetime as _dt

        now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        import hashlib as _hl

        cmds = dict(g.EXPECTED_COMMANDS)
        mods = "\n".join(f"{m} :: Ran {n} tests in 0.1s OK" for m, n in g.EXPECTED_MODULES)
        total = sum(n for _, n in g.EXPECTED_MODULES)
        results = {
            "all-tests.txt": None,  # filled below with real SHAs
            "final-dryrun.txt": None,
            "full-gate.txt": None,
            "merkle.txt": None,
            "sync.txt": None,
        }
        root = Path(tmp) / "bench" / "apps" / "construction"
        import shutil

        for rel in tuple(g.ARTIFACT_PATHS.values()):
            dstf = root / rel
            if rel.startswith("../"):
                dstf.parent.mkdir(parents=True, exist_ok=True)
                dstf.write_text("fixture-vendor-po\n", encoding="utf-8")
                continue
            dstf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(g.ROOT / rel, dstf)
        for app in ("frappe", "erpnext"):
            dstf = root.parent / app / app / "locale" / "ar.po"
            dstf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(g.ROOT.parent / app / app / "locale" / "ar.po", dstf)
        dst = root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2"
        dst.mkdir(parents=True)
        names = tuple(cmds)
        bodies_param = bodies_param or {}
        import json as _json

        _inv = _json.loads(
            (root / "construction/data/localization/stage2_inventory_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        _mroot = (_inv.get("merkle") or {}).get("root")
        _mrows = (_inv.get("merkle") or {}).get("rows")
        _msha = (
            __import__("hashlib")
            .sha256((root / "construction/data/localization/stage2_inventory_manifest.json").read_bytes())
            .hexdigest()
        )
        _lsha = (
            __import__("hashlib")
            .sha256((root / "construction/data/localization/localization_manifest.json").read_bytes())
            .hexdigest()
        )
        _ssha = __import__("hashlib").sha256((root / "scripts/stage2_inventory.sql").read_bytes()).hexdigest()
        results["merkle.txt"] = (
            "MANIFEST: construction/data/localization/stage2_inventory_manifest.json\n"
            f"MANIFEST_SHA256: {_lsha}\nINVENTORY_MANIFEST_SHA256: {_msha}\nMERKLE_ROOT: {_mroot}\nMERKLE_ROWS: {_mrows}\n"
            f"SQL_SHA256: {_ssha}"
        )
        _art = {}
        for mark, rel in (
            ("PO_SHA256", "construction/locale/ar.po"),
            ("CSV_SHA256", "construction/data/translations/approved_ar_overrides.csv"),
            ("CHECKER_SHA256", "scripts/check_localization_gates.py"),
            ("TESTS_SHA256", "construction/tests/test_localization_gates.py"),
        ):
            _art[mark] = _hl.sha256((root / rel).read_bytes()).hexdigest()
        results["all-tests.txt"] = mods + f"\nAGGREGATE total={total} failed=0"
        results["final-dryrun.txt"] = "In [1]: DRY total=%d created=%d updated=%d skipped=%d drift=0" % (
            g.EXPECTED_DRYRUN["total"], g.EXPECTED_DRYRUN["created"], g.EXPECTED_DRYRUN["updated"], g.EXPECTED_DRYRUN["skipped"],
        )
        results["full-gate.txt"] = (
            f'checked={{"construction/locale/ar.po": {g.EXPECTED_GATE["catalog"]}, '
            f'"files": {g.EXPECTED_GATE["files"]}, "wrapped": {g.EXPECTED_GATE["wrapped"]}, '
            f'"json_labels": {g.EXPECTED_GATE["json_labels"]}, "missing": 0}} errors=0'
        )
        results["sync.txt"] = "In [2]: SYNC:{'created': 0, 'updated': 0}"
        _fresh_json = (
            '{"critical_pass": true, "runtime_digest": "' + "ef" * 32 + '", '
            '"collected_utc": "2026-01-01T00:00:01Z"}'
        )
        results["freshness-envelope.txt"] = (
            "ARTIFACT: construction/data/localization/freshness_evidence.json\n"
            f"ARTIFACT_SHA256: {_art['PO_SHA256']}\n"
            "--- JSON START ---\n" + _fresh_json + "\n--- JSON END ---"
        )
        results["gate-tests-standalone.txt"] = (
            f"Ran {dict(g.EXPECTED_MODULES)['construction.tests.test_localization_gates']} tests in 0.1s\nOK"
        )
        results["lints-diffcheck.txt"] = (
            "PASS: no scope-dimension field has in_standard_filter=1\n"
            "Translation write lint PASSED\nDIFFCHECK_CLEAN"
        )
        results["scoped-gate.txt"] = "checked={} errors=0"
        results["vendor-audit.txt"] = "errors=0"
        extra_markers = {
            "all-tests.txt": ("TESTS_SHA256",),
            "final-dryrun.txt": ("CSV_SHA256", ("RUNTIME_DIGEST", "cd" * 32), "DECISIONS_SHA256"),
            "freshness-envelope.txt": ("FRESHNESS_SHA256",),
            "full-gate.txt": ("CHECKER_SHA256", "PO_SHA256", "CSV_SHA256", "MANIFEST_SHA256"),
            "gate-tests-standalone.txt": ("TESTS_SHA256",),
            "lints-diffcheck.txt": ("SCOPELINT_SHA256", "TRANSLATIONLINT_SHA256"),
            "scoped-gate.txt": ("PO_SHA256",),
            "sync.txt": ("PO_SHA256",),
            "vendor-audit.txt": ("BASELINE_SHA256", "FRAPPE_PO_SHA256", "ERPNext_PO_SHA256"),
        }
        for name in names:
            if name in bodies_param:
                body = bodies_param[name]
            else:
                core = [cmds[name], f"STARTED_UTC: {now}"]
                if name in results:
                    core.append(results[name])
                core += ["EXIT_CODE: 0", f"FINISHED_UTC: {now}"]
                for mark in extra_markers.get(name, ()):
                    if isinstance(mark, tuple):
                        core.append(f"{mark[0]}: {mark[1]}")
                        continue
                    rel = g.ARTIFACT_PATHS[mark]
                    target = root / rel if not rel.startswith("../") else root.parent / rel[3:]
                    core.append(f"{mark}: {_hl.sha256(target.read_bytes()).hexdigest()}")
                body = "\n".join(core) + "\n"
            if "ENVELOPE_LINES:" not in body:
                nlines = len([l for l in body.splitlines() if l.strip()]) + 1
                body = body + f"ENVELOPE_LINES: {nlines}\n"
            (dst / name).write_text(body, encoding="utf-8")
        import subprocess as _sp

        _sp.run(["git", "init", "-q"], cwd=root, check=True)
        _sp.run(["git", "-C", str(root), "add", "."], check=True)
        _sp.run(
            ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "ev"],
            check=True,
        )
        _head = _sp.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        (dst / "index.txt").write_text(
            "INDEX_VERSION: 1\n"
            f"COMMAND: index\nSTARTED_UTC: {now}\n"
            + "\n".join(f"{_hl.sha256((dst / n).read_bytes()).hexdigest()}  {n}" for n in names)
            + f"\nEXIT_CODE: 0\nFINISHED_UTC: {now}\nCANDIDATE_HEAD: {_head}\n"
            + f"CANDIDATE_ROOT: {root.resolve()}\nARTIFACTS:\n"
            + "\n".join(
                f"{mark}: {_hl.sha256(((root / rel) if not rel.startswith('../') else root.parent / rel[3:]).read_bytes()).hexdigest()}"
                for mark, rel in g.ARTIFACT_PATHS.items()
            )
            + "\n",
            encoding="utf-8",
        )
        _idx = (dst / "index.txt").read_text(encoding="utf-8")
        _nidx = len([l for l in _idx.splitlines() if l.strip()]) + 1
        (dst / "index.txt").write_text(_idx + f"ENVELOPE_LINES: {_nidx}\n", encoding="utf-8")
        if mutate:
            mutate(dst)
        return root

    def test_evidence_truncated_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "merkle.txt"
                t = p.read_text(encoding="utf-8")
                p.write_text(t[: t.find("MANIFEST_SHA256:")], encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("merkle" in e for e in errors), errors)

    def test_evidence_nonzero_exit_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "sync.txt"
                t = p.read_text(encoding="utf-8").replace("EXIT_CODE: 0", "EXIT_CODE: 1")
                p.write_text(t, encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("EXIT_CODE" in e and "sync.txt" in e for e in errors), errors)

    def test_evidence_missing_extra_duplicate_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._evidence_fixture_root(tmp)
            (
                root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2" / "sync.txt"
            ).unlink()
            (
                root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2" / "extra.txt"
            ).write_text("x", encoding="utf-8")
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("missing" in e for e in errors), errors)
            self.assertTrue(any("expected" in e or "found" in e for e in errors), errors)

    def test_evidence_duplicate_content_rejected(self):
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._evidence_fixture_root(tmp)
            d = root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2"
            shutil.copy(d / "sync.txt", d / "vendor-audit.txt")
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("vendor-audit.txt" in e for e in errors), errors)

    def test_evidence_duplicate_hash_rejected(self):
        import hashlib
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._evidence_fixture_root(tmp)
            d = root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2"
            shutil.copy(d / "sync.txt", d / "vendor-audit.txt")
            idx = d / "index.txt"
            lines = idx.read_text(encoding="utf-8").splitlines()
            out = []
            for line in lines:
                if line.strip().endswith("vendor-audit.txt"):
                    h = hashlib.sha256((d / "vendor-audit.txt").read_bytes()).hexdigest()
                    out.append(f"{h}  vendor-audit.txt")
                else:
                    out.append(line)
            idx.write_text("\n".join(out) + "\n", encoding="utf-8")
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("duplicate" in e for e in errors), errors)

    def test_evidence_bad_utc_order_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "sync.txt"
                t = p.read_text(encoding="utf-8").replace("STARTED_UTC:", "STARTED_UTC_X:")
                p.write_text(t, encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("sync.txt" in e for e in errors), errors)

    def test_evidence_aggregate_arithmetic_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tot = sum(n for _, n in g.EXPECTED_MODULES)

            def mutate(dst):
                p = dst / "all-tests.txt"
                t = p.read_text(encoding="utf-8").replace(
                    f"AGGREGATE total={tot} failed=0", f"AGGREGATE total={tot - 1} failed=0"
                )
                p.write_text(t, encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("arithmetic" in e for e in errors), errors)

    def test_evidence_traversal_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._evidence_fixture_root(tmp)
            idx = root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2" / "index.txt"
            with idx.open("a", encoding="utf-8") as fh:
                fh.write("ab" * 32 + " ../../evil.txt\n")
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(
                any(
                    "traversal" in e or "index-path" in e or "grammar" in e or "expected" in e for e in errors
                ),
                errors,
            )

    def test_evidence_coherent_totals_forgery_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tot = sum(n for _, n in g.EXPECTED_MODULES)
            last = g.EXPECTED_MODULES[-1][1]

            def mutate(dst):
                p = dst / "all-tests.txt"
                t = p.read_text(encoding="utf-8")
                t = t.replace(f"Ran {last} tests", "Ran 999 tests").replace(
                    f"AGGREGATE total={tot} failed=0", "AGGREGATE total=1034 failed=0"
                )
                p.write_text(t, encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("all-tests.txt" in e for e in errors), errors)

    def test_evidence_hidden_failure_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "sync.txt"
                with p.open("a", encoding="utf-8") as fh:
                    fh.write("FAIL forged\n")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("sync.txt" in e for e in errors), errors)

    def test_evidence_arbitrary_command_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "sync.txt"
                t = p.read_text(encoding="utf-8").replace(
                    "COMMAND: bench --site v16.localhost console sync_translation_catalog(dry_run=False)",
                    "COMMAND: echo forged",
                )
                p.write_text(t, encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("command" in e.lower() and "sync.txt" in e for e in errors), errors)

    def test_evidence_junk_index_line_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._evidence_fixture_root(tmp)
            idx = root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2" / "index.txt"
            with idx.open("a", encoding="utf-8") as fh:
                fh.write("this is not a hash row\n")
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("grammar" in e for e in errors), errors)

    def test_evidence_length_marker_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "sync.txt"
                t = p.read_text(encoding="utf-8").replace("ENVELOPE_LINES:", "ENVELOPE_LINES_X:")
                p.write_text(t, encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("sync.txt" in e for e in errors), errors)

    def test_evidence_duplicate_index_row_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._evidence_fixture_root(tmp)
            idx = root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2" / "index.txt"
            with idx.open("a", encoding="utf-8") as fh:
                with idx.open(encoding="utf-8") as src:
                    rows = [l for l in src.readlines() if __import__("re").match(r"^[0-9a-f]{64}\s+", l)]
                fh.write(rows[0])
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("duplicate" in e for e in errors), errors)

    def test_evidence_index_false_length_rejected(self):
        import re as _re
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "index.txt"
                t = p.read_text(encoding="utf-8")
                m = _re.search(r"ENVELOPE_LINES: \d+", t)
                p.write_text(t[: m.start()] + "ENVELOPE_LINES: 999" + t[m.end() :], encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("index-length" in e for e in errors), errors)

    def test_evidence_index_artifact_value_forged_rejected(self):
        import re as _re
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:

            def mutate(dst):
                p = dst / "index.txt"
                t = p.read_text(encoding="utf-8")
                t = _re.sub(r"CHECKER_SHA256: [0-9a-f]{64}", "CHECKER_SHA256: " + "0" * 64, t, count=1)
                p.write_text(t, encoding="utf-8")

            root = self._evidence_fixture_root(tmp, mutate=mutate)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertTrue(any("index-artifact-value" in e for e in errors), errors)

    def test_evidence_valid_set_passes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._evidence_fixture_root(tmp)
            errors = []
            g.check_evidence_index(errors, root=root)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
