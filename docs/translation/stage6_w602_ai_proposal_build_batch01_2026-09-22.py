"""W6-2 batch-1 governed proposal build (2026-09-22).

Owner-approved exact 270-row W6-2 Buying+Selling scope (sha
b017df4787ff8754be0bf43425151b748ba0aa019348fa29187f660130408fae).

Outputs (fail-closed, deterministic):
  - stage6_w602_payload_applied_rows_batch01_2026-09-22.csv  (270 dispositions, tab-sep)
  - construction/data/translations/approved_ar_overrides.csv (append 86 Released) 2190 -> 2276
  - stage6_w602_batch01_released_list.txt                    (86)
  - stage6_w602_batch01_site_recon_2026-09-22.json           (authoritative summary refresh)
"""

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w602_batch01_rows_2026-09-22.csv"
PAYLOAD = HERE / "stage6_w602_payload_applied_rows_batch01_2026-09-22.csv"
RELEASED_LIST = HERE / "stage6_w602_batch01_released_list.txt"
SITE_RECON = HERE / "stage6_w602_batch01_site_recon_2026-09-22.json"
APPROVED = HERE.parent.parent / "construction/data/translations/approved_ar_overrides.csv"

DATE = "2026-09-22"
SCOPE_SHA = "b017df4787ff8754be0bf43425151b748ba0aa019348fa29187f660130408fae"
DECISION_REF = f"content:docs/translation/stage6_w602_payload_applied_rows_batch01_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger erpnext_ar_missing_review_filled.csv; plan D5; W6-2 batch-01"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed (W6-2 batch-01; "
    "owner-approved 270-row Buying+Selling scope minus site-override preserves "
    "and already-released catalog row)"
)
RELEASE_VERSION = "1.4"
REVIEWERS = (
    "AI-A1 (recorded review run)",
    "AI-A2 (recorded review run)",
    "AI-A3 (recorded review run)",
)
TS = "2026-09-22 00:00:00"
DOMAIN = "buying-selling-desk"
GOVERNANCE_REF = f"stage6-W6-2 batch-01 owner-approved {DATE}"
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

# already Released in managed catalog (Stage-1C / legacy sign-off); not re-appended
ALREADY = {"Advance Payment": "دفعة مقدمة"}

# EXCEPTION-technical for this batch: none after quorum (all unfilled are full UI sentences)
TECHNICAL = set()

