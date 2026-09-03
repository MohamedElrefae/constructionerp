"""Override the core Translation DocType to support catalog-aware editing.

When a user edits a row mirrored from a .po catalog, the catalog row stays in
place for review and the edited value is upserted into the canonical runtime
Translation row. This avoids duplicate runtime keys and preserves provenance.
"""

import frappe
from frappe.core.doctype.translation.translation import Translation
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY


class CustomTranslation(Translation):
    def validate(self):
        super().validate()
        # Runtime lookup keys must match what the UI requests. Accidental
        # leading/trailing whitespace (paste artifacts) breaks the lookup while
        # remaining self-consistent in the digest, so trim it here. Catalog
        # bulk inserts bypass validate and keep exact upstream msgid bytes.
        self.source_text = (self.source_text or "").strip()
        self.context = (self.context or "").strip()
        if not self.source_text:
            frappe.throw("source_text is required (whitespace-only values are rejected)")
        if not self.get("ct_is_catalog_entry") and not (self.translated_text or "").strip():
            # A runtime row with an empty value would blank the UI string
            # (loader shadowing) — reject it; catalog rows may stay empty
            # (they represent untranslated upstream strings).
            frappe.throw("translated_text is required for runtime (non-catalog) translations")
        if "\x00" in (self.source_text or "") or "\x00" in (self.translated_text or "") or "\x00" in (self.context or ""):
            frappe.throw("Translation key/value contains embedded NUL")
        if self.meta.has_field("ct_key_digest"):
            from construction.translation_service import _compute_digest, _search_normalized

            is_catalog = bool(self.get("ct_is_catalog_entry"))
            self.ct_key_digest = _compute_digest(
                self.language or "", self.source_text or "", self.context or "", self.get("ct_app") or "", is_catalog
            )
            # Friendly duplicate message instead of a raw IntegrityError when
            # trimming collapses this row onto an existing key.
            clash = frappe.db.get_value(
                "Translation",
                {"ct_key_digest": self.ct_key_digest, "name": ("!=", self.name or "")},
                "name",
            )
            if clash:
                frappe.throw(
                    f"A translation with this key already exists ({clash}). "
                    "Edit that row instead of creating a duplicate."
                )
        if self.meta.has_field("ct_search_normalized"):
            from construction.translation_service import _search_normalized

            self.ct_search_normalized = _search_normalized(self.source_text or "")
        if self.meta.has_field("ct_origin"):
            is_catalog = bool(self.get("ct_is_catalog_entry"))
            if is_catalog:
                if self.get("ct_origin") and self.ct_origin not in ("Packaged Release", "Site Override", ""):
                    frappe.throw("ct_origin for catalog must be empty, Packaged Release or Site Override")
                if not self.get("ct_origin"):
                    self.ct_origin = ""
            else:
                if not self.get("ct_origin"):
                    self.ct_origin = "Site Override"
                elif self.ct_origin not in ("Packaged Release", "Site Override"):
                    frappe.throw("ct_origin for runtime must be Packaged Release or Site Override")
        if self.get("ct_is_catalog_entry") and self.get("ct_po_translation") is not None:
            if self.meta.has_field("ct_proposed_translation"):
                po_value = self.ct_po_translation or ""
                current = self.translated_text or ""
                if current != po_value:
                    if current:
                        self.ct_proposed_translation = current
                        if self.meta.has_field("ct_review_status"):
                            if self.ct_review_status in (None, "", "Approved"):
                                self.ct_review_status = "Pending"
                    else:
                        self.ct_proposed_translation = ""
                else:
                    if self.get("ct_proposed_translation"):
                        self.ct_proposed_translation = ""
                    if self.meta.has_field("ct_review_status") and self.ct_review_status == "Pending":
                        pass
            else:
                po_value = (self.ct_po_translation or "").strip()
                current = (self.translated_text or "").strip()
                if current and current != po_value:
                    self.flags.ct_runtime_value = current

    def on_update(self):
        super().on_update()
        if runtime_value := self.flags.get("ct_runtime_value"):
            from construction.api.translation_tools import upsert_runtime_translation

            upsert_runtime_translation(
                self.source_text,
                runtime_value,
                language=self.language,
                context=self.context or "",
                app=self.get("ct_app"),
                ignore_permissions=True,
            )
        from construction.translation_service import invalidate_translation_caches

        invalidate_translation_caches(self.language)
