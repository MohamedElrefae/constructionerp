"""W6-2 batch-02 governed proposal build (2026-09-23).

Owner-approved exact 48-row W6-2 Selling scope (sha
9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce).

Outputs (fail-closed, deterministic):
  - stage6_w602_payload_applied_rows_batch02_2026-09-23.csv  (48 dispositions, tab-sep)
  - construction/data/translations/approved_ar_overrides.csv (append 44 Released) 2275 -> 2319
  - stage6_w602_batch02_released_list.txt                    (44)
  - stage6_w602_batch02_site_recon_2026-09-23.json           (authoritative summary refresh)
"""

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w602_batch02_rows_2026-09-23.csv"
PAYLOAD = HERE / "stage6_w602_payload_applied_rows_batch02_2026-09-23.csv"
RELEASED_LIST = HERE / "stage6_w602_batch02_released_list.txt"
SITE_RECON = HERE / "stage6_w602_batch02_site_recon_2026-09-23.json"
APPROVED = HERE.parent.parent / "construction/data/translations/approved_ar_overrides.csv"

DATE = "2026-09-23"
SCOPE_SHA = "9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce"
DECISION_REF = f"content:docs/translation/stage6_w602_payload_applied_rows_batch02_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger erpnext_ar_missing_review_filled.csv; plan D5; W6-2 batch-02"
NOTES = (
    "AI proposal 2026-09-23 + quorum-confirmed (W6-2 batch-02; "
    "owner-approved 48-row Selling scope minus site-override preserve "
    "and identifier technical tokens)"
)
RELEASE_VERSION = "1.5"
REVIEWERS = (
    "AI-A1 (recorded review run)",
    "AI-A2 (recorded review run)",
    "AI-A3 (recorded review run)",
)
TS = "2026-09-23 00:00:00"
DOMAIN = "selling-desk"
GOVERNANCE_REF = f"stage6-W6-2 batch-02 owner-approved {DATE}"
CT_APP = "erpnext"

FIELDNAMES = [
    "language",
    "source_text",
    "context",
    "ct_app",
    "translated_text",
    "domain",
    "release_status",
    "release_version",
    "a1_reviewer",
    "a1_approved_at",
    "a2_reviewer",
    "a2_approved_at",
    "a3_reviewer",
    "a3_approved_at",
    "references",
    "notes",
    "decision_ref",
]

# snake_case field identifiers — keep vendor rendering
TECHNICAL = {"doctype", "doc_type", "quotation_item"}

