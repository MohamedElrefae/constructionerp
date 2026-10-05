"""Tier 5G apply — import the approved v2 Department proposal via standard doc.save().

Fail-closed gates before any write:
  1. proposal.json sha256 == owner-approved v2 sha;
  2. private dry-run.json bound to the same proposal sha, writes_performed == 0;
  3. byte-scan of each value; every row pre-validated (exists, label/company match,
     shape match, Arabic empty-or-equal) BEFORE the first write;
  4. excluded set still 262 and site Arabic total still 0.

Apply paths (both disclosed in owner-approval.md §1-2 / SCOPE §2.1 P3):
  - 13 company rows: plain doc.save() (validate hook derives _norm server-side);
  - row 1 'All Departments': flags.ignore_mandatory + module-scoped
    get_root_of -> None (restored in finally) so the NestedSet controller does not
    self-parent; all other validations still run.

On any exception: full transaction rollback, APPLY RESULT: FAIL, exit 1.
"""

import hashlib
import json
import sys
import unicodedata

import frappe

PRIVATE = "/home/mohamed/frappe-bench/sites/v16.localhost/private/department-phase1-population"
APPROVED_SHA = "dba85a4ceba5826094c1c7b6e25117afe8e0a696bcb1c3564699b0d736bf64a4"
AR_FIELD, NORM_FIELD, LABEL_FIELD = "department_name_ar", "department_name_ar_norm", "department_name"
ROOT_NAME = "All Departments"


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
        print("FAIL: dry-run not bound to the approved proposal sha")
        sys.exit(1)
    if dry.get("writes_performed") != 0:
        print("FAIL: dry-run did not record zero writes")
        sys.exit(1)
    dry_by = {r["name"]: r for r in dry.get("rows", [])}
    if len(dry_by) != 14:
        print(f"FAIL: dry-run row set has {len(dry_by)} rows, expected 14")
        sys.exit(1)

    from construction.services.bilingual_service import normalize_arabic

    # Gate 3: pre-validate EVERY row before the first write.
    plan = []
    for row in proposal["rows"]:
        name, value = row["name"], row["arabic"]
        problems = byte_scan(value)
        if problems:
            print(f"FAIL pre-validate {name}: {problems}")
            sys.exit(1)
        snap = frappe.db.get_value(
            "Department", name,
            [LABEL_FIELD, "company", "parent_department", "is_group", AR_FIELD], as_dict=True)
        if not snap:
            print(f"FAIL pre-validate {name}: absent")
            sys.exit(1)
        if snap[LABEL_FIELD] != row["english_label"]:
            print(f"FAIL pre-validate {name}: label drift")
            sys.exit(1)
        if (snap["company"] or None) != (row["company"] or None):
            print(f"FAIL pre-validate {name}: company drift")
            sys.exit(1)
        if snap[AR_FIELD] and snap[AR_FIELD] != value:
            print(f"FAIL pre-validate {name}: conflicting existing value")
            sys.exit(1)
        is_root = name == ROOT_NAME
        if is_root:
            if snap["parent_department"] or not snap["is_group"] or snap["company"]:
                print(f"FAIL pre-validate {name}: root shape drift")
                sys.exit(1)
        elif snap["parent_department"] != "All Departments":
            print(f"FAIL pre-validate {name}: parent drift")
            sys.exit(1)
        plan.append({"name": name, "value": value, "already": bool(snap[AR_FIELD]),
                     "root": is_root})
    site_ar = frappe.db.count("Department", {AR_FIELD: ("!=", "")})
    excluded = frappe.db.count("Department") - len(plan)
    if site_ar != 0 or excluded != 262:
        print(f"FAIL pre-state: arabic={site_ar} excluded={excluded}")
        sys.exit(1)
    print(f"PREVALIDATE_OK rows={len(plan)} plain=13 r3b_root=1 site_arabic=0 excluded=262")

    # Apply through the standard document lifecycle.
    import erpnext.setup.doctype.department.department as dept_mod
    orig_get_root_of = dept_mod.get_root_of
    results = []
    try:
        for item in plan:
            if item["already"]:
                print(f"SKIP Department {item['name']!r} already applied")
                results.append({"name": item["name"], "action": "skip-already-applied"})
                continue
            d = frappe.get_doc("Department", item["name"])
            label_before = d.get(LABEL_FIELD)
            parent_before = d.get("parent_department")
            company_before = d.get("company")
            lft_before, rgt_before = d.get("lft"), d.get("rgt")
            before_fields = dict(d.as_dict())
            d.set(AR_FIELD, item["value"])
            # Amendment V2 (apply attempt 1, fail-closed): stale `old_parent` bookkeeping
            # made update_nsm() take the sibling-repositioning branch (lft/rgt would have
            # been rewritten across the tree). Pre-syncing old_parent to the unchanged
            # parent keeps update_nsm on its normal no-move path — the unconditional
            # old_parent sync below runs in both branches, so no field write is added.
            d.set("old_parent", d.get("parent_department") or None)
            if item["root"]:
                dept_mod.get_root_of = lambda doctype: None  # disclosed R3B, P3-proven
                d.flags.ignore_mandatory = True             # root has NULL company by design
                path = "R3B_ROOT"
            else:
                path = "PLAIN"
            try:
                d.save()
            finally:
                if item["root"]:
                    dept_mod.get_root_of = orig_get_root_of
            if d.get(LABEL_FIELD) != label_before:
                raise RuntimeError(f"{item['name']}: department_name changed")
            if d.get("parent_department") != parent_before or d.get("company") != company_before:
                raise RuntimeError(f"{item['name']}: tree identity changed")
            if (d.get("lft"), d.get("rgt")) != (lft_before, rgt_before):
                raise RuntimeError(f"{item['name']}: lft/rgt changed")
            if d.get(AR_FIELD) != item["value"]:
                raise RuntimeError(f"{item['name']}: value not stored")
            expected = normalize_arabic(item["value"])
            if d.get(NORM_FIELD) != expected:
                raise RuntimeError(f"{item['name']}: norm not server-derived")
            after_fields = dict(d.as_dict())
            allowed = {AR_FIELD, NORM_FIELD, "old_parent"}
            changed = {k for k in before_fields
                       if before_fields.get(k) != after_fields.get(k)
                       and k not in ("modified", "modified_by", "idx")}
            unexpected = changed - allowed
            if unexpected:
                raise RuntimeError(f"{item['name']}: unexpected field changes {sorted(unexpected)}")
            print(f"WRITE Department {item['name']!r} value={sha16(item['value'])} "
                  f"norm={sha16(expected)} identity=unchanged tree=unchanged "
                  f"fields_changed={sorted(changed)} {path}")
            results.append({"name": item["name"], "action": "written",
                            "value": item["value"], "norm": expected, "path": path})
        frappe.db.commit()
    except Exception as exc:  # noqa: BLE001 - fail-closed rollback
        frappe.db.rollback()
        print(f"FAIL during apply, transaction rolled back: {type(exc).__name__}: {exc}")
        sys.exit(1)
    finally:
        dept_mod.get_root_of = orig_get_root_of  # never leak the patch

    private = {
        "proposal_sha256": APPROVED_SHA,
        "dry_run_sha256": hashlib.sha256(dry_raw).hexdigest(),
        "apply_utc": frappe.utils.now_datetime().isoformat(),
        "written": sum(1 for r in results if r["action"] == "written"),
        "skipped": sum(1 for r in results if r["action"] != "written"),
        "root_r3b": sum(1 for r in results if r.get("path") == "R3B_ROOT"),
        "results": results,
    }
    with open(f"{PRIVATE}/apply.json", "w", encoding="utf-8") as fh:
        json.dump(private, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    apply_sha = hashlib.sha256(open(f"{PRIVATE}/apply.json", "rb").read()).hexdigest()
    print(f"SUMMARY written={private['written']} skipped={private['skipped']} failed=0 "
          f"r3b_root={private['root_r3b']}")
    print(f"PRIVATE apply.json sha256={apply_sha}")
    print("APPLY RESULT: PASS")


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()
