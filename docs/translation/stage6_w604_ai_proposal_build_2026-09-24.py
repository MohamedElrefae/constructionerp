"""Build W6-4 proposal dispositions after owner-approved read-only recon."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w604_projects_boq_rows_2026-09-24.csv"
RECON = HERE / "stage6_w604_projects_boq_site_recon_2026-09-24.json"
OUT = HERE / "stage6_w604_proposal_2026-09-24.csv"
SCOPE_SHA = "93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe"
DECISION_REF = "stage6-W6-4 Projects + BOQ owner-approved 2026-09-24"
PLACEHOLDER = re.compile(r"\{\d*\}")

# AI draft values for unfilled scope rows only. The live Site Overrides are
# copied verbatim by the builder and never replaced by these proposals.
A = {
    "Cannot complete task {0} as its dependant task {1} are not completed / cancelled.": "لا يمكن إكمال المهمة {0} لأن المهمة التي تعتمد عليها ({1}) لم تكتمل أو تُلغَ.",
    "Cannot convert Task to non-group because the following child Tasks exist: {0}.": "لا يمكن تحويل المهمة إلى مهمة غير تجميعية لوجود المهام الفرعية التالية: {0}.",
    "Costing and Billing fields has been updated": "تم تحديث حقول التكلفة والفوترة.",
    "Dependent Task {0} is not a Template Task": "المهمة {0} التي تعتمد عليها المهمة الحالية ليست مهمة قالب.",
    "Enabling the check box will fetch timesheet on select of a Project in Sales Invoice": "عند تفعيل مربع الاختيار، سيتم جلب سجل الدوام عند تحديد مشروع في فاتورة المبيعات.",
    "Expected End Date should be less than or equal to parent task's Expected End Date {0}.": "يجب ألا يتجاوز تاريخ الانتهاء المتوقع تاريخ الانتهاء المتوقع للمهمة الرئيسية {0}.",
    "For project {0}, update your status": "حدّث حالة المشروع {0}.",
    "Learn Project Management": "تعلّم إدارة المشاريع",
    "Parent Task {0} is not a Template Task": "المهمة الرئيسية {0} ليست مهمة قالب.",
    "Parent Task {0} must be a Group Task": "يجب أن تكون المهمة الرئيسية {0} مهمة تجميعية.",
    "Please set a default Holiday List for Company {0}": "يُرجى تعيين قائمة العطلات الافتراضية للشركة {0}.",
    "Row {0}: Project must be same as the one set in the Timesheet: {1}.": "الصف {0}: يجب أن يكون المشروع مطابقًا للمشروع المحدد في سجل الدوام: {1}.",
    "Row {0}: Task {1} does not belong to Project {2}": "الصف {0}: المهمة {1} لا تتبع المشروع {2}.",
    "Task {0} depends on Task {1}. Please add Task {1} to the Tasks list.": "تعتمد المهمة {0} على المهمة {1}. يُرجى إضافة المهمة {1} إلى قائمة المهام.",
    "Total hours: {0}": "إجمالي الساعات: {0}",
    "Warning - Row {0}: Billing Hours are more than Actual Hours": "تحذير - الصف {0}: ساعات الفوترة أكثر من الساعات الفعلية.",
    "You have been invited to collaborate on the project {0}.": "لقد دُعيت للمشاركة في المشروع {0}.",
    "hours": "ساعات",
    "{0} hours": "{0} ساعات",
    "{0}'s {1} cannot be after {2}'s Expected End Date.": "لا يمكن أن يكون {1} الخاص بـ {0} بعد تاريخ الانتهاء المتوقع لـ {2}.",
    "Accounting Entry for Landed Cost Voucher for SCR {0}": "قيد محاسبي لسند تكاليف الوصول لإيصال استلام مقاولات باطن SCR {0}.",
    "Additional {0} {1} of item {2} required as per BOM to complete this transaction": "يلزم توفير كمية إضافية قدرها {0} {1} من الصنف {2} وفقًا لقائمة المواد لإكمال هذه المعاملة.",
    "Atleast one raw material for Finished Good Item {0} should be customer provided.": "يجب أن تكون مادة خام واحدة على الأقل للصنف النهائي {0} مقدمة من العميل.",
    "Creating Subcontracting Receipt ...": "جارٍ إنشاء إيصال استلام مقاولات باطن ...",
    "Customer Warehouse {0} does not belong to Customer {1}.": "مستودع العميل {0} لا يتبع العميل {1}.",
    "Finished Good {0} does not have a default BOM.": "لا توجد قائمة مواد افتراضية للصنف النهائي {0}.",
    "Finished Good {0} is disabled.": "الصنف النهائي {0} معطّل.",
    "Finished Good {0} must be a stock item.": "يجب أن يكون الصنف النهائي {0} صنفًا مخزنيًا.",
    "Finished Good {0} must be a sub-contracted item.": "يجب أن يكون الصنف النهائي {0} بندًا منفذًا من الباطن.",
    "Getting Scrap Items": "جارٍ جلب أصناف الخردة.",
    "Please select Finished Good Item for Service Item {0}": "يُرجى تحديد الصنف النهائي للصنف الخدمي {0}.",
    "Please select a Subcontracting Purchase Order.": "يُرجى تحديد أمر شراء مقاول باطن.",
    "Please select a valid Purchase Order that has Service Items.": "يُرجى تحديد أمر شراء صالح يتضمن أصنافًا خدمية.",
    "Please select a valid Purchase Order that is configured for Subcontracting.": "يُرجى تحديد أمر شراء صالح مُعدّ لمقاولات الباطن.",
    "Purchase Order Item reference is missing in Subcontracting Receipt {0}": "مرجع بند أمر الشراء غير موجود في إيصال استلام مقاولات باطن {0}.",
    "Purchase Receipt {0} created.": "تم إنشاء سند استلام الشراء {0}.",
    "Row #{0}: Accepted Warehouse is mandatory for the accepted Item {1}": "الصف رقم {0}: مستودع الأصناف المقبولة إلزامي للصنف {1}.",
    "Row #{0}: Finished Good reference is mandatory for Scrap Item {1}.": "الصف رقم {0}: مرجع الصنف النهائي إلزامي لصنف الخردة {1}.",
    "Row #{0}: Rejected Qty cannot be set for Scrap Item {1}.": "الصف رقم {0}: لا يمكن تحديد كمية مرفوضة لصنف الخردة {1}.",
    "Row #{0}: Scrap Item Qty cannot be zero": "الصف رقم {0}: لا يمكن أن تكون كمية صنف الخردة صفرًا.",
    "Row {0}: Accepted Qty and Rejected Qty can't be zero at the same time.": "الصف {0}: لا يمكن أن تكون الكمية المقبولة والكمية المرفوضة صفرًا في الوقت نفسه.",
    "Service Item {0} is disabled.": "الصنف الخدمي {0} معطّل.",
    "Service Item {0} must be a non-stock item.": "يجب أن يكون الصنف الخدمي {0} غير مخزني.",
    "Sets 'Accepted Warehouse' in each row of the Items table.": "يحدد مستودع الأصناف المقبولة في كل صف من جدول الأصناف.",
    "Sets 'Rejected Warehouse' in each row of the Items table.": "يحدد مستودع الأصناف المرفوضة في كل صف من جدول الأصناف.",
    "Sets 'Reserve Warehouse' in each row of the Supplied Items table.": "يحدد مستودع الحجز في كل صف من جدول الأصناف الموردة.",
    "Stock Reservation Entries created": "تم إنشاء قيود حجز المخزون.",
    "There is already an active Subcontracting BOM {0} for the Finished Good {1}.": "توجد بالفعل قائمة مواد مقاول الباطن {0} للصنف النهائي {1}.",
}
DEFERRED = {
    "Progress % for a task cannot be more than 100.": (
        "DEFERRED-format-ambiguity",
        "Defer this row: the source's literal `% for` is ambiguous to the legacy printf-placeholder gate. "
        "Do not release it until its formatter/source contract is resolved separately."
    ),
    " Summary": (
        "DEFERRED-runtime-key-normalization",
        "Defer this fragment: the vendor constructs `project_name + ' ' + 'Summary'`; the standalone fragment is not the runtime msgid."
    ),
    "Distribute Additional Costs Based On ": (
        "DEFERRED-runtime-key-normalization",
        "Defer this edge-padded DocType label: the runtime importer strips source edge whitespace, so the exact scoped key cannot bind without normalization."
    ),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    assert hashlib.sha256(SCOPE.read_bytes()).hexdigest() == SCOPE_SHA
    scope = read_rows(SCOPE)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["site"] == "v16.localhost" and recon["scope_sha256"] == SCOPE_SHA
    assert recon["scope_rows"] == len(scope) == 147
    preserve_rows = recon["site_overrides"]
    preserve = {row["source_text"]: row["translated_text"] for row in preserve_rows}
    assert len(preserve) == len(preserve_rows) == 96
    assert len(set(preserve) & set(A)) == 0
    keys = {row["source_text"] for row in scope}
    assert not (set(preserve) & set(DEFERRED)) and not (set(A) & set(DEFERRED))
    assert set(preserve) | set(A) | set(DEFERRED) == keys, "proposal does not partition exact approved scope"
    assert not recon["nonempty_non_site_overrides"]
    assert not recon["duplicate_runtime_keys"]
    for source, arabic in A.items():
        assert arabic and arabic != source
        assert sorted(PLACEHOLDER.findall(source)) == sorted(PLACEHOLDER.findall(arabic)), source
        assert source[: len(source) - len(source.lstrip())] == arabic[: len(arabic) - len(arabic.lstrip())], source
        assert source[len(source.rstrip()):] == arabic[len(arabic.rstrip()):], source
        assert not any(char in arabic for char in "\x00\t\r\n")

    fields = [
        "source_text", "proposed_ar", "proposed_disposition",
        "disposition_rationale", "decision_ref", "locations",
    ]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in scope:
            source = row["source_text"]
            if source in preserve:
                disposition, arabic, rationale = (
                    "preserved-site-override", preserve[source],
                    "Preserve the exact live v16.localhost Site Override; do not import or replace.",
                )
            elif source in DEFERRED:
                deferred_disposition, deferred_rationale = DEFERRED[source]
                disposition, arabic, rationale = (
                    deferred_disposition, "", deferred_rationale,
                )
            else:
                disposition, arabic, rationale = (
                    "PROPOSED-payload", A[source],
                    "AI draft; requires independent A1/A2/A3 quorum before release.",
                )
            writer.writerow({
                "source_text": source,
                "proposed_ar": arabic,
                "proposed_disposition": disposition,
                "disposition_rationale": rationale,
                "decision_ref": DECISION_REF,
                "locations": row["locations"],
            })

    payload = OUT.read_bytes()
    print(f"scope={len(scope)} preserve={len(preserve)} proposed_payload={len(A)}")
    print(f"proposal_sha256={hashlib.sha256(payload).hexdigest()}")
    print(f"proposal={OUT}")


if __name__ == "__main__":
    main()
