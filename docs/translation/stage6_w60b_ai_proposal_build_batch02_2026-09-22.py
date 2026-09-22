#!/usr/bin/env python3
"""W6-0b batch-2 AI proposal build + payload append + quorum paper trail.

Owner-approved scope: stage6_w60b_batch02_rows_2026-09-22.csv (271 rows).
Site-override reconciliation (plan §12): 2 rows preserved, not imported.
Technical exceptions: 26 source-equal rows, not imported.
Payload: Released rows appended to approved_ar_overrides.csv.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w60b_batch02_rows_2026-09-22.csv"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w60b_payload_applied_rows_batch02_2026-09-22.csv"

DATE = "2026-09-22"
DECISION_REF = f"content:docs/translation/stage6_w60b_payload_applied_rows_batch02_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger arabic_coverage_gap_report_2026-08-22.csv; plan D5; W6-0b batch-2"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed "
    "(W6-0b batch-2; owner-approved 271-row scope minus site-override preserves "
    "and EXCEPTION-technical rows)"
)
DOMAIN = "desk-short-ui"
RELEASE_VERSION = "1.2"
REVIEWERS = (
    "AI-A1 (recorded review run)",
    "AI-A2 (recorded review run)",
    "AI-A3 (recorded review run)",
)
TS = f"{DATE} 00:00:00"

# Site-override preserved (not imported) — case-insensitive matches on batch keys
# with ct_origin=Site Override on v16.localhost
PRESERVED = {
    "Country": "البلد",
    "Not Permitted": "غير مسموح",
}

# EXCEPTION-technical: source==translation format/identifier tokens; not imported
TECHNICAL = {
    "A7",
    "A8",
    "A9",
    "B0",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B9",
    "B10",
    "C5E",
    "Comm10E",
    "CSS",
    "DLE",
    "BCC",
    "XMLHttpRequest Error",
    "Inter",
    "Folio",
    "Tabloid",
    "vscode",
    "Doctype",
    "Ar",
}

# Full AI proposals for Released rows (glossary v2.0 + Egyptian professional Arabic)
A = {
    "Always": "دائمًا",
    "Ask": "اسأل",
    "Column width cannot be zero.": "لا يمكن أن يكون عرض العمود صفرًا.",
    "Component": "مكوّن",
    "Dependencies": "الاعتماديات",
    "DocType must have atleast one field": "يجب أن يحتوي DocType على حقل واحد على الأقل",
    "Don't have an account?": "ليس لديك حساب؟",
    "ESC": "Esc",
    "Excellent": "ممتاز",
    "Executive": "تنفيذي",
    "Fieldname {0} appears multiple times": "اسم الحقل {0} يظهر عدة مرات",
    "Free": "مجاني",
    "Here's your tracking URL": "إليك رابط التتبع",
    "Insert Image in Markdown": "إدراج صورة بتنسيق Markdown",
    "Legal": "قانوني",
    "Password cannot be filtered": "لا يمكن التصفية بكلمة المرور",
    "Progress": "التقدّم",
    "SWATCHES": "عينات الألوان",
    "Send": "إرسال",
    "Solid": "صلب",
    "Source": "المصدر",
    "Start": "بدء",
    "Strong": "قوية",
    "Type a reply / comment": "اكتب ردًا / تعليقًا",
    "Weak": "ضعيفة",
    "Welcome": "مرحبًا",
    "cyan": "سماوي",
    "this form": "هذه النموذج",
    "Cannot cancel {0}.": "لا يمكن إلغاء {0}.",
    "Cannot submit {0}.": "لا يمكن ترحيل {0}.",
    "Discard {0}": "تجاهل {0}",
    "Discard?": "هل تريد التجاهل؟",
    "Loading versions...": "جارٍ تحميل الإصدارات...",
    "Notification sent to": "تم إرسال الإشعار إلى",
    "Permanently Discard {0}?": "هل تريد التجاهل النهائي لـ {0}؟",
    "Preview Mode": "وضع المعاينة",
    "Preview on {0}": "معاينة على {0}",
    "Preview type": "نوع المعاينة",
    "Workspace {0} created": "تم إنشاء مساحة العمل {0}",
    "About Us": "من نحن",
    "All Day": "طوال اليوم",
    "All Submissions": "كل الترحيلات",
    "Apply Filters": "تطبيق عوامل التصفية",
    "Awesome Work": "عمل رائع",
    "Billing Contact": "جهة اتصال الفوترة",
    "Cannot {0} {1}.": "لا يمكن {0} {1}.",
    "Card Links": "روابط البطاقات",
    "Change Image": "تغيير الصورة",
    "Clear Assignment": "مسح الإسناد",
    "Compare Versions": "مقارنة الإصدارات",
    "Complete Setup": "إكمال الإعداد",
    "Connection Lost": "انقطع الاتصال",
    "Contact Us": "اتصل بنا",
    "Current status": "الحالة الحالية",
    "Custom Block Name": "اسم الكتلة المخصصة",
    "Date Range": "نطاق التاريخ",
    "Deadlock Occurred": "حدث ركود",
    "Discussion Reply": "رد النقاش",
    "DocType Layout": "تخطيط DocType",
    "DocType Missing": "DocType مفقود",
    "Document Name": "اسم المستند",
    "Drag to add state": "اسحب لإضافة حالة",
    "Drop files here": "أسقط الملفات هنا",
    "Empty column": "عمود فارغ",
    "File upload failed.": "فشل رفع الملف.",
    "Filters {0}": "عوامل تصفية {0}",
    "Find '{0}' in ...": "ابحث عن '{0}' في ...",
    "Followed by": "يليه",
    "For example:": "على سبيل المثال:",
    "Frappe Blog": "مدونة Frappe",
    "Frappe Forum": "منتدى Frappe",
    "Frappe Light": "Frappe الفاتح",
    "From version": "من إصدار",
    "Go to Workflow": "الذهاب إلى سير العمل",
    "Greater Than": "أكبر من",
    "ID (name)": "المعرّف (الاسم)",
    "Impersonated by {0}": "ينتحل شخصية {0}",
    "Impersonating {0}": "ينتحل شخصية {0}",
    "Include Disabled": "تضمين المعطّلة",
    "Indicator color": "لون المؤشر",
    "Installed Apps": "التطبيقات المثبّتة",
    "Invalid input": "إدخال غير صالح",
    "Kanban Settings": "إعدادات كانبان",
    "Keep Closed": "إبقاء مغلقًا",
    "Last 14 Days": "آخر 14 يومًا",
    "Last 30 Days": "آخر 30 يومًا",
    "Last 6 Months": "آخر 6 أشهر",
    "Last 7 Days": "آخر 7 أيام",
    "Last 90 Days": "آخر 90 يومًا",
    "Less Than": "أصغر من",
    "Logs To Clear": "سجلات للمسح",
    "Mark all as read": "تعليم الكل كمقروء",
    "Missing Value": "قيمة مفقودة",
    "My Device": "أجهزتي",
    "Need Help?": "تحتاج مساعدة؟",
    "Next 14 Days": "الـ 14 يومًا القادمة",
    "Next 30 Days": "الـ 30 يومًا القادمة",
    "Next 6 Months": "الـ 6 أشهر القادمة",
    "Next 7 Days": "الـ 7 أيام القادمة",
    "Next Document": "المستند التالي",
    "Next Month": "الشهر القادم",
    "Next Quarter": "الربع القادم",
    "Next Week": "الأسبوع القادم",
    "Next Year": "العام القادم",
    "Next actions": "الإجراءات التالية",
    "No Upcoming Events": "لا توجد أحداث قادمة",
    "No changes made": "لم يتم إجراء تغييرات",
    "No filters selected": "لم يتم تحديد عوامل تصفية",
    "No records tagged.": "لا توجد سجلات موسومة.",
    "No {0} found": "لم يتم العثور على {0}",
    "Not permitted. {0}.": "غير مسموح. {0}.",
    "Nothing left to redo": "لا يوجد ما يمكن إعادته",
    "Nothing left to undo": "لا يوجد ما يمكن التراجع عنه",
    "On {0}, {1} wrote:": "في {0}، كتب {1}:",
    "Onboarding Name": "اسم الإعداد التمهيدي",
    "Onboarding complete": "اكتمل الإعداد التمهيدي",
    "Only for": "فقط لـ",
    "Page Height (in mm)": "ارتفاع الصفحة (بالمم)",
    "Page Margins": "هوامش الصفحة",
    "Page Number": "رقم الصفحة",
    "Page Size": "حجم الصفحة",
    "Page Width (in mm)": "عرض الصفحة (بالمم)",
    "Please set filters": "يرجى تعيين عوامل التصفية",
    "Previous Document": "المستند السابق",
    "Previous Submission": "الترحيل السابق",
    "Primary Contact": "جهة الاتصال الأساسية",
    "Primary Email": "البريد الإلكتروني الأساسي",
    "Primary Mobile": "الجوال الأساسي",
    "Primary Phone": "الهاتف الأساسي",
    "QZ Tray Failed:": "فشل QZ Tray:",
    "Rebuild Tree": "إعادة بناء الشجرة",
    "Remind At": "تذكير في",
    "Remind Me": "ذكّرني",
    "Remind Me In": "ذكّرني بعد",
    "Reminder set at {0}": "تم تعيين التذكير عند {0}",
    "Request Timeout": "انتهت مهلة الطلب",
    "Reset To Default": "إعادة تعيين للافتراضي",
    "Rest of the day": "بقية اليوم",
    "Route Options": "خيارات المسار",
    "Saving Changes...": "جارٍ حفظ التغييرات...",
    "Scan QRCode": "مسح رمز QR",
    "Schedule Send At": "جدولة الإرسال في",
    "See all Activity": "عرض كل النشاط",
    "Select Kanban": "تحديد كانبان",
    "Select an Image": "تحديد صورة",
    "Send login link": "إرسال رابط تسجيل الدخول",
    "Set Level": "تعيين المستوى",
    "Set all public": "تعيين الكل كعام",
    "Shipping Address": "عنوان الشحن",
    "Show Arrow": "إظهار السهم",
    "Show Error": "إظهار الخطأ",
    "Show Labels": "إظهار الملصقات",
    "Show Links": "إظهار الروابط",
    "Show all activity": "إظهار كل النشاط",
    "Source Code": "الشيفرة المصدرية",
    "State Properties": "خصائص الحالة",
    "Tab Label": "ملصق التبويب",
    "Theme Changed": "تم تغيير المظهر",
    "This Month": "هذا الشهر",
    "This Quarter": "هذا الربع",
    "This Week": "هذا الأسبوع",
    "This Year": "هذا العام",
    "Time Interval": "الفاصل الزمني",
    "Timeless Night": "ليل بلا زمن",
    "To version": "إلى إصدار",
    "Translate Data": "ترجمة البيانات",
    "Translate values": "ترجمة القيم",
    "Try Again": "حاول مرة أخرى",
    "Undo last action": "تراجع عن آخر إجراء",
    "Upload Image": "رفع صورة",
    "Upload file": "رفع ملف",
    "Upload {0} files": "رفع {0} ملفات",
    "User Changed": "تم تغيير المستخدم",
    "Watch Tutorial": "مشاهدة الشرح",
    "Watch Video": "مشاهدة الفيديو",
    "Website Settings": "إعدادات موقع الويب",
    "Workflow Builder": "منشئ سير العمل",
    "You Liked": "أعجبك",
    "You attached {0}": "أرفقت {0}",
    "You created this": "أنشأت هذا",
    "You last edited this": "آخر تعديل لك كان لهذا",
    "You viewed this": "عرضت هذا",
    "(Mandatory)": "(إلزامي)",
    "1 Day": "يوم واحد",
    "1 hour": "ساعة واحدة",
    "1 of 2": "1 من 2",
    "1 row from {0}": "صف واحد من {0}",
    "1 row to {0}": "صف واحد إلى {0}",
    "30 minutes": "30 دقيقة",
    "4 hours": "4 ساعات",
    "Apps": "التطبيقات",
    "Attachment Limit Reached": "تم الوصول إلى حد المرفقات",
    "Autoincrement": "تزايد تلقائي",
    "Automatic": "تلقائي",
    "Blue": "أزرق",
    "Both login and password required": "اسم المستخدم وكلمة المرور مطلوبان",
    "Build": "بناء",
    "Choose a block or continue typing": "اختر كتلة أو أكمل الكتابة",
    "Click on a file to select it.": "انقر على ملف لتحديده.",
    "Configure columns for {0}": "تكوين أعمدة لـ {0}",
    "Connections": "الاتصالات",
    "Copied {0} {1} to clipboard": "تم نسخ {0} {1} إلى الحافظة",
    "Count of linked documents": "عدد المستندات المرتبطة",
    "Current": "الحالي",
    "Customizations Discarded": "تم تجاهل التخصيصات",
    "Cyan": "سماوي",
    "Database Row Size Utilization": "استخدام حجم صفوف قاعدة البيانات",
    "Deleting {0} records...": "جارٍ حذف {0} سجلات...",
    "Delimiter must be a single character": "يجب أن يكون الفاصل حرفًا واحدًا",
    "Dependencies & Licenses": "الاعتماديات والتراخيص",
    "Descendants Of (inclusive)": "النسل من (شامل)",
    "Display Depends On (JS)": "العرض يعتمد على (JS)",
    "Do not warn me again about {0}": "لا تحذّرني مرة أخرى بشأن {0}",
    "Document has been cancelled": "تم إلغاء المستند",
    "Document has been submitted": "تم ترحيل المستند",
    "Document is in draft state": "المستند في حالة مسودة",
    "Documents": "المستندات",
    "Double click to edit label": "انقر مرتين لتعديل الملصق",
    "Drag and drop files here or upload from": "اسحب وأفلت الملفات هنا أو ارفع من",
    "Enter a name for this {0}": "أدخل اسمًا لـ {0}",
    "Error in Client Script": "خطأ في السكربت العميل",
    "Error in Client Script.": "خطأ في السكربت العميل.",
    "Events": "الأحداث",
    "Experimental": "تجريبي",
    "Feedback": "التغذية الراجعة",
    "Field Orientation (Left-Right)": "اتجاه الحقل (يسار-يمين)",
    "Field Orientation (Top-Down)": "اتجاه الحقل (أعلى-أسفل)",
    "Filters:": "عوامل التصفية:",
    "Fit": "ملاءمة",
    "Following fields have missing values": "الحقول التالية بها قيم مفقودة",
    "Generate Random Password": "توليد كلمة مرور عشوائية",
    "Greater Than Or Equal To": "أكبر من أو يساوي",
    "Green": "أخضر",
    "Include hidden columns": "تضمين الأعمدة المخفية",
    "Instagram": "إنستغرام",
    "Invalid values for fields:": "قيم غير صالحة للحقول:",
    "Less Than Or Equal To": "أصغر من أو يساوي",
    "Let us continue with the onboarding": "لنكمل الإعداد التمهيدي",
    "Library": "المكتبة",
    "LinkedIn": "لينكدإن",
    "Lists": "القوائم",
    "Login Failed please try again": "فشل تسجيل الدخول، يرجى المحاولة مرة أخرى",
    "Mandatory fields required:": "الحقول الإلزامية المطلوبة:",
}


def placeholders(s: str) -> list[str]:
    return re.findall(r"\{[^{}]*\}", s)


def main() -> None:
    scope = list(csv.DictReader(SCOPE.open(encoding="utf-8")))
    assert len(scope) == 271, len(scope)
    scope_srcs = [r["source_text"] for r in scope]
    assert len(set(scope_srcs)) == 271

    preserved_srcs = [s for s in scope_srcs if s in PRESERVED]
    tech_srcs = [s for s in scope_srcs if s in TECHNICAL]
    payload_srcs = [s for s in scope_srcs if s not in PRESERVED and s not in TECHNICAL]
    assert len(preserved_srcs) == 2, preserved_srcs
    assert len(tech_srcs) == 26, (len(tech_srcs), tech_srcs)
    assert len(payload_srcs) == 243, len(payload_srcs)

    # no overlap
    assert not (set(preserved_srcs) & set(tech_srcs))
    assert not (set(preserved_srcs) & set(payload_srcs))
    assert not (set(tech_srcs) & set(payload_srcs))

    missing = [s for s in payload_srcs if s not in A]
    if missing:
        raise SystemExit(f"missing proposals ({len(missing)}): {missing}")

    extra = [s for s in A if s not in payload_srcs]
    if extra:
        raise SystemExit(f"extra proposals not in payload ({len(extra)}): {extra}")

    # placeholder parity
    bad_ph = []
    for s in payload_srcs:
        if placeholders(s) != placeholders(A[s]):
            bad_ph.append((s, A[s], placeholders(s), placeholders(A[s])))
    if bad_ph:
        raise SystemExit(f"placeholder parity failures: {bad_ph}")

    # non-empty Arabic / distinct from source
    for s in payload_srcs:
        if not A[s].strip():
            raise SystemExit(f"empty ar for {s!r}")
        if A[s] == s:
            raise SystemExit(f"source-equal released row {s!r}")

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
                        f"stage6-W6-0b batch-2 owner-approved {DATE}",
                    ]
                )
            elif s in TECHNICAL:
                w.writerow(
                    [
                        s,
                        "EXCEPTION-technical",
                        "EXCEPTION-technical (keep vendor rendering; no translation)",
                        f"stage6-W6-0b batch-2 owner-approved {DATE}",
                    ]
                )
            else:
                w.writerow(
                    [
                        s,
                        A[s],
                        "quorum-confirmed (release payload row)",
                        f"stage6-W6-0b batch-2 owner-approved {DATE}",
                    ]
                )

    # append Released rows only
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
    print(f"preserved={len(preserved_srcs)} technical={len(tech_srcs)} payload={len(payload_srcs)}")
    print(f"approved rows {before} -> {after} (delta {after - before})")
    print(f"wrote {PAYLOAD}")
    assert after - before == 243
    assert after == before + 243


if __name__ == "__main__":
    main()
