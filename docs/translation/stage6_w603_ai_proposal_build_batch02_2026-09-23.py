"""Build the reviewed-input proposal table for W6-3 batch 02.

This script does not modify the managed catalog, release decisions, or site.
It emits only a 250-row proposal/disposition table bound to the approved scope.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w603_batch02_rows_2026-09-23.csv"
RECON = HERE / "stage6_w603_batch02_site_recon_2026-09-23.json"
OUT = HERE / "stage6_w603_proposal_batch02_2026-09-23.csv"
SCOPE_SHA = "701ad13e6b4cc530ebd7dbd95705979b70055c46f39da37d4532a26ba60439ef"
DECISION_REF = "stage6-W6-3 batch-02 owner-approved 2026-09-23"
TECHNICAL = {"JAN", "PZN"}
DEFERRED_SOURCE_DEFECTS = {
    "Reserved Qty ({0}) cannot be a fraction. To allow this, disable '{1}' in UOM {3}.": "Source requests {3}, but the inspected formatter does not provide that positional argument; vendor source fix is outside this batch.",
    "Row # {0}: Please enter quantity for Item {1} as it is not zero.": "Source raises this while current_qty is zero; source condition/message conflict requires vendor-side correction.",
}

# Draft translations for rows with no previously reviewed Arabic suggestion.
# Site Override values are excluded by the live recon; A1/A2/A3 must review
# every proposed release row independently before anything enters the catalog.
A = {
    "Incorrect Check in (group) Warehouse for Reorder": "مستودع المجموعة المحدد لإعادة الطلب غير صحيح",
    "Incorrect Component Quantity": "كمية المكوّن غير صحيحة",
    "Incorrect Reference Document (Purchase Receipt Item)": "مستند مرجعي غير صحيح (صنف سند استلام الشراء)",
    "Incorrect Type of Transaction": "نوع المعاملة غير صحيح",
    "Individual Stock Ledger Entry cannot be cancelled.": "لا يمكن إلغاء قيد فردي في دفتر الأستاذ المخزني.",
    "Invalid Item Defaults": "الإعدادات الافتراضية للصنف غير صالحة",
    "Invalid Priority": "أولوية غير صالحة",
    "Invalid Query": "استعلام غير صالح",
    "Invalid Serial and Batch Bundle": "حزمة الأرقام التسلسلية والدفعات غير صالحة",
    "Invalid Source and Target Warehouse": "مستودعا المصدر والوجهة غير صالحين",
    "Invalid search query": "استعلام البحث غير صالح",
    "It can take upto few hours for accurate stock values to be visible after merging items.": "قد يستغرق ظهور قيم المخزون الدقيقة بضع ساعات بعد دمج الأصناف.",
    "Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, Batch, UOM, Qty, and Dates.": "قد يظهر سعر الصنف عدة مرات بحسب قائمة الأسعار والمورد/العميل والعملة والصنف والدفعة ووحدة القياس والكمية والتواريخ.",
    "Item Warehouse based reposting has been enabled.": "تم تفعيل إعادة الترحيل بحسب الصنف والمستودع.",
    "Item rate has been updated to zero as Allow Zero Valuation Rate is checked for item {0}": "تم تحديث سعر تقييم الصنف إلى صفر لأن خيار السماح بسعر تقييم صفري محدد للصنف {0}",
    "Item valuation rate is recalculated considering landed cost voucher amount": "أُعيد احتساب سعر تقييم الصنف مع مراعاة مبلغ سند تكاليف الوصول",
    "Item valuation reposting in progress. Report might show incorrect item valuation.": "جارٍ إعادة ترحيل تقييم الصنف. قد يعرض التقرير تقييمًا غير صحيح للصنف.",
    "Item {0} is already reserved/delivered against Sales Order {1}.": "الصنف {0} محجوز أو تم تسليمه بالفعل مقابل أمر البيع {1}.",
    "Item {0} must be a Non-Stock Item": "يجب أن يكون الصنف {0} غير مخزني",
    "Item {0} not found in 'Raw Materials Supplied' table in {1} {2}": "لم يتم العثور على الصنف {0} في جدول 'المواد الخام الموردة' ضمن {1} {2}",
    "Item {0} not found.": "لم يتم العثور على الصنف {0}.",
    "Item {} does not exist.": "الصنف {} غير موجود.",
    "Item/Item Code required to get Item Tax Template.": "يلزم تحديد الصنف/رمز الصنف للحصول على قالب ضريبة الصنف.",
    "Items rate has been updated to zero as Allow Zero Valuation Rate is checked for the following items: {0}": "تم تحديث أسعار تقييم الأصناف التالية إلى صفر لأن خيار السماح بسعر تقييم صفري محدد لها: {0}",
    "Last Name, Email or Phone/Mobile of the user are mandatory to continue.": "يلزم إدخال اسم العائلة والبريد الإلكتروني أو رقم الهاتف/الجوال للمستخدم للمتابعة.",
    "Learn Inventory Management": "تعلّم إدارة المخزون",
    "Limit timeslot for Stock Reposting": "حدّد الفترة الزمنية لإعادة ترحيل المخزون",
    "Limits don't apply on": "لا تنطبق الحدود على",
    "Linked with submitted documents": "مرتبط بمستندات مُقدَّمة",
    "Log the selling and buying rate of an Item": "سجّل سعر بيع وشراء الصنف",
    "Make {0} Variant": "إنشاء متغير للصنف {0}",
    "Make {0} Variants": "إنشاء متغيرات للصنف {0}",
    "Manufacturers used in Items": "الشركات المصنّعة المرتبطة بالأصناف",
    "Min Value: {0}, Max Value: {1}, in Increments of: {2}": "الحد الأدنى: {0}، الحد الأقصى: {1}، بخطوات قدرها: {2}",
    "Multiple items cannot be marked as finished item": "لا يمكن تحديد عدة أصناف كمنتج نهائي",
    "No additional fields available": "لا توجد حقول إضافية متاحة",
    "No available quantity to reserve for item {0} in warehouse {1}": "لا توجد كمية متاحة لحجزها للصنف {0} في المستودع {1}",
    "No of Months (Expense)": "عدد الأشهر (المصروف)",
    "No of Months (Revenue)": "عدد الأشهر (الإيراد)",
    "No of Parallel Reposting (Per Item)": "عدد عمليات إعادة الترحيل المتوازية (لكل صنف)",
    "No of Shift": "عدد الورديات",
    "No of Units Produced": "عدد الوحدات المنتجة",
    "No of Workstations": "عدد محطات العمل",
    "No stock ledger entries were created. Please set the quantity or valuation rate for the items properly and try again.": "لم تُنشأ قيود في دفتر الأستاذ المخزني. يُرجى ضبط كمية الأصناف أو سعر تقييمها بشكل صحيح ثم المحاولة مجددًا.",
    "No stock transactions can be created or modified before this date.": "لا يمكن إنشاء معاملات المخزون أو تعديلها قبل هذا التاريخ.",
    "Note: To merge the items, create a separate Stock Reconciliation for the old item {0}": "ملاحظة: لدمج الأصناف، أنشئ تسوية مخزون منفصلة للصنف القديم {0}",
    "Only one {0} entry can be created against the Work Order {1}": "يمكن إنشاء قيد واحد فقط من النوع {0} مقابل أمر العمل {1}",
    "Only to be used for Subcontracting Inward.": "للاستخدام في استلام مقاولات الباطن فقط.",
    "Over Billing Allowance exceeded for Purchase Receipt Item {0} ({1}) by {2}%": "تم تجاوز سماحية الفوترة لصنف سند استلام الشراء {0} ({1}) بنسبة {2}%",
    "Pallets": "منصات التحميل",
    "Parcel weight cannot be 0": "لا يمكن أن يكون وزن الطرد 0",
    "Per Day": "يوميًا",
    "Per Unit Time in Mins": "الوقت لكل وحدة بالدقائق",
    "Pickup Date cannot be before this day": "لا يمكن أن يسبق تاريخ الاستلام هذا اليوم",
    "Pickup To time should be greater than Pickup From time": "يجب أن يكون وقت انتهاء الاستلام بعد وقت بدايته",
    "Pickup from": "وقت بدء الاستلام",
    "Pickup to": "وقت انتهاء الاستلام",
    "Please check the error message and take necessary actions to fix the error and then restart the reposting again.": "يُرجى مراجعة رسالة الخطأ واتخاذ الإجراءات اللازمة لإصلاحه، ثم إعادة بدء الترحيل.",
    "Please contact any of the following users to {} this transaction.": "يُرجى التواصل مع أحد المستخدمين التاليين لإجراء {} لهذه المعاملة.",
    "Please create Landed Cost Vouchers against Invoices that have 'Update Stock' enabled.": "يُرجى إنشاء سندات تكاليف الوصول للفواتير التي فُعّل فيها خيار 'تحديث المخزون'.",
    "Please delete Product Bundle {0}, before merging {1} into {2}": "يُرجى حذف حزمة المنتج {0} قبل دمج {1} في {2}",
    "Please enable Use Old Serial / Batch Fields to make_bundle": "يُرجى تفعيل «استخدام حقول الرقم التسلسلي/الدفعة القديمة» لإنشاء الحزمة.",
    "Please enable {0} in the {1}.": "يُرجى تفعيل {0} في {1}.",
    "Please enter Shipment Parcel information": "يُرجى إدخال بيانات طرد الشحنة",
    "Please first set Last Name, Email and Phone for the user": "يُرجى إدخال اسم العائلة والبريد الإلكتروني والهاتف للمستخدم أولًا",
    "Please mention 'Weight UOM' along with Weight.": "يُرجى تحديد 'وحدة قياس الوزن' مع الوزن.",
    "Please rectify and try again.": "يُرجى التصحيح والمحاولة مجددًا.",
    "Please select Serial/Batch Nos to reserve or change Reservation Based On to Qty.": "يُرجى تحديد الأرقام التسلسلية/الدفعات لحجزها، أو تغيير أساس الحجز إلى الكمية.",
    "Please select Subcontracting Order instead of Purchase Order {0}": "يُرجى اختيار أمر مقاولات الباطن بدلًا من أمر الشراء {0}",
    "Please select at least one filter: Item Code, Batch, or Serial No.": "يُرجى تحديد عامل تصفية واحد على الأقل: رمز الصنف أو الدفعة أو الرقم التسلسلي.",
    "Please select at least one row with difference value": "يُرجى تحديد صف واحد على الأقل يتضمن قيمة الفرق",
    "Please select either the Item or Warehouse or Warehouse Type filter to generate the report.": "يُرجى تحديد عامل تصفية الصنف أو المستودع أو نوع المستودع لإنشاء التقرير.",
    "Please select only one row to create a Reposting Entry": "يُرجى تحديد صف واحد فقط لإنشاء قيد إعادة الترحيل",
    "Please select rows to create Reposting Entries": "يُرجى تحديد الصفوف لإنشاء قيود إعادة الترحيل",
    "Please select the required filters": "يُرجى تحديد عوامل التصفية المطلوبة",
    "Please set Email/Phone for the contact": "يُرجى إدخال البريد الإلكتروني/الهاتف لجهة الاتصال",
    "Priority cannot be lesser than 1.": "لا يمكن أن تكون الأولوية أقل من 1.",
    "Putaway Rule already exists for Item {0} in Warehouse {1}.": "توجد بالفعل قاعدة تخزين للصنف {0} في المستودع {1}.",
    "Qty of Finished Goods Item should be greater than 0.": "يجب أن تكون كمية الصنف النهائي أكبر من 0.",
    "Quantity cannot be greater than {0} for Item {1}": "لا يمكن أن تتجاوز كمية الصنف {1} القيمة {0}",
    "Quantity must be greater than zero, and less or equal to {0}": "يجب أن تكون الكمية أكبر من صفر وأقل من أو مساوية لـ {0}",
    "References to Sales Invoices are Incomplete": "مراجع فواتير المبيعات غير مكتملة",
    "References to Sales Orders are Incomplete": "مراجع أوامر البيع غير مكتملة",
    "Remove item if charges is not applicable to that item": "أزل الصنف إذا لم تنطبق عليه الرسوم",
    "Repost Item Valuation restarted for selected failed records.": "أُعيد بدء ترحيل تقييم الأصناف للسجلات المحددة التي فشلت.",
    "Reposting Completed {0}%": "اكتملت إعادة الترحيل بنسبة {0}%",
    "Reposting entries created: {0}": "عدد قيود إعادة الترحيل المنشأة: {0}",
    "Reposting has been started in the background.": "بدأت إعادة الترحيل في الخلفية.",
    "Reserved Qty should be greater than Delivered Qty.": "يجب أن تكون الكمية المحجوزة أكبر من الكمية المسلّمة.",
    "Restart": "إعادة التشغيل",
    "Restart Failed Entries": "إعادة تشغيل القيود الفاشلة",
    "Row # {0}: Please add Serial and Batch Bundle for Item {1}": "الصف رقم {0}: يُرجى إضافة حزمة الأرقام التسلسلية والدفعات للصنف {1}",
    "Row #{0}: A reorder entry already exists for warehouse {1} with reorder type {2}.": "الصف رقم {0}: يوجد بالفعل قيد إعادة طلب للمستودع {1} من النوع {2}.",
    "Row #{0}: Acceptance Criteria Formula is incorrect.": "الصف رقم {0}: صيغة معايير القبول غير صحيحة.",
    "Row #{0}: Acceptance Criteria Formula is required.": "الصف رقم {0}: صيغة معايير القبول مطلوبة.",
    "Row #{0}: Batch No {1} is already selected.": "الصف رقم {0}: تم تحديد رقم الدفعة {1} بالفعل.",
    "Row #{0}: Finished Good must be {1}": "الصف رقم {0}: يجب أن يكون المنتج النهائي {1}",
    "Row #{0}: Item {1} has been picked, please reserve stock from the Pick List.": "الصف رقم {0}: تم انتقاء الصنف {1}، يُرجى حجز المخزون من قائمة الانتقاء.",
    "Row #{0}: Only {1} available to reserve for the Item {2}": "الصف رقم {0}: المتاح لحجزه للصنف {2} هو {1} فقط",
    "Row #{0}: Quantity to reserve for the Item {1} should be greater than 0.": "الصف رقم {0}: يجب أن تكون كمية الصنف {1} المراد حجزها أكبر من 0.",
    "Row #{0}: Serial No {1} for Item {2} is not available in {3} {4} or might be reserved in another {5}.": "الصف رقم {0}: الرقم التسلسلي {1} للصنف {2} غير متاح في {3} {4} أو ربما يكون محجوزًا في {5} آخر.",
    "Row #{0}: Serial No {1} is already selected.": "الصف رقم {0}: تم تحديد الرقم التسلسلي {1} بالفعل.",
    "Row #{0}: Source and Target Warehouse cannot be the same for Material Transfer": "الصف رقم {0}: لا يمكن أن يكون مستودع المصدر والوجهة واحدًا عند تحويل المواد",
}

def main() -> None:
    assert hashlib.sha256(SCOPE.read_bytes()).hexdigest() == SCOPE_SHA
    with SCOPE.open(encoding="utf-8", newline="") as fh:
        scope = list(csv.DictReader(fh))
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert len(scope) == 250 and len({r["source_text"] for r in scope}) == 250
    assert recon["scope_sha256"] == SCOPE_SHA and recon["site_override_key_count"] == 143
    preserved = {r["source_text"]: r["translated_text"] for r in recon["site_overrides"]}
    keys = {r["source_text"] for r in scope}
    assert len(A) == 103, f"expected 103 releasable drafts, got {len(A)}"
    assert set(A) | set(preserved) | TECHNICAL | set(DEFERRED_SOURCE_DEFECTS) == keys, "scope disposition does not partition exact keys"
    assert not (set(A) & set(preserved) or set(A) & TECHNICAL or set(preserved) & TECHNICAL or set(A) & set(DEFERRED_SOURCE_DEFECTS))
    ph = re.compile(r"\{[^{}]*\}")
    for src, dst in A.items():
        assert dst and dst != src
        assert sorted(ph.findall(src)) == sorted(ph.findall(dst)), f"placeholder mismatch: {src!r}"
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
                disp, ar = "preserved-site-override", preserved[src]
            elif src in TECHNICAL:
                disp, ar = "EXCEPTION-technical", ""
            elif src in DEFERRED_SOURCE_DEFECTS:
                disp, ar = "DEFERRED-source-defect", ""
            else:
                disp, ar = "PROPOSED-payload", A[src]
            writer.writerow({
                "source_text": src,
                "proposed_ar": ar,
                "proposed_disposition": disp,
                "disposition_rationale": DEFERRED_SOURCE_DEFECTS.get(src, ""),
                "decision_ref": DECISION_REF,
                "locations": row["locations"],
            })
    print(f"scope={len(scope)} preserved={len(preserved)} technical={len(TECHNICAL)} deferred_source_defects={len(DEFERRED_SOURCE_DEFECTS)} draft_payload={len(A)}")
    print(f"proposal={OUT.relative_to(HERE.parents[1])} sha256={hashlib.sha256(OUT.read_bytes()).hexdigest()}")

if __name__ == "__main__":
    main()
