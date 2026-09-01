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
        # Record a meaningful catalog edit for promotion after this row saves.
        if self.get("ct_is_catalog_entry") and self.get("ct_po_translation") is not None:
            po_value = (self.ct_po_translation or "").strip()
            current = (self.translated_text or "").strip()
            if current and current != po_value:
                self.ct_review_status = "Approved"
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

        # Ensure any status/value change is reflected in runtime and list views.
        frappe.cache.hdel(USER_TRANSLATION_KEY, self.language)
        frappe.cache.hdel(MERGED_TRANSLATION_KEY, self.language)
