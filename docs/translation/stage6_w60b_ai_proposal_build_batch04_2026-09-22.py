#!/usr/bin/env python3
"""W6-0b batch-4 AI proposal build + payload append + quorum paper trail.

Owner-approved scope: stage6_w60b_batch04_rows_2026-09-22.csv (271 rows).
Site-override reconciliation (plan §12): 3 rows preserved, not imported.
Technical exceptions: 12 source-equal rows, not imported.
Payload: 256 Released rows appended to approved_ar_overrides.csv.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w60b_batch04_rows_2026-09-22.csv"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w60b_payload_applied_rows_batch04_2026-09-22.csv"

DATE = "2026-09-22"
DECISION_REF = f"content:docs/translation/stage6_w60b_payload_applied_rows_batch04_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger arabic_coverage_gap_report_2026-08-22.csv; plan D5; W6-0b batch-4"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed "
    "(W6-0b batch-4; owner-approved 271-row scope minus site-override preserves "
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
# with ct_origin=Site Override on v16.localhost (recon 2026-09-22)
PRESERVED = {
    "Client Id": "معرف العميل",
    "Delimiter Options": "خيارات الفاصل",
    "Missing Field": "حقل مفقود",
}

# EXCEPTION-technical: source==translation format/identifier tokens; not imported
TECHNICAL = {
    "Client URI",
    "Client Metadata",
    "Client Secret Basic",
    "Client Secret Post",
    "Code Challenge",
    "Condition JSON",
    "Form Dict",
    "JS Message",
    "Header, Robots",
    "Logo URI",
    "Introspection URI",
    "Normalized Query",
}

# Full AI proposals for Released rows (glossary v2.0 + Egyptian professional Arabic)
A = {
    "Child Doctype": "نوع مستند فرعي",
    "Click here": "انقر هنا",
    "Click to Set Filters": "انقر لتعيين عوامل التصفية",
    "Client script": "سكربت العميل",
    "Code Editor Type": "نوع محرر الشيفرة",
    "Column 1": "العمود 1",
    "Column 2": "العمود 2",
    "Column {0}": "العمود {0}",
    "Communication Date": "تاريخ التواصل",
    "Communication Logs": "سجلات التواصل",
    "Company Name": "اسم الشركة",
    "Compilation warning": "تحذير التجميع",
    "Completed By Role": "مكتمل بواسطة الدور",
    "Completed By User": "مكتمل بواسطة المستخدم",
    "Condition Type": "نوع الشرط",
    "Configure Recorder": "تكوين المسجّل",
    "Connect to {}": "الاتصال بـ {}",
    "Connected App": "التطبيق المتصل",
    "Connected User": "المستخدم المتصل",
    "Contact Us Settings": "إعدادات اتصل بنا",
    "Correct version :": "الإصدار الصحيح:",
    "Could not start up:": "تعذّر بدء التشغيل:",
    "Created At": "أنشئ في",
    "Current Job ID": "معرف المهمة الحالي",
    "Current Value": "القيمة الحالية",
    "Custom Blocks": "كتل مخصصة",
    "Custom Delimiters": "فواصل مخصصة",
    "Custom Footer": "تذييل مخصص",
    "Custom Label": "تسمية مخصصة",
    "Custom Translation": "ترجمة مخصصة",
    "Customize Form - {0}": "تخصيص النموذج - {0}",
    "Daily Maintenance": "صيانة يومية",
    "Database Processes": "عمليات قاعدة البيانات",
    "Database Version": "إصدار قاعدة البيانات",
    "Debug Log": "سجل تصحيح الأخطاء",
    "Default App": "التطبيق الافتراضي",
    "Default Naming": "التسمية الافتراضية",
    "Default User Role": "دور المستخدم الافتراضي",
    "Default User Type": "نوع المستخدم الافتراضي",
    "Defaults Updated": "تم تحديث الإعدادات الافتراضية",
    "Deletion Steps": "خطوات الحذف",
    "Delivery Status": "حالة التسليم",
    "Desk Settings": "إعدادات المكتب",
    "Desk Theme": "سمة المكتب",
    "Desk User": "مستخدم المكتب",
    "Desktop Settings": "إعدادات سطح المكتب",
    "Detect CSV type": "اكتشاف نوع CSV",
    "Directory Server": "خادم الدليل",
    "Disable Scrolling": "تعطيل التمرير",
    "Disable signups": "تعطيل التسجيلات",
    "DocType Layout Field": "حقل تخطيط نوع المستند",
    "DocType State": "حالة نوع المستند",
    "DocType {} not found": "نوع المستند {} غير موجود",
    "Document Linking": "ربط المستندات",
    "Document Unlocked": "تم فتح قفل المستند",
    "Domain Name": "اسم النطاق",
    "Download Backups": "تنزيل النسخ الاحتياطية",
    "Download Template": "تنزيل القالب",
    "Download as CSV": "تنزيل كـ CSV",
    "Download vCard": "تنزيل vCard",
    "Download vCards": "تنزيل بطاقات vCard",
    "Element Selector": "عنصر التحديد",
    "Email Domain": "نطاق البريد الإلكتروني",
    "Email Header": "ترويسة البريد الإلكتروني",
    "Email ID": "معرف البريد الإلكتروني",
    "Email Id": "معرف البريد الإلكتروني",
    "Email Queue records.": "سجلات طابور البريد الإلكتروني.",
    "Email Retry Limit": "حد إعادة محاولة البريد",
    "Email Sent At": "أُرسل البريد في",
    "Emails Pulled": "الرسائل المسحوبة",
    "Embed code copied": "تم نسخ كود التضمين",
    "Enable Rate Limit": "تفعيل حد المعدل",
    "Enable Scheduler": "تفعيل المجدول",
    "Enabled Scheduler": "المجدول مفعّل",
    "Encrypt Backups": "تشفير النسخ الاحتياطية",
    "Ended At": "انتهى في",
    "Enqueued By": "طُرح بواسطة",
    "Entity Type": "نوع الكيان",
    "Error Logs": "سجلات الأخطاء",
    "Error Message": "رسالة الخطأ",
    "Error {0}: {1}": "خطأ {0}: {1}",
    "Event Frequency": "تكرار الحدث",
    "Exact Copies": "نسخ مطابقة",
    "Existing Role": "الدور الحالي",
    "Expires On": "تنتهي في",
    "Extra Parameters": "معاملات إضافية",
    "Failed Emails": "رسائل بريد فاشلة",
    "Failed Job Count": "عدد المهام الفاشلة",
    "Failed Jobs": "مهام فاشلة",
    "Failure Rate": "معدل الفشل",
    "Field Missing": "حقل مفقود",
    "Field Name": "اسم الحقل",
    "File Storage": "تخزين الملفات",
    "Filtered By": "مُصفّى بواسطة",
    "Filters Editor": "محرر عوامل التصفية",
    "Finished At": "انتهى في",
    "Folder Name": "اسم المجلد",
    "Footer Based On": "التذييل بناءً على",
    "Footer Content": "محتوى التذييل",
    "Footer Details": "تفاصيل التذييل",
    "Footer Image": "صورة التذييل",
    "Footer Script": "سكربت التذييل",
    "For DocType": "لنوع المستند",
    "For Document": "للمستند",
    "Force Stop job": "إيقاف المهمة قسريًا",
    "Form Builder": "منشئ النماذج",
    "Form Tour Step": "خطوة جولة النموذج",
    "Frappe Mail": "بريد Frappe",
    "Frappe Mail Site": "موقع بريد Frappe",
    "Frappe Support": "دعم Frappe",
    "From Date": "من تاريخ",
    "From Field": "من حقل",
    "From User": "من مستخدم",
    "Geolocation Settings": "إعدادات تحديد الموقع الجغرافي",
    "Google Drive Picker": "منتقي Google Drive",
    "Half Yearly": "نصف سنوي",
    "Handled Emails": "رسائل بريد تمت معالجتها",
    "Has Next Condition": "لديه شرط تالٍ",
    "Has Setup Wizard": "لديه معالج الإعداد",
    "Header Icon": "أيقونة الترويسة",
    "Header Script": "سكربت الترويسة",
    "Help Articles": "مقالات المساعدة",
    "Hidden Fields": "حقول مخفية",
    "Hide Buttons": "إخفاء الأزرار",
    "Hide Descendants": "إخفاء التبعيات",
    "Hide Label": "إخفاء التسمية",
    "Hide footer": "إخفاء التذييل",
    "Hide footer signup": "إخفاء تسجيل التذييل",
    "Hide navbar": "إخفاء شريط التنقل",
    "Hourly Maintenance": "صيانة كل ساعة",
    "IMAP Details": "تفاصيل IMAP",
    "IMAP Folder": "مجلد IMAP",
    "Icon Style": "نمط الأيقونة",
    "Icon Type": "نوع الأيقونة",
    "Illegal template": "قالب غير صالح",
    "Image Height": "ارتفاع الصورة",
    "Image Width": "عرض الصورة",
    "Image optimized": "تم تحسين الصورة",
    "Impersonate as {0}": "انتحال هوية {0}",
    "In Minutes": "بالدقائق",
    "In Read Only Mode": "في وضع القراءة فقط",
    "Include Name Field": "تضمين حقل الاسم",
    "Incoming Server": "خادم الوارد",
    "Incoming Settings": "إعدادات الوارد",
    "Incorrect value:": "قيمة غير صحيحة:",
    "Indicator Color": "لون المؤشر",
    "Intro Video URL": "رابط الفيديو التعريفي",
    "Invalid Action": "إجراء غير صالح",
    "Invalid Credentials": "بيانات اعتماد غير صالحة",
    "Invalid DocType": "نوع مستند غير صالح",
    "Invalid DocType: {0}": "نوع مستند غير صالح: {0}",
    "Invalid Doctype": "نوع مستند غير صالح",
    "Invalid Fieldname": "اسم حقل غير صالح",
    "Invalid File URL": "رابط ملف غير صالح",
    "Invalid Operation": "عملية غير صالحة",
    "Invalid Override": "تجاوز غير صالح",
    "Invalid Parameters.": "معاملات غير صالحة.",
    "Invalid Phone Number": "رقم هاتف غير صالح",
    "Invalid app": "تطبيق غير صالح",
    "Invalid docstatus": "حالة مستند غير صالحة",
    "Invalid key": "مفتاح غير صالح",
    "Invalid request body": "جسم الطلب غير صالح",
    "Invalid role": "دور غير صالح",
    "Invitation not found": "الدعوة غير موجودة",
    "Invited By": "مدعو بواسطة",
    "Is Current": "هو الحالي",
    "Is Custom": "مخصص",
    "Is Dynamic URL?": "هل هو رابط ديناميكي؟",
    "Is Hidden": "مخفي",
    "Is Primary Address": "عنوان رئيسي",
    "Is Remote Request?": "هل هو طلب عن بعد؟",
    "Is Setup Complete?": "هل اكتمل الإعداد؟",
    "Is System Generated": "منشأ بواسطة النظام",
    "Is Table Field": "حقل جدول",
    "Is Virtual": "افتراضي",
    "Is standard": "قياسي",
    "Job ID": "معرف المهمة",
    "Job Id": "معرف المهمة",
    "Job Info": "معلومات المهمة",
    "Job Name": "اسم المهمة",
    "Job Status": "حالة المهمة",
    "Job is not running.": "المهمة غير تعمل.",
    "LDAP Auth": "مصادقة LDAP",
    "LDAP Custom Settings": "إعدادات LDAP المخصصة",
    "LDAP Mobile Field": "حقل الجوال LDAP",
    "LDAP Server Settings": "إعدادات خادم LDAP",
    "Last 10 active users": "آخر 10 مستخدمين نشطين",
    "Last Heartbeat": "آخر نبضة",
    "Last Modified Date": "تاريخ آخر تعديل",
    "Last Received At": "آخر استلام في",
    "Last Run": "آخر تشغيل",
    "Last Updated": "آخر تحديث",
    "Layout Reset": "إعادة تعيين التخطيط",
    "Learn more": "اعرف المزيد",
    "Left Bottom": "أسفل اليسار",
    "Left Center": "وسط اليسار",
    "Letter Head Scripts": "سكربتات ترويسة الرسائل",
    "License Type": "نوع الترخيص",
    "Light Blue": "أزرق فاتح",
    "Log API Requests": "تسجيل طلبات API",
    "Log DocType": "تسجيل نوع المستند",
    "Log Index": "فهرس السجل",
    "Login Methods": "طرق تسجيل الدخول",
    "Login To {0}": "تسجيل الدخول إلى {0}",
    "Login required": "تسجيل الدخول مطلوب",
    "Logs to Clear": "سجلات للمسح",
    "MIT License": "ترخيص MIT",
    "Maintenance Manager": "مدير الصيانة",
    "Maintenance User": "مستخدم الصيانة",
    "Margin Bottom": "الهامش السفلي",
    "Margin Left": "الهامش الأيسر",
    "Margin Right": "الهامش الأيمن",
    "Margin Top": "الهامش العلوي",
    "MariaDB Variables": "متغيرات MariaDB",
    "Marketing Manager": "مدير التسويق",
    "Max File Size (MB)": "أقصى حجم ملف (ميجابايت)",
    "Max Height": "أقصى ارتفاع",
    "Max attachment size": "أقصى حجم مرفق",
    "Meets Condition?": "يحقق الشرط؟",
    "Memory Usage": "استخدام الذاكرة",
    "Memory Usage in MB": "استخدام الذاكرة بالميجابايت",
    "Message Type": "نوع الرسالة",
    "Meta image": "صورة الميتا",
    "Meta title": "عنوان الميتا",
    "Method Not Allowed": "الطريقة غير مسموحة",
    "Mid Center": "وسط المنتصف",
    "Minutes After": "دقائق بعد",
    "Minutes Before": "دقائق قبل",
    "Minutes Offset": "إزاحة الدقائق",
    "Missing DocType": "نوع مستند مفقود",
    "Missing Permission": "إذن مفقود",
    "Module HTML": "وحدة HTML",
    "Module Profile": "ملف الوحدة",
    "Module Profile Name": "اسم ملف الوحدة",
    "Module {} not found": "الوحدة {} غير موجودة",
    "Name (Doc Name)": "الاسم (اسم المستند)",
    "Naming Rule": "قاعدة التسمية",
    "Navbar Style": "نمط شريط التنقل",
    "Navigation Settings": "إعدادات التنقل",
    "Next Execution": "التنفيذ التالي",
    "Next Form Tour": "جولة النموذج التالية",
    "Next Scheduled Date": "التاريخ المجدول التالي",
    "Next Step Condition": "شرط الخطوة التالية",
    "Next Sync Token": "رمز المزامنة التالي",
    "Next on Click": "التالي عند النقر",
    "No Roles Specified": "لم تُحدد أدوار",
    "No Suggestions": "لا توجد اقتراحات",
    "No changes to sync": "لا توجد تغييرات للمزامنة",
    "No changes to update": "لا توجد تغييرات للتحديث",
    "No failed logs": "لا توجد سجلات فاشلة",
    "No of Requested SMS": "عدد رسائل SMS المطلوبة",
    "No of Sent SMS": "عدد رسائل SMS المرسلة",
    "No subject": "بدون موضوع",
    "No {0}": "لا {0}",
    "Normalized Copies": "نسخ مُطبّعة",
    "Not Allowed": "غير مسموح",
}


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 271, f"expected 271 scope rows, got {len(scope_rows)}"

    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {diff}"

    for s, ar in A.items():
        src_ph = sorted(re.findall(r"\{[0-9]*\}", s))
        ar_ph = sorted(re.findall(r"\{[0-9]*\}", ar))
        assert src_ph == ar_ph, f"placeholder mismatch on '{s}': {src_ph} != {ar_ph}"

    preserved_srcs = [s for s in scope_rows if s in PRESERVED]
    tech_srcs = [s for s in scope_rows if s in TECHNICAL]
    payload_srcs = [s for s in scope_rows if s in A]

    assert len(preserved_srcs) == 3, f"expected 3 preserved, got {len(preserved_srcs)}"
    assert len(tech_srcs) == 12, f"expected 12 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 256, f"expected 256 payload, got {len(payload_srcs)}"

    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    with PAYLOAD.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["source_text", "translated_text", "quorum_decision", "decision_ref"])
        for s in scope_rows:
            if s in PRESERVED:
                w.writerow(
                    [
                        s,
                        PRESERVED[s],
                        "preserved-site-override (not imported, plan §12)",
                        f"stage6-W6-0b batch-4 owner-approved {DATE}",
                    ]
                )
            elif s in TECHNICAL:
                w.writerow(
                    [
                        s,
                        "EXCEPTION-technical",
                        "EXCEPTION-technical (keep vendor rendering; no translation)",
                        f"stage6-W6-0b batch-4 owner-approved {DATE}",
                    ]
                )
            else:
                w.writerow(
                    [
                        s,
                        A[s],
                        "quorum-confirmed (release payload row)",
                        f"stage6-W6-0b batch-4 owner-approved {DATE}",
                    ]
                )

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
    assert after - before == 256
    assert after == before + 256


if __name__ == "__main__":
    main()
