import csv
from pathlib import Path

import frappe
from babel.messages.pofile import read_po, write_po


DEFAULT_PO_REVIEW_PATH = "apps/construction/docs/arabic_po_review.csv"
DEFAULT_DB_REVIEW_PATH = "apps/construction/docs/arabic_db_translation_review.csv"


def export_po_review(csv_path=DEFAULT_PO_REVIEW_PATH):
	"""Export Construction Arabic PO entries to CSV for linguistic review."""
	po_path = _po_path()
	rows = []

	with po_path.open("rb") as po_file:
		catalog = read_po(po_file, locale="ar")

	for message in catalog:
		if not message.id:
			continue
		rows.append({
			"msgid": message.id,
			"msgstr": message.string or "",
			"context": message.context or "",
			"locations": "; ".join(f"{path}:{line}" for path, line in message.locations),
			"comments": " | ".join(message.auto_comments or []),
			"review_notes": "",
		})

	output_path = _bench_path(csv_path)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	_write_csv(output_path, rows, ["msgid", "msgstr", "context", "locations", "comments", "review_notes"])
	print(f"Exported {len(rows)} PO rows to {output_path}")
	return str(output_path)


def import_po_review(csv_path=DEFAULT_PO_REVIEW_PATH, dry_run=True):
	"""Import reviewed Arabic PO translations from CSV.

	The CSV must include `msgid` and `msgstr`. Context is optional but supported.
	"""
	input_path = _bench_path(csv_path)
	rows = _read_csv(input_path)
	reviewed = {
		(row["msgid"], row.get("context") or None): row["msgstr"]
		for row in rows
		if row.get("msgid") and row.get("msgstr")
	}

	po_path = _po_path()
	with po_path.open("rb") as po_file:
		catalog = read_po(po_file, locale="ar")

	changed = 0
	for message in catalog:
		if not message.id:
			continue
		key = (message.id, message.context or None)
		if key in reviewed and message.string != reviewed[key]:
			message.string = reviewed[key]
			changed += 1

	if not dry_run:
		with po_path.open("wb") as po_file:
			write_po(po_file, catalog, width=120, sort_output=False, include_previous=False)

	result = {"changed": changed, "dry_run": dry_run, "source": str(input_path), "target": str(po_path)}
	print(result)
	return result


def export_db_review(csv_path=DEFAULT_DB_REVIEW_PATH):
	"""Export Arabic DB Translation rows for review.

	These are global translations. Edit with care because they affect all apps.
	"""
	rows = frappe.get_all(
		"Translation",
		fields=["source_text", "translated_text", "context"],
		filters={"language": "ar"},
		order_by="source_text asc",
	)
	output_path = _bench_path(csv_path)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	_write_csv(
		output_path,
		rows,
		["source_text", "translated_text", "context", "review_notes"],
		defaults={"review_notes": ""},
	)
	print(f"Exported {len(rows)} DB translation rows to {output_path}")
	return str(output_path)


def import_db_review(csv_path=DEFAULT_DB_REVIEW_PATH, dry_run=True):
	"""Import reviewed Arabic DB Translation rows from CSV.

	The CSV must include `source_text` and `translated_text`.
	"""
	input_path = _bench_path(csv_path)
	rows = _read_csv(input_path)
	changed = 0

	for row in rows:
		source_text = row.get("source_text")
		translated_text = row.get("translated_text")
		context = row.get("context") or None
		if not source_text or not translated_text:
			continue

		filters = {"language": "ar", "source_text": source_text, "context": context}
		name = frappe.db.exists("Translation", filters)
		if name:
			doc = frappe.get_doc("Translation", name)
			if doc.translated_text == translated_text:
				continue
			if not dry_run:
				doc.translated_text = translated_text
				doc.flags.ignore_permissions = True
				doc.save(ignore_permissions=True)
			changed += 1
		else:
			if not dry_run:
				doc = frappe.get_doc({
					"doctype": "Translation",
					"language": "ar",
					"source_text": source_text,
					"translated_text": translated_text,
					"context": context,
				})
				doc.flags.ignore_permissions = True
				doc.insert(ignore_permissions=True)
			changed += 1

	if changed and not dry_run:
		from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY

		frappe.cache.hdel(USER_TRANSLATION_KEY, "ar")
		frappe.cache.hdel(MERGED_TRANSLATION_KEY, "ar")
		frappe.cache.delete_value(keys=["bootinfo"])
		frappe.db.commit()

	result = {"changed": changed, "dry_run": dry_run, "source": str(input_path)}
	print(result)
	return result


def _po_path():
	return Path(frappe.get_app_path("construction")) / "locale" / "ar.po"


def _bench_path(path):
	path = Path(path)
	if path.is_absolute():
		return path
	return Path(frappe.get_app_path("construction")).parents[2] / path


def _write_csv(path, rows, fieldnames, defaults=None):
	defaults = defaults or {}
	with path.open("w", newline="", encoding="utf-8") as csv_file:
		writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
		writer.writeheader()
		for row in rows:
			output = {field: row.get(field, defaults.get(field, "")) for field in fieldnames}
			writer.writerow(output)


def _read_csv(path):
	with path.open(newline="", encoding="utf-8") as csv_file:
		return list(csv.DictReader(csv_file))
