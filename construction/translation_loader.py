import frappe

try:
    import frappe.translate as _translate

    _original_get_user_translations = _translate.get_user_translations

    def _get_user_translations_excluding_catalog(lang: str):
        if not lang:
            return {}
        has_catalog = frappe.db.has_column("Translation", "ct_is_catalog_entry")
        if not has_catalog:
            try:
                return _original_get_user_translations(lang)
            except Exception as e:
                frappe.log_error(f"Translation loader fallback failed: {e}", "Translation Loader")
                return {}

        def _read_from_db():
            user_translations = {}
            try:
                rows = frappe.get_all(
                    "Translation",
                    fields=["source_text", "translated_text", "context"],
                    filters={"language": lang, "ct_is_catalog_entry": 0},
                    order_by="modified asc, creation asc, name asc",
                    limit_page_length=0,
                )
            except Exception as e:
                msg = str(e)
                if "Unknown column" in msg or "no such column" in msg or "ct_is_catalog_entry" in msg:
                    rows = frappe.get_all(
                        "Translation",
                        fields=["source_text", "translated_text", "context"],
                        filters={"language": lang},
                        order_by="modified asc, creation asc, name asc",
                        limit_page_length=0,
                    )
                else:
                    frappe.log_error(f"Translation loader DB error: {e}\n{frappe.get_traceback()}", "Translation Loader")
                    return {}
            for t in rows:
                # An empty runtime value must never shadow the .mo catalog:
                # storing it would blank the UI string entirely.
                if not t.translated_text:
                    continue
                key = t.source_text
                if t.context:
                    key += ":" + t.context
                user_translations[key] = t.translated_text
            return user_translations

        return frappe.cache.hget(_translate.USER_TRANSLATION_KEY, lang, generator=_read_from_db)

    _translate.get_user_translations = _get_user_translations_excluding_catalog
    _TRANSLATION_LOADER_INSTALLED = True
    _TRANSLATION_LOADER_ERROR = None
except Exception as e:
    _TRANSLATION_LOADER_INSTALLED = False
    _TRANSLATION_LOADER_ERROR = str(e)
    try:
        frappe.log_error(f"Translation loader install failed: {e}\n{frappe.get_traceback()}", "Translation Loader")
    except Exception:
        pass


def is_translation_loader_installed():
    return bool(globals().get("_TRANSLATION_LOADER_INSTALLED", False))


def get_translation_loader_error():
    return globals().get("_TRANSLATION_LOADER_ERROR")


def translation_loader_health():
    from construction.translation_service import get_translation_health

    base = get_translation_health()
    base["loader_installed"] = is_translation_loader_installed()
    base["loader_error"] = get_translation_loader_error()
    return base
