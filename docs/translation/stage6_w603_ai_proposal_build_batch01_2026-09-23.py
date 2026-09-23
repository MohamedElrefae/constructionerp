"""W6-3 batch-01 governed proposal build (2026-09-23).

Owner-approved exact 250-row W6-3 Stock batch-01 scope (sha
5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380).

Outputs (fail-closed, deterministic):
  - stage6_w603_payload_applied_rows_batch01_2026-09-23.csv  (250 dispositions, tab-sep)
  - construction/data/translations/approved_ar_overrides.csv (append 118 Released) 2319 -> 2437
  - stage6_w603_batch01_released_list.txt                    (118)
  - stage6_w603_batch01_site_recon_2026-09-23.json           (authoritative summary refresh)
"""

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w603_batch01_rows_2026-09-23.csv"
PAYLOAD = HERE / "stage6_w603_payload_applied_rows_batch01_2026-09-23.csv"
RELEASED_LIST = HERE / "stage6_w603_batch01_released_list.txt"
SITE_RECON = HERE / "stage6_w603_batch01_site_recon_2026-09-23.json"
APPROVED = HERE.parent.parent / "construction/data/translations/approved_ar_overrides.csv"

DATE = "2026-09-23"
SCOPE_SHA = "5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380"
DECISION_REF = f"content:docs/translation/stage6_w603_payload_applied_rows_batch01_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger erpnext_ar_missing_review_filled.csv; plan D5; W6-3 batch-01"
NOTES = (
    "AI proposal 2026-09-23 + quorum-confirmed (W6-3 batch-01; "
    "owner-approved 250-row Stock scope minus site-override preserves "
    "and identifier technical tokens)"
)
RELEASE_VERSION = "1.5"
REVIEWERS = (
    "AI-A1 (recorded review run)",
    "AI-A2 (recorded review run)",
    "AI-A3 (recorded review run)",
)
TS = "2026-09-23 00:00:00"
DOMAIN = "stock-desk"
GOVERNANCE_REF = f"stage6-W6-3 batch-01 owner-approved {DATE}"
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

# Identifier / barcode technical tokens — keep vendor rendering
TECHNICAL = {
    "A - B",
    "A - C",
    "CODE-39",
    "D - E",
    "EAN",
    "EAN-12",
    "EAN-8",
    "G - D",
    "GS1",
    "GTIN",
    "H - F",
    "I - J",
    "I - K",
    "ISBN",
    "ISBN-10",
    "ISBN-13",
    "ISSN",
}

# Whitespace-variant site overrides: runtime _runtime_source strips edge
# whitespace and finds Site Override rows for the unstripped scope keys, so
# import marks drift. Preserve site values (plan §12); not payload.
PRESERVED_DRIFT = {
    " Is Child Table": "جدول فرعي",
    "Finished Good Quantity ": "كمية المنتج النهائي",
}

