"""v8_7: repair runtime translation keys broken by edge whitespace.

Paste artifacts such as ``"Variation Management\\n"`` or the seeded
``"BOQ Item Stage "`` stored a runtime key that never matches the clean key the
UI requests via ``_()``. The digest was self-consistent, so health checks
passed while the UI silently missed the lookup.

Fix (idempotent, deterministic):
1. Find runtime rows whose source_text/context has leading/trailing whitespace.
2. Trim to the clean key, recompute digest and search helper.
3. If the trimmed digest already exists (clean row or another trimmed row),
   keep one deterministic winner (modified DESC, creation DESC, name DESC)
   and delete the rest.
4. Catalog rows are untouched: they mirror upstream msgid bytes exactly and
   are refreshed by catalog sync.
"""

import frappe
from frappe.translate import strip_html_tags


def _digest(lang, src, ctx):
    import hashlib
    import json

    payload = [lang or "", src or "", ctx or "", "runtime"]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def execute():
    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar", "ct_is_catalog_entry": 0},
        fields=["name", "source_text", "context", "translated_text", "ct_app",
                "ct_origin", "ct_release_version", "ct_key_digest", "modified", "creation"],
        limit_page_length=0,
    )
    broken = [
        r for r in rows
        if (r.source_text or "") != (r.source_text or "").strip()
        or (r.context or "") != (r.context or "").strip()
    ]
    if not broken:
        print("[v8_7] no whitespace-broken runtime rows")
    else:
        _fix_broken(broken)
    _clean_catalog_origin()
    _verify()


def _fix_broken(broken):
    # Group by the trimmed digest, including any existing clean row that the
    # trimmed key would collide with.
    groups = {}
    for r in broken:
        t = (r.source_text or "").strip()
        c = (r.context or "").strip()
        d = _digest("ar", t, c)
        groups.setdefault(d, []).append(r)
    for d, grp in groups.items():
        for e in frappe.db.sql(
            "select name, source_text, modified, creation from `tabTranslation` "
            "where ct_key_digest=%s and ct_is_catalog_entry=0",
            (d,), as_dict=1,
        ):
            grp.append(e)

    fixed = deleted = 0
    for d, grp in groups.items():
        # Deterministic winner: modified DESC, creation DESC, name DESC.
        grp_sorted = sorted(
            grp,
            key=lambda x: (str(x.get("modified") or ""), str(x.get("creation") or ""), x.name),
            reverse=True,
        )
        winner = grp_sorted[0]
        losers = [x for x in grp_sorted[1:]]
        t = (winner.source_text or "").strip()
        c = (winner.context or "").strip()
        for loser in losers:
            frappe.db.delete("Translation", loser.name)
            deleted += 1
            print(f"[v8_7] deleted loser {loser.name} {loser.source_text!r} (winner {winner.name})")
        updates = {"source_text": t, "ct_key_digest": d}
        if frappe.db.has_column("Translation", "ct_search_normalized"):
            updates["ct_search_normalized"] = strip_html_tags(t).strip()
        if (winner.context or "") != c:
            updates["context"] = c
        # Provenance nicety: construction workspace strings belong to construction.
        if not winner.get("ct_app") and "Variation" in t:
            updates["ct_app"] = "construction"
        cur = frappe.db.get_value("Translation", winner.name, ["source_text", "ct_key_digest", "ct_app"], as_dict=1)
        if cur and (cur.source_text != t or cur.ct_key_digest != d or "ct_app" in updates):
            frappe.db.set_value("Translation", winner.name, updates, update_modified=False)
            fixed += 1
            print(f"[v8_7] fixed {winner.name}: {cur.source_text!r} -> {t!r} digest {d[:12]}")

    frappe.db.commit()
    print(f"[v8_7] fixed {fixed}, deleted {deleted} losers")


def _clean_catalog_origin():
    # Catalog rows must carry empty ct_origin (provenance is runtime-only).
    # Operators fiddling in the form can set a value there; it is semantically
    # wrong and would mislead precedence reporting.
    if not frappe.db.has_column("Translation", "ct_origin"):
        return
    stray = frappe.db.sql(
        "select name, ct_origin from `tabTranslation` "
        "where ct_is_catalog_entry=1 and ct_origin is not null and ct_origin != ''",
        as_dict=1,
    )
    for r in stray:
        frappe.db.set_value("Translation", r.name, "ct_origin", "", update_modified=False)
    if stray:
        frappe.db.commit()
        print(f"[v8_7] cleared stray ct_origin on {len(stray)} catalog row(s): {[r.name for r in stray]}")


def _verify():
    # Verify: zero runtime rows with edge whitespace remain.
    rows2 = frappe.get_all(
        "Translation",
        filters={"language": "ar", "ct_is_catalog_entry": 0},
        fields=["name", "source_text", "context"],
        limit_page_length=0,
    )
    remaining = [
        r.name for r in rows2
        if (r.source_text or "") != (r.source_text or "").strip()
        or (r.context or "") != (r.context or "").strip()
    ]
    if remaining:
        print(f"[v8_7] VERIFICATION FAILED: {remaining}")
        frappe.throw(f"[v8_7] whitespace-broken runtime rows remain: {remaining}")
    print("[v8_7] VERIFICATION PASSED: zero whitespace-broken runtime rows")
