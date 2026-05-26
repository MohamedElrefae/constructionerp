"""Ensure reviewed BOQ Item Stage Arabic translation exists after deploy."""

import re

import frappe

from construction.insert_translations import execute as seed_translations


SOURCE = "BOQ Item Stage"
TRANSLATION = "مراحل تنفيذ البنود"


def _normalize_source(value):
	return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip()


def _clear_translation_caches():
	from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY

	frappe.cache.hdel(USER_TRANSLATION_KEY, "ar")
	frappe.cache.hdel(MERGED_TRANSLATION_KEY, "ar")
	frappe.cache.delete_value(keys=["bootinfo", USER_TRANSLATION_KEY, MERGED_TRANSLATION_KEY])
	frappe.clear_cache()


def _upsert_boq_item_stage_translation():
	exact = frappe.db.get_value(
		"Translation",
		{"language": "ar", "source_text": SOURCE, "context": ""},
		"name",
	)
	if exact:
		frappe.db.set_value("Translation", exact, "translated_text", TRANSLATION, update_modified=False)
		return

	for row in frappe.get_all(
		"Translation",
		filters={"language": "ar", "source_text": ("like", "%BOQ%Item%Stage%")},
		fields=["name", "source_text"],
		limit_page_length=0,
	):
		if _normalize_source(row.source_text) == SOURCE:
			frappe.db.set_value("Translation", row.name, "source_text", SOURCE, update_modified=False)
			frappe.db.set_value("Translation", row.name, "context", "", update_modified=False)
			frappe.db.set_value("Translation", row.name, "translated_text", TRANSLATION, update_modified=False)
			return

	doc = frappe.get_doc(
		{
			"doctype": "Translation",
			"language": "ar",
			"source_text": SOURCE,
			"context": "",
			"translated_text": TRANSLATION,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)


def execute():
	seed_translations()
	_upsert_boq_item_stage_translation()
	frappe.db.commit()
	_clear_translation_caches()
