"""Override the core Translation DocType to support catalog-aware editing.

When a user edits a row that was originally auto-created from the .po catalog,
flipping ``ct_is_catalog_entry`` to 0 promotes it to a real manual override so it
is included in the runtime translation cache.
"""

import frappe
from frappe.core.doctype.translation.translation import Translation
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY


class CustomTranslation(Translation):
    def validate(self):
        super().validate()
        # Editing the Arabic text of a catalog entry promotes it to a manual
        # override. We detect a meaningful change vs the stored PO baseline.
        if self.get("ct_is_catalog_entry") and self.get("ct_po_translation") is not None:
            po_value = (self.ct_po_translation or "").strip()
            current = (self.translated_text or "").strip()
            if current and current != po_value:
                self.ct_is_catalog_entry = 0
                self.ct_review_status = "Approved"

    def on_update(self):
        super().on_update()
        # Ensure any status change is reflected in list filters.
        frappe.cache.hdel(USER_TRANSLATION_KEY, self.language)
        frappe.cache.hdel(MERGED_TRANSLATION_KEY, self.language)
