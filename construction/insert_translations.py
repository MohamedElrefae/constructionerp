import csv
from pathlib import Path

import frappe
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY


REVIEW_FILES = (
	"docs/arabic_db_translation_review.csv",
	"docs/arabic_po_review.csv",
	"docs/erpnext_ar_missing_review_filled.csv",
	"docs/frappe_ar_missing_review.csv",
)

CRITICAL_OVERRIDES = {
	"Submit": "ترحيل",
	"Submitted": "تم الترحيل",
	"Save and Submit": "حفظ وترحيل",
	"Home": "الرئيسية",
	"Projects": "المشاريع",
	"Reports & Masters": "التقارير والبيانات الرئيسية",
	"Reports &amp; Masters": "التقارير والبيانات الرئيسية",
	"Masters & Reports": "البيانات الرئيسية والتقارير",
	"Masters &amp; Reports": "البيانات الرئيسية والتقارير",
	"Quick Access": "وصول سريع",
	"Shortcuts": "الاختصارات",
	"Your Shortcuts": "اختصاراتك",
	"BOQ Management": "إدارة جدول الكميات",
	"Theme Settings": "إعدادات السمة",
	"Scope Context": "سياق النطاق",
	"Scope Management": "إدارة النطاق",
	"User Scope Context": "سياق نطاق المستخدم",
	"Scope Context Settings": "إعدادات سياق النطاق",
	"Construction Settings": "إعدادات المقاولات",
	'<span class="h4"><b>Reports & Masters</b></span>': '<span class="h4"><b>التقارير والبيانات الرئيسية</b></span>',
	'<span class="h4"><b>Reports &amp; Masters</b></span>': '<span class="h4"><b>التقارير والبيانات الرئيسية</b></span>',
	'<span class="h4"><b>Masters &amp; Reports</b></span>': '<span class="h4"><b>البيانات الرئيسية والتقارير</b></span>',
	'<span class="h4"><b>Quick Access</b></span>': '<span class="h4"><b>وصول سريع</b></span>',
	'<span class="h4"><b>Shortcuts</b></span>': '<span class="h4"><b>الاختصارات</b></span>',
	'<span class="h4"><b>Your Shortcuts</b></span>': '<span class="h4"><b>اختصاراتك</b></span>',
}


def _repo_root():
	return Path(__file__).resolve().parents[1]


def _row_value(row, *keys):
	for key in keys:
		value = (row.get(key) or "").strip()
		if value:
			return value
	return ""


def _load_reviewed_translations():
	translations = {}
	root = _repo_root()

	for relative_path in REVIEW_FILES:
		path = root / relative_path
		if not path.exists():
			continue

		with path.open(newline="", encoding="utf-8") as handle:
			reader = csv.DictReader(handle)
			for row in reader:
				if _row_value(row, "skip").lower() in {"1", "yes", "true"}:
					continue

				source_text = _row_value(row, "source_text", "msgid", "source")
				translated_text = _row_value(row, "translated_text", "msgstr", "translation")
				context = _row_value(row, "context")

				if not source_text or not translated_text:
					continue

				translations[(source_text, context)] = translated_text

	for source_text, translated_text in CRITICAL_OVERRIDES.items():
		translations[(source_text, "")] = translated_text

	return translations


def _clear_translation_caches():
	frappe.cache.hdel(USER_TRANSLATION_KEY, "ar")
	frappe.cache.hdel(MERGED_TRANSLATION_KEY, "ar")
	frappe.cache.delete_value(keys=["bootinfo", USER_TRANSLATION_KEY, MERGED_TRANSLATION_KEY])
	frappe.clear_cache()


def _get_existing_arabic_translation_map():
	existing = {}
	for row in frappe.get_all(
		"Translation",
		filters={"language": "ar"},
		fields=["name", "source_text", "context"],
		limit_page_length=0,
	):
		key = (row.source_text, row.context or "")
		existing.setdefault(key, row.name)
	return existing


def execute(commit=False):
	translations = _load_reviewed_translations()
	existing_translations = _get_existing_arabic_translation_map()

	count = 0
	for (source_text, context), translated_text in translations.items():
		exists = existing_translations.get((source_text, context))

		if not exists:
			doc = frappe.get_doc(
				{
					"doctype": "Translation",
					"language": "ar",
					"source_text": source_text,
					"context": context,
					"translated_text": translated_text,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			existing_translations[(source_text, context)] = doc.name
			count += 1
			print(f"Added translation for: {source_text}")
		else:
			doc = frappe.get_doc("Translation", exists)
			if doc.translated_text != translated_text:
				doc.translated_text = translated_text
				doc.flags.ignore_permissions = True
				doc.save(ignore_permissions=True)
				count += 1
				print(f"Updated translation for: {source_text}")

	if commit:
		frappe.db.commit()

	_clear_translation_caches()
	print(f"Successfully processed {count} translations from {len(translations)} reviewed Arabic entries.")


@frappe.whitelist()
def get_arabic_translation_seed_status():
	seed = _load_reviewed_translations()
	samples = {}
	for source_text in (
		"Submit",
		"Sales Invoice",
		"Purchase Invoice",
		"Construction Settings",
		"Scope Context Settings",
		"Home",
		"Projects",
		"Reports & Masters",
		'<span class="h4"><b>Reports &amp; Masters</b></span>',
		"Scope Management",
		"User Scope Context",
	):
		samples[source_text] = frappe.db.get_value(
			"Translation",
			{"language": "ar", "source_text": source_text},
			["translated_text", "context"],
			as_dict=True,
		)

	sidebar_items = []
	if frappe.db.table_exists("Workspace Sidebar Item"):
		sidebar_items = frappe.get_all(
			"Workspace Sidebar Item",
			filters={"parent": "Construction"},
			fields=["label", "type", "link_to", "idx"],
			order_by="idx asc",
			limit_page_length=0,
		)

	return {
		"seed_count": len(seed),
		"db_count": frappe.db.count("Translation", {"language": "ar"}),
		"patch_v6_3": bool(
			frappe.db.exists("Patch Log", "construction.patches.v6_3.seed_reviewed_arabic_translation_files")
		),
		"patch_v6_4": bool(
			frappe.db.exists("Patch Log", "construction.patches.v6_4.reconcile_sidebar_and_arabic_translations")
		),
		"samples": samples,
		"construction_sidebar_items": sidebar_items,
	}
