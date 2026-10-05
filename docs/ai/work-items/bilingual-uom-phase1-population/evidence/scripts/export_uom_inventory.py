"""Tier 5F inventory export — UOM fixture audit (read-only).

Classification rules (R1, first match wins):
  1. vendor_fixture: name starts with `_Test`            -> never translated (2 rows)
  2. app_fixture:    name in construction/fixtures/uom.json (12 construction units)
  3. in_use:         referenced by live Item.stock_uom or BOQ Item.unit (non-fixture)
  4. disabled:       enabled = 0 and not already classed -> excluded from every phase
  5. remainder:      enabled, not app fixture, unused    -> Phase 2+ (audited only)

Finding F1 (audited 2026-10-05): all 12 app_fixture rows are enabled=0 on this site.
Fixture sync (frappe data_import import_doc) materializes keys absent from uom.json as
enabled=0 AND clobbers a manual enable back to 0 on every migrate (probed with rollback).
F1 is reported (FINDING lines), not gate-failed: the enable decision belongs to the owner.

Asserts, fail-closed:
  - the rule-derived Phase-1 set equals the frozen 17-row allowlist below;
  - pre-state: uom_name_ar populated on 0 rows;
  - no in_use row is disabled (site-corruption guard);
  - construction/fixtures/uom.json carries no uom_name_ar key (R3 disclosure holds);
  - registry UOM entry active with the expected fields; schema fields present.

Informational (not gated): picker visibility of each Phase-1 row via search_link —
disabled rows are hidden by the enabled=1 link filter (mirrored in
test_bilingual_desk_link_dispatch).

Run from apps/construction:
  /home/mohamed/frappe-bench/env/bin/python <this file path>
"""

import json
import sys

import frappe

APP_FIXTURE_JSON = "construction/fixtures/uom.json"

# R1 frozen Phase-1 allowlist (v2, owner-approved): 12 app fixtures + 3 non-fixture
# in-use units. F4 prune: 'Pint (US)' and 'Acre' (test-project BOQ drafts only) were
# dropped from Phase-1 by owner decision 2026-10-05; they remain classified in_use
# but are NOT populated (Phase 2+ candidate).
PHASE1_FROZEN = {
    "M3",
    "M2",
    "M",
    "TON",
    "KG",
    "PCS",
    "LS",
    "DAY",
    "HR",
    "BAG",
    "LTR",
    "SET",
    "Nos",
    "Tonne",
    "Box",
}
PRUNED_BY_OWNER = {"Pint (US)", "Acre"}


def classify(name, enabled, app_fixture_names, item_uoms, boq_units):
    if name.startswith("_Test"):
        return "vendor_fixture"
    if name in app_fixture_names:
        return "app_fixture"
    if name in item_uoms or name in boq_units:
        return "in_use"
    if not enabled:
        return "disabled"
    return "remainder"


