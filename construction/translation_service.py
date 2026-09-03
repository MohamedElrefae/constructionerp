import hashlib
import json

import frappe
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY, strip_html_tags
from frappe.utils import cint, now_datetime


def _exact_source(source):
    return source or ""


def _compute_digest(language, source_text, context, ct_app, is_catalog):
    source_text = _exact_source(source_text)
    if "\x00" in source_text or "\x00" in (context or "") or "\x00" in (ct_app or "") or "\x00" in (language or ""):
        frappe.throw("Translation key contains embedded NUL character")
    if is_catalog:
        payload = [language or "", source_text, context or "", ct_app or "", "catalog"]
    else:
        payload = [language or "", source_text, context or "", "runtime"]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _search_normalized(source_text):
    return strip_html_tags(source_text or "").strip()


def _ensure_no_nul(value, field):
    if value and "\x00" in value:
        frappe.throw(f"{field} contains embedded NUL")


def _is_catalog_row(row):
    return bool(cint(row.get("ct_is_catalog_entry")))


def _get_runtime_rows(language, source_text, context=""):
    has_catalog = frappe.db.has_column("Translation", "ct_is_catalog_entry")
    has_digest = frappe.db.has_column("Translation", "ct_key_digest")
    if has_digest:
        digest = _compute_digest(language, source_text, context, None, False)
        filters = {"language": language, "ct_key_digest": digest}
        if has_catalog:
            filters["ct_is_catalog_entry"] = 0
        rows = frappe.get_all(
            "Translation",
            filters=filters,
            fields=["name", "context", "creation", "modified", "ct_origin", "ct_release_version"],
            order_by="modified desc, creation desc, name desc",
            limit_page_length=0,
        )
        return [r for r in rows if (r.context or "") == (context or "")]
    fields = ["name", "context", "creation", "modified"]
    if has_catalog:
        fields.append("ct_is_catalog_entry")
    rows = frappe.get_all(
        "Translation",
        filters={"language": language, "source_text": source_text},
        fields=fields,
        order_by="modified desc, creation desc, name desc",
        limit_page_length=0,
    )
    return [
        r
        for r in rows
        if (r.context or "") == (context or "") and (not has_catalog or not cint(r.ct_is_catalog_entry))
    ]


def get_runtime_rows(language, source_text, context=""):
    return _get_runtime_rows(language, source_text, context)


def get_effective_translation(language, source_text, context=""):
    if frappe.db.has_column("Translation", "ct_is_catalog_entry"):
        rows = _get_runtime_rows(language, source_text, context)
        if rows:
            return frappe.db.get_value("Translation", rows[0].name, "translated_text") or ""
    try:
        from frappe.translate import get_all_translations

        return get_all_translations(language).get(source_text if not context else f"{source_text}:{context}", "") or frappe.db.get_value(
            "Translation", {"language": language, "source_text": source_text, "context": context or ""}, "translated_text"
        ) or ""
    except Exception:
        return frappe.db.get_value(
            "Translation", {"language": language, "source_text": source_text, "context": context or ""}, "translated_text"
        ) or ""


def _prepare_digest_and_search(doc, is_catalog):
    lang = doc.language or ""
    src = doc.source_text or ""
    ctx = doc.context or ""
    app = doc.get("ct_app") or ""
    _ensure_no_nul(src, "source_text")
    _ensure_no_nul(doc.translated_text or "", "translated_text")
    _ensure_no_nul(ctx, "context")
    digest = _compute_digest(lang, src, ctx, app, is_catalog)
    normalized = _search_normalized(src)
    return digest, normalized


def _apply_origin(doc, origin, release_version, released_by):
    if doc.get("ct_is_catalog_entry"):
        if doc.meta.has_field("ct_origin"):
            doc.ct_origin = ""
        return
    if not origin:
        origin = "Site Override"
    if origin not in ("Packaged Release", "Site Override"):
        frappe.throw("ct_origin must be Packaged Release or Site Override for runtime rows")
    doc.ct_origin = origin
    if release_version and doc.meta.has_field("ct_release_version"):
        doc.ct_release_version = release_version
    if doc.meta.has_field("ct_released_at"):
        doc.ct_released_at = now_datetime()
    if released_by and doc.meta.has_field("ct_released_by"):
        doc.ct_released_by = released_by