A = {
    "Added Supplier Role to User {0}.": "تمت إضافة دور المورد للمستخدم {0}.",
    "Allow Purchase Order with Zero Quantity": "السماح بأمر شراء بكمية صفر",
    "Allow Request for Quotation with Zero Quantity": "السماح بطلب عرض سعر بكمية صفر",
    "Allow Supplier Quotation with Zero Quantity": "السماح بعرض سعر مورد بكمية صفر",
    "Analysis Chart": "مخطط التحليل",
    "Billed, Received & Returned": "مفوتر، مستلَم، ومرتجع",
    "Configure the action to stop the transaction or just warn if the same rate is not maintained.": "تكوين الإجراء لإيقاف المعاملة أو مجرد تنبيه في حال عدم الالتزام بنفس السعر.",
    "Could not find path for ": "تعذّر العثور على المسار لـ ",
    "Creating Subcontracting Order ...": "جارٍ إنشاء أمر مقاولة باطن ...",
    "Criteria weights must add up to 100%": "يجب أن يكون مجموع أوزان المعايير 100%",
    "Expires in a week or less": "تنتهي صلاحيته خلال أسبوع أو أقل",
    "Expires today or already expired": "تنتهي صلاحيته اليوم أو انتهت بالفعل",
    "How often should Project be updated of Total Purchase Cost ?": "كم مرة يجب تحديث إجمالي تكلفة الشراء في المشروع؟",
    "If checked, Rejected Quantity will be included while making Purchase Invoice from Purchase Receipt.": "عند التحديد، ستُضمَّن الكمية المرفوضة عند إنشاء فاتورة الشراء من إيصال الشراء.",
    "If enabled, a print of this document will be attached to each email": "عند التفعيل، ستُرفق طباعة لهذا المستند مع كل رسالة بريد إلكتروني",
    "If enabled, all files attached to this document will be attached to each email": "عند التفعيل، ستُرفق جميع الملفات المرفقة بهذا المستند مع كل رسالة بريد إلكتروني",
    "If enabled, the system will generate an accounting entry for materials rejected in the Purchase Receipt.": "عند التفعيل، سيُنشئ النظام قيدًا محاسبيًا للمواد المرفوضة في إيصال الشراء.",
    "Internal Supplier for company {0} already exists": "يوجد مورد داخلي بالفعل للشركة {0}",
    "Learn Procurement": "تعرّف على المشتريات",
    "Linking to Customer Failed. Please try again.": "فشل الربط بالعميل. يرجى المحاولة مرة أخرى.",
    "Partnership": "شراكة",
    "Percentage you are allowed to order beyond the Blanket Order quantity.": "النسبة المسموح بها للطلب بما زاد عن كمية الأمر المفتوح.",
    "Please add 'Supplier' role to user {0}.": "يرجى إضافة دور 'المورد' للمستخدم {0}.",
    "Please add Request for Quotation to the sidebar in Portal Settings.": "يرجى إضافة طلب عرض السعر إلى الشريط الجانبي في إعدادات البوابة.",
    "Portal Users": "مستخدمو البوابة",
    "Price ({0})": "السعر ({0})",
    "Price Per Unit ({0})": "السعر لكل وحدة ({0})",
    "Purchase Receipt (Draft) will be auto-created on submission of Subcontracting Receipt.": "سيُنشأ إيصال الشراء (مسودة) تلقائيًا عند ترحيل إيصال مقاولة الباطن.",
    "Raw materials consumed qty will be validated based on FG BOM required qty": "ستُتحقق الكمية المستهلكة من المواد الخام بناءً على الكمية المطلوبة في قائمة مواد المنتج النهائي",
    "Row #{0}: BOM is not specified for subcontracting item {0}": "الصف #{0}: لم يُحدد إجراء قائمة المواد لصنف مقاولة الباطن {0}",
    "Row #{0}: Default BOM not found for FG Item {1}": "الصف #{0}: لم يتم العثور على قائمة المواد الافتراضية لصنف المنتج النهائي {1}",
    "Row #{0}: Finished Good Item Qty can not be zero": "الصف #{0}: لا يمكن أن تكون كمية صنف المنتج النهائي صفرًا",
    "Row #{0}: Finished Good Item is not specified for service item {1}": "الصف #{0}: لم يُحدد صنف المنتج النهائي للصنف الخدمي {1}",
    "Row #{0}: Finished Good Item {1} must be a sub-contracted item": "الصف #{0}: يجب أن يكون صنف المنتج النهائي {1} صنف مقاولة باطن",
    "Row #{0}: Item {1} does not exist": "الصف #{0}: الصنف {1} غير موجود",
    "Row #{1}: Warehouse is mandatory for stock Item {0}": "الصف #{1}: المستودع إلزامي لصنف المخزون {0}",
    "Subcontracting Order (Draft) will be auto-created on submission of Purchase Order.": "سيُنشأ أمر مقاولة الباطن (مسودة) تلقائيًا عند ترحيل أمر الشراء.",
    "Subcontracting Order {0} created.": "تم إنشاء أمر مقاولة الباطن {0}.",
    "Successfully linked to Customer": "تم الربط بالعميل بنجاح",
    "Supplied Item": "الصنف المورَّد",
    "Supplier of Goods or Services.": "مورد للسلع أو الخدمات.",
    "This Purchase Order has been fully subcontracted.": "تمت مقاولة الباطن لأمر الشراء هذا بالكامل.",
    "This is a preview of the email to be sent. A PDF of the document will automatically be attached with the email.": "هذه معاينة للرسالة المراد إرسالها. ستُرفق تلقائيًا نسخة PDF من المستند مع البريد الإلكتروني.",
    "To be Delivered to Customer": "للتسليم للعميل",
    "Unable to find variable:": "تعذّر العثور على المتغير:",
    "{}  To Receive": "{}  للمستلَم",
    "{} Pending": "{} معلّق",
    "% of materials billed against this Sales Order": "نسبة المواد المفوترة ضد أمر البيع هذا",
    "% of materials delivered against this Sales Order": "نسبة المواد المسلَّمة ضد أمر البيع هذا",
    "'Allow Multiple Sales Orders Against a Customer's Purchase Order'": "السماح بأوامر بيع متعددة ضد أمر شراء العميل",
    "Action if Same Rate is Not Maintained Throughout Sales Cycle": "الإجراء إذا لم يُحافظ على نفس السعر طوال دورة البيع",
    "All the items have been already returned.": "تم إرجاع جميع الأصناف بالفعل.",
    "Allow Item to be Added Multiple Times in a Transaction": "السماح بإضافة الصنف عدة مرات في المعاملة",
    "Allow Quotation with Zero Quantity": "السماح بعرض سعر بكمية صفر",
    "Allow Sales Order Creation For Expired Quotation": "السماح بإنشاء أمر بيع لعرض سعر منتهي الصلاحية",
    "Allow Sales Order with Zero Quantity": "السماح بأمر بيع بكمية صفر",
    "Buyer of Goods and Services.": "مشتري للسلع والخدمات.",
    "Bypass credit check at Sales Order": "تجاوز فحص الائتمان عند أمر البيع",
    "Calculate Product Bundle Price based on Child Items' Rates": "احتساب سعر حزمة المنتج بناءً على أسعار الأصناف الفرعية",
    "Changed customer name to '{}' as '{}' already exists.": "تم تغيير اسم العميل إلى '{}' لوجود '{}' بالفعل.",
    "Click to add email / phone": "انقر لإضافة بريد إلكتروني / هاتف",
    "Creating Delivery Schedule...": "جارٍ إنشاء جدول التسليم...",
    "Creating Subcontracting Inward Order ...": "جارٍ إنشاء أمر مقاولة الباطن الوارد ...",
    "Curves": "منحنيات",
    "Discount cannot be greater than 100%": "لا يمكن أن يتجاوز الخصم 100%",
    "Discount cannot be greater than 100%.": "لا يمكن أن يتجاوز الخصم 100%.",
    "Don't Reserve Sales Order Qty on Sales Return": "لا تحجز كمية أمر البيع عند مرتجع المبيعات",
    "Editing {0} is not allowed as per POS Profile settings": "التعديل على {0} غير مسموح وفقًا لإعدادات ملف نقطة البيع",
    "Enable Cut-Off Date on Bulk Delivery Note Creation": "تفعيل تاريخ القطع عند إنشاء أذونات التسليم الجماعية",
    "Fetched only {0} available serial numbers.": "تم جلب {0} من أرقام تسلسلية متاحة فقط.",
    "If enabled, additional ledger entries will be made for discounts in a separate Discount Account": "عند التفعيل، ستُنشأ قيود دفتر إضافية للخصومات في حساب خصم منفصل",
    "Internal Customer for company {0} already exists": "يوجد عميل داخلي بالفعل للشركة {0}",
    "Item is removed since no serial / batch no selected.": "تمت إزالة الصنف لعدم اختيار رقم تسلسلي / دفعة.",
    "Item {0} has no Serial No. Only serialized items can have delivery based on Serial No": "الصنف {0} ليس له رقم تسلسلي. الأصناف المسلسلة فقط يمكن تسليمها برقم تسلسلي",
    "Learn Sales Management": "تعرّف على إدارة المبيعات",
    "Linking to Supplier Failed. Please try again.": "فشل الربط بالمورد. يرجى المحاولة مرة أخرى.",
    "Mention if non-standard Receivable account": "اذكر إذا كان حساب المدينون غير قياسي",
    "Multiple Loyalty Programs found for Customer {}. Please select manually.": "تم العثور على برامج ولاء متعددة للعميل {}. يرجى الاختيار يدويًا.",
    "No of Deliveries": "عدد التسليمات",
    "Non-Zeros": "غير الأصفار",
    "Only Value available for Payment Entry": "القيمة المتاحة فقط لقيد الدفع",
    "Opportunities by Campaign": "الفرص حسب الحملة",
    "Opportunities by Medium": "الفرص حسب الوسيط",
    "Opportunities by Source": "الفرص حسب المصدر",
    "POS Opening Entry has been cancelled. Please refresh the page.": "تم إلغاء قيد فتح نقطة البيع. يرجى تحديث الصفحة.",
    " Address": " العنوان"
}


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 270, f"expected 270 scope rows, got {len(scope_rows)}"
    assert len(set(scope_rows)) == 270, "scope source_text not unique"

    recon = json.loads(SITE_RECON.read_text(encoding="utf-8"))
    PRESERVED = {p["source_text"]: p["translated_text"] for p in recon["preserved"]}
    assert len(PRESERVED) == 183, f"expected 183 preserved, got {len(PRESERVED)}"

    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(ALREADY) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {sorted(diff, key=str)}"
    assert not (set(A) & set(PRESERVED)), "A and PRESERVED overlap"
    assert not (set(A) & set(ALREADY)), "A and ALREADY overlap"
    assert not (set(A) & set(TECHNICAL)), "A and TECHNICAL overlap"
    assert not (set(TECHNICAL) & set(PRESERVED)), "TECHNICAL and PRESERVED overlap"

    ph_re = re.compile(r"\{[^{}]*\}")
    for s, ar in A.items():
        assert "\x00" not in ar
        assert ar[: len(ar) - len(ar.lstrip())] == s[: len(s) - len(s.lstrip())], f"affix-lstrip: {s!r}"
        assert ar[len(ar.rstrip()):] == s[len(s.rstrip()):], f"affix-rstrip: {s!r}"
        src_ph = sorted(ph_re.findall(s))
        ar_ph = sorted(ph_re.findall(ar))
        assert src_ph == ar_ph, f"placeholder mismatch on {s!r}: {src_ph} != {ar_ph}"
        assert ar != s, f"source-equal released: {s!r}"
        assert "\t" not in ar and "\n" not in ar and "\r" not in ar, repr(ar)

    for s in TECHNICAL:
        assert s not in A

    preserved_srcs = [s for s in scope_rows if s in PRESERVED]
    already_srcs = [s for s in scope_rows if s in ALREADY]
    tech_srcs = [s for s in scope_rows if s in TECHNICAL]
    payload_srcs = [s for s in scope_rows if s in A]

    assert len(preserved_srcs) == 183, f"expected 183 preserved, got {len(preserved_srcs)}"
    assert len(already_srcs) == 1, f"expected 1 already, got {len(already_srcs)}"
    assert len(tech_srcs) == 0, f"expected 0 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 86, f"expected 86 payload, got {len(payload_srcs)}"
    assert len(preserved_srcs) + len(already_srcs) + len(tech_srcs) + len(payload_srcs) == 270

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
        elif s in ALREADY:
            rows_out.append(
                (
                    s,
                    ALREADY[s],
                    "already-released (catalog row retained; not re-appended)",
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

    # Catalog: append 86 new Released rows; keep existing 2190 including Advance Payment
    with APPROVED.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == FIELDNAMES, f"catalog header drift: {reader.fieldnames}"
        existing_rows = list(reader)
    before = len(existing_rows)
    assert before == 2190, f"expected 2190 catalog rows, got {before}"
    existing_srcs = {r["source_text"] for r in existing_rows}
    for s in A:
        assert s not in existing_srcs, f"would duplicate catalog row: {s!r}"
    for s in ALREADY:
        assert s in existing_srcs, f"already-released missing from catalog: {s!r}"
    for s in PRESERVED:
        assert s not in existing_srcs, f"preserved key already in catalog: {s!r}"

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
    assert len(out_rows) == 2276, f"expected 2276 rows, got {len(out_rows)}"
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

    # refresh recon summary counters (keep matches intact)
    recon_out = dict(recon)
    recon_out.update(
        {
            "scope_sha256": SCOPE_SHA,
            "disposition": {
                "preserved_site_override": 183,
                "already_released_catalog": 1,
                "exception_technical": 0,
                "quorum_confirmed_payload": 86,
                "total": 270,
            },
            "note": (
                "Authoritative dump "
                f"{recon.get('runtime_rows_scanned')} runtime rows. "
                "183 ct_origin='Site Override' preserves; 1 already-released catalog "
                "row (Advance Payment); 86 new Released payload rows appended "
                "(85 AI-proposed unfilled + 1 pre-filled ' Address')."
            ),
        }
    )
    SITE_RECON.write_text(json.dumps(recon_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    after = len(out_rows)
    print(f"preserved={len(preserved_srcs)} already={len(already_srcs)} technical={len(tech_srcs)} payload={len(payload_srcs)}")
    print(f"approved rows {before} -> {after}")
    print(f"wrote {PAYLOAD}")
    print(f"wrote {RELEASED_LIST} ({len(payload_srcs)} lines)")
    print(f"wrote {SITE_RECON}")
    assert before == 2190
    assert after == 2276


if __name__ == "__main__":
    main()
