"""W6-0b batch-7 corrected governed proposal build (2026-09-22).

Supersedes the stub that shipped 270 empty translations (commit 8bfc23a,
rejected by owner). Full AI-authored Arabic proposals for all Released rows;
29 EXCEPTION-technical dispositions row-by-row; zero Site-Override preserves
(authoritative recon: no ct_origin='Site Override' rows among batch-7 keys).

Outputs (all fail-closed, deterministic):
  - stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv  (270 dispositions, tab-sep)
  - construction/data/translations/approved_ar_overrides.csv (Pending->Released in place;
    EXCEPTION-technical rows removed)  2219 -> 2190, all Released
  - stage6_w60b_batch07_released_list.txt                    (241)
  - stage6_w60b_batch07_site_recon_2026-09-22.json           (authoritative)
"""

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w60b_batch07_rows_2026-09-22.csv"
PAYLOAD = HERE / "stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv"
RELEASED_LIST = HERE / "stage6_w60b_batch07_released_list.txt"
SITE_RECON = HERE / "stage6_w60b_batch07_site_recon_2026-09-22.json"
APPROVED = HERE.parent.parent / "construction/data/translations/approved_ar_overrides.csv"

DATE = "2026-09-22"
DECISION_REF = f"content:docs/translation/stage6_w60b_payload_applied_rows_batch07_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger arabic_coverage_gap_report_2026-08-22.csv; plan D5; W6-0b batch-7"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed (W6-0b batch-7; "
    "owner-approved 270-row scope minus EXCEPTION-technical rows)"
)
RELEASE_VERSION = "1.4"
REVIEWERS = (
    "AI-A1 (recorded review run)",
    "AI-A2 (recorded review run)",
    "AI-A3 (recorded review run)",
)
TS = "2026-09-22 00:00:00"
DOMAIN = "desk-short-ui"
GOVERNANCE_REF = f"stage6-W6-0b batch-7 owner-approved {DATE}"

# Site-override preserved (not imported) — empty: authoritative recon found zero
# ct_origin='Site Override' rows among the 270 batch-7 keys (20367 runtime rows).
PRESERVED = {}

# EXCEPTION-technical: format/identifier/brand/protocol tokens; keep vendor
# rendering; not Released; not imported (29).
TECHNICAL = {
    "OAuth",
    "OpenLDAP",
    "PATCH",
    "PUT",
    "PID",
    "Outlook.com",
    "Sendgrid",
    "SparkPost",
    "Yandex.Mail",
    "UIDNEXT",
    "UIDVALIDITY",
    "processlist",
    "s256",
    "vim",
    "emacs",
    "login_required",
    "on_cancel",
    "on_trash",
    "on_update",
    "on_update_after_submit",
    "workflow_transition",
    "version_table",
    "fairlogin",
    "wkhtmltopdf",
    "macOS Launchpad",
    "Webhook",
    "Websocket",
    "XLSX",
    "Read Only Depends On (JS)",
}

