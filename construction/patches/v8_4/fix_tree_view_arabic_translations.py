"""Fix Arabic translations for tree-view action buttons.

Many tree views (Chart of Accounts, Cost Center, Item Group, Territory, ...)
share the same action labels from frappe/public/js/frappe/views/treeview.js.
The source string "Add Child" was being rendered as the literal/junk
"اضافة طفل" because of an existing bad Translation row or an empty PO entry.

This patch force-corrects the most common tree-view action strings and seeds
missing rows. It is idempotent and safe to re-run.
"""

import frappe
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY

# Map of source string -> correct Arabic translation.
# NOTE: "Add Child" is shared by ALL tree views (accounts, cost centers,
# item groups, territories, etc.). We use the generic "إضافة فرع" so it is
# correct in every tree. If you prefer account-specific wording, change this
# to "إضافة حساب فرعي" — but it will then appear in non-account trees too.
TREE_ACTION_TRANSLATIONS = {
	"Add Child": "إضافة فرع",
	"Edit": "تعديل",
	"Rename": "إعادة تسمية",
	"Delete": "حذف",
	"Details": "التفاصيل",
	"Expand All": "توسيع الكل",
	"Collapse All": "طي الكل",
	"Refresh": "تحديث",
}


def _clear_translation_caches():
	frappe.cache.hdel(USER_TRANSLATION_KEY, "ar")
	frappe.cache.hdel(MERGED_TRANSLATION_KEY, "ar")
	frappe.cache.delete_value(keys=["bootinfo", USER_TRANSLATION_KEY, MERGED_TRANSLATION_KEY])
	frappe.clear_cache()


def execute():
	updated = 0
	created = 0

	for source_text, translated_text in TREE_ACTION_TRANSLATIONS.items():
		rows = frappe.get_all(
			"Translation",
			filters={"language": "ar", "source_text": source_text},
			fields=["name", "context", "translated_text"],
			limit_page_length=0,
		)

		if rows:
			for row in rows:
				if row.translated_text != translated_text:
					frappe.db.set_value(
						"Translation",
						row.name,
						"translated_text",
						translated_text,
						update_modified=False,
					)
					updated += 1
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Translation",
					"language": "ar",
					"source_text": source_text,
					"context": "",
					"translated_text": translated_text,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			created += 1

	frappe.db.commit()
	_clear_translation_caches()
	print(f"[v8_4] Tree-view Arabic translations: updated={updated} created={created}")
