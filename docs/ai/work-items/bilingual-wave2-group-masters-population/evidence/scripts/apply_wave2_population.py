"""Tier 5D apply — import the approved proposal through standard doc.save().

Fail-closed gates before any write:
  1. proposal.json sha256 == the owner-approved sha (R2 approval binding);
  2. private dry-run.json exists, references the same proposal sha, and every
     row is in a non-conflicting state (empty before / already-applied);
  3. byte-scan of each value (bidi, controls, tatweel, digits, whitespace).

All 23 rows are pre-validated before the first write; any failure rolls the
transaction back. Norm keys are derived server-side by the existing
enforce_bilingual_arabic_policy validate hook — this script never writes a
_norm field itself.

R3a safety net (expected dormant — export proved all four parent_* fields
optional): if a root row still raises MandatoryError, retry it with
flags.ignore_mandatory=True on a freshly loaded copy; any trigger is logged.

R3b root workaround (SCOPE R3b, proved fail-closed on attempt 1): ERPNext forces
empty-parent roots to reparent under themselves, which NestedSet then rejects.
The 4 root rows save under a narrow disclosed workaround (Item Group:
frappe.in_test guard; other trees: scoped get_root_of patch -> None); the 19
non-root rows save strictly plain. All validate hooks still run on every row.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/wave2-group-masters-population"
APPROVED_SHA = "08dba90a8134c238d2e2e74b69081c0ec0c879ddecb82b2b7bb3a0ed2f6ea47e"
FIELDS = {
    "Item Group": ("item_group_name_ar", "item_group_name_ar_norm", "item_group_name"),
    "Customer Group": ("customer_group_name_ar", "customer_group_name_ar_norm", "customer_group_name"),
    "Supplier Group": ("supplier_group_name_ar", "supplier_group_name_ar_norm", "supplier_group_name"),
    "Territory": ("territory_name_ar", "territory_name_ar_norm", "territory_name"),
}
PARENT_FIELDS = {
    "Item Group": "parent_item_group",
    "Customer Group": "parent_customer_group",
    "Supplier Group": "parent_supplier_group",
    "Territory": "parent_territory",
}

# R3b: modules whose validate() force empty-parent roots to self-parent via get_root_of.
ROOT_PATCH_MODULES = {}


def _load_root_patch_modules():
    import erpnext.setup.doctype.customer_group.customer_group as cg
    import erpnext.setup.doctype.supplier_group.supplier_group as sg
    import erpnext.setup.doctype.territory.territory as tr

    ROOT_PATCH_MODULES.update(
        {"Customer Group": cg, "Supplier Group": sg, "Territory": tr}
    )


def save_with_root_workaround(d, item):
    """Save one row; root rows get the disclosed R3b vendor-workaround (SCOPE R3b).

    Only the forced self-parent of empty-parent roots is prevented; every validate
    hook (incl. enforce_bilingual_arabic_policy) and ERPNext validation still runs.
    """
    doctype, name = item["doctype"], item["name"]
    if d.get(PARENT_FIELDS[doctype]):
        d.save()  # strict plain save for the 19 non-root rows
        return "plain"
    if doctype == "Item Group":
        # ERPNext's own exemption: `if not parent and not frappe.in_test` skips the
        # hardcoded self-parent forcing of the root.
        frappe.in_test = True
        try:
            d.save()
        finally:
            frappe.in_test = False
        print(
            f"R3B_ROOT_SAVE {doctype} {name!r} via frappe.in_test guard "
            f"(vendor forces empty-parent root to self-parent otherwise)"
        )
        return "r3b-in_test"
    mod = ROOT_PATCH_MODULES[doctype]
    original = mod.get_root_of
    mod.get_root_of = lambda _dt: None  # keep the empty parent empty (root stays root)
    try:
        d.save()
    finally:
        mod.get_root_of = original
    print(
        f"R3B_ROOT_SAVE {doctype} {name!r} via scoped get_root_of patch -> None "
        f"(vendor forces empty-parent root to self-parent otherwise)"
    )
    return "r3b-get_root_of"


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
    # Gate 1: approved proposal bytes.
    raw = open(f"{PRIVATE}/proposal.json", "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != APPROVED_SHA:
        print(f"FAIL: proposal sha {sha} != approved {APPROVED_SHA} — approval invalidated")
        sys.exit(1)
    proposal = json.loads(raw)

    # Gate 2: completed dry-run bound to the same proposal.
    dry_raw = open(f"{PRIVATE}/dry-run.json", "rb").read()
    dry = json.loads(dry_raw)
    if dry.get("proposal_sha256") != APPROVED_SHA:
        print("FAIL: dry-run is not bound to the approved proposal sha")
        sys.exit(1)
    dry_by = {(r["doctype"], r["name"]): r for r in dry.get("rows", [])}
    if len(dry_by) != 23:
        print(f"FAIL: dry-run row set has {len(dry_by)} rows, expected 23")
        sys.exit(1)

    from construction.services.bilingual_service import normalize_arabic

    # Pre-validate EVERY row before the first write.
    plan = []
    for row in proposal["rows"]:
        doctype, name = row["doctype"], row["name"]
        ar_field, norm_field, label_field = FIELDS[doctype]
        value = row["arabic"].strip()
        problems = byte_scan(value)
        if problems:
            print(f"FAIL pre-validate {doctype} {name}: {problems}")
            sys.exit(1)
        d = frappe.get_doc(doctype, name)
        if d.get(label_field) != row["english_label"]:
            print(f"FAIL pre-validate {doctype} {name}: english label drift")
            sys.exit(1)
        current = d.get(ar_field)
        if current and current != value:
            print(f"FAIL pre-validate {doctype} {name}: conflicting existing value {sha16(current)}")
            sys.exit(1)
        if (doctype, name) not in dry_by:
            print(f"FAIL pre-validate {doctype} {name}: absent from dry-run")
            sys.exit(1)
        plan.append(
            {
                "doctype": doctype, "name": name, "field": ar_field,
                "norm_field": norm_field, "label_field": label_field,
                "value": value, "already": bool(current),
                "label_before": d.get(label_field),
            }
        )
    print(f"PREVALIDATE_OK rows={len(plan)}")
    _load_root_patch_modules()

    # Apply through the standard document lifecycle (validate hook derives _norm).
    results = []
    try:
        for item in plan:
            d = frappe.get_doc(item["doctype"], item["name"])
            if item["already"]:
                print(f"SKIP {item['doctype']} {item['name']!r} already applied")
                results.append({**{k: item[k] for k in ("doctype", "name")},
                                "action": "skip-already-applied"})
                continue
            d.set(item["field"], item["value"])
            # enforce_bilingual_arabic_policy: bidi gate + server-derived norm.
            # Roots (4 rows) go through the disclosed R3b workaround; non-roots plain.
            try:
                save_with_root_workaround(d, item)
            except frappe.MandatoryError:
                # R3a safety net — export proved parent_* optional, so this should not fire.
                parent_field = PARENT_FIELDS.get(item["doctype"])
                if not parent_field or d.get(parent_field):
                    raise
                print(
                    f"R3A_ROOT_RETRY {item['doctype']} {item['name']!r} "
                    f"(empty parent {parent_field!r}; flags.ignore_mandatory=True) "
                    f"UNEXPECTED — parent fields were verified optional by export"
                )
                # fresh copy: attempt 1 bumped in-memory modified, reusing the object
                # would trip check_if_latest (TimestampMismatchError)
                d = frappe.get_doc(item["doctype"], item["name"])
                d.set(item["field"], item["value"])
                d.flags.ignore_mandatory = True
                try:
                    d.save()
                finally:
                    d.flags.ignore_mandatory = False
            if d.get(item["label_field"]) != item["label_before"]:
                raise RuntimeError(f"{item['doctype']} {item['name']}: english identity changed")
            if d.get(item["field"]) != item["value"]:
                raise RuntimeError(f"{item['doctype']} {item['name']}: value not stored")
            expected_norm = normalize_arabic(item["value"])
            if d.get(item["norm_field"]) != expected_norm:
                raise RuntimeError(f"{item['doctype']} {item['name']}: norm not server-derived")
            print(
                f"WRITE {item['doctype']} {item['name']!r} value={sha16(item['value'])} "
                f"norm={sha16(expected_norm)} identity=unchanged"
            )
            results.append({**{k: item[k] for k in ("doctype", "name")},
                            "action": "written", "value": item["value"],
                            "norm": expected_norm})
        frappe.db.commit()
    except Exception as exc:  # noqa: BLE001 - fail-closed rollback
        frappe.db.rollback()
        print(f"FAIL during apply, transaction rolled back: {exc}")
        sys.exit(1)

    private = {
        "proposal_sha256": APPROVED_SHA,
        "dry_run_sha256": hashlib.sha256(dry_raw).hexdigest(),
        "apply_utc": frappe.utils.now_datetime().isoformat(),
        "written": sum(1 for r in results if r["action"] == "written"),
        "skipped": sum(1 for r in results if r["action"] != "written"),
        "results": results,
    }
    with open(f"{PRIVATE}/apply.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    apply_sha = hashlib.sha256(open(f"{PRIVATE}/apply.json", "rb").read()).hexdigest()
    print(f"SUMMARY written={private['written']} skipped={private['skipped']} failed=0")
    print(f"PRIVATE apply.json sha256={apply_sha}")
    print("APPLY RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
