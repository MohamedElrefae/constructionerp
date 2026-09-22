#!/usr/bin/env python3
"""W6-0b batch-6 AI proposal build + payload append + quorum paper trail.

Owner-approved scope: stage6_w60b_batch06_rows_2026-09-22.csv (270 rows).
Site-override reconciliation (plan §12): 1 row preserved, not imported.
Technical exceptions: source-equal rows, not imported.
Payload: Released rows appended to approved_ar_overrides.csv.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE = ROOT / "docs/translation/stage6_w60b_batch06_rows_2026-09-22.csv"
APPROVED = ROOT / "construction/data/translations/approved_ar_overrides.csv"
PAYLOAD = ROOT / "docs/translation/stage6_w60b_payload_applied_rows_batch06_2026-09-22.csv"

DATE = "2026-09-22"
DECISION_REF = f"content:docs/translation/stage6_w60b_payload_applied_rows_batch06_{DATE}.csv"
REFERENCES = "glossary v2.0; vendor ledger arabic_coverage_gap_report_2026-08-22.csv; plan D5; W6-0b batch-6"
NOTES = (
    "AI proposal 2026-09-22 + quorum-confirmed "
    "(W6-0b batch-6; owner-approved 270-row scope minus site-override preserves "
    "and EXCEPTION-technical rows)"
)
DOMAIN = "desk-short-ui"
RELEASE_VERSION = "1.3"
REVIEWERS = (
    "AI-A1 (recorded review run)",
    "AI-A2 (recorded review run)",
    "AI-A3 (recorded review run)",
)
TS = f"{DATE} 00:00:00"

# Site-override preserved (not imported) — case-insensitive matches on batch keys
# with ct_origin=Site Override on v16.localhost (recon 2026-09-22)
PRESERVED = {
    "City": "المدينة",
}

# EXCEPTION-technical: source==translation format/identifier tokens; not imported
TECHNICAL = {
    "InnoDB",
    "Geoapify",
    "Keycloak",
    "Nomatim",
    "DocShare",
    "Awesomebar",
    "Mx",
    "Code challenge method",
    "Collapsible Depends On (JS)",
    "Mandatory Depends On (JS)",
    'By \\"Naming Series\\" field',
}

# Full AI proposals for Released rows (glossary v2.0 + Egyptian professional Arabic)
A = {
    "2 years ago": "منذ عامين",
    "3 minutes ago": "منذ 3 دقائق",
    "5 days ago": "منذ 5 أيام",
    "API Endpoint Args should be valid JSON": "يجب أن تكون وسيطات نقطة نهاية API قيمة JSON صالحة",
    "API Key cannot be regenerated": "لا يمكن إعادة إنشاء مفتاح API",
    "About {0} minute remaining": "بقيت دقيقة تقريبًا {0}",
    "About {0} minutes remaining": "بقيت حوالي {0} دقائق",
    "About {0} seconds remaining": "بقيت حوالي {0} ثانية",
    "Added": "تمت الإضافة",
    "Added default log doctypes: {}": "تمت إضافة أنواع مستندات السجل الافتراضية: {}",
    "Adds a custom client script to a DocType": "يضيف سكربت عميل مخصصًا إلى نوع مستند",
    "Adds a custom field to a DocType": "يضيف حقلًا مخصصًا إلى نوع مستند",
    "Administrator can't follow": "لا يمكن للمدير التنفيذي المتابعة",
    "Alias must be a string": "يجب أن يكون الاسم المستعار نصًا",
    "Align": "محاذاة",
    "Allow Consecutive Login Attempts": "السماح بمحاولات تسجيل الدخول المتتالية",
    "Allow incomplete forms": "السماح بالنماذج غير المكتملة",
    "Allow multiple responses": "السماح بردود متعددة",
    "Allowed File Extensions": "امتدادات الملفات المسموح بها",
    "Allowed Public Client Origins": "مصادر العميل العام المسموح بها",
    "Allowed embedding domains": "نطاقات التضمين المسموح بها",
    "Always use this name as sender name": "استخدم دائمًا هذا الاسم كاسم المرسل",
    "Amended Document Naming Settings": "إعدادات تسمية المستندات المعدّلة",
    "Amendment Naming Override": "تجاوز تسمية التسوية",
    "Amendment Not Allowed": "التسوية غير مسموح بها",
    "Amendment naming rules updated.": "تم تحديث قواعد تسمية التسوية.",
    "Announcements": "الإعلانات",
    "Annual": "سنوي",
    "App Name (Client Name)": "اسم التطبيق (اسم العميل)",
    "App not found for module: {0}": "التطبيق غير موجود للوحدة: {0}",
    "Application is not installed": "التطبيق غير مثبت",
    "Apply User Permission On": "تطبيق إذن المستخدم على",
    "Apply document permissions": "تطبيق أذونات المستند",
    "Assignee": "المفوّض",
    "Assignment": "التكليف",
    "Assignment of {0} removed by {1}": "أُزيل تكليف {0} بواسطة {1}",
    "Asynchronous": "غير متزامن",
    "Auth URL data should be valid JSON": "يجب أن تكون بيانات رابط المصادقة قيمة JSON صالحة",
    "Authenticate as Service Principal": "المصادقة كجهة خدمة رئيسية",
    "Authorization": "التفويض",
    "Auto follow documents that you Like": "متابعة تلقائية للمستندات التي تُعجب بها",
    "Auto follow documents that you create": "متابعة تلقائية للمستندات التي تنشئها",
    "Background Job Activity": "نشاط المهام الخلفية",
    "Background Jobs Check": "فحص المهام الخلفية",
    "Background Jobs Queue": "طابور المهام الخلفية",
    "Backup Encryption Key": "مفتاح تشفير النسخ الاحتياطي",
    "Beginner": "مبتدئ",
    "Brand": "العلامة التجارية",
    "Bulk Operation Failed": "فشلت العملية الجماعية",
    "Bulk Operation Successful": "نجحت العملية الجماعية",
    "Bulk {0} is enqueued in background.": "تمت في قائمة {0} في الخلفية.",
    "Cache": "الذاكرة المؤقتة",
    "Campaign Description (Optional)": "وصف الحملة (اختياري)",
    "Cannot access file path {0}": "لا يمكن الوصول إلى مسار الملف {0}",
    "Cannot edit Standard Dashboards": "لا يمكن تحرير لوحات المعلومات القياسية",
    "Cannot edit Standard charts": "لا يمكن تحرير الرسوم البيانية القياسية",
    "Cannot find file {} on disk": "لا يمكن العثور على الملف {} على القرص",
    "Cannot get file contents of a Folder": "لا يمكن الحصول على محتويات المجلد",
    "Cannot use sub-query here.": "لا يمكن استخدام الاستعلام الفرعي هنا.",
    "Cannot use {0} in order/group by": "لا يمكن استخدام {0} في order/group by",
    "Child DocTypes are not allowed": "أنواع مستندات فرعية غير مسموح بها",
    "Clear Logs After (days)": "مسح السجلات بعد (أيام)",
    "Click to Set Dynamic Filters": "انقر لتعيين عوامل التصفية الديناميكية",
    "Committed": "تم الإيداع",
    "Common words are easy to guess.": "الكلمات الشائعة يسهل تخمينها.",
    "Communication secret not set": "سر التواصل غير معيّن",
    "Compressed": "مضغوط",
    "Condition": "الشرط",
    "Condition description": "وصف الشرط",
    "Conditions": "الشروط",
    "Configuration": "الإعدادات",
    "Console Logs can not be deleted": "لا يمكن حذف سجلات وحدة التحكم",
    "Constraints": "القيود",
    "Contacts": "جهات الاتصال",
    "Contains {0} security fix": "يتضمن إصلاح أمني {0}",
    "Contains {0} security fixes": "يتضمن إصلاحات أمنية {0}",
    "Content data shoud be a list": "يجب أن تكون بيانات المحتوى قائمة",
    "Could not parse field: {0}": "تعذر تحليل الحقل: {0}",
    "Country Code Required": "رمز الدولة مطلوب",
    "Custom Document Types Limit Exceeded": "تم تجاوز حد أنواع المستندات المخصصة",
    "Customize Child Table": "تخصيص الجدول الفرعي",
    "Database": "قاعدة البيانات",
    "Database Storage Usage By Tables": "استخدام التخزين في قاعدة البيانات حسب الجداول",
    "Database Table Row Size Limit": "حد حجم صفوف جدول قاعدة البيانات",
    "Default Amendment Naming": "تسمية التسوية الافتراضية",
    "Default Email Template": "قالب البريد الإلكتروني الافتراضي",
    "Default Template For Field": "القالب الافتراضي للحقل",
    "Delayed": "متأخر",
    "Deleted all documents successfully": "تم حذف جميع المستندات بنجاح",
    "Disable Automatic Recency Filters": "تعطيل عوامل التصفية الحديثة التلقائية",
    "Disable Comment Count": "تعطيل عدّاد التعليقات",
    "Disable Document Sharing": "تعطيل مشاركة المستندات",
    "Disable Product Suggestion": "تعطيل اقتراح المنتجات",
    "Disable Username/Password Login": "تعطيل تسجيل الدخول باسم المستخدم وكلمة المرور",
    "Discarded": "مهمل",
    "Do you still want to proceed?": "هل ما زلت تريد المتابعة؟",
    "DocType must be a string": "يجب أن يكون نوع المستند نصًا",
    "DocType not supported by Log Settings.": "إعدادات السجل لا تدعم نوع المستند هذا.",
    "DocType {0} does not exist.": "نوع المستند {0} غير موجود.",
    "Document Name must be a string": "يجب أن يكون اسم المستند نصًا",
    "Document Naming Settings": "إعدادات تسمية المستندات",
    "Document Types (Select Permissions Only)": "أنواع المستندات (أذونات الاختيار فقط)",
    "Document Types and Permissions": "أنواع المستندات والأذونات",
    "Document not Relinked": "لم يُعاد ربط المستند",
    "Document {0} {1} does not exist": "المستند {0} {1} غير موجود",
    "Dr": "الدكتور",
    "Dynamic": "ديناميكي",
    "Either key or IP flag is required.": "المفتاح أو علامة IP مطلوب.",
    "Email Account Disabled.": "حساب البريد معطّل.",
    "Email Account {0} Disabled": "حساب البريد {0} معطّل",
    "Email Threads on Assigned Document": "سلاسل البريد على المستند المكلف به",
    "Email is mandatory to create User Email": "البريد إلزامي لإنشاء بريد المستخدم",
    "Emails": "رسائل البريد",
    "Empty alias is not allowed": "الاسم المستعار الفارغ غير مسموح به",
    "Empty string arguments are not allowed": "وسائط النص الفارغ غير مسموح بها",
    "Enable Action Confirmation": "تفعيل تأكيد الإجراء",
    "Enable Address Autocompletion": "تفعيل الإكمال التلقائي للعنوان",
    "Enable Dynamic Client Registration": "تفعيل تسجيل العميل الديناميكي",
    "Enable Google indexing": "تفعيل فهرسة Google",
    "Enable in-app website tracking": "تفعيل تتبع الموقع داخل التطبيق",
    "Enables Calendar and Gantt views.": "يمكّن عروض التقويم وغانت.",
    "Encryption key is in invalid format!": "مفتاح التشفير بتنسيق غير صالح!",
    "End Date cannot be today.": "لا يمكن أن يكون تاريخ النهاية اليوم.",
    "Endpoints": "نقاط النهاية",
    "Enqueued creation of indexes": "تمت جدولة إنشاء الفهارس",
    "Error connecting via IMAP/POP3: {e}": "خطأ في الاتصال عبر IMAP/POP3: {e}",
    "Error connecting via SMTP: {e}": "خطأ في الاتصال عبر SMTP: {e}",
    "Error in Header/Footer Script": "خطأ في سكربت الترويسة/التذييل",
    "Error in print format on line {0}: {1}": "خطأ في تنسيق الطباعة في السطر {0}: {1}",
    "Error in {0}.get_list: {1}": "خطأ في {0}.get_list: {1}",
    "Error parsing nested filters: {0}. {1}": "خطأ في تحليل عوامل التصفية المتداخلة: {0}. {1}",
    "Error: Data missing in table {0}": "خطأ: بيانات مفقودة في الجدول {0}",
    "Errors": "الأخطاء",
    "Executing...": "جارٍ التنفيذ...",
    "Expired": "منتهي الصلاحية",
    "Fail": "فشل",
    "Failed Logins (Last 30 days)": "محاولات دخول فاشلة (آخر 30 يومًا)",
    "Failed to compute request body: {}": "فشل حساب جسم الطلب: {}",
    "Failed to decrypt key {0}": "فشل فك تشفير المفتاح {0}",
    "Failed to enable scheduler: {0}": "فشل تفعيل المجدول: {0}",
    "Failed to evaluate conditions: {}": "فشل تقييم الشروط: {}",
    "Failed to generate names from the series": "فشل توليد الأسماء من السلسلة",
    "Failed to get method {0} with {1}": "فشل الحصول على الدالة {0} بوساطة {1}",
    "Failed to get site info": "فشل الحصول على معلومات الموقع",
    "Failed to optimize image: {0}": "فشل تحسين الصورة: {0}",
    "Failed to render message: {}": "فشل عرض الرسالة: {}",
    "Failed to render subject: {}": "فشل عرض الموضوع: {}",
    "Failed to request login to Frappe Cloud": "فشل طلب تسجيل الدخول إلى Frappe Cloud",
    "Failed to send email with subject:": "فشل إرسال البريد بالموضوع:",
    "Failed to update global settings": "فشل تحديث الإعدادات العامة",
    "Failed while calling API {0}": "فشل أثناء استدعاء API {0}",
    "Failing Scheduled Jobs (last 7 days)": "المهام المجدولة الفاشلة (آخر 7 أيام)",
    "Failure": "فشل",
    "Female": "أنثى",
    "Fetching fields from {0}...": "جارٍ جلب الحقول من {0}...",
    "Field not permitted in query": "الحقل غير مسموح به في الاستعلام",
    "Field {0} does not exist on {1}": "الحقل {0} غير موجود على {1}",
    "File type of {0} is not allowed": "نوع الملف {0} غير مسموح به",
    "First Day of the Week": "أول يوم في الأسبوع",
    "Following document {0}": "المستند التالي {0}",
    "Footer HTML set from attachment {0}": "تم تعيين HTML التذييل من المرفق {0}",
    'Footer \\"Powered By\\"': 'تذييل "مدفوع بواسطة"',
    "Force Web Capture Mode for Uploads": "فرض وضع التقاط الويب للرفع",
    "Forward Query Parameters": "إعادة توجيه معاملات الاستعلام",
    "Frappe Mail OAuth Error": "خطأ OAuth في Frappe Mail",
    "Frappe page builder using components": "منشئ صفحات Frappe باستخدام المكوّنات",
    "Function {0} is not whitelisted.": "الدالة {0} غير مدرجة في القائمة البيضاء.",
    "GNU Affero General Public License": "رخصة GNU Affero العامة",
    "GNU General Public License": "رخصة GNU العامة",
    "Genderqueer": "هوية جندرية غير تقليدية",
    "Get Backup Encryption Key": "الحصول على مفتاح تشفير النسخ الاحتياطي",
    "Get OpenID Configuration": "الحصول على تهيئة OpenID",
    "Github flavoured markdown syntax": "صياغة Markdown بنكهة Github",
    "Go to this URL after completing the form": "انتقل إلى رابط URL بعد إكمال النموذج",
    "Google Analytics anonymise IP": "تعقيم Google Analytics لعنوان IP",
    "Google Drive Picker Enabled": "تم تفعيل منتقي Google Drive",
    "Gray": "رمادي",
    "HERE": "هنا",
    "HTML with jinja support": "HTML مع دعم jinja",
    "Headers must be a dictionary": "يجب أن تكون الترويسات قاموسًا",
    "Helpful": "مفيد",
    "Hidden columns include: {0}": "الأعمدة المخفية تشمل: {0}",
    "Hide Empty Read-Only Fields": "إخفاء الحقول للقراءة فقط الفارغة",
    "Highlight": "تمييز",
    "Image link '{0}' is not valid": "رابط الصورة '{0}' غير صالح",
    "Image: Corrupted Data Stream": "الصورة: تدفق بيانات تالف",
    "Impersonate": "انتحال الهوية",
    "Importing {0} is not allowed.": "لا يُسمح باستيراد {0}.",
    "Importing {0} of {1}, {2}": "جارٍ استيراد {0} من {1}، {2}",
    "Incoming": "وارد",
    "Incoming (POP/IMAP) Settings": "إعدادات الوارد (POP/IMAP)",
    "Incoming Emails (Last 7 days)": "رسائل البريد الواردة (آخر 7 أيام)",
    "Incorrect value in row {0}:": "قيمة غير صحيحة في الصف {0}:",
    "Indexing authorization code": "رمز تفويض الفهرسة",
    "Insufficient Permission Level for {0}": "مستوى إذن غير كافٍ لـ {0}",
    "Insufficient attachment limit": "حد المرفقات غير كافٍ",
    "Intermediate": "متوسط",
    "Internal record of document shares": "سجل داخلي لمشاركات المستندات",
    "Introduction": "مقدمة",
    "Invalid": "غير صالح",

    "Invalid Code. Please try again.": "رمز غير صالح. يرجى المحاولة مرة أخرى.",
    "Invalid Condition: {}": "شرط غير صالح: {}",
    "Invalid Naming Series: {}": "سلسلة تسمية غير صالحة: {}",
    "Invalid Table Fieldname": "اسم حقل الجدول غير صالح",
    "Invalid Webhook Secret": "سر Webhook غير صالح",
    "Invalid aggregate function": "دالة تجميع غير صالحة",
    "Invalid characters in table name: {0}": "أحرف غير صالحة في اسم الجدول: {0}",
    "Invalid field type: {0}": "نوع حقل غير صالح: {0}",
    "Invalid redirect regex in row #{}: {}": "تعبير توجيه إعادة غير صالح في الصف #{}: {}",
    "Invalid request arguments": "وسائط طلب غير صالحة",
    "Invalid value specified for UUID: {}": "قيمة غير صالحة لـ UUID: {}",
    "Invalid wkhtmltopdf version": "إصدار wkhtmltopdf غير صالح",
    "Invalid {0} dictionary format": "تنسيق قاموس {0} غير صالح",
    "Invitation already accepted": "تم قبول الدعوة بالفعل",
    "Invitation already exists": "الدعوة موجودة بالفعل",
    "Invitation cannot be cancelled": "لا يمكن إلغاء الدعوة",
    "Invitation is cancelled": "تم إلغاء الدعوة",
    "Invitation is expired": "انتهت صلاحية الدعوة",
    "Invitation to join {0} cancelled": "تم إلغاء دانضمام {0}",
    "Invitation to join {0} expired": "انتهت صلاحية دعوة الانضمام إلى {0}",
    "Is Calendar and Gantt": "هو التقويم وغانت",
    "Job Stopped Successfully": "تم إيقاف المهمة بنجاح",
    "Job stopped successfully": "تم إيقاف المهمة بنجاح",
    "Join video conference with {0}": "الانضمام إلى مؤتمر فيديو مع {0}",
    "Keep track of all update feeds": "تتبع جميع تدفقات التحديث",
    "Keeps track of all communications": "يتتبع جميع الاتصالات",
    "Last Reset Password Key Generated On": "تاريخ آخر إنشاء لمفتاح إعادة تعيين كلمة المرور",
    "Length": "الطول",
    "Let's set up your account": "لنقم بإعداد حسابك",
    "Likes": "الإعجابات",
    "Limit must be a non-negative integer": "يجب أن يكون الحد عددًا صحيحًا غير سالب",
    "Location": "الموقع",
    "Login with email link": "الدخول برابط البريد الإلكتروني",
    "Madam": "السيدة",
    "Major": "رئيسي",
    "Make Attachment Public (by default)": "جعل المرفق عامًا (افتراضيًا)",
    "Make Attachments Public by Default": "جعل المرفقات عامة افتراضيًا",
    "Male": "ذكر",
    "Master": "الماستر",
    "Max auto email report per user": "الحد الأقصى لتقرير البريد الآلي لكل مستخدم",
    "Max signups allowed per hour": "الحد الأقصى للتسجيلات المسموح بها في الساعة",
    "Meeting": "اجتماع",
    "Members": "الأعضاء",
    "Metadata": "البيانات الوصفية",
    "Middle Name (Optional)": "الاسم الأوسط (اختياري)",
    "Minor": "ثانوي",
    "Misconfigured": "إعداد خاطئ",
    "Miss": "الآنسة",
    "Missing Filters Required": "عوامل تصفية مطلوبة مفقودة",
    "Mobile": "جوال",
    "Module onboarding progress reset": "تمت إعادة تعيين تقدم إعداد الوحدة",
    "Most probably your password is too long.": "على الأرجح كلمة مرورك طويلة جدًا.",
    "Mr": "السيد",
    "Mrs": "السيدة",
    "Ms": "السيدة",
    "Network Printer Settings": "إعدادات الطابعة الشبكية",
    "No Email field found in {0}": "لم يُعثر على حقل بريد في {0}",
    "No email addresses to invite": "لا توجد عناوين بريد لدعوتها",
}


def main():
    with SCOPE.open(encoding="utf-8") as fh:
        scope_rows = [r["source_text"] for r in csv.DictReader(fh)]
    assert len(scope_rows) == 270, f"expected 270 scope rows, got {len(scope_rows)}"

    all_keys = set(scope_rows)
    accounted = set(PRESERVED) | set(TECHNICAL) | set(A)
    diff = all_keys ^ accounted
    assert not diff, f"classification mismatch on keys: {sorted(diff, key=str)}"

    ph_re = re.compile(r"\{[^{}]*\}")
    for s, ar in A.items():
        src_ph = sorted(ph_re.findall(s))
        ar_ph = sorted(ph_re.findall(ar))
        assert src_ph == ar_ph, f"placeholder mismatch on '{s}': {src_ph} != {ar_ph}"
        assert ar != s, f"source-equal released: '{s}'"

    # TECHNICAL must be source-equal (not released into A with distinct text)
    for s in TECHNICAL:
        assert s not in A

    preserved_srcs = [s for s in scope_rows if s in PRESERVED]
    tech_srcs = [s for s in scope_rows if s in TECHNICAL]
    payload_srcs = [s for s in scope_rows if s in A]

    assert len(preserved_srcs) == 1, f"expected 1 preserved, got {len(preserved_srcs)}"
    assert len(tech_srcs) == 11, f"expected 11 technical, got {len(tech_srcs)}"
    assert len(payload_srcs) == 258, f"expected 258 payload, got {len(payload_srcs)}"
    assert len(preserved_srcs) + len(tech_srcs) + len(payload_srcs) == 270

    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    # QUOTE_NONE so decision-binding can find exact source+translation substrings
    # in the raw file text (csv-decision-binding reads file content, not CSV-parsed).
    rows_out = []
    for s in scope_rows:
        if s in PRESERVED:
            rows_out.append(
                (
                    s,
                    PRESERVED[s],
                    "preserved-site-override (not imported, plan §12)",
                    f"stage6-W6-0b batch-6 owner-approved {DATE}",
                )
            )
        elif s in TECHNICAL:
            rows_out.append(
                (
                    s,
                    "EXCEPTION-technical",
                    "EXCEPTION-technical (keep vendor rendering; no translation)",
                    f"stage6-W6-0b batch-6 owner-approved {DATE}",
                )
            )
        else:
            rows_out.append(
                (
                    s,
                    A[s],
                    "quorum-confirmed (release payload row)",
                    f"stage6-W6-0b batch-6 owner-approved {DATE}",
                )
            )
    for row in rows_out:
        for cell in row:
            assert "\t" not in cell and "\n" not in cell and "\r" not in cell, repr(cell)
    with PAYLOAD.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE)
        w.writerow(["source_text", "translated_text", "quorum_decision", "decision_ref"])
        w.writerows(rows_out)

    # Safe overrides for existing non-empty non-site-override rows (value correction via set_value path at import)
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
    existing_src = {r["source_text"] for r in existing_rows}
    dup = [s for s in payload_srcs if s in existing_src]
    assert not dup, f"payload keys already in catalog: {dup}"

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