A = {
    "POS has been closed at {0}. Please refresh the page.": "أُغلقت نقطة البيع في {0}. يرجى تحديث الصفحة.",
    "POS invoice {0} created successfully": "تم إنشاء فاتورة نقطة البيع {0} بنجاح",
    "Parent Item {0} must not be a Fixed Asset": "يجب ألا يكون الصنف الأعلى {0} أصلًا ثابتًا",
    "Payment of {0} received successfully. Waiting for other requests to complete...": "تم استلام دفعة {0} بنجاح. بانتظار اكتمال الطلبات الأخرى...",
    "Percentage you are allowed to sell beyond the Blanket Order quantity.": "النسبة المسموح لك بيعها زائدًا عن كمية أمر البيع المفتوح.",
    "Please contact any of the following users to extend the credit limits for {0}: {1}": "يرجى التواصل مع أحد المستخدمين التاليين لتمديد حدود الائتمان لـ {0}: {1}",
    "Please contact your administrator to extend the credit limits for {0}.": "يرجى التواصل مع المسؤول لتمديد حدود الائتمان لـ {0}.",
    "Please enter a valid number of deliveries": "يرجى إدخال عدد تسليمات صالح",
    "Please enter at least one delivery date and quantity": "يرجى إدخال تاريخ تسليم وكمية على الأقل",
    "Please enter the first delivery date": "يرجى إدخال تاريخ التسليم الأول",
    "Please save the Sales Order before adding a delivery schedule.": "يرجى حفظ أمر البيع قبل إضافة جدول التسليم.",
    "Please select a frequency for delivery schedule": "يرجى تحديد تكرار جدول التسليم",
    "Please select atleast one item to continue": "يرجى تحديد صنف واحد على الأقل للمتابعة",
    "Quarter {0} {1}": "الربع {0} {1}",
    "Reason for hold:": "سبب الإيقاف:",
    "Restrict Items Based On": "تقييد الأصناف بناءً على",
    "Row #{0}: BOM not found for FG Item {1}": "الصف #{0}: لم يتم العثور على قائمة المواد لصنف المنتج النهائي {1}",
    "Row #{0}: Quantity cannot be a non-positive number. Please increase the quantity or remove the Item {1}": "الصف #{0}: لا يمكن أن تكون الكمية رقمًا غير موجب. يرجى زيادة الكمية أو إزالة الصنف {1}",
    "Sales Invoice {0} must be deleted before cancelling this Sales Order": "يجب حذف فاتورة البيع {0} قبل إلغاء أمر البيع هذا",
    "Sales Opportunities by Campaign": "فرص البيع حسب الحملة",
    "Sales Opportunities by Medium": "فرص البيع حسب الوسيط",
    "Sales Opportunities by Source": "فرص البيع حسب المصدر",
    "Sales Order {0} already exists against Customer's Purchase Order {1}. To allow multiple Sales Orders, Enable {2} in {3}": "يوجد أمر بيع {0} بالفعل مقابل أمر شراء العميل {1}. للسماح بأوامر بيع متعددة، فعّل {2} في {3}",
    "Sales Partner Target Variance Based On Item Group": "الفرق المستهدف لشركاء البيع بناءً على مجموعة الأصناف",
    "Sales Pipeline by Stage": "مسار البيع حسب المرحلة",
    "Select an item from each set to be used in the Sales Order.": "حدد صنفًا من كل مجموعة لاستخدامه في أمر البيع.",
    "Serial numbers unavailable for Item {0} under warehouse {1}. Please try changing warehouse.": "الأرقام التسلسلية غير متاحة للصنف {0} في المستودع {1}. يرجى تجريب تغيير المستودع.",
    "Show Aggregate Value from Subsidiary Companies": "عرض القيمة الإجمالية للشركات التابعة",
    "Sold by": "تم البيع بواسطة",
    "Stock quantity not enough for Item Code: {0} under warehouse {1}. Available quantity {2} {3}.": "كمية المخزون غير كافية لرمز الصنف: {0} في المستودع {1}. الكمية المتاحة {2} {3}.",
    "Successfully linked to Supplier": "تم الربط بالمورد بنجاح",
    "Supplier is required for all selected Items": "المورد مطلوب لجميع الأصناف المحددة",
    "Supplier numbers assigned by the customer": "أرقام الموردين التي يعينها العميل",
    "The current POS opening entry is outdated. Please close it and create a new one.": "قيد فتح نقطة البيع الحالي قديم. يرجى إغلاقه وإنشاء قيد جديد.",
    "This Sales Order has been fully subcontracted.": "تم التعاقد بأكمله بمقاولة الباطن لأمر البيع هذا.",
    "This item filter has already been applied for the {0}": "تم تطبيق عامل تصفية الأصناف هذا بالفعل للـ {0}",
    "Total Only": "الإجمالي فقط",
    "Total Picked Quantity {0} is more than ordered qty {1}. You can set the Over Picking Allowance in Stock Settings.": "إجمالي الكمية الملتقطة {0} أكبر من الكمية المطلوبة {1}. يمكنك ضبط حصة الالتقاط الزائد في إعدادات المخزون.",
    "Total quantity in delivery schedule cannot be greater than the item quantity": "إجمالي الكمية في جدول التسليم لا يمكن أن يكون أكبر من كمية الصنف",
    "Use Legacy (Client side) Reactivity": "استخدام نموذج التفاعلية القديم (من جهة العميل)",
    "Week {0} {1}": "الأسبوع {0} {1}",
    "You have unsaved changes. Do you want to save the invoice?": "لديك تغييرات غير محفوظة. هل تريد حفظ الفاتورة؟",
    "discount applied": "تم تطبيق الخصم",
    "{}  To Deliver": "{}  للتسليم",
}


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 48, f"expected 48 scope rows, got {len(scope_rows)}"
    assert len(set(scope_rows)) == 48, "scope source_text not unique"

    recon = json.loads(SITE_RECON.read_text(encoding="utf-8"))
    PRESERVED = {p["source_text"]: p["translated_text"] for p in recon["preserved"]}
    assert len(PRESERVED) == 1, f"expected 1 preserved, got {len(PRESERVED)}"
    assert "Address" in PRESERVED, PRESERVED.keys()

    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {sorted(diff, key=str)}"
    assert not (set(A) & set(PRESERVED)), "A and PRESERVED overlap"
    assert not (set(A) & set(TECHNICAL)), "A and TECHNICAL overlap"
    assert not (set(TECHNICAL) & set(PRESERVED)), "TECHNICAL and PRESERVED overlap"

    ph_re = re.compile(r"\{[^{}]*\}")
    for s, ar in A.items():
        assert "\x00" not in ar
        assert ar[: len(ar) - len(ar.lstrip())] == s[: len(s) - len(s.lstrip())], f"affix-lstrip: {s!r}"
        assert ar[len(ar.rstrip()):] == s[len(s.rstrip()):], f"affix-rstrip: {s!r} -> {ar!r}"
        src_ph = sorted(ph_re.findall(s))
        ar_ph = sorted(ph_re.findall(ar))
        assert src_ph == ar_ph, f"placeholder mismatch on {s!r}: {src_ph} != {ar_ph}"
        assert ar != s, f"source-equal released: {s!r}"
        assert "\t" not in ar and "\n" not in ar and "\r" not in ar, repr(ar)

    for s in TECHNICAL:
        assert s not in A

    preserved_srcs = [s for s in scope_rows if s in PRESERVED]
    tech_srcs = [s for s in scope_rows if s in TECHNICAL]
    payload_srcs = [s for s in scope_rows if s in A]

    assert len(preserved_srcs) == 1, f"expected 1 preserved, got {len(preserved_srcs)}"
    assert len(tech_srcs) == 3, f"expected 3 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 44, f"expected 44 payload, got {len(payload_srcs)}"
    assert len(preserved_srcs) + len(tech_srcs) + len(payload_srcs) == 48

    rows_out = []
    for s in scope_rows:
        if s in PRESERVED:
            rows_out.append(
                (
                    s,
                    PRESERVED[s],
                    "preserved-site-override (not imported, plan §12)",
                    GOVERNANCE_REF,
                )
            )
        elif s in TECHNICAL:
            rows_out.append(
                (
                    s,
                    "EXCEPTION-technical",
                    "EXCEPTION-technical (keep vendor rendering; no translation)",
                    GOVERNANCE_REF,
                )
            )
        else:
            rows_out.append(
                (
                    s,
                    A[s],
                    "quorum-confirmed (release payload row)",
                    GOVERNANCE_REF,
                )
            )
    for row in rows_out:
        for cell in row:
            assert "\t" not in cell and "\n" not in cell and "\r" not in cell, repr(cell)
    with PAYLOAD.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE, quotechar=None)
        w.writerow(["source_text", "translated_text", "quorum_decision", "decision_ref"])
        w.writerows(rows_out)

    with APPROVED.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == FIELDNAMES, f"catalog header drift: {reader.fieldnames}"
        existing_rows = list(reader)
    before = len(existing_rows)
    assert before == 2275, f"expected 2275 catalog rows, got {before}"
    existing_srcs = {r["source_text"] for r in existing_rows}
    for s in A:
        assert s not in existing_srcs, f"would duplicate catalog row: {s!r}"
    for s in PRESERVED:
        assert s not in existing_srcs, f"preserved key already in catalog: {s!r}"
    for s in TECHNICAL:
        assert s not in existing_srcs, f"technical key already in catalog: {s!r}"

    new_rows = []
    for s in payload_srcs:
        new_rows.append(
            {
                "language": "ar",
                "source_text": s,
                "context": "",
                "ct_app": CT_APP,
                "translated_text": A[s],
                "domain": DOMAIN,
                "release_status": "Released",
                "release_version": RELEASE_VERSION,
                "a1_reviewer": REVIEWERS[0],
                "a1_approved_at": TS,
                "a2_reviewer": REVIEWERS[1],
                "a2_approved_at": TS,
                "a3_reviewer": REVIEWERS[2],
                "a3_approved_at": TS,
                "references": REFERENCES,
                "notes": NOTES,
                "decision_ref": DECISION_REF,
            }
        )
    out_rows = existing_rows + new_rows
    assert len(out_rows) == 2319, f"expected 2319 rows, got {len(out_rows)}"
    assert all(r["release_status"] == "Released" for r in out_rows), "non-Released row remains"
    for r in new_rows:
        for col in (
            "a1_reviewer",
            "a2_reviewer",
            "a3_reviewer",
            "a1_approved_at",
            "a2_approved_at",
            "a3_approved_at",
            "release_version",
            "references",
            "decision_ref",
            "translated_text",
        ):
            assert (r.get(col) or "").strip(), f"empty {col} on {r['source_text']!r}"

    with APPROVED.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)

    with RELEASED_LIST.open("w", encoding="utf-8", newline="\n") as fh:
        for s in payload_srcs:
            fh.write(s + "\n")

    recon_out = dict(recon)
    recon_out.update(
        {
            "scope_sha256": SCOPE_SHA,
            "disposition": {
                "preserved_site_override": 1,
                "already_released_catalog": 0,
                "exception_technical": 3,
                "quorum_confirmed_payload": 44,
                "total": 48,
            },
            "note": (
                "Authoritative dump "
                f"{recon.get('runtime_rows_scanned')} runtime rows. "
                "1 ct_origin='Site Override' preserve (Address); "
                "3 identifier technical tokens (doctype, doc_type, quotation_item); "
                "44 new Released payload rows appended."
            ),
        }
    )
    SITE_RECON.write_text(json.dumps(recon_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    after = len(out_rows)
    print(f"preserved={len(preserved_srcs)} technical={len(tech_srcs)} payload={len(payload_srcs)}")
    print(f"approved rows {before} -> {after}")
    print(f"wrote {PAYLOAD}")
    print(f"wrote {RELEASED_LIST} ({len(payload_srcs)} lines)")
    print(f"wrote {SITE_RECON}")
    assert before == 2275
    assert after == 2319


if __name__ == "__main__":
    main()