def _runtime_source(source_text):
    """Normalize a runtime lookup key.

    Runtime keys must match what the UI requests via ``_()``. Accidental
    leading/trailing whitespace (paste artifacts such as a trailing newline)
    makes the stored key diverge from the requested key while staying
    self-consistent in the digest, so strip it here. Internal whitespace is
    preserved (some legitimate msgids contain spaces mid-string).
    """
    return (source_text or "").strip()


def upsert_runtime_translation(
    source_text,
    translated_text,
    language="ar",
    context="",
    app=None,
    origin="Site Override",
    release_version=None,
    reason=None,
    ignore_permissions=False,
    released_by=None,
):
    source_text = _runtime_source(source_text)
    translated_text = translated_text or ""
    context = (context or "").strip()
    if not source_text or not language or not translated_text:
        return None
    _ensure_no_nul(source_text, "source_text")
    _ensure_no_nul(translated_text, "translated_text")
    _ensure_no_nul(context, "context")
    rows = _get_runtime_rows(language, source_text, context)
    is_new = not rows
    if rows:
        doc = frappe.get_doc("Translation", rows[0].name)
        existing_origin = doc.get("ct_origin") or ""
        if existing_origin == "Site Override" and origin == "Packaged Release":
            return {"name": doc.name, "skipped": True, "reason": "drift_site_override"}
        if existing_origin == "Packaged Release" and origin == "Packaged Release" and release_version:
            existing_ver = doc.get("ct_release_version") or ""
            if existing_ver and release_version and not _is_newer_version(release_version, existing_ver):
                return {"name": doc.name, "skipped": True, "reason": "not_newer_version"}
        doc.translated_text = translated_text
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Translation",
                "language": language,
                "source_text": source_text,
                "translated_text": translated_text,
                "context": context,
            }
        )
    if doc.meta.has_field("ct_is_catalog_entry"):
        doc.ct_is_catalog_entry = 0
    if app and doc.meta.has_field("ct_app"):
        doc.ct_app = app
    if doc.meta.has_field("ct_review_status"):
        doc.ct_review_status = "Released"
    if doc.meta.has_field("ct_key_digest"):
        doc.ct_key_digest = _compute_digest(language, source_text, context, None, False)
    if doc.meta.has_field("ct_search_normalized"):
        doc.ct_search_normalized = _search_normalized(source_text)
    _apply_origin(doc, origin, release_version, released_by or frappe.session.user if hasattr(frappe.session, "user") else None)
    try:
        if doc.is_new():
            doc.insert(ignore_permissions=ignore_permissions)
        else:
            doc.save(ignore_permissions=ignore_permissions)
    except (frappe.exceptions.DuplicateEntryError, frappe.exceptions.UniqueValidationError):
        # Race or trim-collision: converge on the existing canonical row.
        rows2 = _get_runtime_rows(language, source_text, context)
        if rows2:
            doc2 = frappe.get_doc("Translation", rows2[0].name)
            doc2.translated_text = translated_text
            _apply_origin(doc2, origin, release_version, released_by)
            if doc2.meta.has_field("ct_key_digest"):
                doc2.ct_key_digest = _compute_digest(language, source_text, context, None, False)
            if doc2.meta.has_field("ct_search_normalized"):
                doc2.ct_search_normalized = _search_normalized(source_text)
            doc2.save(ignore_permissions=ignore_permissions)
            invalidate_translation_caches(language)
            return doc2.name
        raise
    invalidate_translation_caches(language)
    return doc.name if isinstance(doc.name, str) else doc.name


def delete_or_revert_runtime_translation(language, source_text, context="", reason=None):
    rows = _get_runtime_rows(language, _runtime_source(source_text), (context or "").strip())
    if not rows:
        return {"deleted": 0}
    has_origin = frappe.db.has_column("Translation", "ct_origin")
    has_digest = frappe.db.has_column("Translation", "ct_key_digest")
    deleted = 0
    for r in rows:
        doc = frappe.get_doc("Translation", r.name)
        origin = doc.get("ct_origin") or ""
        if origin == "Packaged Release":
            packaged = None
            if has_origin and has_digest:
                try:
                    import csv
                    from pathlib import Path

                    p = Path(frappe.get_app_path("construction", "data", "translations", "approved_ar_overrides.csv"))
                    if p.exists():
                        with p.open(encoding="utf-8") as fh:
                            reader = csv.DictReader(fh)
                            for row in reader:
                                if (
                                    (row.get("language") or "ar") == language
                                    and (row.get("source_text") or "") == source_text
                                    and (row.get("context") or "") == (context or "")
                                    and (row.get("release_status") or "") == "Released"
                                ):
                                    packaged = row.get("translated_text") or ""
                                    break
                        if packaged:
                            doc.translated_text = packaged
                            if doc.meta.has_field("ct_release_version"):
                                doc.ct_release_version = row.get("release_version") or ""
                            doc.save(ignore_permissions=True)
                            continue
                except Exception:
                    pass
            frappe.db.delete("Translation", r.name)
            deleted += 1
        else:
            frappe.db.delete("Translation", r.name)
            deleted += 1
    if deleted or rows:
        invalidate_translation_caches(language)
    return {"deleted": deleted, "kept": len(rows) - deleted}