def main():
    fail = []
    print(f"UOM_INVENTORY_EXPORT v1 site={frappe.local.site}")

    # --- R5: registry + schema surface must be active before any population talk.
    registry_path = "construction/data/bilingual/bilingual_registry.json"
    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    entry = registry.get("doctypes", {}).get("UOM")
    if not entry or entry.get("state") != "active":
        fail.append(f"registry UOM entry missing/inactive: {entry}")
    else:
        expected = {
            "english_field": "uom_name",
            "arabic_field": "uom_name_ar",
            "norm_field": "uom_name_ar_norm",
            "code_field": "common_code",
        }
        for k, v in expected.items():
            if entry.get(k) != v:
                fail.append(f"registry UOM {k}={entry.get(k)!r} != {v!r}")
    print(f"REGISTRY_UOM {'OK' if not fail else 'CHECK'}")

    meta = frappe.get_meta("UOM")
    for f in ("uom_name", "uom_name_ar", "uom_name_ar_norm", "enabled", "common_code"):
        if not meta.has_field(f):
            fail.append(f"UOM schema missing field {f}")
    print(f"SCHEMA_FIELDS {'OK' if not any('schema missing' in x for x in fail) else 'MISSING'}")

    # --- R3 disclosure: fixture JSON must not carry an Arabic key.
    with open(APP_FIXTURE_JSON, encoding="utf-8") as fh:
        fx_rows = json.load(fh)
    app_fixture_names = {r["name"] for r in fx_rows}
    if any("uom_name_ar" in r for r in fx_rows):
        fail.append("construction/fixtures/uom.json unexpectedly carries uom_name_ar (R3 disclosure stale)")
    print(f"FIXTURE_JSON app_rows={len(fx_rows)} has_arabic_key={'yes' if any('uom_name_ar' in r for r in fx_rows) else 'no'}")

    # --- Live usage joins (broad: any Item / any BOQ Item, R7).
    item_uoms = set(
        frappe.db.sql(
            "SELECT DISTINCT stock_uom FROM tabItem "
            "WHERE stock_uom IS NOT NULL AND stock_uom != ''",
            pluck=True,
        )
    )
    boq_units = set(
        frappe.db.sql(
            "SELECT DISTINCT unit FROM `tabBOQ Item` "
            "WHERE unit IS NOT NULL AND unit != ''",
            pluck=True,
        )
    )
    print(f"USAGE items_distinct={len(item_uoms)} boq_distinct={len(boq_units)}")

    rows = frappe.get_all(
        "UOM",
        fields=["name", "uom_name", "uom_name_ar", "uom_name_ar_norm", "common_code", "symbol", "enabled", "category"],
        limit_page_length=0,
    )
    classified = {"vendor_fixture": [], "app_fixture": [], "in_use": [], "disabled": [], "remainder": []}
    for r in rows:
        cls = classify(r["name"], r["enabled"], app_fixture_names, item_uoms, boq_units)
        classified[cls].append(r)

    # --- R1 frozen-allowlist assertion (derived from rules + live joins, less owner prune).
    derived_phase1 = (
        {r["name"] for r in classified["app_fixture"]}
        | {r["name"] for r in classified["in_use"]}
    ) - PRUNED_BY_OWNER
    if derived_phase1 != PHASE1_FROZEN:
        fail.append(
            f"rule-derived Phase-1 {sorted(derived_phase1)} != frozen {sorted(PHASE1_FROZEN)}"
        )
    print(f"PHASE1_FROZEN_MATCH {'yes' if derived_phase1 == PHASE1_FROZEN else 'NO'}")
    in_use_pruned = sorted({r["name"] for r in classified["in_use"]} & PRUNED_BY_OWNER)
    print(f"PRUNED_BY_OWNER {in_use_pruned}")

    # --- Pre-state: zero Arabic anywhere (clean pre-cycle).
    pre = [r for r in rows if r["uom_name_ar"]]
    if pre:
        fail.append(f"pre-existing uom_name_ar on {len(pre)} rows: {[r['name'] for r in pre][:10]}")
    print(f"PRE_STATE arabic_populated={len(pre)}")

    # --- Fixture-rule guard: vendor fixtures must not sneak into phase 1.
    fixture_in_phase1 = sorted(n for n in derived_phase1 if n.startswith("_Test"))
    if fixture_in_phase1:
        fail.append(f"vendor fixtures inside Phase-1: {fixture_in_phase1}")
    print(f"FIXTURES_IN_PHASE1 {fixture_in_phase1 or 'none'}")

    # --- Corruption guard: a unit referenced by live Item/BOQ must be enabled.
    disabled_in_use = sorted(r["name"] for r in classified["in_use"] if not r["enabled"])
    if disabled_in_use:
        fail.append(f"disabled rows referenced by live usage: {disabled_in_use}")
    print(f"DISABLED_IN_USE {disabled_in_use or 'none'}")

    # --- F1: app fixture enablement state (finding, not gate).
    fx_disabled = sorted(r["name"] for r in classified["app_fixture"] if not r["enabled"])
    print(
        f"FINDING F1 app_fixture_disabled={len(fx_disabled)}/"
        f"{len(classified['app_fixture'])} rows={fx_disabled}"
    )

    # --- F2: picker visibility of Phase-1 rows (finding, not gate).
    # Link search mirrors enabled=1 (contract-tested in test_bilingual_desk_link_dispatch).
    # Hidden rows are reported with their enabled flag to distinguish filter-hide from
    # ranking/pagination artifacts.
    from frappe.desk.search import search_link

    enabled_map = {r["name"]: r["enabled"] for r in rows}
    hidden, visible = [], []
    for name in sorted(derived_phase1):
        hits = [o.get("value") for o in search_link("UOM", name, page_length=50)]
        (visible if name in hits else hidden).append(name)
    print(f"FINDING F2 phase1_visible_in_picker={len(visible)}/{len(derived_phase1)}")
    print(
        "FINDING F2 phase1_hidden_in_picker="
        f"{[(n, enabled_map[n]) for n in hidden] or 'none'}"
    )

    for cls in ("vendor_fixture", "app_fixture", "in_use", "disabled", "remainder"):
        members = sorted(classified[cls], key=lambda x: x["name"])
        print(f"CLASS {cls} count={len(members)}")
        for r in members:
            usage = []
            if r["name"] in item_uoms:
                usage.append("item")
            if r["name"] in boq_units:
                usage.append("boq")
            print(
                f"  ROW class={cls} name={r['name']!r} uom_name={r['uom_name']!r} "
                f"enabled={r['enabled']} category={r['category']!r} "
                f"common_code={r['common_code']!r} usage={'+'.join(usage) or '-'}"
            )

    summary = {cls: len(classified[cls]) for cls in classified}
    summary["total"] = len(rows)
    summary["phase1"] = len(derived_phase1)
    print(f"SUMMARY {json.dumps(summary, sort_keys=True)}")
    if fail:
        for f in fail:
            print("FAIL:", f)
        print("INVENTORY RESULT: FAIL")
        sys.exit(1)
    print("INVENTORY RESULT: PASS (R1 rule-derived Phase-1 matches frozen 15-row allowlist; "
          "pre-state empty; F4 owner prune applied; F1/F2 findings reported; "
          "no in_use row disabled)")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
