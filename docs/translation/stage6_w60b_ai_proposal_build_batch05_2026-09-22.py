#!/usr/bin/env python3
"""W6-0b batch-5 AI proposal build + payload append + quorum paper trail.

Owner-approved scope: stage6_w60b_batch05_rows_2026-09-22.csv (270 rows).
Site-override reconciliation (plan §12): 1 row preserved, not imported.
Technical exceptions: source-equal rows, not imported.
Payload: Released rows appended to approved_ar_overrides.csv.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w60b_batch05_rows_2026-09-22.csv"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w60b_payload_applied_rows_batch05_2026-09-22.csv"

DATE = "2026-09-22"
DECISION_REF = f"content:docs/translation/stage6_w60b_payload_applied_rows_batch05_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger arabic_coverage_gap_report_2026-08-22.csv; plan D5; W6-0b batch-5"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed "
    "(W6-0b batch-5; owner-approved 270-row scope minus site-override preserves "
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
    "Postal Code": "الرمز البريدي",
}

# EXCEPTION-technical: source==translation format/identifier tokens; not imported
TECHNICAL = {
    "Not Nullable",
    "Policy URI",
    "Redirect URI",
    "Resource Policy URI",
    "Resource TOS URI",
    "Revocation URI",
    "SQL Explain",
    "SQL Output",
    "Success URI",
    "TOS URI",
    "Token URI",
    "Userinfo URI",
    "RQ Worker",
    "Realtime (SocketIO)",
    "SocketIO Ping Check",
    "Use STARTTLS",
    "Setup > User",
}

# Full AI proposals for Released rows (glossary v2.0 + Egyptian professional Arabic)
A = {
    "Not Helpful": "غير مفيد",
    "Not a valid user": "مستخدم غير صالح",
    "Not active": "غير نشط",
    "Number Card Name": "اسم بطاقة العدد",
    "Number of Queries": "عدد الاستعلامات",
    "Number of keys": "عدد المفاتيح",
    "OAuth Client Role": "دور عميل OAuth",
    "OAuth Error": "خطأ OAuth",
    "OAuth Scope": "نطاق OAuth",
    "OAuth Settings": "إعدادات OAuth",
    "OTP SMS Template": "قالب رسالة OTP",
    "Offset X": "إزاحة X",
    "Offset Y": "إزاحة Y",
    "Onboarding Status": "حالة الإعداد التمهيدي",
    "OpenID Configuration": "تهيئة OpenID",
    "Optimizing image...": "جارٍ تحسين الصورة...",
    "Original Value": "القيمة الأصلية",
    "Outgoing Server": "خادم الصادر",
    "Outgoing Settings": "إعدادات الصادر",
    "PDF Generator": "مولّد PDF",
    "Package Name": "اسم الحزمة",
    "Package Release": "إصدار الحزمة",
    "Page Route": "مسار الصفحة",
    "Page Title": "عنوان الصفحة",
    "Parent DocType": "نوع المستند الأب",
    "Parent Field": "الحقل الأب",
    "Parent Icon": "الأيقونة الأب",
    "Parent Missing": "الأب مفقود",
    "Parent Page": "الصفحة الأم",
    "Partial Success": "نجاح جزئي",
    "Partially Sent": "أُرسل جزئيًا",
    "Password Email Sent": "أُرسل بريد كلمة المرور",
    "Payload Count": "عدد الحمولة",
    "Peak Memory Usage": "ذروة استخدام الذاكرة",
    "Pending Emails": "رسائل بريد معلّقة",
    "Pending Jobs": "مهام معلّقة",
    "Permission Inspector": "فاحص الأذونات",
    "Permission Levels": "مستويات الأذونات",
    "Permission Log": "سجل الأذونات",
    "Permission Manager": "مدير الأذونات",
    "Permission Query": "استعلام الأذونات",
    "Permission Type": "نوع الإذن",
    "Permissions Error": "خطأ في الأذونات",
    "Permitted Roles": "الأدوار المسموح بها",
    "Plain Text": "نص عادي",
    "Please select {0}": "يرجى اختيار {0}",
    "Popover Element": "عنصر منبثق",
    "Prefer not to say": "أفضل عدم الذكر",
    "Private Files (MB)": "ملفات خاصة (ميجابايت)",
    "Profile Picture": "صورة الملف الشخصي",
    "Protected File": "ملف محمي",
    "Public Files (MB)": "ملفات عامة (ميجابايت)",
    "Published Web Forms": "نماذج ويب منشورة",
    "Published Web Pages": "صفحات ويب منشورة",
    "Publishing Dates": "تواريخ النشر",
    "Pull Emails": "سحب الرسائل",
    "Pulling emails...": "جارٍ سحب الرسائل...",
    "Purchase Manager": "مدير المشتريات",
    "Purchase User": "مستخدم المشتريات",
    "Push Notifications": "إشعارات فورية",
    "Put on Hold": "تعليق",
    "Query Parameters": "معاملات الاستعلام",
    "Queue Overloaded": "الطابور مثقل",
    "Queue Status": "حالة الطابور",
    "Queue Type(s)": "نوع الطابور",
    "Queued At": "طُرح في",
    "Queued By": "طُرح بواسطة",
    "Quick Entry": "إدخال سريع",
    "Quick Lists": "قوائم سريعة",
    "Rate Limiting": "تحديد المعدل",
    "Raw Printing Setting": "إعداد الطباعة الخام",
    "Re-Run in Console": "إعادة التشغيل في وحدة التحكم",
    "Read mode": "وضع القراءة",
    "Recorder Query": "استعلام المسجّل",
    "Recursive Fetch From": "جلب تعاودي من",
    "Redirect HTTP Status": "حالة إعادة التوجيه HTTP",
    "Redirect To Path": "إعادة توجيه إلى مسار",
    "Reference Datetime": "تاريخ ووقت المرجع",
    "Reference Doc": "المستند المرجعي",
    "Reference Document": "المستند المرجعي",
    "Reference Name": "اسم المرجع",
    "Relay Settings": "إعدادات الترحيل",
    "Release Notes": "ملاحظات الإصدار",
    "Repeat on Days": "التكرار في الأيام",
    "Request Body": "جسم الطلب",
    "Request Description": "وصف الطلب",
    "Request Headers": "ترويسات الطلب",
    "Request ID": "معرف الطلب",
    "Request Limit": "حد الطلبات",
    "Request Method": "طريقة الطلب",
    "Requested Numbers": "الأرقام المطلوبة",
    "Reset Layout": "إعادة تعيين التخطيط",
    "Resource Name": "اسم المورد",
    "Response Headers": "ترويسات الاستجابة",
    "Retry Sending": "إعادة محاولة الإرسال",
    "Right Bottom": "أسفل اليمين",
    "Right Center": "وسط اليمين",
    "Role Profiles": "ملفات تعريف الأدوار",
    "Role Replication": "استنساخ الأدوار",
    "Roles & Permissions": "الأدوار والأذونات",
    "Rounding Method": "طريقة التقريب",
    "Row #": "رقم الصف #",
    "Row Format": "تنسيق الصف",
    "Row Indexes": "فهرس الصفوف",
    "Row Number": "رقم الصف",
    "Row Values Changed": "تغيّرت قيم الصف",
    "Row {0}": "الصف {0}",
    "Runtime in Minutes": "وقت التشغيل بالدقائق",
    "Runtime in Seconds": "وقت التشغيل بالثواني",
    "SMS Log": "سجل SMS",
    "SMS Settings": "إعدادات SMS",
    "SQL Queries": "استعلامات SQL",
    "Sales Manager": "مدير المبيعات",
    "Sales Master Manager": "مدير المبيعات الرئيسي",
    "Sales User": "مستخدم المبيعات",
    "Scheduled Against": "مجدول ضد",
    "Scheduled Jobs Logs": "سجلات المهام المجدولة",
    "Scheduler Inactive": "المجدول غير نشط",
    "Scheduler Status": "حالة المجدول",
    "Scheduler: Active": "المجدول: نشط",
    "Scheduler: Inactive": "المجدول: غير نشط",
    "Scopes Supported": "النطاقات المدعومة",
    "Scripting / Style": "السكربتات / التنسيق",
    "Section ID": "معرف القسم",
    "Select Country": "اختر الدولة",
    "Select Page": "اختر الصفحة",
    "Select Time Zone": "اختر المنطقة الزمنية",
    "Select Workflow": "اختر مسار العمل",
    "Select Workspaces": "اختر مساحات العمل",
    "Send Email On State": "إرسال بريد عند الحالة",
    "Send Now": "إرسال الآن",
    "Sender Email": "بريد المرسل",
    "Sender Email Field": "حقل بريد المرسل",
    "Sender Name": "اسم المرسل",
    "Sender Name Field": "حقل اسم المرسل",
    "Sent Folder Name": "اسم مجلد المرسل",
    "Sent On": "أُرسل في",
    "Sent To": "أُرسل إلى",
    "Sequence Id": "معرف التسلسل",
    "Session Created": "أُنشئت الجلسة",
    "Set Limit": "تعيين حد",
    "Set Properties": "تعيين الخصائص",
    "Set only once": "تعيين مرة واحدة فقط",
    "Set size in MB": "تعيين الحجم بالميجابايت",
    "Setup failed": "فشل الإعداد",
    "Show Absolute Values": "إظهار القيم المطلقة",
    "Show Full Number": "إظهار الرقم الكامل",
    "Show Language Picker": "إظهار منتقي اللغة",
    "Show Processlist": "إظهار قائمة العمليات",
    "Show Related Errors": "إظهار الأخطاء ذات الصلة",
    "Show Tour": "إظهار الجولة",
    "Show Traceback": "إظهار تتبع الأخطاء",
    "Show attachments": "إظهار المرفقات",
    "Show footer on login": "إظهار التذييل عند تسجيل الدخول",
    "Show list": "إظهار القائمة",
    "Show on Timeline": "إظهار على الجدول الزمني",
    "Sign Out": "تسجيل الخروج",
    "Sign ups": "التسجيلات",
    "Size (MB)": "الحجم (ميجابايت)",
    "Slack Webhook URL": "رابط Webhook الخاص بـ Slack",
    "Software ID": "معرف البرنامج",
    "Software Version": "إصدار البرنامج",
    "Source Name": "اسم المصدر",
    "Splash Image": "صورة البداية",
    "Stack Trace": "تتبع المكدس",
    "Standard Permissions": "أذونات قياسية",
    "Start Recording": "بدء التسجيل",
    "Start Time": "وقت البدء",
    "Started At": "بدأ في",
    "Storage Usage (MB)": "استخدام التخزين (ميجابايت)",
    "Submission Queue": "طابور الإرسال",
    "Success message": "رسالة نجاح",
    "Success title": "عنوان النجاح",
    "Successful Job Count": "عدد المهام الناجحة",
    "Suggested Indexes": "الفهارس المقترحة",
    "Sync {0} Fields": "مزامنة حقول {0}",
    "Synced Fields": "حقول متزامنة",
    "Syntax Error": "خطأ في الصياغة",
    "System Health": "صحة النظام",
    "System Logs": "سجلات النظام",
    "Table Field": "حقل الجدول",
    "Table Fieldname": "اسم حقل الجدول",
    "Table Trimmed": "الجدول مقصوص",
    "Template File": "ملف القالب",
    "Test Data": "بيانات الاختبار",
    "Test Job ID": "معرف مهمة الاختبار",
    "Test Spanish": "اختبار الإسبانية",
    "Time Taken": "الوقت المستغرق",
    "Time in Queries": "الوقت في الاستعلامات",
    "Timed Out": "انتهت المهلة",
    "Timeless Launchpad": "لوحة الإطلاق بدون وقت",
    "Timeout (In Seconds)": "مهلة (بالثواني)",
    "To Date": "إلى تاريخ",
    "Token Cache": "ذاكرة التخزين المؤقت للرمز",
    "Token Type": "نوع الرمز",
    "Too Many Documents": "عدد كبير جدًا من المستندات",
    "Top 10": "أفضل 10",
    "Top Errors": "أهم الأخطاء",
    "Total Users": "إجمالي المستخدمين",
    "Total Working Time": "إجمالي وقت العمل",
    "Trace ID": "معرف التتبع",
    "Track Steps": "تتبع الخطوات",
    "Transition Tasks": "مهام الانتقال",
    "Trigger caching": "تشغيل التخزين المؤقت",
    "Trim Table": "تقليم الجدول",
    "Try a Naming Series": "جرّب سلسلة التسمية",
    "UI Tour": "جولة الواجهة",
    "Uncaught Exception": "استثناء غير مُعالَج",
    "Unhandled Emails": "رسائل بريد غير معالجة",
    "Unsafe SQL query": "استعلام SQL غير آمن",
    "Unsubscribe Params": "معاملات إلغاء الاشتراك",
    "Unsupported {0}: {1}": "غير مدعوم {0}: {1}",
    "Upgrade plan": "خطة الترقية",
    "Used OAuth": "OAuth المستخدم",
    "User Details": "تفاصيل المستخدم",
    "User Id Field": "حقل معرف المستخدم",
    "User Invitation": "دعوة المستخدم",
    "User Role": "دور المستخدم",
    "User Role Profile": "ملف تعريف دور المستخدم",
    "User Session Display": "عرض جلسة المستخدم",
    "User Type Module": "وحدة نوع المستخدم",
    "User does not exist.": "المستخدم غير موجود.",
    "User is disabled": "المستخدم معطّل",
    "User {0} is disabled": "المستخدم {0} معطّل",
    "Utilization %": "نسبة الاستغلال %",
    "Value Change": "تغيّر القيمة",
    "Values Changed": "القيم المتغيّرة",
    "Visit Desktop": "زيارة سطح المكتب",
    "Visitor ID": "معرف الزائر",
    "Webhook Request Log": "سجل طلبات Webhook",
    "Webhook Secret": "سر Webhook",
    "Webhook Trigger": "مشغّل Webhook",
    "Webhook URL": "رابط Webhook",
    "Website Manager": "مدير الموقع",
    "Website Script": "سكربت الموقع",
    "Website Theme": "سمة الموقع",
    "Website Visits": "زيارات الموقع",
    "Welcome URL": "رابط الترحيب",
    "Welcome to {0}": "مرحبًا بك في {0}",
    "Worker Information": "معلومات العامل",
    "Worker Name": "اسم العامل",
    "Workflow Builder ID": "معرف منشئ مسار العمل",
    "Workflow Data": "بيانات مسار العمل",
    "Workflow Task": "مهمة مسار العمل",
    "Wrapping up": "جارٍ الإنهاء",
    "'{0}' is not a valid IBAN": "'{0}' ليس رقم IBAN صالحًا",
    "'{0}' is not a valid URL": "'{0}' ليس رابط URL صالحًا",
    "1 day ago": "منذ يوم واحد",
    "1 second ago": "منذ ثانية واحدة",
    "2 hours ago": "منذ ساعتين",
    "2 months ago": "منذ شهرين",
    "2 weeks ago": "منذ أسبوعين",
}


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 270, f"expected 270 scope rows, got {len(scope_rows)}"

    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {diff}"

    for s, ar in A.items():
        src_ph = sorted(re.findall(r"\{[0-9]*\}", s))
        ar_ph = sorted(re.findall(r"\{[0-9]*\}", ar))
        assert src_ph == ar_ph, f"placeholder mismatch on '{s}': {src_ph} != {ar_ph}"
        assert ar != s, f"source-equal released: '{s}'"

    preserved_srcs = [s for s in scope_rows if s in PRESERVED]
    tech_srcs = [s for s in scope_rows if s in TECHNICAL]
    payload_srcs = [s for s in scope_rows if s in A]

    assert len(preserved_srcs) == 1, f"expected 1 preserved, got {len(preserved_srcs)}"
    assert len(tech_srcs) == 17, f"expected 17 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 252, f"expected 252 payload, got {len(payload_srcs)}"

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
                        f"stage6-W6-0b batch-5 owner-approved {DATE}",
                    ]
                )
            elif s in TECHNICAL:
                w.writerow(
                    [
                        s,
                        "EXCEPTION-technical",
                        "EXCEPTION-technical (keep vendor rendering; no translation)",
                        f"stage6-W6-0b batch-5 owner-approved {DATE}",
                    ]
                )
            else:
                w.writerow(
                    [
                        s,
                        A[s],
                        "quorum-confirmed (release payload row)",
                        f"stage6-W6-0b batch-5 owner-approved {DATE}",
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
    assert after - before == 252
    assert after == before + 252


if __name__ == "__main__":
    main()