def sync_catalog(apps=None, dry_run=True):
    from construction.api.translation_tools import sync_translation_catalog as _sync

    return _sync(apps=apps, dry_run=dry_run)


def import_released_overrides(path=None, dry_run=True, _skip_permission=False):
    import csv
    from pathlib import Path

    if not _skip_permission:
        frappe.only_for("System Manager")
    path = Path(path) if path else Path(frappe.get_app_path("construction", "data", "translations", "approved_ar_overrides.csv"))
    if not path.exists():
        return {"total": 0, "created": 0, "updated": 0, "skipped": 0, "drift": 0, "preview": []}
    dry_run = bool(cint(dry_run) if isinstance(dry_run, str) else dry_run)
    rows = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if (row.get("release_status") or "").strip() != "Released":
                continue
            a1 = (row.get("a1_reviewer") or "").strip()
            a2 = (row.get("a2_reviewer") or "").strip()
            a3 = (row.get("a3_reviewer") or "").strip()
            a1_at = (row.get("a1_approved_at") or "").strip()
            a2_at = (row.get("a2_approved_at") or "").strip()
            a3_at = (row.get("a3_approved_at") or "").strip()
            if not a1 or not a3 or not a1_at or not a3_at:
                frappe.throw(f"Quorum missing for {row.get('source_text')}: A1/A3 reviewer and timestamp required")
            if not a2:
                frappe.throw(f"Quorum missing for {row.get('source_text')}: A2 reviewer required (use Not Applicable for non-domain)")
            if a1 in ("A1", "A2", "A3") or a2 in ("A1", "A2", "A3") or a3 in ("A1", "A2", "A3"):
                frappe.throw(f"Placeholder reviewer not allowed for {row.get('source_text')}: {a1}/{a2}/{a3}")
            rows.append(row)
    total = len(rows)
    created = updated = skipped = drift = 0
    preview = []
    for row in rows:
        lang = (row.get("language") or "ar").strip() or "ar"
        src = row.get("source_text") or ""
        ctx = row.get("context") or ""
        val = row.get("translated_text") or ""
        if not src or not val:
            skipped += 1
            continue
        if "\x00" in src or "\x00" in val:
            skipped += 1
            continue
        ver = (row.get("release_version") or "").strip()
        expected_app = (row.get("ct_app") or "").strip()
        existing_rows = _get_runtime_rows(lang, src, ctx)
        existing_val = ""
        existing_origin = ""
        existing_app = ""
        existing_ver = ""
        if existing_rows:
            existing_val = frappe.db.get_value("Translation", existing_rows[0].name, "translated_text") or ""
            existing_origin = frappe.db.get_value("Translation", existing_rows[0].name, "ct_origin") or ""
            existing_app = frappe.db.get_value("Translation", existing_rows[0].name, "ct_app") or ""
            existing_ver = frappe.db.get_value("Translation", existing_rows[0].name, "ct_release_version") or ""
        needs_update = False
        if existing_val != val:
            needs_update = True
        if (existing_app or "") != expected_app:
            needs_update = True
        if existing_origin != "Packaged Release" and existing_rows:
            needs_update = True
        if not needs_update:
            if existing_origin == "Packaged Release" and ver and existing_ver and not _is_newer_version(ver, existing_ver):
                skipped += 1
                continue
            if existing_rows:
                skipped += 1
                continue
        if (existing_app or "") != expected_app and existing_rows and existing_val == val and existing_origin == "Packaged Release":
            if not dry_run:
                frappe.db.set_value("Translation", existing_rows[0].name, {"ct_app": expected_app, "ct_origin": "Packaged Release", "ct_release_version": ver, "ct_released_at": frappe.utils.now(), "ct_released_by": row.get("a1_reviewer") or "packaged"}, update_modified=False)
                try:
                    catalog_rows = frappe.get_all(
                        "Translation",
                        filters={"language": lang, "source_text": src, "context": ctx or "", "ct_is_catalog_entry": 1},
                        fields=["name", "ct_app"],
                        limit_page_length=0,
                    )
                    for crow in catalog_rows:
                        if expected_app and crow.ct_app and crow.ct_app != expected_app:
                            continue
                        if (crow.ct_app or "") != expected_app:
                            frappe.db.set_value("Translation", crow.name, {"ct_app": expected_app}, update_modified=False)
                except Exception:
                    pass
            updated += 1
            preview.append({"source_text": src, "context": ctx, "before": existing_val, "after": val, "action": "metadata_repair"})
            continue
        if existing_origin == "Site Override" and existing_rows:
            drift += 1
            preview.append({"source_text": src, "context": ctx, "before": existing_val, "after": val, "action": "drift_site_override"})
            continue
        if existing_origin == "Packaged Release" and ver and existing_ver and not _is_newer_version(ver, existing_ver):
            skipped += 1
            continue
        action = "update" if existing_rows else "create"
        preview.append({"source_text": src, "context": ctx, "before": existing_val, "after": val, "action": action})
        if dry_run:
            if action == "create":
                created += 1
            else:
                updated += 1
            continue
        res = upsert_runtime_translation(src, val, language=lang, context=ctx, app=expected_app or None, origin="Packaged Release", release_version=ver, ignore_permissions=True, released_by=row.get("a1_reviewer") or "packaged")
        if isinstance(res, dict) and res.get("skipped"):
            if res.get("reason") == "drift_site_override":
                drift += 1
            else:
                skipped += 1
        elif action == "create":
            created += 1
        else:
            updated += 1
        if not dry_run and not isinstance(res, dict):
            try:
                catalog_rows = frappe.get_all(
                    "Translation",
                    filters={"language": lang, "source_text": src, "context": ctx or "", "ct_is_catalog_entry": 1},
                    fields=["name", "ct_app", "translated_text", "ct_po_translation", "ct_review_status"],
                    limit_page_length=0,
                )
                for crow in catalog_rows:
                    if expected_app and crow.ct_app and crow.ct_app != expected_app:
                        continue
                    if crow.translated_text != val or (crow.ct_review_status or "") != "Released":
                        frappe.db.set_value(
                            "Translation",
                            crow.name,
                            {"translated_text": val, "ct_review_status": "Released", "ct_proposed_translation": ""},
                            update_modified=False,
                        )
            except Exception:
                pass
    if not dry_run:
        try:
            frappe.cache.set_value("translation_last_drift_check", frappe.utils.now())
        except Exception:
            pass
    if not dry_run and (created or updated):
        frappe.db.commit()
    return {"total": total, "created": created, "updated": updated, "skipped": skipped, "drift": drift, "preview": preview, "dry_run": dry_run}


