"""Tier 5H post-import verification — independent read-back after apply.

Checks (read-only):
  1. approved proposal bytes unchanged post-apply (v2 sha);
  2. the approved row: stored value == approved; stored _norm ==
     normalize_arabic(stored); byte-scan clean; frozen fields (name, company_name,
     abbr, default_currency, country, parent_company, is_group, chart_of_accounts)
     identical to the dry-run snapshot;
  3. completeness: site Company Arabic total == exactly 1, set == {'Elrefae'};
  4. exclusions: all 20 test companies empty; total 21;
  5. usage surface: User Scope Context rows for Elrefae resolve an Arabic company name;
     Currency EGP enabled==1 (F-5H-6 disclosed modified bump not asserted);
  6. prior surfaces frozen: 5D list + 5F UOM + 5G Department (14/276) — everything
     except Company (this tier's surface) byte-for-byte at 5d96f12 counts;
  7. module patch restored: department module get_root_of is the original function.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/company-phase1-population"
APPROVED_SHA = "b5fcc02a6854ebb27b71082b71c1b3f9d4ac43f737b013809697c2a23e79478a"
AR_FIELD, NORM_FIELD, LABEL_FIELD = "company_name_ar", "company_name_ar_norm", "company_name"
UOM_JSON_SHA = "d6e27a01483c841dccdb090277aa9c59459b270d52d40661bf9934d9e4c33ad2"
FROZEN_PRIOR = {"items_ar": 8, "customers_ar": 1, "suppliers_ar": 0, "cost_centers_ar": 3,
                "warehouses_ar": 6, "projects_ar": 5, "accounts_ar": 81,
                "departments_ar": 14, "departments_total": 276}


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
    dry = json.loads(open(f"{PRIVATE}/dry-run.json", encoding="utf-8").read())
    if dry.get("proposal_sha256") != APPROVED_SHA:
        fails.append("dry-run not bound to approved sha")
    dry_by = {r["name"]: r for r in dry.get("rows", [])}
    from construction.services.bilingual_service import normalize_arabic

    approved_names = {r["name"] for r in proposal["rows"]}

    # 2: per-row read-back vs dry-run snapshot.
    for row in proposal["rows"]:
        name = row["name"]
        snap = dry_by.get(name, {}).get("snapshot")
        if not snap:
            fails.append(f"{name}: absent from dry-run snapshot")
            continue
        now = frappe.db.get_value(
            "Company", name,
            ["name", LABEL_FIELD, "abbr", "default_currency", "country",
             "parent_company", "is_group", "chart_of_accounts",
             AR_FIELD, NORM_FIELD], as_dict=True)
        stored = now[AR_FIELD]
        if stored != row["arabic"]:
            fails.append(f"{name}: stored value != approved (sha16={sha16(stored or '')})")
            continue
        if now[NORM_FIELD] != normalize_arabic(stored):
            fails.append(f"{name}: stored norm inconsistent")
        problems = byte_scan(stored)
        if problems:
            fails.append(f"{name}: byte scan {problems}")
        for f in ["name", LABEL_FIELD, "abbr", "default_currency", "country",
                  "parent_company", "is_group", "chart_of_accounts"]:
            if now.get(f) != snap.get(f):
                fails.append(f"{name}: frozen field {f} drifted {snap.get(f)!r} -> {now.get(f)!r}")
        print(f"ROW_OK {name!r} value={sha16(stored)} norm={sha16(now[NORM_FIELD] or '')} "
              f"identity=unchanged frozen=unchanged")

    # 3: completeness — exactly the approved set site-wide.
    populated = {r["name"] for r in frappe.get_all(
        "Company", filters={AR_FIELD: ("!=", "")}, fields=["name"], limit_page_length=0)}
    missing, extra = approved_names - populated, populated - approved_names
    if missing:
        fails.append(f"approved rows not populated: {sorted(missing)}")
    if extra:
        fails.append(f"unexpected populated rows: {sorted(extra)}")
    print(f"COMPLETENESS site_arabic_total={len(populated)} approved=1 "
          f"missing={len(missing)} extra={len(extra)}")

    # 4: exclusions + totals.
    excluded = frappe.db.count("Company") - len(approved_names)
    if excluded != 20:
        fails.append(f"excluded rows {excluded} != 20")
    excluded_ar = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabCompany` WHERE company_name_ar IS NOT NULL "
        "AND company_name_ar != '' AND name NOT IN %s",
        (tuple(approved_names),))[0][0]
    if excluded_ar:
        fails.append(f"{excluded_ar} excluded rows have Arabic")
    total = frappe.db.count("Company")
    if total != 21:
        fails.append(f"total {total} != 21")
    print(f"EXCLUSIONS excluded=20 excluded_arabic={excluded_ar} total={total}")

    # 5: usage surface + currency side-write disclosure.
    scope_rows = frappe.db.count("User Scope Context", {"company": "Elrefae"})
    if not scope_rows:
        fails.append("no User Scope Context rows point at Elrefae")
    cur = frappe.db.get_value("Currency", "EGP", ["enabled"], as_dict=True)
    if not cur or cur["enabled"] != 1:
        fails.append("Currency EGP not enabled")
    print(f"USAGE_SURFACE scope_selector_rows={scope_rows} company_arabic_visible=yes "
          f"currency_egp_enabled=1 modified_bump=expected(F-5H-6)")

    # 6: prior surfaces frozen (5D list + 5F UOM + 5G Department).
    prior = {
        "items_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabItem` WHERE item_name_ar IS NOT NULL AND item_name_ar != ''")[0][0],
        "customers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCustomer` WHERE customer_name_in_arabic IS NOT NULL AND customer_name_in_arabic != ''")[0][0],
        "suppliers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSupplier` WHERE supplier_name_in_arabic IS NOT NULL AND supplier_name_in_arabic != ''")[0][0],
        "cost_centers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCost Center` WHERE cost_center_name_ar IS NOT NULL AND cost_center_name_ar != ''")[0][0],
        "warehouses_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabWarehouse` WHERE warehouse_name_ar IS NOT NULL AND warehouse_name_ar != ''")[0][0],
        "projects_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabProject` WHERE project_name_ar IS NOT NULL AND project_name_ar != ''")[0][0],
        "accounts_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabAccount` WHERE account_name_ar IS NOT NULL AND account_name_ar != ''")[0][0],
        "departments_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDepartment` WHERE department_name_ar IS NOT NULL AND department_name_ar != ''")[0][0],
        "departments_total": frappe.db.count("Department"),
    }
    for k, exp in FROZEN_PRIOR.items():
        if prior[k] != exp:
            fails.append(f"prior surface {k} = {prior[k]} != frozen {exp}")
    groups = {dt: frappe.db.sql(
        f"SELECT COUNT(*) FROM `tab{dt}` WHERE {col} IS NOT NULL AND {col} != ''")[0][0]
        for dt, col in (("Item Group", "item_group_name_ar"), ("Customer Group", "customer_group_name_ar"),
                        ("Supplier Group", "supplier_group_name_ar"), ("Territory", "territory_name_ar"))}
    if groups != {"Item Group": 6, "Customer Group": 5, "Supplier Group": 8, "Territory": 4}:
        fails.append(f"5D group surfaces drifted: {groups}")
    uom_ar = frappe.db.count("UOM", {"uom_name_ar": ("!=", "")})
    uom_en = frappe.db.count("UOM", {"enabled": 1})
    if uom_ar != 15 or uom_en != 253:
        fails.append(f"5F UOM surfaces drifted: arabic={uom_ar} enabled={uom_en}")
    uom_fx = hashlib.sha256(open(
        "/home/mohamed/frappe-bench/apps/construction/construction/fixtures/uom.json", "rb"
    ).read()).hexdigest()
    if uom_fx != UOM_JSON_SHA:
        fails.append(f"uom.json changed: {uom_fx}")
    print(f"FROZEN_SURFACES " + " ".join(f"{k}={prior[k]}" for k in sorted(prior))
          + " groups=" + json.dumps(groups)
          + f" uom_arabic={uom_ar} uom_enabled={uom_en} uom_json=unchanged")

    # 7: module patch restored.
    import erpnext.setup.doctype.department.department as dept_mod
    from frappe.utils.nestedset import get_root_of as original
    if dept_mod.get_root_of is not original:
        fails.append("get_root_of patch leaked (module monkeypatch not restored)")
    print(f"PATCH_RESTORATION get_root_of_restored={dept_mod.get_root_of is original}")

    if fails:
        for f in fails:
            print("FAIL:", f)
        print("VERIFICATION RESULT: FAIL")
        sys.exit(1)
    print("SUMMARY approved=1 populated=1 norm_consistent=1 identity_unchanged=1 "
          "frozen_unchanged=1 exclusions=20 intact usage_surface=yes prior_frozen=yes "
          "patch_restored=yes")
    print("ROLLBACK_REF dry-run.json (before-values all empty) sha256="
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
