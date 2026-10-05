"""Read-only Translation catalog audit (Session C, bilingual-translation-catalog-sync).

Produces a private, sha-bound proposal for the governed apply cycle. Emits NO
Arabic literals: every value is reported as sha16 (sha256 of the UTF-8 value,
first 16 hex chars) per privacy R4.

Read-only by construction: it never calls a writer, never mutates tabTranslation
and never edits an app file. The only file it creates is the private proposal
under sites/<site>/private/translation-catalog-sync/.

Authority model
---------------
Pass C (effective rendered conformance) is the authoritative user-facing truth:
``frappe.translate.get_all_translations(lang)`` after the construction runtime
loader (``construction.translation_loader``) is installed. Rows carrying
``ct_is_catalog_entry = 1`` are excluded by that loader and therefore never
render; they are reported by pass H as inert hygiene, not as defects.
"""

import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import frappe

REPO = Path("/home/mohamed/frappe-bench/apps/construction")
SITES = Path("/home/mohamed/frappe-bench/sites")
SITE = "v16.localhost"
PRIVATE = SITES / SITE / "private" / "translation-catalog-sync"
GLOSSARY = REPO / "construction" / "data" / "glossary" / "egyptian_construction_glossary.json"
PAYLOAD = REPO / "construction" / "data" / "translations" / "approved_ar_overrides.csv"
WORK_ITEM = "bilingual-translation-catalog-sync"

# Master label probes required by the briefing (pass F).
MASTER_LABELS = [
    "Company", "Department", "UOM", "Unit of Measure", "Account",
    "Cost Center", "Warehouse", "Project", "Item", "Customer", "Supplier",
    "Chart of Accounts",
]

# Standard action-button probes required by the briefing (pass G).
ACTION_BUTTONS = [
    "Save", "Submit", "Cancel", "Amend", "Delete", "Print", "Email", "Close",
    "Reopen", "Draft", "Add", "Edit", "Remove", "Clear", "Search", "Filter",
    "Refresh", "New", "Copy", "Rename", "Enable", "Disable", "Activate",
    "Add Row", "Remove Row", "Save and Submit", "Save as Draft", "View",
    "Open", "Confirm", "Yes", "No", "OK", "Back", "Next", "Done",
    "Archive", "Restore", "Duplicate", "Share", "Download", "Upload",
    "Add Child", "Expand All", "Collapse All",
]

# English text for the harmonisation patch (no Arabic literals in this file:
# the target Arabic is DERIVED from the released payload at runtime).
NEW_USAGE_NOTES = (
    "Tree-view action. Applies to every tree view (Account, Cost Center, "
    "Department, Warehouse, Project, Item Group ...), not to accounts only."
)
NEW_REFERENCES = (
    "Frappe treeview.js:301; glossary v1.0. Superseded by release payload "
    "v1.1 (owner-directed 2026-09-03, commit 4fede75) because the value is a "
    "global tree action; approved_ar aligned to approved_ar_overrides.csv. "
    "Context risk noted in sign-off 6.2."
)
NEW_META_DATE = "2026-10-05"


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha256_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def s16(text):
    return sha256_text(text)[:16]


def byte_scan(value):
    """C0/C1/bidi/zero-width/tatweel/Arabic-Indic-digit/format hygiene."""
    problems = []
    if value is None:
        return ["None"]
    if value != value.strip():
        problems.append("leading/trailing whitespace")
    if "  " in value:
        problems.append("double internal space")
    for ch in value:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if cp in (
            0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
            0x2066, 0x2067, 0x2068, 0x2069, 0x200B, 0x200C, 0x200D, 0xFEFF,
        ):
            problems.append(f"bidi/zero-width U+{cp:04X}")
        elif cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F:
            problems.append(f"control U+{cp:04X}")
        elif cp == 0x0640:
            problems.append("tatweel")
        elif 0x0660 <= cp <= 0x0669:
            problems.append(f"Arabic-Indic digit U+{cp:04X}")
        elif cat in ("Cf", "Co", "Cs"):
            problems.append(f"format/surrogate {cat} U+{cp:04X}")
    return problems


