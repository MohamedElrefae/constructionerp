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


@frappe.whitelist()
def seed_missing_arabic_translations(limit=500):
    """Create Arabic Translation rows for source texts missing Arabic entries."""
    limit = max(1, min(cint(limit) or 500, 5000))

    rows = frappe.db.sql(
        """
		select t.source_text
		from `tabTranslation` t
		where ifnull(t.source_text, '') != ''
		group by t.source_text
		having sum(case when t.language='ar' then 1 else 0 end)=0
		order by t.source_text
		limit %(limit)s
		""",
        {"limit": limit},
        as_dict=True,
    )

    created = 0
    for row in rows:
        source_text = row.get("source_text")
        if not source_text:
            continue
        if frappe.db.exists("Translation", {"language": "ar", "source_text": source_text, "context": ""}):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Translation",
                "language": "ar",
                "source_text": source_text,
                # Translation.translated_text is mandatory in Frappe.
                # Use source_text as placeholder so rows can be created and then reviewed.
                "translated_text": source_text,
                "context": "",
            }
        )
        doc.insert()
        created += 1

    frappe.db.commit()
    return {"created": created, "checked": len(rows)}


@frappe.whitelist()
def get_missing_arabic_translation_names(limit=1000):
    """Return Translation row names where Arabic text still equals source text."""
    limit = max(1, min(cint(limit) or 1000, 5000))
    rows = frappe.db.sql(
        """
		select name
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
    return [r["name"] for r in rows]


@frappe.whitelist()
def normalize_translation_keys():
    """Trim source_text whitespace and normalize common Arabic translation mistakes."""
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

    frappe.db.commit()
    return {"updated": updated}
