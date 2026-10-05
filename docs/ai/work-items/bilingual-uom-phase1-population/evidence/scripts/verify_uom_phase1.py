"""Tier 5F post-import verification — independent read-back after apply.

Checks (all read-only except the explicitly suppressed-and-rolled-back durability proof):
  1. approved proposal bytes unchanged post-apply;
  2. every approved row carries exactly the approved value; stored _norm ==
     normalize_arabic(stored value); stored values pass the byte/bidi scan; identity
     (uom_name) unchanged;
  3. completeness: exactly 15 site rows have uom_name_ar (the approved set);
  4. exceptions: vendor `_Test` rows, F4-pruned Pint (US)/Acre, the 234 remainder, and
     zero PROBE residue rows all remain empty;
  5. enablement: all 12 fixture rows enabled=1; site-wide disabled count == 0;
  6. fixture file byte-stable at the recorded post-edit sha, consistent with the proposal,
     no norm key;
  7. picker visibility: search_link resolves all 15 approved rows (F2 closed);
  8. durability proof: commit-suppressed fixture sync (delete+reinsert from uom.json)
     preserves Arabic + enabled + server-derived norm on all 12 fixture rows, then the
     whole proof is rolled back (site state unchanged);
  9. prior-tier surfaces frozen (5D list) and UOM total still 253.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/uom-phase1-population"
APPROVED_SHA = "18a16a953ebbaad704acc7982ed96de71808235c7fc5b258b6825fbd80598bbf"
UOM_JSON = "/home/mohamed/frappe-bench/apps/construction/construction/fixtures/uom.json"
UOM_JSON_POST_SHA = "d6e27a01483c841dccdb090277aa9c59459b270d52d40661bf9934d9e4c33ad2"
AR_FIELD, NORM_FIELD, LABEL_FIELD = "uom_name_ar", "uom_name_ar_norm", "uom_name"
FIXTURE_NAMES = {"M3", "M2", "M", "TON", "KG", "PCS", "LS", "DAY", "HR", "BAG", "LTR", "SET"}
PRUNED = {"Pint (US)", "Acre"}
FROZEN_PRIOR = {
    "items_ar": 8,
    "customers_ar": 1,
    "suppliers_ar": 0,
    "cost_centers_ar": 3,
    "warehouses_ar": 6,
    "projects_ar": 5,
    "accounts_ar": 81,
}


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def byte_scan(value):
    problems = []
    if value != value.strip():
        problems.append("whitespace")
    for ch in value:
        cp = ord(ch)
        if cp in (0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
                  0x2066, 0x2067, 0x2068, 0x2069, 0x200B, 0x200C, 0x200D, 0xFEFF):
            problems.append(f"bidi/zw U+{cp:04X}")
        elif cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F:
            problems.append(f"control U+{cp:04X}")
        elif ch == "ـ":
            problems.append("tatweel")
        elif 0x0660 <= cp <= 0x0669:
            problems.append(f"arabic-digit U+{cp:04X}")
        elif unicodedata.category(ch) in ("Cf", "Co", "Cs"):
            problems.append(f"format U+{cp:04X}")
    return problems


def main():
    fails = []
    raw = open(f"{PRIVATE}/proposal.json", "rb").read()
    if hashlib.sha256(raw).hexdigest() != APPROVED_SHA:
        print("FAIL: approved proposal bytes changed after import")
        sys.exit(1)
    proposal = json.loads(raw)
    from construction.services.bilingual_service import normalize_arabic

    approved_names = {r["name"] for r in proposal["rows"]}

    # 2: per-row read-back.
    for row in proposal["rows"]:
        name = row["name"]
        d = frappe.get_doc("UOM", name)
        stored = d.get(AR_FIELD)
        if stored != row["arabic"]:
            fails.append(f"UOM {name}: stored value != approved (sha16={sha16(stored or '')})")
            continue
        if d.get(NORM_FIELD) != normalize_arabic(stored):
            fails.append(f"UOM {name}: stored norm inconsistent")
        problems = byte_scan(stored)
        if problems:
            fails.append(f"UOM {name}: byte scan {problems}")
        if d.get(LABEL_FIELD) != row["english_label"]:
            fails.append(f"UOM {name}: identity changed")
        print(f"ROW_OK UOM {name!r} value={sha16(stored)} norm={sha16(d.get(NORM_FIELD) or '')} identity=unchanged")

    # 3: completeness — exactly the approved 15 site-wide.
    populated = {r["name"] for r in frappe.get_all(
        "UOM", filters={AR_FIELD: ("!=", "")}, fields=["name"], limit_page_length=0)}
    missing = approved_names - populated
    extra = populated - approved_names
    if missing:
        fails.append(f"approved rows not populated: {sorted(missing)}")
    if extra:
        fails.append(f"unexpected populated rows: {sorted(extra)}")
    print(f"COMPLETENESS site_arabic_total={len(populated)} approved=15 missing={len(missing)} extra={len(extra)}")

    # 4: exception integrity.
    for name in sorted(PRUNED):
        d = frappe.get_doc("UOM", name)
        if d.get(AR_FIELD):
            fails.append(f"F4-pruned {name} unexpectedly populated")
    for name in ("_Test UOM", "_Test UOM 1"):
        d = frappe.get_doc("UOM", name)
        if d.get(AR_FIELD):
            fails.append(f"vendor fixture {name} populated")
    probe_rows = frappe.db.sql("SELECT name FROM `tabUOM` WHERE name LIKE 'PROBE%'")
    if probe_rows:
        fails.append(f"probe residue rows present: {probe_rows}")
    print("EXCEPTIONS_OK pruned=2 vendor=2 remainder_unpopulated=yes probe_residue=0")

    # 5: enablement.
    fx_disabled = frappe.get_all("UOM", filters={"name": ["in", sorted(FIXTURE_NAMES)], "enabled": 0})
    if fx_disabled:
        fails.append(f"fixture rows still disabled: {[r['name'] for r in fx_disabled]}")
    site_disabled = frappe.db.count("UOM", {"enabled": 0})
    if site_disabled != 0:
        fails.append(f"site disabled count {site_disabled} != 0")
    print(f"ENABLEMENT fixtures_enabled={12 - len(fx_disabled)}/12 site_disabled={site_disabled}")

    # 6: fixture file byte-stability + consistency.
    fx_raw = open(UOM_JSON, "rb").read()
    fx_sha = hashlib.sha256(fx_raw).hexdigest()
    if fx_sha != UOM_JSON_POST_SHA:
        fails.append(f"uom.json sha changed post-apply: {fx_sha}")
    fx = json.loads(fx_raw)
    for r in fx:
        approved = next((x for x in proposal["rows"] if x["name"] == r.get("name")), None)
        if not approved or r.get("uom_name_ar") != approved["arabic"] or r.get("enabled") != 1:
            fails.append(f"uom.json row {r.get('name')} inconsistent with proposal")
        if "uom_name_ar_norm" in r:
            fails.append(f"uom.json row {r.get('name')} carries a norm key")
    print(f"FIXTURE_FILE sha256={fx_sha} rows={len(fx)} consistent=yes")

    # 7: picker visibility (F2 closed: all 15 enabled).
    from frappe.desk.search import search_link
    hidden = []
    for name in sorted(approved_names):
        hits = [o.get("value") for o in search_link("UOM", name, page_length=50)]
        if name not in hits:
            hidden.append(name)
    if hidden:
        fails.append(f"approved rows invisible in picker: {hidden}")
    print(f"VISIBILITY phase1_visible_in_picker={15 - len(hidden)}/15")

    # 8: durability proof — fixture sync round-trip, commit suppressed, rolled back.
    orig_commit = frappe.db.commit
    frappe.db.commit = lambda *a, **k: None
    proof_ok = True
    try:
        from frappe.core.doctype.data_import.data_import import import_doc
        import_doc(UOM_JSON, sort=True)
        for r in proposal["rows"]:
            if r["name"] not in FIXTURE_NAMES:
                continue
            db_row = frappe.db.get_value(
                "UOM", r["name"], [AR_FIELD, NORM_FIELD, "enabled"], as_dict=True)
            if not db_row or db_row.get(AR_FIELD) != r["arabic"]:
                proof_ok = False
                fails.append(f"durability proof: {r['name']} Arabic lost/changed under fixture sync")
            elif int(db_row.get("enabled") or 0) != 1:
                proof_ok = False
                fails.append(f"durability proof: {r['name']} enabled lost under fixture sync")
            elif db_row.get(NORM_FIELD) != normalize_arabic(r["arabic"]):
                proof_ok = False
                fails.append(f"durability proof: {r['name']} norm not re-derived on import")
    except Exception as exc:  # noqa: BLE001
        proof_ok = False
        fails.append(f"durability proof raised: {exc}")
    finally:
        frappe.db.commit = orig_commit
        frappe.db.rollback()
    # Re-read post-rollback to prove the proof left no trace.
    post = frappe.db.get_value("UOM", "M3", [AR_FIELD, "enabled"], as_dict=True)
    if not post or post.get(AR_FIELD) != next(r for r in proposal["rows"] if r["name"] == "M3")["arabic"] or int(post.get("enabled") or 0) != 1:
        fails.append("durability proof rollback failed to restore M3")
    print(f"DURABILITY_PROOF fixture_sync_roundtrip={'PASS' if proof_ok else 'FAIL'} rollback_restored=yes")

    # 9: totals + frozen prior surfaces.
    total = frappe.db.count("UOM")
    if total != 253:
        fails.append(f"UOM total {total} != 253")
    prior = {
        "items_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabItem` WHERE item_name_ar IS NOT NULL AND item_name_ar != ''"
        )[0][0],
        "customers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCustomer` WHERE customer_name_in_arabic IS NOT NULL AND customer_name_in_arabic != ''"
        )[0][0],
        "suppliers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSupplier` WHERE supplier_name_in_arabic IS NOT NULL AND supplier_name_in_arabic != ''"
        )[0][0],
        "cost_centers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCost Center` WHERE cost_center_name_ar IS NOT NULL AND cost_center_name_ar != ''"
        )[0][0],
        "warehouses_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabWarehouse` WHERE warehouse_name_ar IS NOT NULL AND warehouse_name_ar != ''"
        )[0][0],
        "projects_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabProject` WHERE project_name_ar IS NOT NULL AND project_name_ar != ''"
        )[0][0],
        "accounts_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabAccount` WHERE account_name_ar IS NOT NULL AND account_name_ar != ''"
        )[0][0],
    }
    for key, expected in FROZEN_PRIOR.items():
        if prior[key] != expected:
            fails.append(f"prior surface {key} = {prior[key]} != frozen {expected}")
    company_ar = frappe.db.get_value("Company", "Elrefae", "company_name_ar")
    if company_ar:
        fails.append(f"Company.company_name_ar was written: {sha16(company_ar)}")
    groups = {
        dt: frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{dt}` WHERE {col} IS NOT NULL AND {col} != ''"
        )[0][0]
        for dt, col in (("Item Group", "item_group_name_ar"), ("Customer Group", "customer_group_name_ar"),
                        ("Supplier Group", "supplier_group_name_ar"), ("Territory", "territory_name_ar"))
    }
    if groups != {"Item Group": 6, "Customer Group": 5, "Supplier Group": 8, "Territory": 4}:
        fails.append(f"5D group surfaces drifted: {groups}")
    print(f"FROZEN_SURFACES " + " ".join(f"{k}={prior[k]}" for k in sorted(prior))
          + f" company_ar={'empty' if not company_ar else 'WRITTEN'} groups={groups}")
    print(f"COUNTS_OK uom_total={total}")

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("VERIFICATION RESULT: FAIL")
        sys.exit(1)
    print("SUMMARY approved=15 populated=15 norm_consistent=15 identity_unchanged=15 "
          "fixtures_enabled=12 visibility=15/15 exceptions=0 durability=PASS prior_frozen=yes")
    print("ROLLBACK_REF dry-run.json (before-values: all empty) sha256="
          + hashlib.sha256(open(f"{PRIVATE}/dry-run.json", "rb").read()).hexdigest())
    print("VERIFICATION RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
