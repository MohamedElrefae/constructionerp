"""Build the reviewed-input proposal table for W6-3 Stock batch 03.

This proposal-only builder is pinned to the owner-approved batch SHA. It does
not modify the managed catalog, release decisions, or the test site.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w603_batch03_rows_2026-09-23.csv"
RECON = HERE / "stage6_w603_batch03_site_recon_2026-09-24.json"
OUT = HERE / "stage6_w603_proposal_batch03_2026-09-24.csv"
SCOPE_SHA = "a5f0e9f604ea52d89072d2c744864fdcbc733bc8307fd427a5c2658f4855dbc9"
DECISION_REF = "stage6-W6-3 batch-03 owner-approved 2026-09-24"
TECHNICAL = {"UPC", "UPC-A"}

# Natural-language proposals for the 111 in-scope keys not already covered by
# a live Site Override. A1/A2/A3 must independently review every proposal.
A = {
    "Row #{0}: Source, Target Warehouse and Inventory Dimensions cannot be the exact same for Material Transfer": "الصف رقم {0}: لا يجوز أن يكون مستودع المصدر والوجهة وأبعاد المخزون متطابقة تمامًا عند نقل المواد",
    "Row #{0}: Status is mandatory": "الصف رقم {0}: الحالة مطلوبة",
    "Row #{0}: Stock cannot be reserved for Item {1} against a disabled Batch {2}.": "الصف رقم {0}: لا يمكن حجز مخزون الصنف {1} على الدفعة المعطلة {2}.",
    "Row #{0}: Stock cannot be reserved for a non-stock Item {1}": "الصف رقم {0}: لا يمكن حجز مخزون لصنف غير مخزني {1}",
    "Row #{0}: Stock cannot be reserved in group warehouse {1}.": "الصف رقم {0}: لا يمكن حجز المخزون في المستودع التجميعي {1}.",
    "Row #{0}: Stock is already reserved for the Item {1}.": "الصف رقم {0}: المخزون محجوز بالفعل للصنف {1}.",
    "Row #{0}: Stock is reserved for item {1} in warehouse {2}.": "الصف رقم {0}: المخزون محجوز للصنف {1} في المستودع {2}.",
    "Row #{0}: Stock not available to reserve for Item {1} against Batch {2} in Warehouse {3}.": "الصف رقم {0}: لا يتوفر مخزون لحجز الصنف {1} على الدفعة {2} في المستودع {3}.",
    "Row #{0}: Stock not available to reserve for the Item {1} in Warehouse {2}.": "الصف رقم {0}: لا يتوفر مخزون لحجز الصنف {1} في المستودع {2}.",
    "Row #{0}: The warehouse {1} is not a child warehouse of a group warehouse {2}": "الصف رقم {0}: المستودع {1} ليس مستودعًا فرعيًا للمستودع التجميعي {2}",
    "Row #{0}: {1} is not a valid reading field. Please refer to the field description.": "الصف رقم {0}: الحقل {1} غير صالح للقراءة. يُرجى الرجوع إلى وصف الحقل.",
    "Row #{}: item {} has been picked already.": "الصف رقم {}: تم انتقاء الصنف {} بالفعل.",
    "Row #{}: {} {} doesn't belong to Company {}. Please select valid {}.": "الصف رقم {}: لا يتبع {} {} الشركة {}. يُرجى تحديد {} صالح.",
    "Row {0} picked quantity is less than the required quantity, additional {1} {2} required.": "كمية الانتقاء في الصف {0} أقل من الكمية المطلوبة؛ يلزم توفير {1} {2} إضافية.",
    "Row {0}# Item {1} cannot be transferred more than {2} against {3} {4}": "الصف {0}# لا يمكن نقل الصنف {1} بكمية تتجاوز {2} مقابل {3} {4}",
    "Row {0}# Item {1} not found in 'Raw Materials Supplied' table in {2} {3}": "الصف {0}# لم يُعثر على الصنف {1} في جدول 'المواد الخام الموردة' ضمن {2} {3}",
    "Row {0}: As {1} is enabled, raw materials cannot be added to {2} entry. Use {3} entry to consume raw materials.": "الصف {0}: بما أن {1} مفعّل، لا يمكن إضافة المواد الخام إلى قيد {2}. استخدم قيد {3} لاستهلاك المواد الخام.",
    "Row {0}: Either Delivery Note Item or Packed Item reference is mandatory.": "الصف {0}: يجب إدخال مرجع بند إذن التسليم أو الصنف المعبأ.",
    "Row {0}: Packed Qty must be equal to {1} Qty.": "الصف {0}: يجب أن تساوي الكمية المعبأة كمية {1}.",
    "Row {0}: Packing Slip is already created for Item {1}.": "الصف {0}: تم إنشاء سند التعبئة للصنف {1} بالفعل.",
    "Row {0}: Please provide a valid Delivery Note Item or Packed Item reference.": "الصف {0}: يُرجى إدخال مرجع صالح لبند إذن التسليم أو للصنف المعبأ.",
    "Row {0}: Purchase Invoice {1} has no stock impact.": "الصف {0}: ليس لفاتورة الشراء {1} أثر على المخزون.",
    "Row {0}: Qty cannot be greater than {1} for the Item {2}.": "الصف {0}: لا يمكن أن تتجاوز كمية الصنف {2} القيمة {1}.",
    "Row {0}: Qty in Stock UOM can not be zero.": "الصف {0}: لا يمكن أن تكون الكمية بوحدة قياس المخزون صفرًا.",
    "Row {0}: Qty must be greater than 0.": "الصف {0}: يجب أن تكون الكمية أكبر من 0.",
    "Row {0}: Transferred quantity cannot be greater than the requested quantity.": "الصف {0}: لا يمكن أن تتجاوز الكمية المنقولة الكمية المطلوبة.",
    "Row {0}: {2} Item {1} does not exist in {2} {3}": "الصف {0}: الصنف {1} من {2} غير موجود في {2} {3}",
    "SCO Supplied Item": "صنف مُورَّد ضمن أمر مقاولات الباطن",
    "Same item and warehouse combination already entered.": "تم إدخال تركيبة الصنف والمستودع نفسها بالفعل.",
    "Scan mode enabled, existing quantity will not be fetched.": "وضع المسح مفعّل؛ لن يتم جلب الكمية الحالية.",
    "Selected Serial and Batch Bundle entries have been fixed.": "تم إصلاح قيود حزمة الأرقام التسلسلية والدفعات المحددة.",
    "Serial No and Batch Selector cannot be use when Use Serial / Batch Fields is enabled.": "لا يمكن استخدام محدد الرقم التسلسلي والدفعة عند تفعيل حقول الرقم التسلسلي/الدفعة.",
    "Serial No and Batch Traceability": "تتبّع الأرقام التسلسلية والدفعات",
    "Serial No {0} does not exists": "الرقم التسلسلي {0} غير موجود",
    "Serial No {0} is already Delivered. You cannot use them again in Manufacture / Repack entry.": "تم تسليم الرقم التسلسلي {0} بالفعل. لا يمكنك استخدامه مرة أخرى في قيد التصنيع/إعادة التعبئة.",
    "Serial No {0} is not present in the {1} {2}, hence you can't return it against the {1} {2}": "الرقم التسلسلي {0} غير موجود في {1} {2}، لذلك لا يمكنك إرجاعه مقابل {1} {2}",
    "Serial Nos are created successfully": "تم إنشاء الأرقام التسلسلية بنجاح",
    "Serial Nos are reserved in Stock Reservation Entries, you need to unreserve them before proceeding.": "الأرقام التسلسلية محجوزة في قيود حجز المخزون؛ يجب إلغاء حجزها قبل المتابعة.",
    "Serial Nos {0} are already Delivered. You cannot use them again in Manufacture / Repack entry.": "تم تسليم الأرقام التسلسلية {0} بالفعل. لا يمكنك استخدامها مرة أخرى في قيد التصنيع/إعادة التعبئة.",
    "Serial and Batch Bundle {0} is not submitted": "حزمة الأرقام التسلسلية والدفعات {0} غير مُقدَّمة",
    "Set fieldname from which you want to fetch the data from the parent form.": "حدد اسم الحقل الذي تريد جلب البيانات منه في النموذج الرئيسي.",
    "Set the status manually.": "حدد الحالة يدويًا.",
    "Similar types of workstations where the same operations run in parallel.": "محطات عمل متشابهة تُنفّذ العمليات نفسها بالتوازي.",
    "Since {0} are Serial No/Batch No items, you cannot enable 'Recreate Stock Ledgers' in Repost Item Valuation.": "بما أن {0} أصناف ذات أرقام تسلسلية/أرقام دفعات، لا يمكنك تفعيل 'إعادة إنشاء قيود دفتر الأستاذ المخزني' في إعادة ترحيل تقييم الصنف.",
    "Source Warehouse is mandatory for the Item {0}.": "مستودع المصدر مطلوب للصنف {0}.",
    "Status set to rejected as there are one or more rejected readings.": "تم تعيين الحالة إلى مرفوض لوجود قراءة مرفوضة واحدة أو أكثر.",
    "Stock Closing Entry {0} already exists for the selected date range": "يوجد بالفعل قيد إقفال المخزون {0} ضمن نطاق التاريخ المحدد",
    "Stock Closing Entry {0} has been queued for processing, system will take sometime to complete it.": "تم وضع قيد إقفال المخزون {0} في قائمة المعالجة؛ سيستغرق النظام بعض الوقت لإكماله.",
    "Stock Entries already created for Work Order {0}: {1}": "تم إنشاء قيود المخزون لأمر العمل {0} بالفعل: {1}",
    "Stock Ledger Entries and GL Entries are reposted for the selected Purchase Receipts": "أُعيد ترحيل قيود دفتر الأستاذ المخزني وقيود الأستاذ العام لسندات استلام الشراء المحددة",
    "Stock Ledgers won’t be reposted.": "لن يُعاد ترحيل قيود دفتر الأستاذ المخزني.",
    "Stock Reservation Entry cannot be updated as it has been delivered.": "لا يمكن تحديث قيد حجز المخزون بعد تسليم الكمية المحجوزة.",
    "Stock Reservation can only be created against {0}.": "لا يمكن إنشاء حجز المخزون إلا مقابل {0}.",
    "Stock cannot be reserved in group warehouse {0}.": "لا يمكن حجز المخزون في المستودع التجميعي {0}.",
    "Stock cannot be reserved in the group warehouse {0}.": "لا يمكن حجز المخزون في المستودع التجميعي {0}.",
    "Stock has been unreserved for work order {0}.": "تم إلغاء حجز المخزون لأمر العمل {0}.",
    "Stock not available for Item {0} in Warehouse {1}.": "المخزون غير متاح للصنف {0} في المستودع {1}.",
    "Stock transactions that are older than the mentioned days cannot be modified.": "لا يمكن تعديل معاملات المخزون الأقدم من عدد الأيام المذكور.",
    "Stock/Accounts can not be frozen as processing of backdated entries is going on. Please try again later.": "لا يمكن تجميد المخزون/الحسابات أثناء معالجة القيود المؤرخة بأثر رجعي. يُرجى المحاولة لاحقًا.",
    "Successfully changed Stock UOM, please redefine conversion factors for new UOM.": "تم تغيير وحدة قياس المخزون بنجاح؛ يُرجى إعادة تحديد عوامل التحويل للوحدة الجديدة.",
    "Table for Item that will be shown in Web Site": "جدول الصنف الذي سيظهر على الموقع الإلكتروني",
    "Taxes row #{0}: {1} cannot be smaller than {2}": "صف الضرائب رقم {0}: لا يمكن أن تكون {1} أقل من {2}",
    "The Process Loss Qty has reset as per job cards Process Loss Qty": "أُعيد ضبط كمية فاقد العملية وفقًا لكمية الفاقد المسجلة في بطاقات العمل",
    "The Serial No at Row #{0}: {1} is not available in warehouse {2}.": "الرقم التسلسلي في الصف رقم {0}: {1} غير متاح في المستودع {2}.",
    "The Serial No {0} is reserved against the {1} {2} and cannot be used for any other transaction.": "الرقم التسلسلي {0} محجوز مقابل {1} {2} ولا يمكن استخدامه في أي معاملة أخرى.",
    "The Work Order is mandatory for Disassembly Order": "أمر العمل مطلوب لأمر التفكيك",
    "The field {0} in row {1} is not set": "الحقل {0} في الصف {1} غير محدد",
    "The following Items, having Putaway Rules, could not be accomodated:": "تعذّر استيعاب الأصناف التالية التي لها قواعد تخزين:",
    "The items {0} and {1} are present in the following {2} :": "الصنفان {0} و{1} موجودان في {2} التالية:",
    "The percentage you are allowed to pick more items in the pick list than the ordered quantity.": "النسبة المسموح بها لانتقاء كمية من الأصناف في قائمة الانتقاء تتجاوز الكمية المطلوبة.",
    "The reserved stock will be released. Are you certain you wish to proceed?": "سيتم تحرير المخزون المحجوز. هل أنت متأكد من المتابعة؟",
    "The serial and batch bundle {0} not linked to {1} {2}": "حزمة الأرقام التسلسلية والدفعات {0} غير مرتبطة بـ {1} {2}",
    "The user cannot submit the Serial and Batch Bundle manually": "لا يمكن للمستخدم تقديم حزمة الأرقام التسلسلية والدفعات يدويًا",
    "The users with this Role are allowed to create/modify a stock transaction, even though the transaction is frozen.": "يُسمح للمستخدمين الذين لديهم هذا الدور بإنشاء/تعديل معاملة مخزون حتى عندما تكون المعاملة مجمدة.",
    "The {0} prefix '{1}' already exists. Please change the Serial No Series, otherwise you will get a Duplicate Entry error.": "البادئة {0} '{1}' موجودة بالفعل. يُرجى تغيير سلسلة الأرقام التسلسلية لتجنب خطأ الإدخال المكرر.",
    "The {0} {1} created successfully": "تم إنشاء {0} {1} بنجاح",
    "There aren't any item variants for the selected item": "لا توجد متغيرات للصنف المحدد",
    "There must be atleast 1 Finished Good in this Stock Entry": "يجب أن يحتوي قيد المخزون هذا على صنف منتج نهائي واحد على الأقل",
    "This field is used to set the 'Customer'.": "يُستخدم هذا الحقل لتحديد 'العميل'.",
    "This is considered dangerous from accounting point of view.": "يُعد هذا الإجراء خطيرًا من منظور محاسبي.",
    "This option can be checked to edit the 'Posting Date' and 'Posting Time' fields.": "يمكن تحديد هذا الخيار لتعديل حقلي 'تاريخ الترحيل' و'وقت الترحيل'.",
    "This table is used to set details about the 'Item', 'Qty', 'Basic Rate', etc.": "يُستخدم هذا الجدول لتحديد تفاصيل 'الصنف' و'الكمية' و'السعر الأساسي' وغيرها.",
    "UOM conversion factor required for UOM: {0} in Item: {1}": "عامل التحويل مطلوب لوحدة القياس {0} في الصنف {1}",
    "UOM {0} not found in Item {1}": "وحدة القياس {0} غير موجودة في الصنف {1}",
    "Upon submission of the Sales Order, Work Order, or Production Plan, the system will automatically reserve the stock.": "عند تقديم أمر البيع أو أمر العمل أو خطة الإنتاج، سيحجز النظام المخزون تلقائيًا.",
    "Users with this role are allowed to over deliver/receive against orders above the allowance percentage": "يُسمح للمستخدمين بهذا الدور بتجاوز نسبة السماح عند التسليم/الاستلام مقابل الأوامر",
    "Using negative stock disables FIFO/Moving average valuation when inventory is negative.": "يؤدي استخدام المخزون السالب إلى تعطيل التقييم بطريقة FIFO/المتوسط المتحرك عندما يصبح المخزون سالبًا.",
    "Valuation (I - K)": "التقييم (I - K)",
    "Valuation rate for customer provided items has been set to zero.": "تم تعيين سعر تقييم الأصناف المقدمة من العميل إلى صفر.",
    "Value (G - D)": "القيمة (G - D)",
    "Value ({0})": "القيمة ({0})",
    "Value of goods cannot be 0": "لا يمكن أن تكون قيمة البضائع 0",
    "Warehouse Capacity for Item '{0}' must be greater than the existing stock level of {1} {2}.": "يجب أن تتجاوز سعة المستودع للصنف '{0}' مستوى المخزون الحالي البالغ {1} {2}.",
    "Warehouse {0} does not belong to Company {1}.": "المستودع {0} لا يتبع الشركة {1}.",
    "Warehouse {0} does not exist": "المستودع {0} غير موجود",
    "Warehouse's Stock Value has already been booked in the following accounts:": "تم تسجيل قيمة مخزون المستودع بالفعل في الحسابات التالية:",
    "When creating an Item, entering a value for this field will automatically create an Item Price at the backend.": "عند إنشاء صنف، يؤدي إدخال قيمة في هذا الحقل إلى إنشاء سعر للصنف تلقائيًا في الخلفية.",
    "You are not authorized to make/edit Stock Transactions for Item {0} under warehouse {1} before this time.": "غير مصرح لك بإنشاء/تعديل معاملات المخزون للصنف {0} في المستودع {1} قبل هذا الوقت.",
    "You cannot repost item valuation before {}": "لا يمكنك إعادة ترحيل تقييم الصنف قبل {}",
    "You have entered a duplicate Delivery Note on Row": "أدخلت إذن تسليم مكررًا في الصف",
    "after": "بعد",
    "image": "صورة",
    "performing either one below:": "تنفيذ أيٍّ مما يلي:",
    "product bundle item row's name in sales order. Also indicates that picked item is to be used for a product bundle": "اسم صف الصنف في حزمة المنتج ضمن أمر البيع. ويشير أيضًا إلى أن الصنف المنتقى سيُستخدم في حزمة منتج.",
    "{0} account not found while submitting purchase receipt": "لم يُعثر على حساب {0} عند تقديم سند استلام الشراء",
    "{0} units are reserved for Item {1} in Warehouse {2}, please un-reserve the same to {3} the Stock Reconciliation.": "تم حجز {0} وحدة للصنف {1} في المستودع {2}؛ يُرجى إلغاء الحجز قبل تنفيذ الإجراء {3} على تسوية المخزون.",
    "{0} units of Item {1} is not available in any of the warehouses.": "لا تتوفر {0} وحدة من الصنف {1} في أي من المستودعات.",
    "{0} units of Item {1} is picked in another Pick List.": "تم انتقاء {0} وحدة من الصنف {1} في قائمة انتقاء أخرى.",
    "{0} units of {1} are required in {2} with the inventory dimension: {3} on {4} {5} for {6} to complete the transaction.": "يلزم توفر {0} وحدة من {1} في {2} ببُعد المخزون {3} بتاريخ {4} {5} لصالح {6} لإكمال المعاملة.",
    "{0} units of {1} needed in {2} on {3} {4} to complete this transaction.": "يلزم توفر {0} وحدة من {1} في {2} بتاريخ {3} {4} لإكمال هذه المعاملة.",
    "{} To Bill": "{} للفوترة",
}


def main() -> None:
    assert hashlib.sha256(SCOPE.read_bytes()).hexdigest() == SCOPE_SHA
    with SCOPE.open(encoding="utf-8", newline="") as fh:
        scope = list(csv.DictReader(fh))
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert len(scope) == 234 and len({r["source_text"] for r in scope}) == 234
    assert recon["scope_sha256"] == SCOPE_SHA and recon["site_override_key_count"] == 121
    preserved = {r["source_text"]: r["translated_text"] for r in recon["site_overrides"]}
    keys = {r["source_text"] for r in scope}
    assert len(A) == 111, f"expected 111 proposed payload rows, got {len(A)}"
    assert set(A) | set(preserved) | TECHNICAL == keys, "scope disposition does not partition exact keys"
    assert not (set(A) & set(preserved) or set(A) & TECHNICAL or set(preserved) & TECHNICAL)
    placeholder = re.compile(r"\{[^{}]*\}")
    for src, dst in A.items():
        assert dst and dst != src
        assert sorted(placeholder.findall(src)) == sorted(placeholder.findall(dst)), f"placeholder mismatch: {src!r}"
        assert not any(ch in dst for ch in "\x00\t\r\n")
        assert src[: len(src) - len(src.lstrip())] == dst[: len(dst) - len(dst.lstrip())]
        assert src[len(src.rstrip()):] == dst[len(dst.rstrip()):]
    fields = ["source_text", "proposed_ar", "proposed_disposition", "disposition_rationale", "decision_ref", "locations"]
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in scope:
            src = row["source_text"]
            if src in preserved:
                disp, ar, rationale = "preserved-site-override", preserved[src], "Preserve existing Site Override; no mutation."
            elif src in TECHNICAL:
                disp, ar, rationale = "EXCEPTION-technical", "", "Technical product-code token; retain vendor rendering."
            else:
                disp, ar, rationale = "PROPOSED-payload", A[src], "AI draft; requires independent A1/A2/A3 quorum."
            writer.writerow({
                "source_text": src,
                "proposed_ar": ar,
                "proposed_disposition": disp,
                "disposition_rationale": rationale,
                "decision_ref": DECISION_REF,
                "locations": row["locations"],
            })
    print(f"scope={len(scope)} preserved={len(preserved)} technical={len(TECHNICAL)} proposed_payload={len(A)}")
    print(f"proposal={OUT.name} sha256={hashlib.sha256(OUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