# Full AI proposals for the 241 Released rows (glossary v2.0 + Egyptian
# professional Arabic). Placeholder parity and ar != source enforced below.
A = {
    "Non-Conforming": "غير مطابق",
    "Not Allowed: Disabled User": "غير مسموح: مستخدم معطّل",
    "Not Permitted to read {0}": "غير مسموح بقراءة {0}",
    "Note: This will be shared with user.": "ملاحظة: ستتم مشاركته مع المستخدم.",
    "Number of onsite backups": "عدد النسخ الاحتياطية المحلية",
    "OTP Secret Reset - {0}": "إعادة تعيين سر OTP - {0}",
    "Occurrences": "التكرارات",
    "Official Documentation": "التوثيق الرسمي",
    "Offset must be a non-negative integer": "يجب أن تكون الإزاحة عددًا صحيحًا غير سالب",
    "Old and new fieldnames are same.": "اسم الحقل القديم والجديد متطابقان.",
    "Oldest Unscheduled Job": "أقدم مهمة غير مجدولة",
    "Only draft documents can be discarded": "يمكن إهمال المستندات المسودات فقط",
    "Order By must be a string": "يجب أن يكون Order By نصًا",
    "Outgoing": "صادر",
    "Outgoing (SMTP) Settings": "إعدادات الصادر (SMTP)",
    "Outgoing Emails (Last 7 days)": "رسائل البريد الصادرة (آخر 7 أيام)",
    "PDF Generation in Progress": "جارٍ إنشاء PDF",
    "PDF Page Height (in mm)": "ارتفاع صفحة PDF (بالمم)",
    "PDF Page Width (in mm)": "عرض صفحة PDF (بالمم)",
    "PDF generation may not work as expected.": "قد لا يعمل إنشاء PDF كما هو متوقع.",
    "Packages": "الحزم",
    "Page to show on the website": "الصفحة المعروضة في الموقع",
    "Parameter": "المعامل",
    "Parent Element Selector": "محدد العنصر الأب",
    "Parentfield not specified in {0}: {1}": "لم يُحدد الحقل الأب في {0}: {1}",
    "Pass": "نجاح",
    "Password not found for {0} {1} {2}": "لم يتم العثور على كلمة مرور لـ {0} {1} {2}",
    "Password requirements not met": "لم تتحقق متطلبات كلمة المرور",
    "Patch type {} not found in patches.txt": "نوع التصحيح {} غير موجود في patches.txt",
    "Path {0} is not within module {1}": "المسار {0} ليس ضمن الوحدة {1}",
    "Path {0} it not a valid path": "المسار {0} ليس مسارًا صالحًا",
    "Personal Data Deletion Step": "خطوة حذف البيانات الشخصية",
    "Please attach the package": "يرجى إرفاق الحزمة",
    "Please enable {} before continuing.": "يرجى تفعيل {} قبل المتابعة.",
    "Please enter OpenID Configuration URL": "يرجى إدخال رابط تهيئة OpenID",
    "Please login to post a comment.": "يرجى تسجيل الدخول لنشر تعليق.",
    "Please set the document name": "يرجى تعيين اسم المستند",
    "Please specify the minutes offset": "يرجى تحديد إزاحة الدقائق",
    "Please update {} before continuing.": "يرجى تحديث {} قبل المتابعة.",
    "Polling": "الاستطلاع",
    "Prepared report render failed": "فشل عرض التقرير المُعد",
    "Printer mapping not set.": "تعيين الطابعة غير مضبوط.",
    "Proceed": "متابعة",
    "Prof": "الأستاذ",
    "Profile": "الملف الشخصي",
    "Protect Attached Files": "حماية الملفات المرفقة",
    "Purchase Master Manager": "مدير ماستر المشتريات",
    "Purple": "بنفسجي",
    "Queue": "الطابور",
    "Queue in Background (BETA)": "الطابور في الخلفية (تجريبي)",
    "Queue(s)": "طابور (طوابور)",
    "Queues": "الطوابور",
    "Queuing {0} for Submission": "جارٍ إضافة {0} إلى طابور الإرسال",
    "Quick Help for Setting Permissions": "مساعدة سريعة لضبط الأذونات",
    "Range": "النطاق",
    "Rate limit for email link login": "حد المعدل لتسجيل الدخول برابط البريد",
    "Read the documentation to know more": "اقرأ التوثيق لمعرفة المزيد",
    "Readme": "ملف README",
    "Reason": "السبب",
    "Received an invalid token type.": "تم استلام نوع رمز غير صالح.",
    "Recipient Account Field": "حقل حساب المستلم",
    "Recorder Suggested Index": "الفهرس المقترح من مسجل الاستعلامات",
    "Redirect to the selected app after login": "إعادة التوجيه إلى التطبيق المحدد بعد تسجيل الدخول",
    "Redirects": "إعادة التوجيه",
    "Reference Document Name": "اسم مستند المرجع",
    "Relay Server URL missing": "رابط خادم الترحيل مفقود",
    "Release": "الإصدار",
    "Reminder": "التذكير",
    "Reminder cannot be created in past.": "لا يمكن إنشاء تذكير في الماضي.",
    "Removed": "تمت الإزالة",
    "Reopen": "إعادة الفتح",
    "Repeat Header and Footer": "تكرار الترويسة والتذييل",
    "Replicate": "استنساخ",
    "Replicating...": "جارٍ الاستنساخ...",
    "Replication completed.": "اكتمل الاستنساخ.",
    "Represents a User in the system.": "يمثل مستخدمًا في النظام.",
    "Request for Account Deletion": "طلب حذف الحساب",
    "Reset All Customizations": "إعادة تعيين كل التخصيصات",
    "Reset Password Template": "قالب إعادة تعيين كلمة المرور",
    "Resource": "المورد",
    "Resource Documentation": "توثيق الموارد",
    'Route: Example \\"/app\\"': 'المسار: مثال \\"/app\\"',
    "Row #{}: Fieldname is required": "صف #{}: اسم الحقل مطلوب",
    "Rules": "القواعد",
    "SMS sent successfully": "تم إرسال الرسالة النصية بنجاح",
    "SMTP Server is required": "خادم SMTP مطلوب",
    "Saving Customization...": "جارٍ حفظ التخصيص...",
    "Schedule": "الجدولة",
    "Scheduler": "المجدول",
    "Scope": "النطاق",
    "Script to attach to all web pages.": "سكربت للإرفاق على جميع صفحات الويب.",
    "Scripting": "البرمجة النصية",
    "Scripts": "السكربتات",
    "See previous responses": "عرض الردود السابقة",
    "Select Network Printer": "تحديد الطابعة الشبكية",
    "Send Email To Creator": "إرسال بريد إلى المنشئ",
    "Sender": "المرسل",
    "Series Updated for {}": "تم تحديث السلسلة لـ {}",
    "Service": "الخدمة",
    "Session Expiry (idle timeout)": "انتهاء الجلسة (مهلة الخمول)",
    "Sessions": "الجلسات",
    "Settings for Contact Us Page": "إعدادات صفحة اتصل بنا",
    "Settings for the About Us Page": "إعدادات صفحة من نحن",
    "Setup > Customize Form": "الإعدادات > تخصيص النموذج",
    "Setup > User Permissions": "الإعدادات > أذونات المستخدم",
    "Setup Series for transactions": "إعداد سلسلة التسمية للمعاملات",
    "Show Absolute Datetime in Timeline": "عرض التاريخ والوقت المطلق في الخط الزمني",
    "Show App Icons As Folder": "إظهار أيقونات التطبيقات كمجلد",
    "Show Auth Server Metadata": "إظهار البيانات الوصفية لخادم المصادقة",
    "Show First Document Tour": "إظهار جولة المستند الأولى",
    "Show Only Failed Logs": "إظهار سجلات الفشل فقط",
    "Show Protected Resource Metadata": "إظهار البيانات الوصفية للمورد المحمي",
    "Show Values over Chart": "إظهار القيم فوق الرسم البياني",
    "Show in Resource Metadata": "إظهار في البيانات الوصفية للمورد",
    "Show link to document": "إظهار رابط المستند",
    "Sign Up and Confirmation": "التسجيل والتأكيد",
    "Skipped": "تم التخطي",
    "Skipping {0} of {1}, {2}": "تخطي {0} من {1}، {2}",
    "Slideshow like display for the website": "عرض شرائح متحرك للموقع",
    "Slug": "الرابط اللطيف",
    "Snippet and more variables:  {0}": "مقتطف ومزيد من المتغيرات: {0}",
    "SocketIO Transport Mode": "وضع انتقال SocketIO",
    "Spawns actions in a background job": "يشغّل إجراءات في مهمة خلفية",
    "Standard DocType can not be deleted.": "لا يمكن حذف نوع المستند القياسي.",
    "Standard Reports cannot be deleted": "لا يمكن حذف التقارير القياسية",
    "Standard Reports cannot be edited": "لا يمكن تحرير التقارير القياسية",
    "Standard rich text editor with controls": "محرر نصوص منسقة قياسي مع أدوات تحكم",
    "State": "الحالة",
    "Statistics": "الإحصائيات",
    "Stop": "إيقاف",
    "Storage Usage By Table": "استخدام التخزين حسب الجدول",
    "Store Attached PDF Document": "تخزين المستند PDF المرفق",
    "Strip EXIF tags from uploaded images": "إزالة وسوم EXIF من الصور المرفوعة",
    "Subtle": "ناعم",
    "Successfully imported {0}": "تم استيراد {0} بنجاح",
    "Successfully signed out": "تم تسجيل الخروج بنجاح",
    "Successfully updated {0}": "تم تحديث {0} بنجاح",
    "Suggest Optimizations": "اقتراح التحسينات",
    "Sync events from Google as public": "مزامنة الأحداث من Google كعامة",
    "System Manager privileges required.": "مطلوب صلاحيات مدير النظام.",
    "Table Fieldname Missing": "اسم حقل الجدول مفقود",
    "Target": "الهدف",
    "Team Members Subtitle": "عنوان فرعي لأعضاء الفريق",
    "Telemetry": "التلمتري",
    "The Condition '{0}' is invalid": "الشرط '{0}' غير صالح",
    "The File URL you've entered is incorrect": "رابط الملف الذي أدخلته غير صحيح",
    "The changes have been reverted.": "تم التراجع عن التغييرات.",
    "The country's ISO 3166 ALPHA-2 code.": "الدولة بنظام ISO 3166 ALPHA-2.",
    "The field {0} is mandatory": "الحقل {0} إلزامي",
    "The reset password link has been expired": "انتهت صلاحية رابط إعادة تعيين كلمة المرور",
    "The role {0} should be a custom role.": "يجب أن يكون الدور {0} دورًا مخصصًا.",
    "The selected document {0} is not a {1}.": "المستند المحدد {0} ليس {1}.",
    'There is no task called \\"{}\\"': 'لا توجد مهمة باسم \\"{}\\"',
    "Time Window (Seconds)": "نافذة الوقت (ثوانٍ)",
    "Timeline": "الخط الزمني",
    "Tip: Try the new dropdown console using": "نصيحة: جرّب وحدة التحكم المنسدلة الجديدة باستخدام",
    "To enable server scripts, read the {0}.": "لتفعيل سكربتات الخادم، اقرأ {0}.",
    "To generate password click {0}": "لتوليد كلمة المرور انقر {0}",
    "To know more click {0}": "لمعرفة المزيد انقر {0}",
    "Token Endpoint Auth Method": "طريقة مصادقة نقطة نهاية الرمز",
    "Total Background Workers": "إجمالي عمّال الخلفية",
    "Total Errors (last 1 day)": "إجمالي الأخطاء (آخر يوم واحد)",
    "Total Outgoing Emails": "إجمالي رسائل البريد الصادرة",
    "Traceback": "التتبع",
    "Track milestones for any document": "تتبع المحطات لأي مستند",
    "Transgender": "متحول جندري",
    "Translator": "المترجم",
    "URL must start with http:// or https://": "يجب أن يبدأ الرابط بـ http:// أو https://",
    "Un-following document {0}": "إلغاء متابعة المستند {0}",
    "Unknown Rounding Method: {}": "طريقة تقريب غير معروفة: {}",
    "Unknown file encoding. Tried to use: {0}": "ترميز ملف غير معروف. تم المحاولة باستخدام: {0}",
    "Unlock Reference Document": "فتح قفل مستند المرجع",
    "Unsupported function or operator: {0}": "دالة أو عامل غير مدعوم: {0}",
    "Updating global settings": "جارٍ تحديث الإعدادات العامة",
    "Updating naming series options": "جارٍ تحديث خيارات سلسلة التسمية",
    "Updating {0} of {1}, {2}": "جارٍ تحديث {0} من {1}، {2}",
    "Use % for any non empty value.": "استخدم % f لأي قيمة غير فارغة.",
    "Use First Day of Period": "استخدم أول يوم في الفترة",
    "Use a few uncommon words together.": "استخدم عدة كلمات غير شائعة معًا.",
    "Use different Email ID": "استخدم معرّف بريد إلكتروني آخر",
    "User Doctype Permissions": "أذونات أنواع المستندات للمستخدم",
    "User Document Types Limit Exceeded": "تم تجاوز حد أنواع مستندات المستخدم",
    "User Permissions created successfully": "تم إنشاء أذونات المستخدم بنجاح",
    "User {0} impersonated as {1}": "تم انتحال هوية المستخدم {0} باسم {1}",
    "Utilization": "معدل الاستخدام",
    "Validate Frappe Mail Settings": "التحقق من إعدادات Frappe Mail",
    "Validate SSL Certificate": "التحقق من شهادة SSL",
    "Views": "العروض",
    "Virtual": "افتراضي",
    "Virtual tables must be virtual fields": "يجب أن تكون الجداول الافتراضية حقولًا افتراضية",
    "Visibility": "الظهور",
    "Warning: Naming is not set": "تحذير: التسمية غير مضبوطة",
    "We've received your query!": "تم استلام استفسارك!",
    "Web Template is not specified": "قالب الموقع غير محدد",
    "Website Theme image link": "رابط صورة سمة الموقع",
    "Website Themes Available": "سمات الموقع المتاحة",
    "Widths can be set in px or %.": "يمكن ضبط العرض بوحدة بكسل أو %.",
    "Workflow Action Permitted Role": "الدور المسموح به لإجراء سير العمل",
    "Workflow States Don't Exist": "حالات سير العمل غير موجودة",
    "Workflow Transition Task": "مهمة انتقال سير العمل",
    "Workflow Transition Tasks": "مهام انتقال سير العمل",
    "Year": "السنة",
    "You are impersonating as another user.": "أنت تنتحل هوية مستخدم آخر.",
    "You are not allowed to edit the report.": "لا يسمح لك بتحرير التقرير.",
    "You can select one from the following,": "يمكنك اختيار واحد مما يلي،",
    "You can use wildcard %": "يمكنك استخدام البديل %",
    "You must be logged in to use this form.": "يجب أن تسجّل الدخول لاستخدام هذا النموذج.",
    "You need to set one IMAP folder for {0}": "تحتاج إلى ضبط مجلد IMAP واحد لـ {0}",
    "You've been invited to join {0}": "تمت دعوتك للانضمام إلى {0}",
    "Your account has been deleted": "تم حذف حسابك",
    "Your exported report: {0}": "تقريرك المُصدَّر: {0}",
    "cProfile Output": "مخرجات cProfile",
    "deferred": "مؤجل",
    "notified": "تم الإشعار",
    "starting the setup...": "جارٍ بدء الإعداد...",
    "string value, i.e. group": "قيمة نصية، أي مجموعة",
    "string value, i.e. member": "قيمة نصية، أي عضو",
    "this shouldn't break": "هذا لا يجب أن ينكسر",
    "via Auto Repeat": "عبر التكرار التلقائي",
    "via Google Meet": "عبر Google Meet",
    "wkhtmltopdf 0.12.x (with patched qt).": "wkhtmltopdf 0.12.x (مع إصلاحات qt).",
    "{0} and {1}": "{0} و{1}",
    "{0} can not be more than {1}": "لا يمكن أن يزيد {0} عن {1}",
    "{0} has invalid backtick notation: {1}": "يحتوي {0} على رمز الاقتباس المائل غير صالح: {1}",
    "{0} is a not a valid zip file": "ليس {0} ملف ZIP صالحًا",
    "{0} is mandatory": "{0} إلزامي",
    "{0} is not a child table of {1}": "ليس {0} جدولًا فرعيًا لـ {1}",
    "{0} is not a field of doctype {1}": "ليس {0} حقلًا من نوع المستند {1}",
    "{0} is not a valid Cron expression.": "ليس {0} تعبير Cron صالحًا.",
    "{0} is not a valid parentfield for {1}": "ليس {0} حقل أب صالحًا لـ {1}",
    "{0} is not a zip file": "ليس {0} ملف ZIP",
    "{0} is not an allowed role for {1}": "ليس {0} دورًا مسموحًا به لـ {1}",
    "{0} must be beginning with '{1}'": "يجب أن يبدأ {0} بـ '{1}'",
    "{0} must be equal to '{1}'": "يجب أن يساوي {0} '{1}'",
    "{0} must be none of {1}": "يجب ألّا يوافق {0} أيًا من {1}",
    "{0} must be {1} {2}": "يجب أن يكون {0} {1} {2}",
    "{0} only.": "{0} فقط.",
    "{0} removed their assignment.": "أزال {0} تكليفه.",
    "{0} row #{1}:": "صف {0} رقم #{1}:",
    "{} Invalid python code on line {}": "كود بايثون غير صالح {} في السطر {}",
    "{} field cannot be empty.": "لا يمكن أن يكون حقل {} فارغًا.",
}

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


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 270, f"expected 270 scope rows, got {len(scope_rows)}"
    assert len(set(scope_rows)) == 270, "scope source_text not unique"

    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {sorted(diff, key=str)}"
    assert not (set(A) & set(TECHNICAL)), "A and TECHNICAL overlap"
    assert not (set(A) & set(PRESERVED)), "A and PRESERVED overlap"
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

    for s in TECHNICAL:
        assert s not in A

    preserved_srcs = [s for s in scope_rows if s in PRESERVED]
    tech_srcs = [s for s in scope_rows if s in TECHNICAL]
    payload_srcs = [s for s in scope_rows if s in A]

    assert len(preserved_srcs) == 0, f"expected 0 preserved, got {len(preserved_srcs)}"
    assert len(tech_srcs) == 29, f"expected 29 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 241, f"expected 241 payload, got {len(payload_srcs)}"
    assert len(preserved_srcs) + len(tech_srcs) + len(payload_srcs) == 270

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

    # Catalog: convert the 270 stub Pending rows in place —
    # 241 -> Released with full quorum metadata, 29 EXCEPTION-technical dropped.
    with APPROVED.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == FIELDNAMES, f"catalog header drift: {reader.fieldnames}"
        existing_rows = list(reader)
    before = len(existing_rows)
    pending_srcs = {r["source_text"] for r in existing_rows if r["release_status"] == "Pending"}
    assert pending_srcs == all_keys, (
        f"pending rows != batch-7 scope: missing={sorted(all_keys - pending_srcs)}, "
        f"extra={sorted(pending_srcs - all_keys)}"
    )

    out_rows = []
    dropped = converted = kept = 0
    for r in existing_rows:
        if r["release_status"] != "Pending":
            kept += 1
            out_rows.append(r)
            continue
        s = r["source_text"]
        if s in TECHNICAL:
            dropped += 1
            continue
        assert s in A, f"pending key not in A: {s!r}"
        r.update(
            {
                "language": "ar",
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
        converted += 1
        out_rows.append(r)

    assert kept == 1949, f"expected 1949 pre-existing Released, got {kept}"
    assert dropped == 29, f"expected 29 dropped technical, got {dropped}"
    assert converted == 241, f"expected 241 converted, got {converted}"
    assert len(out_rows) == 2190, f"expected 2190 rows, got {len(out_rows)}"
    assert all(r["release_status"] == "Released" for r in out_rows), "non-Released row remains"
    for r in out_rows:
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

    recon = {
        "batch": "07",
        "generated": "2026-09-22",
        "site": "v16.localhost",
        "scope_sha256": "1716d01c20129b86d629034d2c826a17a3029feb44b7006e1e19b7faa9bc76d4",
        "total_keys": 270,
        "runtime_rows_scanned": 20367,
        "exact_case_matches": 267,
        "case_variant_rows_with_arabic": [
            {"source_text": "Patch", "translated_text": "بقعة", "ct_origin": ""},
            {"source_text": "purple", "translated_text": "أرجواني", "ct_origin": ""},
        ],
        "missing_keys": [
            'Route: Example \\"/app\\"',
            'There is no task called \\"{}\\"',
            "Page to show on the website",
        ],
        "matched_origins": {"": 267},
        "matched_nonempty_values": 0,
        "site_override_origin_rows": 0,
        "preserved": [],
        "note": (
            "Authoritative dump 20367 runtime rows. Zero ct_origin='Site Override' "
            "among batch-7 keys -> PRESERVED=0, drift=0 expected. PATCH/Purple have "
            "exact-cased empty runtime rows; case-variant Patch/purple carry operator "
            "values but are separate rows (PATCH is EXCEPTION-technical; Purple imports "
            "against its exact-cased row). 238 of 241 Released keys have exact-cased "
            "empty-origin runtime rows (-> updates); 3 have no runtime row (-> creates)."
        ),
    }
    SITE_RECON.write_text(json.dumps(recon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    after = len(out_rows)
    print(f"preserved={len(preserved_srcs)} technical={len(tech_srcs)} payload={len(payload_srcs)}")
    print(f"approved rows {before} -> {after} (kept={kept} converted={converted} dropped={dropped})")
    print(f"wrote {PAYLOAD}")
    print(f"wrote {RELEASED_LIST} ({len(payload_srcs)} lines)")
    print(f"wrote {SITE_RECON}")
    assert before == 2219
    assert after == 2190


if __name__ == "__main__":
    main()
