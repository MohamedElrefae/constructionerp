"""P1 migration: add translation identity fields, backfill digests, dedup, enforce constraints."""

import hashlib
import json

import frappe
from frappe.translate import strip_html_tags


def _digest(lang, src, ctx, app, is_catalog):
    if "\x00" in (src or "") or "\x00" in (ctx or "") or "\x00" in (app or ""):
        frappe.throw("NUL in key")
    payload = [lang or "", src or "", ctx or "", app or "", "catalog"] if is_catalog else [lang or "", src or "", ctx or "", "runtime"]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _norm(src):
    return strip_html_tags(src or "").strip()


def execute():
    from construction.setup.translation_catalog_fields import ensure_custom_fields

    ensure_custom_fields()
    frappe.db.commit()

    has_digest = frappe.db.has_column("Translation", "ct_key_digest")
    has_norm = frappe.db.has_column("Translation", "ct_search_normalized")
    has_origin = frappe.db.has_column("Translation", "ct_origin")
    if not has_digest:
        print("[v8_6] ct_key_digest column not yet created, skipping backfill")
        return

    batch = 500
    total_backfilled = 0
    for is_catalog in (1, 0):
        offset = 0
        while True:
            rows = frappe.get_all(
                "Translation",
                filters={"ct_is_catalog_entry": is_catalog} if frappe.db.has_column("Translation", "ct_is_catalog_entry") else {},
                fields=["name", "language", "source_text", "context", "ct_app", "ct_key_digest", "ct_search_normalized", "ct_origin"],
                limit_start=offset,
                limit_page_length=batch,
            )
            if not rows:
                break
            for r in rows:
                lang = r.language or ""
                src = r.source_text or ""
                ctx = r.context or ""
                app = r.get("ct_app") or ""
                digest = _digest(lang, src, ctx, app, bool(is_catalog))
                norm = _norm(src)
                updates = {}
                if (r.get("ct_key_digest") or "") != digest:
                    updates["ct_key_digest"] = digest
                if has_norm and (r.get("ct_search_normalized") or "") != norm:
                    updates["ct_search_normalized"] = norm
                if not is_catalog and has_origin:
                    cur_origin = (r.get("ct_origin") or "").strip()
                    if not cur_origin:
                        updates["ct_origin"] = "Site Override"
                if updates:
                    frappe.db.set_value("Translation", r.name, updates, update_modified=False)
                    total_backfilled += 1
            offset += batch
            if len(rows) < batch:
                break
    frappe.db.commit()
    print(f"[v8_6] Backfilled {total_backfilled} digests/normalized/origin")

    dup_groups = frappe.db.sql(
        """
        select ct_key_digest, group_concat(name) names, count(*) c
        from `tabTranslation` where language='ar' and ct_key_digest is not null and ct_key_digest != ''
        group by ct_key_digest having c>1
        """
    )
    archived = 0
    deleted = 0
    for digest, names, c in dup_groups:
        name_list = names.split(",")
        rows = frappe.get_all(
            "Translation",
            filters={"name": ["in", name_list]},
            fields=["name", "modified", "creation", "ct_is_catalog_entry"],
            order_by="modified desc, creation desc, name desc",
        )
        winner = rows[0].name
        losers = [r.name for r in rows[1:]]
        for los in losers:
            frappe.db.delete("Translation", los)
            deleted += 1
        archived += len(losers)
    if deleted:
        frappe.db.commit()
    print(f"[v8_6] Dedup: {len(dup_groups)} groups, deleted {deleted}")

    try:
        frappe.db.sql("select ct_key_digest from `tabTranslation` limit 1")
        idx = frappe.db.sql("show index from `tabTranslation` where Column_name='ct_key_digest'")
        if not idx:
            frappe.db.sql("alter table `tabTranslation` add unique index `ct_translation_key_digest` (`ct_key_digest`)")
            print("[v8_6] Created unique index ct_translation_key_digest")
            frappe.db.commit()
        else:
            print("[v8_6] Unique index already exists")
    except Exception as e:
        print(f"[v8_6] Index creation skipped/failed: {e}")

    try:
        nulls = frappe.db.sql("select count(*) from `tabTranslation` where ct_key_digest is null or ct_key_digest=''")[0][0]
        if nulls:
            print(f"[v8_6] WARNING: {nulls} null digests remain")
        else:
            print("[v8_6] Zero null digests")
    except Exception as e:
        print(f"[v8_6] null check failed: {e}")

    try:
        if has_origin:
            frappe.db.sql(
                """
                alter table `tabTranslation` add constraint `chk_ct_origin`
                check (
                    (ct_is_catalog_entry = 1 and (ct_origin is null or ct_origin = '' or ct_origin in ('Packaged Release','Site Override')))
                    or
                    (ct_is_catalog_entry = 0 and ct_origin in ('Packaged Release','Site Override'))
                    or
                    (ct_is_catalog_entry is null and (ct_origin is null or ct_origin in ('Packaged Release','Site Override')))
                )
                """
            )
            print("[v8_6] Added CHECK constraint chk_ct_origin")
            frappe.db.commit()
    except Exception as e:
        if "Duplicate" in str(e) or "already exists" in str(e) or "chk_ct_origin" in str(e):
            print("[v8_6] CHECK constraint already exists")
        else:
            print(f"[v8_6] CHECK constraint skipped: {e}")

    verify_dup = frappe.db.sql("select count(*) from (select ct_key_digest from `tabTranslation` where language='ar' and ct_key_digest is not null group by ct_key_digest having count(*)>1) t")[0][0]
    verify_null = frappe.db.sql("select count(*) from `tabTranslation` where ct_key_digest is null or ct_key_digest=''")[0][0]
    print(f"[v8_6] Verification: dup_groups={verify_dup} null_digests={verify_null}")
    if verify_dup or verify_null:
        print("[v8_6] VERIFICATION FAILED")
    else:
        print("[v8_6] VERIFICATION PASSED")
