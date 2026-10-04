"""Read-only probe: would the registry half cover the vendor's search fields?

For every active registry entry, compare:
  vendor_fields   = {"name"} | {title_field} | meta.get_search_fields()
                    (the candidate set frappe/desk/search.py:169-179 filters
                    down to by fieldtype)
  registry_fields = {"name"} | {f in entry.search.fields that the doctype has}

Coverage holds when vendor_fields is a subset of registry_fields. It is the
condition under which skipping the vendor baseline cannot lose a row that the
stock endpoint would have found (candidate A6).
"""

import json

import frappe

FIELD_TYPES = {
    "Autocomplete",
    "Data",
    "Text",
    "Small Text",
    "Long Text",
    "Link",
    "Select",
    "Read Only",
    "Text Editor",
}


def probe():
    from construction.services.bilingual_registry import load_registry

    data, errors = load_registry()
    rows = []
    for doctype, entry in sorted((data.get("doctypes") or {}).items()):
        if not isinstance(entry, dict) or entry.get("state") != "active":
            continue
        meta = frappe.get_meta(doctype)
        search_fields = ["name"]
        if meta.title_field:
            search_fields.append(meta.title_field)
        if meta.search_fields:
            search_fields.extend(meta.get_search_fields())

        vendor_candidate = set()
        vendor_actual = set()
        for f in search_fields:
            name = (f or "").strip()
            if not name:
                continue
            vendor_candidate.add(name)
            if name == "name":
                vendor_actual.add(name)
                continue
            fmeta = meta.get_field(name)
            if fmeta and fmeta.fieldtype in FIELD_TYPES:
                vendor_actual.add(name)

        declared = entry.get("search", {}).get("fields") or []
        registry = {"name"} | {f for f in declared if f == "name" or meta.has_field(f)}

        missing_candidate = sorted(vendor_candidate - registry)
        missing_actual = sorted(vendor_actual - registry)
        rows.append(
            {
                "doctype": doctype,
                "title_field": meta.title_field,
                "meta_search_fields": sorted(vendor_candidate - {"name"}),
                "registry_search_fields": sorted(f for f in declared),
                "vendor_actual_fields": sorted(vendor_actual),
                "missing_actual": missing_actual,
                "missing_candidate": missing_candidate,
                "covers_actual": not missing_actual,
                "covers_candidate": not missing_candidate,
                "translated_doctype": bool(meta.translated_doctype),
            }
        )
    return {"registry_load_errors": list(errors or []), "entries": rows}


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    out = probe()
    covered_actual = [r for r in out["entries"] if r["covers_actual"]]
    covered_candidate = [r for r in out["entries"] if r["covers_candidate"]]
    translated = [r for r in out["entries"] if r["translated_doctype"]]
    print("REGISTRY_LOAD_ERRORS:", json.dumps(out["registry_load_errors"]))
    print(
        "COVERAGE:",
        json.dumps(
            {
                "entries": len(out["entries"]),
                "covers_vendor_actual_fields": len(covered_actual),
                "covers_vendor_candidate_fields": len(covered_candidate),
                "translated_doctypes": [r["doctype"] for r in translated],
            }
        ),
    )
    for row in out["entries"]:
        status = "OK " if row["covers_candidate"] else "GAP"
        print(
            f"{status} {row['doctype']:<24} vendor={row['vendor_actual_fields']} "
            f"registry={row['registry_search_fields']} "
            f"missing_candidate={row['missing_candidate']}"
        )
    json.dump(
        out,
        open(
            "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/"
            "bilingual-desk-link-dispatch/evidence/registry-field-coverage.json",
            "w",
            encoding="utf-8",
        ),
        indent=1,
        sort_keys=True,
        ensure_ascii=False,
    )