def submit_review_decision(key, persona, decision, notes="", references=""):
    frappe.only_for("Translator")
    if persona not in ("A1", "A2", "A3"):
        frappe.throw("persona must be A1, A2, or A3")
    if not frappe.db.has_column("Translation", "ct_proposed_translation"):
        frappe.throw("ct_proposed_translation field not yet migrated")
    source_text, context, ct_app = key if isinstance(key, (list, tuple)) and len(key) == 3 else (key, "", "")
    if isinstance(key, dict):
        source_text = key.get("source_text") or ""
        context = key.get("context") or ""
        ct_app = key.get("ct_app") or ""
    has_catalog = frappe.db.has_column("Translation", "ct_is_catalog_entry")
    if not has_catalog:
        frappe.throw("catalog fields not present")
    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar", "source_text": source_text, "ct_is_catalog_entry": 1},
        fields=["name", "context", "ct_app", "ct_review_status", "ct_proposed_translation"],
        limit_page_length=0,
    )
    target = None
    for r in rows:
        if (r.context or "") == (context or "") and (ct_app == "" or (r.ct_app or "") == ct_app):
            target = r
            break
    if not target:
        frappe.throw("catalog row not found for key")
    field_map = {"A1": "a1_status", "A2": "a2_status", "A3": "a3_status"}
    frappe.db.set_value("Translation", target.name, {f"ct_{field_map[persona].lower()}": decision})
    return target.name


