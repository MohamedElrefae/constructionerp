"""Fix Arabic domain terminology to Egyptian construction & accounting standards.

Replaces the manufacturing phr:
  * Subcontracting family: 'التصنيع بالعقد' / 'مصنع بالعقد' -> مقاولات الباطن / من الباطن.
  * Payment Entry: 'قيد دفع' -> سند قبض / سند صرف.
  * Journal Entry: standardize to 'قيد يومية'.
  * Mobilization Cost -> تكلفة تجهيز الموقع.

Also seeds the highest-priority construction terms that were completely absent
(Retention, Advance, Subcontractor, Variation Order, Bill of Quantities, ...).
Idempotent and non-destructive to non-mapped rows. Runs during ``bench migrate``
via construction.patches.txt (v8_3). Seeding is insert-only; existing mapped rows
are only updated to the canonical value (this is an explicit one-time remediation,
not a migrate-time overwrite).
"""

import re

import frappe

ALL_MAP = {
    # ——— Subcontracting family — manufacturing phrasing → Egyptian construction ———
    "Subcontracting": "مقاولات الباطن",
    "Subcontract Order": "أمر مقاولات باطن",
    "Subcontract Order Summary": "ملخص أمر مقاولات باطن",
    "Subcontract BOM": "قائمة مواد مقاول الباطن",
    "Subcontract Return": "مرتجع مقاولات باطن",
    "Subcontracted Purchase Order": "أمر شراء مقاول باطن",
    "Subcontracted Quantity": "الكمية المنفذة من الباطن",
    "Subcontracting BOM": "قائمة مواد مقاول الباطن",
    "Subcontracting Conversion Factor": "معامل تحويل مقاولات الباطن",
    "Subcontracting Delivery": "تسليم مقاولات الباطن",
    "Subcontracting Inward": "استلام مقاولات الباطن",
    "Subcontracting Inward Order": "أمر استلام مقاولات باطن",
    "Subcontracting Inward Order Count": "عدد أوامر استلام مقاولات باطن",
    "Subcontracting Inward Order Item": "بند أمر استلام مقاولات باطن",
    "Subcontracting Inward Order Received Item": "بند مستلم لأمر استلام مقاولات باطن",
    "Subcontracting Inward Order Scrap Item": "بند هالك لأمر استلام مقاولات باطن",
    "Subcontracting Inward Order Service Item": "بند خدمة لأمر استلام مقاولات باطن",
    "Subcontracting Inward Settings": "إعدادات استلام مقاولات باطن",
    "Subcontracting Order": "أمر مقاولات باطن",
    "Subcontracting Order Item": "بند أمر مقاولات باطن",
    "Subcontracting Order Service Item": "بند خدمة أمر مقاولات باطن",
    "Subcontracting Order Supplied Item": "بند مورد لأمر مقاولات باطن",
    "Subcontracting Outward Order": "أمر إرسال مقاولات باطن",
    "Subcontracting Outward Order Count": "عدد أوامر إرسال مقاولات باطن",
    "Subcontracting Purchase Order": "أمر شراء مقاول باطن",
    "Subcontracting Receipt": "إيصال استلام مقاولات باطن",
    "Subcontracting Receipt Item": "بند إيصال مقاولات باطن",
    "Subcontracting Receipt Supplied Item": "بند مورد لإيصال مقاولات باطن",
    "Subcontracting Return": "مرتجع مقاولات باطن",
    "Subcontracting Sales Order": "أمر بيع مقاول باطن",
    "Subcontracting Settings": "إعدادات مقاولات الباطن",
    "Is Subcontracted": "من الباطن",
    "Is Subcontracted Item": "بند منفذ من الباطن",
    "Is Old Subcontracting Flow": "التدفق القديم لمقاولات الباطن",
    "Has Subcontracted": "يوجد مقاولات باطن",
    "Reserved Qty for Subcontract": "الكمية المحجوزة لمقاول الباطن",
    "Return Against Subcontracting Receipt": "مرتجع مقابل إيصال مقاولات باطن",
    "Auto Create Subcontracting Order": "إنشاء أمر مقاولات باطن تلقائيًا",
    "Make Subcontracting PO": "إنشاء أمر شراء مقاول باطن",
    "Mapping Subcontracting Order ...": "جارٍ ربط أمر مقاولات باطن ...",
    "Mapping Subcontracting Inward Order ...": "جارٍ ربط أمر استلام مقاولات باطن ...",
    "Active Subcontracted Items": "الأصناف المنفذة من الباطن النشطة",
    "Work Order / Subcontract PO": "أمر عمل / أمر شراء مقاول باطن",
    # ——— Accounting terms — Egyptian registers ———
    "Journal Entry": "قيد يومية",
    "Payment Entry": "سند قبض / سند صرف",
    "Mobilization Cost": "تكلفة تجهيز الموقع",
}

