import json

import frappe
from frappe import _
from frappe.translate import strip_html_tags
from frappe.utils import cint


def _normalize_source_text(source: str) -> str:
    source = (source or "").strip()
    if not source:
        return ""
    return strip_html_tags(source)


@frappe.whitelist()
def update_translations_for_source_safe(source=None, translation_dict=None):
    """Safer replacement for frappe.translate.update_translations_for_source.

    - Never deletes existing records as a side effect.
    - Updates one row per language for the provided source text.
    - Creates missing language rows with empty context.
    """
    frappe.only_for("System Manager")
    source = _normalize_source_text(source)
    if not source or not translation_dict:
        return []

    if isinstance(translation_dict, str):
        translation_dict = json.loads(translation_dict)

    # Only keep non-empty language keys
    normalized = {}
    for lang, translated_text in (translation_dict or {}).items():
        lang = (lang or "").strip()
        if not lang:
            continue
        normalized[lang] = translated_text or ""

    if not normalized:
        return []

    existing = frappe.get_all(
        "Translation",
        filters={"source_text": source},
        fields=["name", "language", "context"],
        order_by="ifnull(context,'') asc, name asc",
    )
    by_lang = {}
    for row in existing:
        by_lang.setdefault(row.language, []).append(row)

    updated = []
    for lang, translated_text in normalized.items():
        target = (by_lang.get(lang) or [None])[0]
        if target:
            doc = frappe.get_doc("Translation", target.name)
            doc.translated_text = translated_text
            doc.save()
            updated.append(doc.name)
        else:
            doc = frappe.get_doc(
                {
                    "doctype": "Translation",
                    "language": lang,
                    "source_text": source,
                    "translated_text": translated_text,
                    "context": "",
                }
            )
            doc.insert()
            updated.append(doc.name)

    return updated


MISSING_SOURCES_SQL = """
	select t.source_text
	from `tabTranslation` t
	where ifnull(t.source_text, '') != ''
	group by t.source_text
	having sum(case when t.language='ar' then 1 else 0 end)=0
	order by t.source_text
	limit %(limit)s
"""


@frappe.whitelist()
def seed_missing_arabic_translations(limit=500):
    """Report source texts missing Arabic entries — WITHOUT creating rows.

    Creating rows with ``translated_text = source_text`` (English) produced junk
    translations that masked real ones. This is now report-only; a safer import
    path (reviewed, insert-only) lives in ``construction.insert_translations``.
    """
    limit = max(1, min(cint(limit) or 500, 5000))
    rows = frappe.db.sql(MISSING_SOURCES_SQL, {"limit": limit}, as_dict=True)
    return {"created": 0, "checked": len(rows), "missing": [r["source_text"] for r in rows]}


@frappe.whitelist()
def get_missing_arabic_translation_sources(limit=1000):
    """Return source texts (not row names) that have no Arabic entry at all."""
    limit = max(1, min(cint(limit) or 1000, 5000))
    rows = frappe.db.sql(MISSING_SOURCES_SQL, {"limit": limit}, as_dict=True)
    return [r["source_text"] for r in rows]


@frappe.whitelist()
def get_placeholder_arabic_translation_sources(limit=1000):
    """Return source texts whose Arabic value still equals the English source (placeholder junk)."""
    limit = max(1, min(cint(limit) or 1000, 5000))
    rows = frappe.db.sql(
        """
		select distinct source_text
		from `tabTranslation`
		where language='ar'
		  and ifnull(source_text,'') != ''
		  and ifnull(translated_text,'') = ifnull(source_text,'')
		order by source_text
		limit %(limit)s
		""",
        {"limit": limit},
        as_dict=True,
    )
    return [r["source_text"] for r in rows]