def release_proposal(key, release_version):
    frappe.only_for("System Manager")
    if isinstance(key, dict):
        source_text = key.get("source_text") or ""
        context = key.get("context") or ""
        ct_app = key.get("ct_app") or ""
        translated = key.get("translated_text") or key.get("ct_proposed_translation") or ""
    elif isinstance(key, (list, tuple)):
        source_text, context, ct_app, translated = (list(key) + ["", "", "", ""])[:4]
    else:
        frappe.throw("invalid key")
    if not translated:
        row = frappe.db.get_value("Translation", {"language": "ar", "source_text": source_text, "ct_is_catalog_entry": 1, "context": context or ""}, ["ct_proposed_translation"], as_dict=False)
        translated = row or ""
    if not translated:
        frappe.throw("no proposed translation to release")
    upsert_runtime_translation(source_text, translated, language="ar", context=context, app=ct_app or None, origin="Packaged Release", release_version=release_version, ignore_permissions=True)
    if frappe.db.has_column("Translation", "ct_is_catalog_entry"):
        for r in frappe.get_all("Translation", filters={"language": "ar", "source_text": source_text, "ct_is_catalog_entry": 1}, fields=["name", "context"], limit_page_length=0):
            if (r.context or "") == (context or ""):
                frappe.db.set_value("Translation", r.name, {"ct_review_status": "Released", "ct_proposed_translation": ""})
    invalidate_translation_caches("ar")
    return True


def invalidate_translation_caches(language):
    frappe.cache.hdel(USER_TRANSLATION_KEY, language)
    frappe.cache.hdel(MERGED_TRANSLATION_KEY, language)
    frappe.cache.delete_value(keys=["bootinfo", USER_TRANSLATION_KEY, MERGED_TRANSLATION_KEY])
    try:
        frappe.clear_cache()
    except Exception:
        pass


def _parse_version(v):
    try:
        parts = [int(x) for x in str(v).strip().split(".")]
        return tuple(parts)
    except Exception:
        return (0,)


def _is_newer_version(new_ver, old_ver):
    return _parse_version(new_ver) > _parse_version(old_ver)


def _compute_drift():
    import csv
    from pathlib import Path

    try:
        p = Path(frappe.get_app_path("construction", "data", "translations", "approved_ar_overrides.csv"))
        if not p.exists():
            return False, []
        payload_map = {}
        with p.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("release_status") or "").strip() != "Released":
                    continue
                key = (row.get("language") or "ar", row.get("source_text") or "", row.get("context") or "")
                payload_map[key] = row
        live_rows = frappe.get_all(
            "Translation",
            filters={"ct_origin": "Packaged Release", "language": "ar"},
            fields=["language", "source_text", "context", "translated_text", "ct_app", "ct_release_version"],
            limit_page_length=0,
        )
        live_map = {(r.language or "ar", r.source_text or "", r.context or ""): r for r in live_rows}
        drifts = []
        for key, prow in payload_map.items():
            live = live_map.get(key)
            if not live:
                drifts.append(f"missing live for {key}")
            else:
                if (live.translated_text or "") != (prow.get("translated_text") or ""):
                    drifts.append(f"value mismatch {key}")
                if (live.ct_app or "") != (prow.get("ct_app") or "").strip():
                    drifts.append(f"ct_app mismatch {key}")
                if (live.ct_release_version or "") != (prow.get("release_version") or "").strip():
                    drifts.append(f"version mismatch {key}")
        for key in live_map:
            if key not in payload_map:
                drifts.append(f"orphan live {key}")
        has_drift = bool(drifts)
        return has_drift, drifts
    except Exception as e:
        return False, [str(e)]


