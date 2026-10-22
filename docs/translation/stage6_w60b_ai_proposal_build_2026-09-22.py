#!/usr/bin/env python3
"""W6-0b batch-1 AI proposal build + payload append + quorum paper trail.

Owner-approved scope: stage6_w60b_batch01_rows_2026-09-22.csv (271 rows).
Site-override reconciliation (plan §12): 7 rows preserved, not imported.
Payload: 264 Released rows appended to approved_ar_overrides.csv.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w60b_batch01_rows_2026-09-22.csv"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w60b_payload_applied_rows_2026-09-22.csv"
SITE_RECON = Path("/tmp/opencode/site_recon.json")

DATE = "2026-09-22"
DECISION_REF = f"content:docs/translation/stage6_w60b_payload_applied_rows_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger arabic_coverage_gap_report_2026-08-22.csv; plan D5; W6-0b batch-1"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed "
    "(W6-0b batch-1; owner-approved 271-row scope minus 7 site-override preserves)"
)
DOMAIN = "desk-short-ui"
RELEASE_VERSION = "1.2"
REVIEWERS = (
    "AI-A1 (recorded review run)",
    "AI-A2 (recorded review run)",
    "AI-A3 (recorded review run)",
)
TS = f"{DATE} 00:00:00"

# Site-override preserved (not imported) — case-insensitive matches on batch
PRESERVED = {
    "Collapse All": "طيّ الكل",
    "Expand All": "توسيع الكل",
    "Dark": "داكن",
    "Light": "فاتح",
    "DELETE": "حذف",
    "email": "البريد الإلكتروني",
    "Phone": "الهاتف",
}

# Full AI proposals for the 264 payload rows (glossary v2.0 + Egyptian professional Arabic)
A = {
    "Ledger": "دفتر الأستاذ",
    "On Payment Failed": "عند فشل الدفع",
    "On Payment Paid": "عند الدفع",
    "Posting Timestamp": "طابع زمني للترحيل",
    "Select Currency": "تحديد العملة",
    "Default display currency": "عملة العرض الافتراضية",
    "No currency fields in {0}": "لا توجد حقول عملة في {0}",
    "On Payment Authorization": "عند تفويض الدفع",
    "On Payment Charge Processed": "عند معالجة الرسوم",
    "On Payment Mandate Acquisition Processed": "عند معالجة اكتساب التفويض",
    "On Payment Mandate Charge Processed": "عند معالجة رسوم التفويض",
    "Show Currency Symbol on Right Side": "إظهار رمز العملة على اليمين",
    "Use Number Format from Currency": "استخدام تنسيق الأرقام من العملة",
    "No Data": "لا توجد بيانات",
    "Reset sorting": "إعادة تعيين الترتيب",
    "{count} cells copied": "تم نسخ {count} خلية",
    "{count} rows selected": "تم تحديد {count} صف",
    "CSV": "CSV",
    "Error": "خطأ",
    "PDF": "PDF",
    "Sr": "م",
    "Success": "نجاح",
    "Action": "إجراء",
    "Clear All": "مسح الكل",
    "Document Type": "نوع المستند",
    "Show Preview": "إظهار المعاينة",
    "Value": "القيمة",
    "System Settings": "إعدادات النظام",
    "Column": "عمود",
    "No values to show": "لا توجد قيم لعرضها",
    "Set by user": "عيّنه المستخدم",
    "Complete": "مكتمل",
    "Move": "نقل",
    "{count} cell copied": "تم نسخ {count} خلية",
    "{count} row selected": "تم تحديد {count} صف",
    "Result": "النتيجة",
    "Undo": "تراجع",
    "ascending": "تصاعدي",
    "descending": "تنازلي",
    "Click to sort by {0}": "انقر للترتيب حسب {0}",
    "Hide Preview": "إخفاء المعاينة",
    "No filters found": "لم يتم العثور على عوامل تصفية",
    "Notification Settings": "إعدادات الإشعارات",
    "Redo last action": "إعادة آخر إجراء",
    "Reset Changes": "إعادة تعيين التغييرات",
    "Select Field...": "تحديد حقل...",
    "Switch Theme": "تبديل المظهر",
    "Indent": "إزاحة بادئة",
    "Redo": "إعادة",
    "Warning": "تحذير",
    "Are you sure you want to proceed?": "هل أنت متأكد من المتابعة؟",
    "Are you sure you want to {0}?": "هل أنت متأكد من رغبتك في {0}؟",
    "Clear Filters": "مسح عوامل التصفية",
    "Download PDF": "تنزيل PDF",
    "Load More Communications": "تحميل المزيد من الاتصالات",
    "Load more": "تحميل المزيد",
    "No Data...": "لا توجد بيانات...",
    "No Results found": "لم يتم العثور على نتائج",
    "No Select Field Found": "لم يتم العثور على حقل تحديد",
    "No rows selected": "لم يتم تحديد صفوف",
    "Select a field to edit its properties.": "حدد حقلًا لتعديل خصائصه.",
    "Activate": "تفعيل",
    "Changes": "التغييرات",
    "OPTIONS": "الخيارات",
    "Template": "قالب",
    "Bulk Actions": "إجراءات جماعية",
    "Log out": "تسجيل الخروج",
    "No data to export": "لا توجد بيانات للتصدير",
    "Parent Document Type": "نوع المستند الأصلي",
    "Push Notification Settings": "إعدادات إشعارات الدفع",
    "Reference Document Type": "نوع المستند المرجعي",
    "User Document Type": "نوع مستند المستخدم",
    "User Select Document Type": "نوع مستند اختيار المستخدم",
    "User Settings": "إعدادات المستخدم",
    "HTML": "HTML",
    "label": "ملصق",
    "L": "L",
    "DocType": "DocType",
    "M": "M",
    "Tab Break": "فاصل تبويب",
    "GET": "GET",
    "POST": "POST",
    "Communication": "اتصال",
    "Percent": "نسبة مئوية",
    "Duration": "المدة",
    "gray": "رمادي",
    "ID": "المعرّف",
    "K": "K",
    "Placeholder": "نص بديل",
    "Subject": "الموضوع",
    "yyyy-mm-dd": "yyyy-mm-dd",
    "Autocomplete": "إكمال تلقائي",
    "Arguments": "وسائط",
    "Tag": "وسم",
    "Workflow State": "حالة سير العمل",
    "Rating": "التقييم",
    "Kanban Board": "لوحة كانبان",
    "JSON": "JSON",
    "long": "طويل",
    "Done": "تم",
    "No Label": "بلا ملصق",
    "Medium": "متوسط",
    "dd.mm.yyyy": "dd.mm.yyyy",
    "Assigned To": "مسند إلى",
    "B": "B",
    "DocField": "DocField",
    "Bar": "شريط",
    "Month": "شهر",
    "Monthly": "شهري",
    "Property": "خاصية",
    "of": "من",
    "plain": "عادي",
    "short": "قصير",
    "Sunday": "الأحد",
    "T": "T",
    "esc": "Esc",
    "Field Template": "قالب الحقل",
    "Form Tour": "جولة النموذج",
    "Archived": "مؤرشف",
    "Daily": "يومي",
    "Python": "Python",
    "Quarterly": "ربع سنوي",
    "Spacer": "فاصل",
    "Weekly": "أسبوعي",
    "Yearly": "سنوي",
    "light-blue": "أزرق فاتح",
    "or": "أو",
    "Saved Filters": "عوامل تصفية محفوظة",
    "High": "عالٍ",
    "Missing Values Required": "قيم مطلوبة مفقودة",
    "and": "و",
    "grey": "رمادي",
    "Added {0} ({1})": "تمت إضافة {0} ({1})",
    "By fieldname": "حسب اسم الحقل",
    "Document Saved": "تم حفظ المستند",
    "Set Quantity": "تعيين الكمية",
    "Drag": "سحب",
    "Expression": "تعبير",
    "Page Break": "فاصل صفحة",
    "Page {0} of {1}": "صفحة {0} من {1}",
    "Unselect All": "إلغاء تحديد الكل",
    "End": "نهاية",
    "JS": "JS",
    "Note": "ملاحظة",
    "Route": "المسار",
    "Tomorrow": "غدًا",
    "Yesterday": "أمس",
    "Automated Message": "رسالة تلقائية",
    "Choose a color": "اختر لونًا",
    "Choose an icon": "اختر أيقونة",
    "Insert Below": "إدراج أدناه",
    "Naming Series": "سلسلة التسمية",
    "UTM Campaign": "حملة UTM",
    "UTM Medium": "وسيلة UTM",
    "UTM Source": "مصدر UTM",
    "Banker's Rounding (legacy)": "تقريب البنوك (قديم)",
    "Expression (old style)": "تعبير (أسلوب قديم)",
    "Low": "منخفض",
    "Monday": "الاثنين",
    "Seconds": "ثوانٍ",
    "Sticky": "مثبت",
    "Configure Columns": "تكوين الأعمدة",
    "Helvetica Neue": "Helvetica Neue",
    "Invalid URL": "رابط غير صالح",
    "Invalid Values": "قيم غير صالحة",
    "Merge with existing": "دمج مع الموجود",
    "Activity": "نشاط",
    "Chart": "مخطط",
    "Diff": "فرق",
    "External": "خارجي",
    "Failed": "فشل",
    "Following fields have invalid values:": "الحقول التالية تحتوي على قيم غير صالحة:",
    "Friday": "الجمعة",
    "Generate Tracking URL": "إنشاء رابط التتبع",
    "HEAD": "HEAD",
    "Kh": "Kh",
    "Never": "أبدًا",
    "Please enable pop-ups": "يرجى تفعيل النوافذ المنبثقة",
    "Saturday": "السبت",
    "Size": "الحجم",
    "Thursday": "الخميس",
    "Tuesday": "الثلاثاء",
    "Updating related fields...": "جارٍ تحديث الحقول المرتبطة...",
    "Wednesday": "الأربعاء",
    "pink": "وردي",
    "{0} is between {1} and {2}": "{0} بين {1} و {2}",
    "{0} is greater than or equal to {1}": "{0} أكبر من أو يساوي {1}",
    "{0} is greater than {1}": "{0} أكبر من {1}",
    "{0} is less than or equal to {1}": "{0} أصغر من أو يساوي {1}",
    "{0} is less than {1}": "{0} أصغر من {1}",
    "{0} is not equal to {1}": "{0} لا يساوي {1}",
    "{0} is not one of {1}": "{0} ليس ضمن {1}",
    "{0} is not set": "{0} غير معيّن",
    "{0} is one of {1}": "{0} ضمن {1}",
    "{0} is set": "{0} معيّن",
    "{0} is within {1}": "{0} ضمن {1}",
    "Action Complete": "اكتمل الإجراء",
    "Bottom Center": "أسفل الوسط",
    "Bottom Left": "أسفل اليسار",
    "Bottom Right": "أسفل اليمين",
    "By script": "حسب السكربت",
    "Change Letter Head": "تغيير الترويسة",
    "Custom HTML Block": "كتلة HTML مخصصة",
    "DocType required": "DocType مطلوب",
    "Editing {0}": "جارٍ تحرير {0}",
    "Get Items": "جلب العناصر",
    "Include filters": "تضمين عوامل التصفية",
    "Invalid Transition": "انتقال غير صالح",
    "No Images": "لا توجد صور",
    "No Letterhead": "بلا ترويسة",
    "On or After": "في أو بعد",
    "On or Before": "في أو قبل",
    "RQ Job": " مهمة RQ",
    "Section Title": "عنوان القسم",
    "Set all private": "تعيين الكل كخاص",
    "Sr No.": "م رقم",
    "Switch Camera": "تبديل الكاميرا",
    "Switching Camera": "جارٍ تبديل الكاميرا",
    "Top Center": "أعلى الوسط",
    "Top Left": "أعلى اليسار",
    "Top Right": "أعلى اليمين",
    "Total Images": "إجمالي الصور",
    "Workflow Details": "تفاصيل سير العمل",
    "After": "بعد",
    "Assigning...": "جارٍ الإسناد...",
    "Before": "قبل",
    "Capture": "التقاط",
    "Crop": "قص",
    "Divider": "فاصل",
    "DocPerm": "DocPerm",
    "Graph": "رسم بياني",
    "Install {0} from Marketplace": "تثبيت {0} من السوق",
    "Meta": "Meta",
    "SQL": "SQL",
    "Section must have at least one column": "يجب أن يحتوي القسم على عمود واحد على الأقل",
    "Unknown": "غير معروف",
    "chrome": "chrome",
    "Loading Filters...": "جارٍ تحميل عوامل التصفية...",
    "Banker's Rounding": "تقريب البنوك",
    "COLOR PICKER": "منتقي الألوان",
    "Column Width": "عرض العمود",
    "Commercial Rounding": "تقريب تجاري",
    "Ctrl + Down": "Ctrl + Down",
    "Ctrl + Up": "Ctrl + Up",
    "Data Clipped": "البيانات مقصوصة",
    "Deleting {0}...": "جارٍ حذف {0}...",
    "Editing Row": "تحرير صف",
    "Executing Code": "تنفيذ الشيفرة",
    "Insert Above": "إدراج أعلى",
    "No rows": "لا توجد صفوف",
    "Please specify": "يرجى التحديد",
    "Read Only Mode": "وضع القراءة فقط",
    "Reload File": "إعادة تحميل الملف",
    "Reset to default": "إعادة تعيين للافتراضي",
    "Show All": "إظهار الكل",
    "Use HTML": "استخدام HTML",
    "Web Page URL": "رابط صفحة الويب",
    "1 = True & 0 = False": "1 = صحيح و 0 = خطأ",
    "A0": "A0",
    "A1": "A1",
    "A2": "A2",
    "A3": "A3",
    "A5": "A5",
    "A6": "A6",
}

# Ledger suggested_ar (4 rows) if present
LEDGER_HINTS = {
    "Phone": "الهاتف",  # preserved as site override anyway
}


def placeholders(s: str) -> list[str]:
    return re.findall(r"\{[^{}]*\}", s)


def main() -> None:
    scope = list(csv.DictReader(SCOPE.open(encoding="utf-8")))
    assert len(scope) == 271, len(scope)
    scope_srcs = [r["source_text"] for r in scope]
    assert len(set(scope_srcs)) == 271

    preserved_srcs = [s for s in scope_srcs if s in PRESERVED]
    payload_srcs = [s for s in scope_srcs if s not in PRESERVED]
    assert len(preserved_srcs) == 7, preserved_srcs
    assert len(payload_srcs) == 264, len(payload_srcs)

    missing = [s for s in payload_srcs if s not in A]
    if missing:
        raise SystemExit(f"missing proposals ({len(missing)}): {missing}")

    # placeholder parity
    bad_ph = []
    for s in payload_srcs:
        if placeholders(s) != placeholders(A[s]):
            bad_ph.append((s, A[s], placeholders(s), placeholders(A[s])))
    if bad_ph:
        raise SystemExit(f"placeholder parity failures: {bad_ph}")

    # non-empty Arabic
    for s in payload_srcs:
        if not A[s].strip():
            raise SystemExit(f"empty ar for {s!r}")

    # existing approved sources must not collide
    existing = {r["source_text"] for r in csv.DictReader(APPROVED.open(encoding="utf-8"))}
    coll = [s for s in payload_srcs if s in existing]
    if coll:
        raise SystemExit(f"already in approved_ar_overrides: {coll}")

    # write payload paper trail: all 271 dispositions
    with PAYLOAD.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["source_text", "translated_text", "quorum_decision", "decision_ref"])
        for s in scope_srcs:
            if s in PRESERVED:
                w.writerow(
                    [
                        s,
                        PRESERVED[s],
                        "preserved-site-override (not imported, plan §12)",
                        f"stage6-W6-0b batch-1 owner-approved {DATE}",
                    ]
                )
            else:
                w.writerow(
                    [
                        s,
                        A[s],
                        "quorum-confirmed (release payload row)",
                        f"stage6-W6-0b batch-1 owner-approved {DATE}",
                    ]
                )

    # append Released rows
    fieldnames = [
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
    existing_rows = list(csv.DictReader(APPROVED.open(encoding="utf-8")))
    before = len(existing_rows)
    with APPROVED.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        for s in payload_srcs:
            w.writerow(
                {
                    "language": "ar",
                    "source_text": s,
                    "context": "",
                    "ct_app": "frappe",
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

    after = len(list(csv.DictReader(APPROVED.open(encoding="utf-8"))))
    print(f"preserved={len(preserved_srcs)} payload={len(payload_srcs)}")
    print(f"approved rows {before} -> {after} (delta {after - before})")
    print(f"wrote {PAYLOAD}")
    assert after - before == 264
    assert after == before + 264


if __name__ == "__main__":
    main()