@frappe.whitelist()
def normalize_translation_keys():
    """Trim source_text whitespace and normalize common Arabic translation mistakes."""
    frappe.only_for("System Manager")
    updated = 0
    for row in frappe.get_all(
        "Translation",
        fields=["name", "language", "source_text", "translated_text", "context"],
        filters={"source_text": ("is", "set")},
    ):
        source = row.source_text or ""
        trimmed = source.strip()
        if trimmed and trimmed != source:
            frappe.db.set_value("Translation", row.name, "source_text", trimmed, update_modified=False)
            updated += 1

    # Repair known BOQ Item Stage Arabic record if it was saved with wrong language/source
    candidates = frappe.get_all(
        "Translation",
        fields=["name", "language", "source_text", "translated_text"],
        filters={"source_text": ("like", "%BOQ Item Stage%")},
    )
    for row in candidates:
        if "BOQ Item Stage" not in (row.source_text or ""):
            continue
        if row.translated_text and row.translated_text.strip() and row.language != "ar":
            frappe.db.set_value("Translation", row.name, "language", "ar", update_modified=False)
            frappe.db.set_value(
                "Translation", row.name, "source_text", "BOQ Item Stage", update_modified=False
            )
            updated += 1

    return {"updated": updated}


def _load_glossary():
    path = frappe.get_app_path("construction", "data", "glossary", "egyptian_construction_glossary.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    glossary = {}
    for term in data.get("terms", []):
        if term.get("en") and term.get("ar"):
            glossary[term["en"].strip()] = term["ar"].strip()
    return glossary


@frappe.whitelist()
def apply_glossary_corrections(dry_run=True):
    """Bulk-correct Arabic Translation rows to the canonical Egyptian glossary."""
    frappe.only_for("System Manager")
    dry_run = bool(dry_run)
    glossary = _load_glossary()
    if not glossary:
        return {"checked": 0, "updated": 0, "created": 0, "preview": []}

    rows = frappe.get_all(
        "Translation",
        fields=["name", "language", "source_text", "context", "translated_text"],
        filters={"source_text": ("in", list(glossary.keys())), "language": "ar"},
        limit_page_length=0,
    )

    preview = []
    updated = created = 0
    for row in rows:
        canonical = glossary.get((row.source_text or "").strip())
        if not canonical or row.translated_text == canonical:
            continue
        preview.append(
            {
                "name": row.name,
                "source_text": row.source_text,
                "context": row.context or "",
                "before": row.translated_text,
                "after": canonical,
            }
        )
        if not dry_run:
            frappe.db.set_value(
                "Translation", row.name, "translated_text", canonical, update_modified=False
            )
            updated += 1

    return {"checked": len(rows), "updated": updated, "created": created, "preview": preview}


REVIEW_QUEUE_COLUMNS = ["app", "source_text", "suggested_ar", "status"]
APPROVED_STATUSES = {"approved", "ok", "correct", "done", ""}


def _read_review_queue(path=None):
    import csv

    path = path or frappe.get_app_path("construction", "data", "translations", "review_queue.csv")
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader if (row.get("suggested_ar") or "").strip()]


@frappe.whitelist()
def import_review_queue(dry_run=True, enable_status_gate=False):
    """Apply rows from the packaged review queue into the DB as Arabic translations."""
    frappe.only_for("System Manager")
    dry_run = bool(dry_run)
    enable_status_gate = bool(enable_status_gate)
    rows = _read_review_queue()
    total = len(rows)

    preview = []
    created = updated = skipped = 0
    for row in rows:
        source = (row.get("source_text") or "").strip()
        value = (row.get("suggested_ar") or "").strip()
        if not source or not value:
            skipped += 1
            continue
        if enable_status_gate and (row.get("status") or "unreviewed").strip().lower() not in APPROVED_STATUSES:
            skipped += 1
            continue

        existing = frappe.db.get_value(
            "Translation",
            {"language": "ar", "source_text": source, "context": ""},
            "name",
        )
        if existing:
            current = frappe.db.get_value("Translation", existing, "translated_text")
            if current == value:
                skipped += 1
                continue
            preview.append({"source_text": source, "before": current, "after": value, "action": "update"})
            if not dry_run:
                frappe.db.set_value("Translation", existing, "translated_text", value, update_modified=False)
                updated += 1
        else:
            preview.append({"source_text": source, "before": "", "after": value, "action": "create"})
            if not dry_run:
                doc = frappe.get_doc(
                    {
                        "doctype": "Translation",
                        "language": "ar",
                        "source_text": source,
                        "context": "",
                        "translated_text": value,
                    }
                )
                doc.insert()
                created += 1

    return {"total": total, "created": created, "updated": updated, "skipped": skipped, "preview": preview}
