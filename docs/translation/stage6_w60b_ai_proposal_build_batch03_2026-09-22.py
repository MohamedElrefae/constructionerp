#!/usr/bin/env python3
"""W6-0b batch-3 AI proposal build + payload append + quorum paper trail.

Owner-approved scope: stage6_w60b_batch03_rows_2026-09-22.csv (271 rows).
Site-override reconciliation (plan §12): 1 row preserved, not imported.
Technical exceptions: 12 source-equal rows, not imported.
Payload: 258 Released rows appended to approved_ar_overrides.csv.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w60b_batch03_rows_2026-09-22.csv"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w60b_payload_applied_rows_batch03_2026-09-22.csv"

DATE = "2026-09-22"
DECISION_REF = f"content:docs/translation/stage6_w60b_payload_applied_rows_batch03_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger arabic_coverage_gap_report_2026-08-22.csv; plan D5; W6-0b batch-3"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed "
    "(W6-0b batch-3; owner-approved 271-row scope minus site-override preserves "
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
    "Module (for export)": "الوحدة (للتصدير)",
}

# EXCEPTION-technical: source==translation format/identifier tokens; not imported
TECHNICAL = {
    "OR",
    "UUID",
    "nonce",
    "on_submit",
    "CMD",
    "Config",
    "Arial",
    "Re:",
    "Timeout",
    "Package",
    "jane@example.com",
    "Preview:",
}

# Full AI proposals for Released rows (glossary v2.0 + Egyptian professional Arabic)
A = {
    "Map columns from {0} to fields in {1}": "تعيين الأعمدة من {0} إلى الحقول في {1}",
    "Move cursor to above row": "تحريك المؤشر إلى الصف السابق",
    "Move cursor to below row": "تحريك المؤشر إلى الصف التالي",
    "Move cursor to next column": "تحريك المؤشر إلى العمود التالي",
    "Move cursor to previous column": "تحريك المؤشر إلى العمود السابق",
    "Move sections to new tab": "نقل الأقسام إلى علامة تبويب جديدة",
    "Navigate to main content": "الانتقال إلى المحتوى الرئيسي",
    "No Email Accounts Assigned": "لا توجد حسابات بريد إلكتروني معينة",
    "No address added yet.": "لم يُضف أي عنوان بعد.",
    "No contacts added yet.": "لم تُضف أي جهات اتصال بعد.",
    "Notifications Disabled": "تم تعطيل الإشعارات",
    "Onboard": "التهيئة",
    "Optimize": "تحسين",
    "Orange": "برتقالي",
    "Overview": "نظرة عامة",
    "Page height and width cannot be zero": "لا يمكن أن يكون ارتفاع الصفحة وعرضها صفرًا",
    "Password missing in Email Account": "كلمة المرور مفقودة في حساب البريد الإلكتروني",
    "Pink": "وردي",
    "Please select X and Y fields": "يرجى تحديد حقلي X و Y",
    "Please select a file first.": "يرجى تحديد ملف أولاً.",
    "Priority": "الأولوية",
    "Quoting must be between 0 and 3": "يجب أن تكون علامات التنصيص بين 0 و 3",
    "Random": "عشوائي",
    "Raw Printing Settings": "إعدادات الطباعة المباشرة",
    "Received": "مُستلَم",
    "Recents": "الأخيرة",
    "Red": "أحمر",
    "Refreshing": "جارٍ التحديث",
    "Replied": "تم الرد",
    "Select Fields (Up to {0})": "تحديد الحقول (حتى {0})",
    "Select a group {0} first.": "يرجى تحديد المجموعة {0} أولاً.",
    "Select records for removing assignment": "تحديد السجلات لإلغاء التعيين",
    "Select two versions to view the diff.": "حدد نسختين لعرض الفروق.",
    "Sending": "جارٍ الإرسال",
    "Showing only first {0} rows out of {1}": "عرض أول {0} صفوف فقط من أصل {1}",
    "Templates": "القوالب",
    "There are no upcoming events for you.": "لا توجد فعاليات قادمة لك.",
    "Totals": "الإجماليات",
    "Transition Properties": "خصائص الانتقال",
    "Unpublish": "إلغاء النشر",
    "Valid Login id required.": "مطلوب معرف تسجيل دخول صالح.",
    "Verification": "التحقق",
    "Visible to website/portal users.": "مرئي لمستخدمي الموقع/البوابة.",
    "Workflow updated successfully": "تم تحديث مسار العمل بنجاح",
    "Yellow": "أصفر",
    "You added 1 row to {0}": "أضفت صفًا واحدًا إلى {0}",
    "You added {0} rows to {1}": "أضفت {0} صفوف إلى {1}",
    "You cancelled this document": "قمت بإلغاء هذا المستند",
    "You cancelled this document {1}": "قمت بإلغاء هذا المستند {1}",
    "You changed the value of {0}": "قمت بتغيير قيمة {0}",
    "You changed the value of {0} {1}": "قمت بتغيير قيمة {0} {1}",
    "You changed the values for {0}": "قمت بتغيير القيم لـ {0}",
    "You changed the values for {0} {1}": "قمت بتغيير القيم لـ {0} {1}",
    "You changed {0} to {1}": "قمت بتغيير {0} إلى {1}",
    "You created this document {0}": "أنشأت هذا المستند {0}",
    "You haven't created a {0} yet": "لم تقم بإنشاء {0} بعد",
    "You must add atleast one link.": "يجب إضافة رابط واحد على الأقل.",
    "You need to create these first:": "يجب عليك إنشاء هذه أولاً:",
    "You removed 1 row from {0}": "حذفت صفًا واحدًا من {0}",
    "You removed attachment {0}": "حذفت المرفق {0}",
    "You removed {0} rows from {1}": "حذفت {0} صفوف من {1}",
    "You submitted this document": "قمت بترحيل هذا المستند",
    "You submitted this document {0}": "قمت بترحيل هذا المستند {0}",
    "You will be redirected to:": "سيتم إعادة توجيهك إلى:",
    "Your PDF is ready for download": "ملف PDF الخاص بك جاهز للتنزيل",
    "Your form has been successfully updated": "تم تحديث النموذج بنجاح",
    "[Action taken by {0}]": "[إجراء متخذ بواسطة {0}]",
    "by Role": "حسب الدور",
    "commented": "علّق",
    "to close": "للإغلاق",
    "to navigate": "للتنقل",
    "to select": "للتحديد",
    "updated to {0}": "تم التحديث إلى {0}",
    "use % as wildcard": "استخدم % كرمز بديل",
    "{0} Liked": "أُعجب {0}",
    "{0} Map": "خريطة {0}",
    "{0} Reports": "تقارير {0}",
    "{0} added 1 row to {1}": "أضاف {0} صفًا واحدًا إلى {1}",
    "{0} added {1} rows to {2}": "أضاف {0} {1} صفوف إلى {2}",
    "{0} attached {1}": "أرفق {0} {1}",
    "{0} cancelled this document": "ألغى {0} هذا المستند",
    "{0} cancelled this document {1}": "ألغى {0} هذا المستند {1}",
    "{0} changed the value of {1}": "غيّر {0} قيمة {1}",
    "{0} changed the value of {1} {2}": "غيّر {0} قيمة {1} {2}",
    "{0} changed the values for {1}": "غيّر {0} القيم لـ {1}",
    "{0} changed the values for {1} {2}": "غيّر {0} القيم لـ {1} {2}",
    "{0} changed {1} to {2}": "غيّر {0} {1} إلى {2}",
    "{0} created this": "أنشأ {0} هذا",
    "{0} created this document {1}": "أنشأ {0} هذا المستند {1}",
    "{0} from {1} to {2}": "{0} من {1} إلى {2}",
    "{0} from {1} to {2} in row #{3}": "{0} من {1} إلى {2} في الصف #{3}",
    "{0} is equal to {1}": "{0} يساوي {1}",
    "{0} is like {1}": "{0} يشبه {1}",
    "{0} is not like {1}": "{0} لا يشبه {1}",
    "{0} last edited this": "آخر من عدّل هذا {0}",
    "{0} records are retained for {1} days.": "يتم الاحتفاظ بـ {0} سجلات لمدة {1} يومًا.",
    "{0} removed 1 row from {1}": "حذف {0} صفًا واحدًا من {1}",
    "{0} removed attachment {1}": "حذف {0} المرفق {1}",
    "{0} removed {1} rows from {2}": "حذف {0} {1} صفوف من {2}",
    "{0} rows from {1}": "{0} صفوف من {1}",
    "{0} rows to {1}": "{0} صفوف إلى {1}",
    "{0} submitted this document": "رحّل {0} هذا المستند",
    "{0} submitted this document {1}": "رحّل {0} هذا المستند {1}",
    "{0} viewed this": "عرض {0} هذا",
    "{1} saved": "تم حفظ {1}",
    "← Back to upload files": "← العودة إلى تحميل الملفات",
    "Confirm Password": "تأكيد كلمة المرور",
    "Accept Invitation": "قبول الدعوة",
    "Accounts Manager": "مدير الحسابات",
    "Accounts User": "مستخدم الحسابات",
    "Built on {0}": "مبني على {0}",
    "Dear System Manager,": "عزيزي مدير النظام،",
    "Discussion Topic": "موضوع النقاش",
    "Domain Settings": "إعدادات النطاق",
    "Get PDF": "الحصول على PDF",
    "Hide Error": "إخفاء الخطأ",
    "Instructions Emailed": "تم إرسال التعليمات عبر البريد الإلكتروني",
    "Jane Doe": "فلان الفلاني",
    "Log In To {0}": "تسجيل الدخول إلى {0}",
    "Login to {0}": "تسجيل الدخول إلى {0}",
    "Login token required": "رمز تسجيل الدخول مطلوب",
    "Login with {0}": "تسجيل الدخول بواسطة {0}",
    "Message Sent": "تم إرسال الرسالة",
    "More Info": "مزيد من المعلومات",
    "Password is valid. 👍": "كلمة المرور صالحة. 👍",
    "Password set": "تم تعيين كلمة المرور",
    "Public Files Backup:": "نسخة احتياطية للملفات العامة:",
    "Type title": "اكتب العنوان",
    "Verification Code": "رمز التحقق",
    "Want to discuss?": "هل تريد النقاش؟",
    "Workflow Action": "إجراء مسار العمل",
    "Attribution": "الإسناد",
    "Authentication Apps you can use are:": "تطبيقات المصادقة التي يمكنك استخدامها هي:",
    "Authorization error for {}.": "خطأ تفويض لـ {}.",
    "Authors": "المؤلفون",
    "Authors / Maintainers": "المؤلفون / مسؤولو الصيانة",
    "Click below to get started:": "انقر أدناه للبدء:",
    "Click on the button to log in to {0}": "انقر على الزر لتسجيل الدخول إلى {0}",
    "Cmd+Enter to add comment": "Cmd+Enter لإضافة تعليق",
    "Dear": "عزيزي",
    "Enter Code displayed in OTP App.": "أدخل الرمز المعروض في تطبيق كلمة المرور لمرة واحدة (OTP).",
    "Hello": "مرحبًا",
    "Invalid Login. Try again.": "تسجيل دخول غير صالح. أعد المحاولة.",
    "Login link sent to your email": "تم إرسال رابط تسجيل الدخول إلى بريدك الإلكتروني",
    "Login to start a new discussion": "سجّل الدخول لبدء نقاش جديد",
    "Login with Frappe Cloud": "تسجيل الدخول باستخدام Frappe Cloud",
    "Manage 3rd party apps": "إدارة تطبيقات الطرف الثالث",
    "Oops! Something went wrong.": "عفوًا! حدث خطأ ما.",
    "Partial": "جزئي",
    "Passwords do not match": "كلمتا المرور غير متطابقتين",
    "Please enter a valid email address.": "يرجى إدخال عنوان بريد إلكتروني صالح.",
    "Please enter your new password.": "يرجى إدخال كلمة المرور الجديدة.",
    "Please enter your old password.": "يرجى إدخال كلمة المرور القديمة.",
    "Portal": "البوابة",
    "Private Files Backup:": "نسخة احتياطية للملفات الخاصة:",
    "Something went wrong.": "حدث خطأ ما.",
    "Start a new discussion": "بدء نقاش جديد",
    "Thank you for your message": "شكرًا لرسالتك",
    "Thanks": "شكرًا",
    "The link will expire in {0} minutes": "ستنتهي صلاحية الرابط خلال {0} دقائق",
    "Type your reply here...": "اكتب ردك هنا...",
    "Valid email and name required": "مطلوب اسم وبريد إلكتروني صالحان",
    "Verifying...": "جارٍ التحقق...",
    "You can also copy-paste this": "يمكنك أيضًا نسخ ولصق هذا",
    "You have a new message from:": "لديك رسالة جديدة من:",
    "You've been invited to join {0}.": "لقد تمت دعوتك للانضمام إلى {0}.",
    "Your invitation to join {0} has expired.": "انتهت صلاحية دعوتك للانضمام إلى {0}.",
    "Your old password is incorrect.": "كلمة المرور القديمة غير صحيحة.",
    "Your verification code is {0}": "رمز التحقق الخاص بك هو {0}",
    "to your browser": "إلى متصفحك",
    "After Discard": "بعد الإهمال",
    "Allow delete": "السماح بالحذف",
    "Allow editing after submit": "السماح بالتعديل بعد الترحيل",
    "Amend Counter": "عداد التعديل",
    "Before Discard": "قبل الإهمال",
    "Cannot delete standard document state.": "لا يمكن حذف حالة المستند القياسية.",
    "Confirm Access": "تأكيد الوصول",
    "Confirm Deletion of Account": "تأكيد حذف الحساب",
    "Default Workspace": "مساحة العمل الافتراضية",
    "Disable Change Log Notification": "تعطيل إشعار سجل التغييرات",
    "Enable Push Notification Relay": "تمكين ترحيل الإشعارات الفورية",
    "Failed to delete {0} documents: {1}": "فشل حذف {0} مستندات: {1}",
    "Failed to export python type hints": "فشل تصدير تلميحات أنواع Python",
    "Failed to generate preview of series": "فشل إنشاء معاينة السلسلة",
    "Failed to send notification email": "فشل إرسال بريد الإشعار الإلكتروني",
    "Go to Workspace": "الانتقال إلى مساحة العمل",
    "Indexing refresh token": "جارٍ فهرسة رمز التحديث",
    "Invalid simple filter format: {0}": "تنسيق عامل التصفية البسيط غير صالح: {0}",
    "LDAP search path for Groups": "مسار بحث LDAP للمجموعات",
    "LDAP search path for Users": "مسار بحث LDAP للمستخدمين",
    "Loading import file...": "جارٍ تحميل ملف الاستيراد...",
    "Modal Trigger": "مُشغّل النافذة المنبثقة",
    "No Preview": "لا توجد معاينة",
    "No Preview Available": "لا تتوفر معاينة",
    "Notification Summary": "ملخص الإشعارات",
    "Please use a valid LDAP search filter": "يرجى استخدام عامل تصفية بحث LDAP صالح",
    "Popover or Modal Description": "وصف النافذة المنبثقة أو المشروحة",
    "Preview of generated names": "معاينة الأسماء المُنشأة",
    "Select Workspace": "تحديد مساحة العمل",
    "Show sidebar": "إظهار الشريط الجانبي",
    "Welcome Workspace": "مساحة عمل الترحيب",
    "Workspace Chart": "رسم بياني لمساحة العمل",
    "Workspace Custom Block": "كتلة مخصصة لمساحة العمل",
    "Workspace Manager": "مدير مساحة العمل",
    "Workspace Number Card": "بطاقة أرقام مساحة العمل",
    "Workspace Settings": "إعدادات مساحة العمل",
    "Workspace Setup Completed": "اكتمل إعداد مساحة العمل",
    "Workspace Shortcut": "اختصار مساحة العمل",
    "Workspace Visibility": "ظهور مساحة العمل",
    "API Keys": "مفاتيح واجهة برمجة التطبيقات (API)",
    "API Logging": "تسجيل واجهة برمجة التطبيقات (API)",
    "API Request Log": "سجل طلبات واجهة برمجة التطبيقات (API)",
    "About Us Settings": "إعدادات من نحن",
    "Accepted At": "قُبل في",
    "Action Label": "تسمية الإجراء",
    "Active Directory": "دليل Active Directory",
    "Address Line 1": "سطر العنوان 1",
    "Address Line 2": "سطر العنوان 2",
    "After Insert": "بعد الإدراج",
    "Allow Bulk Editing": "السماح بالتحرير الجماعي",
    "Allow comments": "السماح بالتعليقات",
    "Allow print": "السماح بالطباعة",
    "Allowed Modules": "الوحدات المسموح بها",
    "Allowed Roles": "الأدوار المسموح بها",
    "Alternative Email ID": "معرف البريد الإلكتروني البديل",
    "Always BCC Address": "عنوان النسخة المخفية (BCC) دائمًا",
    "Amended Documents": "المستندات المُعدَّلة",
    "Amended From": "مُعدَّل من",
    "Announcement Widget": "عنصر واجهة الإعلانات",
    "Anonymization Matrix": "مصفوفة إخفاء الهوية",
    "Anonymous responses": "ردود مجهولة المصدر",
    "App ID": "معرف التطبيق",
    "App Logo": "شعار التطبيق",
    "Applicable For": "ينطبق على",
    "Applies To (DocType)": "ينطبق على (DocType)",
    "Apply To": "تطبيق على",
    "Attachment Settings": "إعدادات المرفقات",
    "Audit System Hooks": "خطافات نظام التدقيق",
    "Audit Trail": "مسار التدقيق",
    "Authorization URI": "معرف URI للتفويض",
    "Authorize API Access": "تفويض الوصول إلى واجهة برمجة التطبيقات (API)",
    "Auto Repeat Day": "يوم التكرار التلقائي",
    "Auto Repeat Schedule": "جدول التكرار التلقائي",
    "Auto Repeat User": "مستخدم التكرار التلقائي",
    "Backups (MB)": "النسخ الاحتياطية (ميجابايت)",
    "Bad Cron Expression": "تعبير Cron غير صالح",
    "Based On": "بناءً على",
    "Basic Info": "المعلومات الأساسية",
    "Before Validate": "قبل التحقق",
    "Binary Logging": "التسجيل الثنائي",
    "Bufferpool Size": "حجم تجمع التخزين المؤقت (Bufferpool)",
    "Build {0}": "بناء {0}",
    "Button Color": "لون الزر",
    "Cannot Fetch Values": "تعذر جلب القيم",
    "Card Break": "فاصل البطاقات",
    "Changed at": "تغير في",
    "Changed by": "تغير بواسطة",
    "Changelog Feed": "موجز سجل التغييرات",
}


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 271, f"expected 271 scope rows, got {len(scope_rows)}"

    # verify completeness of classifications
    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {diff}"

    # placeholder parity on all released proposals
    for s, ar in A.items():
        src_ph = sorted(re.findall(r"\{[0-9]*\}", s))
        ar_ph = sorted(re.findall(r"\{[0-9]*\}", ar))
        assert src_ph == ar_ph, f"placeholder mismatch on '{s}': {src_ph} != {ar_ph}"

    preserved_srcs = [s for s in scope_rows if s in PRESERVED]
    tech_srcs = [s for s in scope_rows if s in TECHNICAL]
    payload_srcs = [s for s in scope_rows if s in A]

    assert len(preserved_srcs) == 1, f"expected 1 preserved, got {len(preserved_srcs)}"
    assert len(tech_srcs) == 12, f"expected 12 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 258, f"expected 258 payload, got {len(payload_srcs)}"

    # write payload CSV (all 271 rows, tab-separated)
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
                        f"stage6-W6-0b batch-3 owner-approved {DATE}",
                    ]
                )
            elif s in TECHNICAL:
                w.writerow(
                    [
                        s,
                        "EXCEPTION-technical",
                        "EXCEPTION-technical (keep vendor rendering; no translation)",
                        f"stage6-W6-0b batch-3 owner-approved {DATE}",
                    ]
                )
            else:
                w.writerow(
                    [
                        s,
                        A[s],
                        "quorum-confirmed (release payload row)",
                        f"stage6-W6-0b batch-3 owner-approved {DATE}",
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
    assert after - before == 258
    assert after == before + 258


if __name__ == "__main__":
    main()