# AI proposal panel: 118 payload rows (all new; 2 former pre-filled moved to PRESERVED_DRIFT)
A = {
    "% of materials delivered against this Pick List": "% o نسبة المواد المسلمة مقابل قائمة الانتقاء هذه",
    "'Inspection Required before Delivery' has disabled for the item {0}, no need to create the QI": "تم تعطيل 'مطلوب فحص قبل التسليم' للصنف {0}، لا حاجة لإنشاء فحص الجودة",
    "'Inspection Required before Purchase' has disabled for the item {0}, no need to create the QI": "تم تعطيل 'مطلوب فحص قبل الشراء' للصنف {0}، لا حاجة لإنشاء فحص الجودة",
    "'To Package No.' cannot be less than 'From Package No.'": "لا يمكن أن يكون 'رقم الطرد إلى' أقل من 'رقم الطرد من'",
    "(A) Qty After Transaction": "(A) الكمية بعد المعاملة",
    "(B) Expected Qty After Transaction": "(B) الكمية المتوقعة بعد المعاملة",
    "(C) Total Qty in Queue": "(C) إجمالي الكمية في الطابور",
    "(C) Total qty in queue": "(C) إجمالي الكمية في الطابور",
    "(D) Balance Stock Value": "(D) قيمة رصيد المخزون",
    "(Daily Yield * No of Units Produced) / 100": "(الإنتاجية اليومية * عدد الوحدات المنتجة) / 100",
    "(E) Balance Stock Value in Queue": "(E) قيمة رصيد المخزون في الطابور",
    "(F) Change in Stock Value": "(F) التغير في قيمة المخزون",
    "(G) Sum of Change in Stock Value": "(G) مجموع التغير في قيمة المخزون",
    "(Good Units Produced / Total Units Produced) × 100": "(الوحدات الجيدة المنتجة / إجمالي الوحدات المنتجة) × 100",
    "(H) Change in Stock Value (FIFO Queue)": "(H) التغير في قيمة المخزون (طابور FIFO)",
    "(H) Valuation Rate": "(H) سعر التقييم",
    "(I) Valuation Rate": "(I) سعر التقييم",
    "(J) Valuation Rate as per FIFO": "(J) سعر التقييم وفق FIFO",
    "(K) Valuation = Value (D) ÷ Qty (A)": "(K) التقييم = القيمة (D) ÷ الكمية (A)",
    "(Total Workstation Time / Manufacturing Time) * 60": "(إجمالي وقت محطة العمل / وقت التصنيع) * 60",
    "A Packing Slip can only be created for Draft Delivery Note.": "يمكن إنشاء سند التعبئة فقط لإذن التسليم المبدئي.",
    "A Price List is a collection of Item Prices either Selling, Buying, or both": "قائمة الأسعار هي مجموعة أسعار أصناف للبيع أو الشراء أو كليهما",
    "A Product or a Service that is bought, sold or kept in stock.": "منتج أو خدمة يتم شراؤها أو بيعها أو حفظها في المخزون.",
    "A driver must be set to submit.": "يجب تحديد السائق قبل الإرسال.",
    "A logical Warehouse against which stock entries are made.": "مستودع منطقي تُنشأ عليه قيود المخزون.",
    "A naming series conflict occurred while creating serial numbers. Please change the naming series for the item {0}.": "حدث تعارض في سلسلة التسمية أثناء إنشاء الأرقام التسلسلية. يرجى تغيير سلسلة التسمية للصنف {0}.",
    "AMC Expiry (Serial)": "انتهاء عقد الصيانة (تسلسلي)",
    "AWB Number": "رقم بوليصة الشحن الجوي",
    "Abbreviation: {0} must appear only once": "الاختصار: يجب أن يظهر {0} مرة واحدة فقط",
    "Acceptance Criteria Formula": "صيغة معايير القبول",
    "Acceptance Criteria Value": "قيمة معايير القبول",
    "According to the BOM {0}, the Item '{1}' is missing in the stock entry.": "وفقًا لقائمة المواد {0}، الصنف '{1}' مفقود في قيد المخزون.",
    "Accounting Entry for {0}": "قيد محاسبي لـ {0}",
    "Add Serial / Batch No (Rejected Qty)": "إضافة رقم تسلسلي / دفعة (كمية مرفوضة)",
    "Adjustment based on Purchase Invoice rate": "تعديل بناءً على سعر فاتورة الشراء",
    "All items have already been received": "تم استلام جميع الأصناف بالفعل",
    "Allow Alternative Item must be checked on Item {}": "يجب تحديد 'السماح بصنف بديل' على الصنف {}",
    "Allow UOM with Conversion Rate Defined in Item": "السماح بوحدة قياس لها سعر تحويل محدد في الصنف",
    "Allow Variant UOM to be different from Template UOM": "السماح لوحدة قياس المتغير أن تختلف عن وحدة القالب",
    "Allow existing Serial No to be Manufactured/Received again": "السماح بإعادة تصنيع/استلام الرقم التسلسلي الموجود",
    "Allow to Edit Stock UOM Qty for Purchase Documents": "السماح بتعديل كمية وحدة قياس المخزون لمستندات الشراء",
    "Allow to Edit Stock UOM Qty for Sales Documents": "السماح بتعديل كمية وحدة قياس المخزون لمستندات البيع",
    "Allow to Make Quality Inspection after Purchase / Delivery": "السماح بإجراء فحص الجودة بعد الشراء / التسليم",
    "Allows to keep aside a specific quantity of inventory for a particular order.": "يسمح بحجز كمية محددة من المخزون لطلب معين.",
    "Also you can't switch back to FIFO after setting the valuation method to Moving Average for this item.": "أيضًا لا يمكنك العودة إلى FIFO بعد ضبط طريقة التقييم بمتوسط المتحرك لهذا الصنف.",
    "An error has been appeared while reposting item valuation via {0}": "ظهر خطأ أثناء إعادة ترحيل تقييم الصنف عبر {0}",
    "Any one of following filters required: warehouse, Item Code, Item Group": "مطلوب أي من المرشحات التالية: مستودع، رمز صنف، مجموعة أصناف",
    "Applied on each reading.": "يُطبق على كل قراءة.",
    "Applied putaway rules.": "تم تطبيق قواعد التخزين.",
    "As there are existing submitted transactions against item {0}, you can not change the value of {1}.": "لوجود معاملات مُرسلة بالفعل مقابل الصنف {0}، لا يمكنك تغيير قيمة {1}.",
    "As there are reserved stock, you cannot disable {0}.": "لوجود مخزون محجوز، لا يمكنك تعطيل {0}.",
    "As {0} is enabled, you can not enable {1}.": "بما أن {0} مفعل، لا يمكنك تفعيل {1}.",
    "At Row #{0}: The picked quantity {1} for the item {2} is greater than available stock {3} in the warehouse {4}.": "في الصف #{0}: الكمية المنتقاة {1} للصنف {2} أكبر من المخزون المتاح {3} في المستودع {4}.",
    "At least one warehouse is mandatory": "مستودع واحد على الأقل إلزامي",
    "At row {0}: Batch No is mandatory for Item {1}": "في الصف {0}: رقم الدفعة إلزامي للصنف {1}",
    "At row {0}: Qty is mandatory for the batch {1}": "في الصف {0}: الكمية إلزامية للدفعة {1}",
    "At row {0}: Serial No is mandatory for Item {1}": "في الصف {0}: الرقم التسلسلي إلزامي للصنف {1}",
    "Attribute value: {0} must appear only once": "قيمة السمة: يجب أن تظهر {0} مرة واحدة فقط",
    "Auto Insert Item Price If Missing": "إدراج سعر الصنف تلقائيًا عند غيابه",
    "Auto Reserve Stock for Sales Order on Purchase": "حجز المخزون تلقائيًا لأمر البيع عند الشراء",
    "Batch No {0} does not exists": "رقم الدفعة {0} غير موجود",
    "Batch No {0} is linked with Item {1} which has serial no. Please scan serial no instead.": "رقم الدفعة {0} مرتبط بالصنف {1} الذي يحمل رقمًا تسلسليًا. يرجى مسح الرقم التسلسلي بدلاً من ذلك.",
    "Batch No {0} is not present in the original {1} {2}, hence you can't return it against the {1} {2}": "رقم الدفعة {0} غير موجود في {1} {2} الأصلي، لذا لا يمكنك إعادته مقابل {1} {2}",
    "Batch Nos are created successfully": "تم إنشاء أرقام الدفعات بنجاح",
    "Batch Qty updated to {0}": "تم تحديث كمية الدفعة إلى {0}",
    "Batch {0} and Warehouse": "الدفعة {0} والمستودع",
    "Booking stock value across multiple accounts will make it harder to track stock and account value.": "تسجيل قيمة المخزون عبر حسابات متعددة يجعل تتبع قيمة المخزون والحساب أصعب.",
    "Cannot amend {0} {1}, please create a new one instead.": "لا يمكن تعديل {0} {1}، يرجى إنشاء سجل جديد بدلاً من ذلك.",
    "Cannot cancel as processing of cancelled documents is pending.": "لا يمكن الإلغاء لوجود معالجة معلقة لمستندات ملغاة.",
    "Cannot cancel the transaction. Reposting of item valuation on submission is not completed yet.": "لا يمكن إلغاء المعاملة. إعادة ترحيل تقييم الصنف عند الإرسال لم تكتمل بعد.",
    "Cannot create Stock Reservation Entries for future dated Purchase Receipts.": "لا يمكن إنشاء قيود حجز مخزون لسندات استلام بتواريخ مستقبلية.",
    "Charges are updated in Purchase Receipt against each item": "تُحدَّث التكاليف في سند استلام الشراء لكل صنف",
    "Charges will be distributed proportionately based on item qty or amount, as per your selection": "ستُوزَّع التكاليف تناسبية بناءً على كمية الصنف أو المبلغ، حسب اختيارك",
    "Company which internal customer represents.": "الشركة التي يمثلها العميل الداخلي.",
    "Conditional Rule Examples": "أمثلة على القواعد الشرطية",
    "Consumed quantity of item {0} exceeds transferred quantity.": "الكمية المستهلكة من الصنف {0} تتجاوز الكمية المنقولة.",
    "Cost of Goods Sold Account in Items Table": "حساب تكلفة البضاعة المباعة في جدول الأصناف",
    "Create a variant with the template image.": "إنشاء متغير بصورة القالب.",
    "Creating Packing Slip ...": "جارٍ إنشاء سند التعبئة ...",
    "Default settings for your stock-related transactions": "الإعدادات الافتراضية لمعاملات المخزون الخاصة بك",
    "Delivery to": "التسليم إلى",
    "Dependant SLE Voucher Detail No": "رقم تفاصيل سند قيد دفتر الأستاذ المخزني التابع",
    "Different 'Source Warehouse' and 'Target Warehouse' can be set for each row.": "يمكن ضبط 'مستودع المصدر' و'مستودع الوجهة' مختلفين لكل صف.",
    "Disabled Warehouse {0} cannot be used for this transaction.": "لا يمكن استخدام المستودع المعطل {0} في هذه المعاملة.",
    "Disables auto-fetching of existing quantity": "يعطيل الجلب التلقائي للكمية الموجودة",
    "Distinct Item and Warehouse": "صنف ومستودع مميزين",
    "Distinct unit of an Item": "وحدة مميزة للصنف",
    "Distribute Manually": "التوزيع يدويًا",
    "Do you still want to enable negative inventory?": "هل ما زلت تريد تفعيل المخزون السالب؟",
    "Do you want to change valuation method?": "هل تريد تغيير طريقة التقييم؟",
    "Due to stock closing entry {0}, you cannot repost item valuation before {1}": "بسبب قيد إغلاق المخزون {0}، لا يمكنك إعادة ترحيل تقييم الصنف قبل {1}",
    "Duplicate Stock Closing Entry": "قيد إغلاق مخزون مكرر",
    "Email or Phone/Mobile of the Contact are mandatory to continue.": "البريد الإلكتروني أو الهاتف/الجوال لجهة الاتصال إلزاميان للمتابعة.",
    "Enable Allow Partial Reservation in the Stock Settings to reserve partial stock.": "فعّل 'السماح بالحجز الجزئي' في إعدادات المخزون لحجز مخزون جزئي.",
    "Enable it if users want to consider rejected materials to dispatch.": "فعّله إذا أردت اعتبار المواد المرفوضة للشحن.",
    "Enter an Item Code, the name will be auto-filled the same as Item Code on clicking inside the Item Name field.": "أدخل رمز صنف، سيُملأ الاسم تلقائيًا بنفس رمز الصنف عند النقر داخل حقل اسم الصنف.",
    "Enter the opening stock units.": "أدخل وحدات المخزون الافتتاحية.",
    "Error while reposting item valuation": "خطأ أثناء إعادة ترحيل تقييم الصنف",
    "Example of a linked document: {0}": "مثال على مستند مرتبط: {0}",
    "Example: Serial No {0} reserved in {1}.": "مثال: تم حجز الرقم التسلسلي {0} في {1}.",
    "FIFO Stock Queue (qty, rate)": "طابور مخزون FIFO (كمية، سعر)",
    "Finished Item {0} does not match with Work Order {1}": "الصنف النهائي {0} لا يتطابق بأمر العمل {1}",
    "Fix SABB Entry": "إصلاح قيد SABB",
    "For quantity {0} should not be greater than allowed quantity {1}": "الكمية {0} يجب ألا تتجاوز الكمية المسموح بها {1}",
    "For the convenience of customers, these codes can be used in print formats like Invoices and Delivery Notes": "لراحة العملاء، يمكن استخدام هذه الرموز في تنسيقات الطباعة مثل الفواتير وإذونات التسليم",
    "For the item {0}, the quantity should be {1} according to the BOM {2}.": "للصنف {0}، يجب أن تكون الكمية {1} وفقًا لقائمة المواد {2}.",
    "From and To dates are required": "تاريخا من وإلى مطلوبان",
    "Generate packing slips for packages to be delivered. Used to notify package number, package contents and its weight.": "إنشاء أوراق تعبئة للطرود المراد تسليمها. تُستخدم لإخطار رقم الطرد ومحتوياته ووزنه.",
    "Get stops from": "الحصول على المحطات من",
    "Have Default Naming Series for Batch ID?": "هل توجد سلسلة تسمية افتراضية لمعرف الدفعة؟",
    "Here are the options to proceed:": "هذه خيارات المتابعة:",
    "Hi,": "مرحبًا،",
    "If checked, picked qty won't automatically be fulfilled on submit of pick list.": "عند التحديد، لن تُنفذ الكمية المنتقاة تلقائيًا عند إرسال قائمة الانتقاء.",
    "If enabled then system won't apply the pricing rule on the delivery note which will be create from the pick list": "عند التفعيل، لن يطبق النظام قاعدة التسعير على إذن التسليم الذي سيُنشأ من قائمة الانتقاء",
    "If enabled then system won't override the picked qty / batches / serial numbers / warehouse.": "عند التفعيل، لن يتجاوز النظام الكمية المنتقة / الدفعات / الأرقام التسلسلية / المستودع.",
    "If not, you can Cancel / Submit this entry": "إذا لم يكن كذلك، يمكنك إلغاء / إرسال هذا القيد",
    "If yes, then this warehouse will be used to store rejected materials": "إذا نعم، فسيُستخدم هذا المستودع لتخزين المواد المرفوضة",
    "In Transit Warehouse": "مستودع قيد العبور",
}


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 250, f"expected 250 scope rows, got {len(scope_rows)}"
    assert len(set(scope_rows)) == 250, "scope source_text not unique"

    recon = json.loads(SITE_RECON.read_text(encoding="utf-8"))
    PRESERVED = {p["source_text"]: p["translated_text"] for p in recon["preserved"]}
    assert len(PRESERVED) == 113, f"expected 113 preserved, got {len(PRESERVED)}"
    PRESERVED.update(PRESERVED_DRIFT)

    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {sorted(diff, key=str)[:20]} (n={len(diff)})"
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

    assert len(preserved_srcs) == 115, f"expected 115 preserved, got {len(preserved_srcs)}"
    assert len(tech_srcs) == 17, f"expected 17 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 118, f"expected 118 payload, got {len(payload_srcs)}"
    assert len(preserved_srcs) + len(tech_srcs) + len(payload_srcs) == 250

    rows_out = []
    for s in scope_rows:
        if s in PRESERVED:
            decision = (
                "preserved-site-override (whitespace-variant drift, plan §12)"
                if s in PRESERVED_DRIFT
                else "preserved-site-override (not imported, plan §12)"
            )
            rows_out.append(
                (
                    s,
                    PRESERVED[s],
                    decision,
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
    assert before == 2319, f"expected 2319 catalog rows, got {before}"
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
    assert len(out_rows) == 2437, f"expected 2437 rows, got {len(out_rows)}"
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
                "preserved_site_override": 115,
                "already_released_catalog": 0,
                "exception_technical": 17,
                "quorum_confirmed_payload": 118,
                "total": 250,
            },
            "note": (
                "Authoritative dump "
                f"{recon.get('runtime_rows_scanned')} runtime rows. "
                "115 ct_origin='Site Override' preserves "
                "(113 exact + 2 whitespace-variant drift); "
                "17 identifier/letter technical tokens; "
                "118 new Released payload rows appended."
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
    assert before == 2319
    assert after == 2437


if __name__ == "__main__":
    main()