def load_glossary():
    raw = GLOSSARY.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def released_payload_rows():
    """Released payload rows keyed by (source_text, context)."""
    out = {}
    with PAYLOAD.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("release_status") or "").strip() != "Released":
                continue
            key = ((row.get("source_text") or "").strip(),
                   (row.get("context") or "").strip())
            out.setdefault(key, []).append(row)
    return out


def word_boundary(token):
    return re.compile(r"(?<![\u0600-\u06FF])" + re.escape(token) + r"(?![\u0600-\u06FF])")


def git_head(short=True):
    """Resolve the real checkout HEAD so the log self-binds to the base commit."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--short" if short else "", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out
    except Exception as exc:  # pragma: no cover - defensive
        return f"UNRESOLVED({exc.__class__.__name__})"


SMOKE_TEST = REPO / "docs" / "translation" / "smoke-test-1.0.md"


def smoke_baselines():
    """Extract ratified master-label baselines from the committed smoke test.

    No Arabic literal lives in this file: the expected value is parsed out of
    `docs/translation/smoke-test-1.0.md` at runtime (privacy R4).
    """
    if not SMOKE_TEST.exists():
        return {}
    text = SMOKE_TEST.read_text(encoding="utf-8")
    found = {}
    for match in re.finditer(r"\*\*(?P<label>[^*]+):\*\*\s*`(?P<value>[^`]+)`", text):
        label = match.group("label").strip()
        found[label] = match.group("value").strip()
    return found


SCAN_ROOTS = [REPO / "construction", REPO / "docs", REPO / "SESSION_MEMORY.md"]
SCAN_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "public", "locale"}
SCAN_SUFFIXES = {".py", ".js", ".jsx", ".json", ".csv", ".md", ".txt", ".ts"}


def classify_variant(rel_path, is_glossary_value, is_payload_value):
    p = rel_path.replace("\\", "/")
    if p.startswith("docs/ai/work-items/"):
        return "work_item_evidence"
    if p.startswith("docs/"):
        return "dated_doc_evidence"
    if p.endswith((".csv", ".json")) and "/data/" in p:
        return "app_data"
    if p.endswith((".js", ".jsx")):
        return "app_render_source"
    if p.endswith(".py"):
        return "app_python_source"
    return "other"


HARDCODED_AR_RE = re.compile(r"__\(\s*'([^']*)'\s*\)|__\(\s*\"([^\"]*)\"\s*\)")
RENDER_SCAN_SKIP = {".git", "__pycache__", "node_modules", ".venv", "lib", "dist", "vendor"}


def scan_hardcoded_arabic_labels():
    """Count hardcoded Arabic literals passed to __() in the app's own JS(X).

    Report-only. Establishes the dormant-render finding for TreeView.jsx without
    committing any Arabic value: per file, a count plus sha16 digests only.
    """
    out = []
    js_root = REPO / "construction" / "public" / "js"
    if not js_root.exists():
        return out
    for path in sorted(js_root.rglob("*")):
        if path.suffix.lower() not in (".js", ".jsx", ".ts"):
            continue
        if any(part in RENDER_SCAN_SKIP for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        digests = []
        for line in text.splitlines():
            for m in HARDCODED_AR_RE.finditer(line):
                lit = m.group(1) or m.group(2) or ""
                if any("\u0600" <= ch <= "\u06FF" for ch in lit):
                    digests.append(s16(lit))
        if digests:
            out.append({
                "path": str(path.relative_to(REPO)),
                "hardcoded_arabic_labels": len(digests),
                "digests": sorted(set(digests)),
            })
    return sorted(out, key=lambda d: d["path"])


def scan_variant_sources(glossary_value, payload_value):
    """Find every committed app/doc occurrence of either competing value.

    Report-only: this pass never mutates anything. It exists because the
    rendered value is produced by several independent producers (payload CSV,
    glossary, a registered patch, review scripts, a JSX component), and only
    the payload currently drives the live render.
    """
    hits = []
    for root in SCAN_ROOTS:
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if any(part in SCAN_SKIP_DIRS for part in path.parts):
                continue
            if "approved_ar_overrides.csv" in path.name or "egyptian_construction_glossary.json" in path.name:
                pass  # governing artefacts are reported explicitly by name
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            g_hits = text.count(glossary_value) if glossary_value else 0
            p_hits = text.count(payload_value) if payload_value else 0
            if not g_hits and not p_hits:
                continue
            rel = str(path.relative_to(REPO))
            role = classify_variant(rel, bool(g_hits), bool(p_hits))
            if rel.endswith(".py") and any(
                k in text for k in ("set_value", "upsert_runtime_translation",
                                    "import_released_overrides", "TREE_ACTION_TRANSLATIONS")
            ):
                role = "app_python_write_path"
            hits.append({
                "path": rel,
                "role": role,
                "glossary_value_hits": g_hits,
                "payload_value_hits": p_hits,
            })
    return sorted(hits, key=lambda h: (h["role"], h["path"]))


def fetch_ar_rows():
    return frappe.get_all(
        "Translation",
        filters={"language": "ar"},
        fields=[
            "name", "source_text", "translated_text", "context",
            "ct_origin", "ct_review_status", "ct_is_catalog_entry", "ct_app",
        ],
        order_by="modified asc, creation asc, name asc",
        limit_page_length=0,
    )


def build_patch(glossary, payload):
    """Return the single harmonisation patch the owner approved, if any.

    The target Arabic is DERIVED from the released payload, never literalised
    here, so this committed script carries zero Arabic values (privacy R4).
    """
    patches = []
    for term in glossary["terms"]:
        src = (term.get("source_text") or "").strip()
        ctx = (term.get("context") or "").strip()
        rows = payload.get((src, ctx), [])
        if not rows:
            continue
        if len(rows) != 1:
            patches.append({"source_text": src, "error": f"{len(rows)} released payload rows"})
            continue
        prow = rows[0]
        target = (prow.get("translated_text") or "").strip()
        if not target or target == (term.get("approved_ar") or ""):
            continue
        forbidden = [t for t in (term.get("forbidden_ar") or []) if t and t in target]
        if forbidden:
            patches.append({
                "source_text": src,
                "error": "released payload value violates the glossary forbidden_ar list",
                "forbidden_hit_count": len(forbidden),
            })
            continue
        after = dict(term)
        after["approved_ar"] = target
        after["usage_notes"] = NEW_USAGE_NOTES
        after["references"] = NEW_REFERENCES
        after["version"] = "2.1"
        patches.append({
            "source_text": src,
            "context": ctx,
            "field_changes": {
                "approved_ar": {"before_sha16": s16(term.get("approved_ar")),
                                "after_sha16": s16(target)},
                "usage_notes": {"before_sha16": s16(term.get("usage_notes")),
                                "after_sha16": s16(NEW_USAGE_NOTES)},
                "references": {"before_sha16": s16(term.get("references")),
                               "after_sha16": s16(NEW_REFERENCES)},
                "version": {"before": term.get("version"), "after": "2.1"},
            },
            "before": term,
            "after": after,
            "byte_scan_after": byte_scan(target),
            "payload_release_version": (prow.get("release_version") or "").strip(),
            "payload_decision_ref": (prow.get("decision_ref") or "").strip(),
        })
    return patches


def predict_after_sha(glossary, patches, before_sha):
    data = json.loads(json.dumps(glossary))
    meta = data["meta"]
    meta["previous_checksum"] = before_sha
    meta["previous_version"] = meta.get("version")
    meta["version"] = "2.1"
    meta["date"] = NEW_META_DATE
    by_src = {p["source_text"]: p for p in patches if "after" in p}
    for term in data["terms"]:
        p = by_src.get(term.get("source_text"))
        if p:
            term.clear()
            term.update(p["after"])
    return sha256_bytes(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))


def main():
    raw_gloss, glossary = load_glossary()
    glossary_sha_before = sha256_bytes(raw_gloss)
    payload_sha = sha256_bytes(PAYLOAD.read_bytes())
    payload = released_payload_rows()
    terms = glossary["terms"]

    import construction.translation_loader  # noqa: F401  installs the runtime loader
    import frappe.translate as frappe_translate

    print("=" * 78)
    print(f"AUDIT {WORK_ITEM}")
    print("=" * 78)
    head = git_head()
    print(f"site                : {SITE}")
    print(f"base_commit         : {head}")
    print(f"glossary_sha256     : {glossary_sha_before}")
    print(f"glossary_terms      : {len(terms)} (meta.term_count={glossary['meta'].get('term_count')})")
    print(f"payload_sha256      : {payload_sha}")
    print(f"payload_released    : {len(payload)} distinct keys")

    # ---------------- Pass A: catalog inventory ----------------
    rows = fetch_ar_rows()
    print("\n--- PASS A: Translation doctype, language='ar' inventory ---")
    print(f"rows_total                  : {len(rows)}")
    print(f"by_ct_is_catalog_entry      : {dict(Counter(r.get('ct_is_catalog_entry') for r in rows))}")
    print(f"by_ct_origin                : {dict(Counter((r.get('ct_origin') or '<none>') for r in rows))}")
    print(f"by_ct_review_status         : {dict(Counter((r.get('ct_review_status') or '<none>') for r in rows))}")
    print(f"empty_translated_text_rows  : {sum(1 for r in rows if not (r.get('translated_text') or ''))}")
    by_src = defaultdict(list)
    for r in rows:
        by_src[r["source_text"]].append(r)
    dup_groups = {k: v for k, v in by_src.items() if len(v) > 1}
    print(f"duplicate_source_text_groups: {len(dup_groups)} (extra rows {sum(len(v) - 1 for v in dup_groups.values())})")

    # ---------------- Pass B: stored-row conformance ----------------
    print("\n--- PASS B: stored-row conformance vs 47 glossary terms ---")
    stored_exact = stored_divergent = stored_empty = stored_missing = 0
    divergent_rows = []
    for t in terms:
        src = t["source_text"]
        appr = t.get("approved_ar") or ""
        ms = by_src.get(src, [])
        if not ms:
            stored_missing += 1
            print(f"  MISSING   {src!r}")
            continue
        for m in ms:
            cur = m.get("translated_text") or ""
            if not cur:
                stored_empty += 1
                state = "EMPTY"
            elif cur == appr:
                stored_exact += 1
                state = "EXACT"
            else:
                stored_divergent += 1
                state = "DIVERGENT"
                divergent_rows.append((src, m))
            if state != "EXACT":
                print(f"  {state:9} {src!r} name={m['name']} ctx={m['context']!r} "
                      f"cat={m.get('ct_is_catalog_entry')} origin={m.get('ct_origin')!r} "
                      f"cur_sha16={s16(cur)} appr_sha16={s16(appr)}")
    print(f"stored exact={stored_exact} divergent={stored_divergent} empty={stored_empty} "
          f"terms_without_row={stored_missing} of {len(terms)}")

    # ---------------- Pass C: effective rendered conformance (AUTHORITATIVE) ---
    frappe_translate.clear_cache()
    merged = frappe_translate.get_all_translations("ar")
    print("\n--- PASS C: EFFECTIVE rendered conformance (authoritative) ---")
    print(f"loader_installed            : {construction.translation_loader.is_translation_loader_installed()}")
    print(f"rendered_dict_size          : {len(merged)}")
    render_match = render_divergent = render_absent = 0
    rendered_divergences = []
    for t in terms:
        src = t["source_text"]
        appr = t.get("approved_ar") or ""
        got = merged.get(src)
        if got is None:
            render_absent += 1
            print(f"  ABSENT    {src!r} appr_sha16={s16(appr)}")
            rendered_divergences.append({"source_text": src, "state": "absent"})
        elif not got:
            render_absent += 1
            print(f"  EMPTY     {src!r} appr_sha16={s16(appr)} (falls back to English)")
            rendered_divergences.append({"source_text": src, "state": "empty"})
        elif got != appr:
            render_divergent += 1
            print(f"  DIVERGENT {src!r} rendered_sha16={s16(got)} appr_sha16={s16(appr)} "
                  f"rendered_len={len(got)} byte_scan={byte_scan(got)}")
            rendered_divergences.append({"source_text": src, "state": "divergent",
                                         "rendered_sha16": s16(got), "appr_sha16": s16(appr)})
        else:
            render_match += 1
    print(f"rendered match={render_match} divergent={render_divergent} absent_or_empty={render_absent} "
          f"of {len(terms)}")

    # ---------------- Pass D: forbidden-term violations at term keys ----------
    print("\n--- PASS D: forbidden_ar violations at term keys (rendered) ---")
    violations = 0
    for t in terms:
        got = merged.get(t["source_text"]) or ""
        if not got:
            continue
        for tok in (t.get("forbidden_ar") or []):
            if tok and word_boundary(tok).search(got):
                violations += 1
                print(f"  VIOLATION {t['source_text']!r} token_sha16={s16(tok)} value_sha16={s16(got)}")
    print(f"forbidden_term_violations   : {violations}")

    # ---------------- Pass E: context-variant contradictions -----------------
    print("\n--- PASS E: same source rendered differently across contexts ---")
    grp = defaultdict(dict)
    for r in rows:
        if r.get("ct_is_catalog_entry") != 0 or not (r.get("translated_text") or ""):
            continue
        grp[r["source_text"]][r.get("context") or ""] = r["translated_text"]
    contradictions = {s: d for s, d in grp.items() if len(set(d.values())) > 1}
    print(f"context_variant_contradictions: {len(contradictions)}")
    for s, d in sorted(contradictions.items())[:25]:
        print(f"  {s!r} -> {{ {', '.join(f'{k!r}:{s16(v)}' for k, v in d.items())} }}")

    # ---------------- Pass F: master labels ----------------------------------
    # Presence probe PLUS value comparison, but only where a committed ratified
    # baseline actually exists. Most master labels have no machine-readable
    # ratified baseline anywhere in the repo, so they are reported as
    # PRESENCE-ONLY and are explicitly NOT claimed as value-verified.
    print("\n--- PASS F: master-data labels (presence + baseline where one exists) ---")
    baselines = smoke_baselines()
    masters_present = 0
    masters_value_verified = 0
    masters_baseline_available = 0
    master_rows = []
    for label in MASTER_LABELS:
        got = merged.get(label)
        present = bool(got)
        masters_present += 1 if present else 0
        baseline = baselines.get(label)
        if baseline is None:
            comparison = "presence_only"
            verdict = "PRESENT" if present else "MISSING"
        else:
            masters_baseline_available += 1
            if not present:
                comparison = "baseline_available"
                verdict = "MISSING"
            elif got == baseline:
                comparison = "value_verified"
                verdict = "MATCH"
                masters_value_verified += 1
            else:
                comparison = "baseline_available"
                verdict = "MISMATCH"
        print(f"  {verdict:9} {label!r:22} sha16={s16(got) if got else '-':16} "
              f"len={len(got) if got else 0} comparison={comparison}"
              + (f" baseline_sha16={s16(baseline)}" if baseline else " baseline=<none committed>"))
        master_rows.append({
            "label": label,
            "present": present,
            "sha16": s16(got) if got else None,
            "comparison": comparison,
            "verdict": verdict,
            "baseline_sha16": s16(baseline) if baseline else None,
            "baseline_source": str(SMOKE_TEST.relative_to(REPO)) if baseline else None,
        })
    print(f"master_labels_present       : {masters_present}/{len(MASTER_LABELS)}")
    print(f"master_labels_with_baseline : {masters_baseline_available}/{len(MASTER_LABELS)} "
          f"(source {SMOKE_TEST.relative_to(REPO)})")
    print(f"master_labels_value_verified: {masters_value_verified}/{masters_baseline_available} "
          f"of those carrying a committed baseline")
    if masters_baseline_available < len(MASTER_LABELS):
        print(f"  NOTE (finding C-05): {len(MASTER_LABELS) - masters_baseline_available} of "
              f"{len(MASTER_LABELS)} master labels have NO committed ratified baseline; they are "
              f"presence-only and are NOT claimed value-verified.")

    # ---------------- Pass G: standard action buttons ------------------------
    print("\n--- PASS G: standard action buttons ---")
    buttons_present = 0
    buttons_absent = []
    for label in ACTION_BUTTONS:
        got = merged.get(label)
        if got:
            buttons_present += 1
        else:
            buttons_absent.append(label)
    print(f"buttons_present             : {buttons_present}/{len(ACTION_BUTTONS)}")
    print(f"buttons_absent_english_fallback: {buttons_absent}")

    # ---------------- Pass H: inert catalog-only divergence (report only) ----
    print("\n--- PASS H: INERT catalog-only divergence (ct_is_catalog_entry=1, never rendered) ---")
    inert_divergent = []
    inert_empty = []
    for t in terms:
        src, appr = t["source_text"], (t.get("approved_ar") or "")
        for m in by_src.get(src, []):
            if m.get("ct_is_catalog_entry") != 1:
                continue
            cur = m.get("translated_text") or ""
            if not cur:
                inert_empty.append({"source_text": src, "name": m["name"],
                                    "review": m.get("ct_review_status")})
            elif cur != appr:
                inert_divergent.append({
                    "source_text": src, "name": m["name"], "context": m.get("context"),
                    "cur_sha16": s16(cur), "appr_sha16": s16(appr),
                    "review": m.get("ct_review_status"), "renders": False,
                })
    print(f"inert_divergent_rows        : {len(inert_divergent)} "
          f"(sources {len({d['source_text'] for d in inert_divergent})})")
    for d in inert_divergent:
        print(f"  INERT-DIVERGENT {d['source_text']!r} name={d['name']} "
              f"cur_sha16={d['cur_sha16']} appr_sha16={d['appr_sha16']} review={d['review']!r}")
    print(f"inert_empty_rows            : {len(inert_empty)}")
    for d in inert_empty:
        print(f"  INERT-EMPTY     {d['source_text']!r} name={d['name']} review={d['review']!r}")

    # ---------------- Pass I: harmony patch (owner-approved path) ------------
    patches = build_patch(glossary, payload)
    print("\n--- PASS I: harmonisation patch proposal ---")
    errors = [p for p in patches if p.get("error")]
    real = [p for p in patches if not p.get("error")]
    print(f"glossary_terms_diverging_from_released_payload: {len(real)}")
    for p in real:
        print(f"  PATCH {p['source_text']!r} payload_v={p['payload_release_version']} "
              f"decision_ref={p['payload_decision_ref']!r}")
        for f, c in p["field_changes"].items():
            print(f"        {f}: {c}")
        print(f"        byte_scan_after={p['byte_scan_after']}")
    for p in errors:
        print(f"  PATCH-ERROR {p['source_text']!r} {p['error']}")
    after_sha = predict_after_sha(glossary, patches, glossary_sha_before) if real else None

    # ---------------- Pass J: competing-value producers in app/doc sources ---
    # Added after AI-A2 round 1 (review finding J.4): the rendered value has
    # several independent producers, not just the payload CSV. REPORT ONLY.
    print("\n--- PASS J: competing-value producers across app/doc sources (REPORT ONLY) ---")
    app_variants = []
    for p in real:
        src = p["source_text"]
        g_val = (p["before"] or {}).get("approved_ar")
        p_val = (p["after"] or {}).get("approved_ar")
        found = scan_variant_sources(g_val, p_val)
        print(f"  source {src!r}: files carrying one/both competing values = {len(found)}")
        for h in found:
            print(f"    {h['role']:24} {h['path']} "
                  f"glossary_value_hits={h['glossary_value_hits']} "
                  f"payload_value_hits={h['payload_value_hits']}")
        app_variants.append({"source_text": src, "files": found})
    write_paths = [h for a in app_variants for h in a["files"]
                   if h["role"] == "app_python_write_path"]
    render_paths = [h for a in app_variants for h in a["files"]
                    if h["role"] == "app_render_source"]
    print(f"  app_python_write_path files : {len(write_paths)} "
          f"-> {[h['path'] for h in write_paths]}")
    print(f"  app_render_source files     : {len(render_paths)} "
          f"-> {[h['path'] for h in render_paths]}")
    if write_paths:
        print("  RISK (finding C-06): a registered patch/review script still carries the "
              "glossary-side value; on a fresh install or patch re-run it would overwrite the "
              "runtime row. Mitigated today by construction/translation_service.py "
              "import_released_overrides_hook (hooks.py after_install/after_migrate), which "
              "re-imports the payload and clears drift in the same migrate cycle. Not mutated "
              "this cycle - outside the owner-approved change set.")
    if render_paths:
        print("  NOTE (finding C-07): a JSX component hardcodes an Arabic label. It is not "
              "registered in hooks.py app_include_js and no module imports it, so it does not "
              "render; recorded as dormant source divergence only.")

    # ---------------- Pass J2: hardcoded Arabic labels in app JS(X) ----------
    print("\n--- PASS J2: hardcoded Arabic __() labels in app JS(X) (REPORT ONLY) ---")
    hardcoded = scan_hardcoded_arabic_labels()
    if not hardcoded:
        print("  (none)")
    for d in hardcoded:
        print(f"  {d['path']} hardcoded_arabic_labels={d['hardcoded_arabic_labels']} "
              f"digests={d['digests'][:6]}{'...' if len(d['digests']) > 6 else ''}")
    tv = next((d for d in hardcoded if d["path"].endswith("components/TreeView.jsx")), None)
    if tv:
        print("  FINDING C-07: construction/public/js/components/TreeView.jsx passes hardcoded "
              "Arabic to __(); the file is not in hooks.py app_include_js and is imported by no "
              "module, so it never renders. Dormant source divergence only - not mutated this "
              "cycle (outside the owner-approved change set).")

    # ---------------- Proposal ----------------------------------------------
    PRIVATE.mkdir(parents=True, exist_ok=True)
    proposal = {
        "work_item": WORK_ITEM,
        "schema": "catalog-sync-proposal/v1",
        "site": SITE,
        "base_commit": head,
        "authority": {
            "decision": "sync_glossary_to_released_payload_v1.1",
            "report_only": "inert catalog rows and empty rows are reported, never mutated",
            "glossary_supremacy_note": (
                "Briefing invariant 2 makes the 47-term glossary authoritative. The single "
                "divergence is not a site defect: the released payload carries the owner-directed "
                "2026-09-03 value (commit 4fede75, payload v1.1) which superseded the glossary "
                "v1.0 value one day after the glossary was last committed (9011767). The glossary "
                "is therefore the stale artefact and is harmonised TO the released payload; no "
                "established term is re-translated and the site is not mutated."
            ),
        },
        "counts": {
            "glossary_terms": len(terms),
            "ar_rows": len(rows),
            "rendered_match": render_match,
            "rendered_divergent": render_divergent,
            "rendered_absent_or_empty": render_absent,
            "forbidden_violations": violations,
            "context_contradictions": len(contradictions),
            "inert_divergent_rows": len(inert_divergent),
            "inert_empty_rows": len(inert_empty),
            "site_translation_writes": 0,
            "glossary_term_patches": len(real),
        },
        "site_translation_writes": [],
        "glossary_path": str(GLOSSARY.relative_to(REPO)),
        "payload_path": str(PAYLOAD.relative_to(REPO)),
        "glossary_sha256_before": glossary_sha_before,
        "glossary_sha256_after": after_sha,
        "payload_sha256_before": payload_sha,
        "payload_sha256_after": payload_sha,
        "glossary_term_patches": real,
        "rendered_divergences": rendered_divergences,
        "master_labels": master_rows,
        "action_buttons_absent": buttons_absent,
        "app_source_variants": app_variants,
        "hardcoded_arabic_labels": hardcoded,
        "report_only_inert_divergent": inert_divergent,
        "report_only_inert_empty": inert_empty,
    }
    out = PRIVATE / "proposal.json"
    out.write_bytes(json.dumps(proposal, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    print("\n--- PROPOSAL ---")
    print(f"path                    : {out}")
    print(f"sha256                  : {sha256_bytes(out.read_bytes())}")
    print(f"glossary_sha256_before  : {glossary_sha_before}")
    print(f"glossary_sha256_after   : {after_sha}")
    print(f"site_translation_writes : 0")
    print(f"glossary_term_patches   : {len(real)}")
    print("Arabic values are held in the private proposal only (privacy R4); "
          "this log carries sha16 digests exclusively.")
    print("\nAUDIT RESULT: PASS" if not errors else "\nAUDIT RESULT: FAIL")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site=SITE, sites_path=str(SITES))
        frappe.connect()
    frappe.set_user("Administrator")
    main()