# Highest-priority domain terms that were completely absent — seed (create if missing).
ADD = {
    "Subcontractor": "مقاول باطن",
    "Subcontract": "عقد مقاولات باطن",
    "Retention": "محتجزات ضمان",
    "Retention Money": "محتجزات ضمان",
    "Advance": "دفعة مقدمة",
    "Advance Payment": "دفعة مقدمة",
    "Overtime": "ساعات إضافية",
    "Progress Billing": "مستخلص جاري",
    "Payment Certificate": "مستخلص",
    "Variation Order": "أمر تغيير",
    "Bill of Quantities": "جدول الكميات",
    "Handover": "التسليم الابتدائي",
}

KNOWN_DUPLICATES = {"Journal Entry", "Payment Entry", "Chart Of Accounts"}


def _standard(text):
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def _clear_translation_caches():
    from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY

    frappe.cache.hdel(USER_TRANSLATION_KEY, "ar")
    frappe.cache.hdel(MERGED_TRANSLATION_KEY, "ar")
    frappe.cache.delete_value(keys=["bootinfo", USER_TRANSLATION_KEY, MERGED_TRANSLATION_KEY])
    frappe.clear_cache()


def _ar_rows_for(source_text):
    """Arabic Translation rows whose normalized source equals source_text (any context/raw)."""
    rows = frappe.get_all(
        "Translation",
        filters={"language": "ar", "source_text": ("like", f"%{source_text}%")},
        fields=["name", "source_text", "context", "translated_text"],
        limit_page_length=0,
    )
    return [r for r in rows if _standard(r.source_text) == source_text]


def _set(rows, value):
    for row in rows:
        frappe.db.set_value(
            "Translation",
            row.name,
            "translated_text",
            value,
            update_modified=False,
        )


def _dedupe(rows):
    """For context-blank rows keep the first, delete duplicate rows for the same source."""
    seen = None
    for row in rows:
        if (row.context or "") != "":
            continue
        if seen is None:
            seen = row.name
            continue
        frappe.db.delete("Translation", row.name)


def execute():
    fixed = created = deduped = 0

    for source_text, value in ALL_MAP.items():
        rows = _ar_rows_for(source_text)
        if not rows:
            # No Arabic row yet -> seed it (insert-only).
            doc = frappe.get_doc(
                {
                    "doctype": "Translation",
                    "language": "ar",
                    "source_text": source_text,
                    "context": "",
                    "translated_text": value,
                }
            )
            doc.flags.ignore_permissions = True
            doc.insert(ignore_permissions=True)
            created += 1
            continue

        _set(rows, value)
        fixed += 1
        if source_text in KNOWN_DUPLICATES and len(rows) > 1:
            before = len(rows)
            _dedupe(rows)
            deduped += before - 1

    for source_text, value in ADD.items():
        if frappe.db.exists(
            "Translation", {"language": "ar", "source_text": source_text, "context": ""}
        ):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Translation",
                "language": "ar",
                "source_text": source_text,
                "context": "",
                "translated_text": value,
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()
    _clear_translation_caches()
    print(
        f"[v8_3] Arabic domain terminology: fixed={fixed} created={created} deduped={deduped}"
    )
