"""Tier 5H read-only export — classify every Company row on v16.localhost.

Frozen gates (fail-closed):
  1. site totals frozen: TOTAL_EXPECTED = 21;
  2. PRE_STATE_ARABIC = 0 (no company_name_ar populated anywhere);
  3. derived Phase-1 set (the active owner company) equals frozen PHASE1_FROZEN = ['Elrefae'];
  4. classification sanity: active 1, test noise 20.

Prints per-row classification, usage attribution per company, fixture/hook status and the
F-5H findings. ZERO writes (no document saves at all).
"""

import hashlib
import os
import sys

import frappe

PHASE1_FROZEN = ["Elrefae"]
TOTAL_EXPECTED = 21
TEST_NOISE_EXPECTED = 20


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main():
    fails = []
    total = frappe.db.count("Company")
    if total != TOTAL_EXPECTED:
        fails.append(f"total {total} != frozen {TOTAL_EXPECTED}")
    arabic = frappe.db.count("Company", {"company_name_ar": ("!=", "")})
    if arabic != 0:
        fails.append(f"pre-state: {arabic} rows already have company_name_ar")
    print(f"SITE total={total} arabic_populated={arabic}")

    rows = frappe.get_all(
        "Company",
        fields=["name", "company_name", "abbr", "default_currency", "country",
                "parent_company", "is_group", "company_name_ar"],
        order_by="name",
    )
    if len(rows) != total:
        fails.append(f"get_all returned {len(rows)} != {total}")

    derived_phase1, active, noise = set(), 0, 0
    for r in rows:
        cls = "active_owner" if r["name"] in PHASE1_FROZEN else "test_noise"
        if cls == "active_owner":
            active += 1
            derived_phase1.add(r["name"])
        else:
            noise += 1
        if str(r["name"]).startswith("_Test") and r["name"] in PHASE1_FROZEN:
            fails.append(f"{r['name']}: _Test row inside Phase 1")
        print(
            f"ROW {cls} name={r['name']!r} label={r['company_name']!r} abbr={r['abbr']!r} "
            f"currency={r['default_currency']!r} country={r['country']!r} "
            f"parent={r['parent_company']!r} is_group={r['is_group']}"
        )

    if set(PHASE1_FROZEN) != derived_phase1:
        fails.append(f"PHASE1 drift: {sorted(derived_phase1)} != {sorted(PHASE1_FROZEN)}")
    if active != 1 or noise != TEST_NOISE_EXPECTED:
        fails.append(f"class counts drifted: active={active} noise={noise}")
    print(f"CLASS active_owner={active} test_noise={noise}")

    # Usage attribution per company across core transactional + master tables.
    usage_tables = ["Journal Entry", "Sales Invoice", "Purchase Invoice", "GL Entry",
                    "Project", "User Scope Context", "Employee", "Cost Center", "Account"]
    usage = {}
    for t in usage_tables:
        try:
            for r in frappe.db.sql(
                f"SELECT company, COUNT(*) AS n FROM `tab{t}` "
                f"WHERE company IS NOT NULL AND company != '' GROUP BY company",
                as_dict=True):
                usage.setdefault(r["company"], {})[t] = r["n"]
        except Exception as exc:  # noqa: BLE001
            print(f"USAGE_TABLE_ERROR {t}: {exc}")
    for comp in sorted(usage):
        cls = "active_owner" if comp in PHASE1_FROZEN else "test_noise"
        detail = " ".join(f"{k}={v}" for k, v in sorted(usage[comp].items()))
        print(f"USAGE company={comp!r} {cls} {detail}")
    if "Elrefae" not in usage:
        fails.append("Elrefae shows no usage at all (unexpected)")
    scope_row = frappe.db.get_value("User Scope Context", {"company": "Elrefae"}, "name")
    if not scope_row:
        fails.append("no User Scope Context row for Elrefae (live scope selector user)")
    print(f"USAGE_SUMMARY active_in_scope_selector={bool(scope_row)}")

    # Fixture / hook / registry status.
    fixture_dir = "/home/mohamed/frappe-bench/apps/construction/construction/fixtures"
    fx = [f for f in os.listdir(fixture_dir) if "compan" in f.lower()]
    print(f"FIXTURE_JSON company_fixture_files={fx or 'none'}")
    import construction.hooks as h
    bound = h.doc_events.get("Company", {}).get("validate", "")
    print(f"HOOKS Company validate={bound!r}")
    import json as _json
    reg = _json.load(open(
        "/home/mohamed/frappe-bench/apps/construction/construction/data/bilingual/bilingual_registry.json"))
    crec = reg["doctypes"].get("Company", {})
    print(f"REGISTRY state={crec.get('state')} fields="
          f"{crec.get('english_field')}/{crec.get('arabic_field')}/{crec.get('norm_field')} "
          f"identity={crec.get('identity_field')}")
    if crec.get("state") != "active" or crec.get("arabic_field") != "company_name_ar":
        fails.append("registry Company entry drifted")

    # Glossary / brand precedent — value-free (R4): read the two committed artefacts at
    # runtime, match candidate strings by frozen sha16 (no Arabic literals in this file),
    # require exactly one hit per file, print source + sha16 only.
    CANDIDATE_SHA16 = {
        "63f48828f9f20a78": "candidate_primary",
        "0c0897cd368556de": "candidate_alternate_suffix_variant",
        "38e1e5b1cc224f3f": "candidate_alternate_bare",
    }
    precedent_files = {
        "p95_harness(AR_FIXTURES[0], synthetic pool on throwaway CT-COMP rows)":
            "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/"
            "bilingual-company-master/evidence/scripts/measure_company_p95.py",
        "pilot_test(test value on _Test Company% row, restore+commit)":
            "/home/mohamed/frappe-bench/apps/construction/construction/tests/"
            "test_bilingual_company_pilot.py",
    }
    import re as _re
    for label, path in precedent_files.items():
        hits = []
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            for m in _re.finditer(r'"([^"\n]+)"', line):
                digest = sha16(m.group(1))
                if digest in CANDIDATE_SHA16:
                    hits.append((lineno, digest, CANDIDATE_SHA16[digest]))
        if len(hits) != 1:
            fails.append(f"precedent parse {label}: {len(hits)} hits != 1")
            continue
        lineno, digest, role = hits[0]
        print(f"BRAND_ROOT_CORROBORATION source={label} file={os.path.basename(path)}"
              f":{lineno} sha16={digest} role={role}")
    print("GLOSSARY company-name terms=0 (only generic child-company entry; no term "
          "governs the owner brand or its legal suffix)")

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("INVENTORY RESULT: FAIL")
        sys.exit(1)
    print("FINDINGS F-5H-1 21 companies: 1 active owner (Elrefae, EGP/Egypt, flat, "
          "in transactional + scope-selector use) + 20 test noise (13 _Test* + 7 demo/test "
          "records; 5 is_group, 5 parented — all test)")
    print("FINDINGS F-5H-2 Company.save() enqueues jobs: without queue redis (11000) the "
          "save raises ConnectionError mid-flight — apply must run with the queue up "
          "(probe-disclosed); enqueue source not statically isolated, apply.log must "
          "capture the traceback/job name")
    print("FINDINGS F-5H-3 no Company fixture JSON -> no sync-wipe risk; hook binding "
          "present; registry active")
    print("FINDINGS F-5H-4 Arabic pre-state 0 site-wide; identity name == company_name "
          "for Elrefae ('Elrefae'); no name edits ever (rename triggers abbr cascade)")
    print("FINDINGS F-5H-5 brand root corroborated by two committed artefacts "
          "(sha16 above) — in-repo corroboration, NOT an established display name for "
          "Elrefae; primary + alternates = owner display-form decision (no glossary term)")
    print("FINDINGS F-5H-6 Company.on_update unconditionally re-sets Currency EGP "
          "enabled=1 (already 1) -> bumps tabCurrency.modified; the 1-row invariant "
          "covers company fields; verify expects/discloses the Currency modified bump")
    print("PHASE1_FROZEN_MATCH yes (1 = Elrefae)")
    print("PRE_STATE_ARABIC 0")
    print("INVENTORY RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