def get_translation_health():
    has_catalog = frappe.db.has_column("Translation", "ct_is_catalog_entry")
    has_digest = frappe.db.has_column("Translation", "ct_key_digest")
    has_origin = frappe.db.has_column("Translation", "ct_origin")
    try:
        import frappe.translate as _t

        loader_installed = getattr(_t.get_user_translations, "__name__", "") == "_get_user_translations_excluding_catalog"
    except Exception:
        loader_installed = False
    using_safe_fallback = False
    try:
        if has_catalog:
            frappe.db.sql("select ct_is_catalog_entry from `tabTranslation` limit 1")
        else:
            using_safe_fallback = True
    except Exception as e:
        if "Unknown column" in str(e) or "no such column" in str(e):
            using_safe_fallback = True
    has_duplicates = False
    has_null_digests = False
    constraint_present = False
    constraint_name = None
    if has_digest:
        try:
            dup = frappe.db.sql(
                "select ct_key_digest, count(*) c from `tabTranslation` where language='ar' and ct_key_digest is not null and ct_key_digest != '' group by ct_key_digest having c>1 limit 1"
            )
            has_duplicates = bool(dup)
            nulls = frappe.db.sql("select count(*) from `tabTranslation` where language='ar' and (ct_key_digest is null or ct_key_digest='') limit 1")[0][0]
            has_null_digests = bool(nulls)
            idx_rows = frappe.db.sql("show index from `tabTranslation` where Column_name='ct_key_digest'", as_dict=True)
            for r in idx_rows:
                if r.get("Non_unique") == 0 and r.get("Key_name") == "ct_translation_key_digest":
                    constraint_present = True
                    constraint_name = r.get("Key_name")
                    break
        except Exception:
            pass
    has_drift, drift_details = _compute_drift()
    last_drift_checked_at = frappe.utils.now() if has_digest else None
    if has_drift:
        try:
            frappe.cache.set_value("translation_last_drift", {"checked_at": last_drift_checked_at, "details": drift_details[:5]})
        except Exception:
            pass
    else:
        try:
            last_drift_checked_at = frappe.cache.get_value("translation_last_drift", {}).get("checked_at") if frappe.cache.get_value("translation_last_drift") else last_drift_checked_at
        except Exception:
            pass
    has_orphan = False
    try:
        if has_origin and frappe.db.has_column("Translation", "ct_review_status"):
            orphans = frappe.db.sql("select count(*) from `tabTranslation` where ct_review_status='Deprecated' and ct_origin='Site Override' limit 1")
            has_orphan = bool(orphans and orphans[0][0] > 0)
    except Exception:
        has_orphan = False
    last_catalog_sync = None
    last_release_import = None
    try:
        if frappe.db.has_column("Translation", "ct_catalog_synced_at"):
            row = frappe.db.sql("select max(ct_catalog_synced_at) from `tabTranslation` where ct_is_catalog_entry=1 limit 1")
            last_catalog_sync = row[0][0] if row and row[0] else None
        if has_origin and frappe.db.has_column("Translation", "ct_released_at"):
            row = frappe.db.sql("select max(ct_released_at) from `tabTranslation` where ct_origin is not null limit 1")
            last_release_import = row[0][0] if row and row[0] else None
        if not last_drift_checked_at:
            last_drift_checked_at = frappe.cache.get_value("translation_last_drift_check")
    except Exception:
        pass
    return {
        "loader_installed": bool(loader_installed),
        "using_safe_fallback": bool(using_safe_fallback),
        "has_duplicates": bool(has_duplicates),
        "has_null_digests": bool(has_null_digests),
        "constraint_present": bool(constraint_present),
        "constraint_name": constraint_name,
        "has_drift": bool(has_drift),
        "drift_details": drift_details[:10] if has_drift else [],
        "has_orphan_site_overrides": bool(has_orphan),
        "last_catalog_sync_at": str(last_catalog_sync) if last_catalog_sync else None,
        "last_release_import_at": str(last_release_import) if last_release_import else None,
        "last_drift_checked_at": str(last_drift_checked_at) if last_drift_checked_at else None,
    }


def assert_translation_health():
    h = get_translation_health()
    errors = []
    if not h["loader_installed"]:
        errors.append("loader not installed")
    if h["has_duplicates"]:
        errors.append("duplicate digests remain")
    if h["has_null_digests"]:
        errors.append("null digests remain")
    if not h["constraint_present"]:
        errors.append(f"digest unique constraint missing (found {h.get('constraint_name')})")
    if h.get("has_drift"):
        details = "; ".join(h.get("drift_details", [])[:3])
        errors.append(f"drift detected: {details}")
    if h.get("has_orphan_site_overrides"):
        errors.append("orphan site overrides remain")
    if h["using_safe_fallback"]:
        errors.append("using safe fallback (catalog fields missing)")
    if errors:
        frappe.throw("Translation health check failed: " + "; ".join(errors))
    return h


def import_released_overrides_hook():
    res = import_released_overrides(dry_run=False, _skip_permission=True)
    if res.get("drift"):
        frappe.throw(f"Translation drift detected during mandatory import: {res['drift']} drift(s) — {res['preview'][:2]}")
    if res.get("error"):
        frappe.throw(f"Translation import failed: {res['error']}")
    if res.get("total", 0) == 0:
        frappe.log_error("Translation import hook: no released rows found", "Translation Service")
    return res


@frappe.whitelist()
def get_translation_health_api():
    frappe.only_for("System Manager")
    return get_translation_health()


@frappe.whitelist()
def assert_translation_health_api():
    frappe.only_for("System Manager")
    return assert_translation_health()
