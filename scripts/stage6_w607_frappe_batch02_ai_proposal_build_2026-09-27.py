#!/usr/bin/env python3
"""Build and verify Stage 6 W6-7 Frappe Framework Remainder Batch 02 Proposal CSV."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

APP_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCOPE_CSV = APP_ROOT / "docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv"
PROPOSAL_CSV = APP_ROOT / "docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv"
PROPOSAL_MD = APP_ROOT / "docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.md"

RE_BRACES = re.compile(r"\{[0-9]*\}")
RE_PERCENT = re.compile(r"%[sdf]")

TRANSLATIONS: dict[str, tuple[str, str]] = {
    # format: source_text: (disposition, translated_text)
    'Please attach an image file to set HTML for Footer.': ('PROPOSED-payload', 'يرجى إرفاق ملف صورة لتعيين HTML للتذييل.'),
    'Please attach an image file to set HTML for Letter Head.': ('PROPOSED-payload', 'يرجى إرفاق ملف صورة لتعيين HTML للترويسة.'),
    'Please check your email login credentials.': ('PROPOSED-payload', 'يرجى التحقق من بيانات اعتماد تسجيل الدخول إلى بريدك الإلكتروني.'),
    'Please click on the following link and follow the instructions on the page. {0}': ('PROPOSED-payload', 'يرجى النقر فوق الرابط التالي واتباع التعليمات الموجودة في الصفحة. {0}'),
    'Please contact your system manager to install correct version.': ('PROPOSED-payload', 'يرجى الاتصال بمدير النظام لتثبيت الإصدار الصحيح.'),
    'Please delete the field from {0} or add the required doctype.': ('PROPOSED-payload', 'يرجى حذف الحقل من {0} أو إضافة نوع المستند المطلوب.'),
    'Please enter both your email and message so that we can get back to you. Thanks!': ('PROPOSED-payload', 'يرجى إدخال بريدك الإلكتروني ورسالتك حتى نتمكن من الرد عليك. شكرًا!'),
    'Please remove the printer mapping in Printer Settings and try again.': ('PROPOSED-payload', 'يرجى إزالة تعيين الطابعة في إعدادات الطابعة والمحاولة مرة أخرى.'),
    'Please save the form before previewing the message': ('PROPOSED-payload', 'يرجى حفظ النموذج قبل معاينة الرسالة'),
    'Please select a DocType in options before setting filters': ('PROPOSED-payload', 'يرجى تحديد نوع المستند في الخيارات قبل تعيين عوامل التصفية'),
    'Please select a country code for field {1}.': ('PROPOSED-payload', 'يرجى تحديد رمز البلد للحقل {1}.'),
    'Please select the LDAP Directory being used': ('PROPOSED-payload', 'يرجى تحديد دليل LDAP المستخدم'),
    'Please setup default outgoing Email Account from Settings > Email Account': ('PROPOSED-payload', 'يرجى إعداد حساب البريد الإلكتروني الصادر الافتراضي من الإعدادات > حساب البريد الإلكتروني'),
    'Please setup default outgoing Email Account from Tools > Email Account': ('PROPOSED-payload', 'يرجى إعداد حساب البريد الإلكتروني الصادر الافتراضي من أدوات > حساب البريد الإلكتروني'),
    'Please specify a valid parent DocType for {0}': ('PROPOSED-payload', 'يرجى تحديد نوع مستند رئيسي صالح لـ {0}'),
    'Please specify at least 10 minutes due to the trigger cadence of the scheduler': ('PROPOSED-payload', 'يرجى تحديد 10 دقائق على الأقل بسبب وتيرة تشغيل المجدول'),
    'Please specify the field from which to attach files': ('PROPOSED-payload', 'يرجى تحديد الحقل الذي سيتم إرفاق الملفات منه'),
    'Please specify which datetime field must be checked': ('PROPOSED-payload', 'يرجى تحديد حقل التاريخ والوقت الذي يجب التحقق منه'),
    'Please use following links to download file backup.': ('PROPOSED-payload', 'يرجى استخدام الروابط التالية لتنزيل النسخة الاحتياطية للملف.'),
    'Please visit https://frappecloud.com/docs/sites/migrate-an-existing-site#encryption-key for more information.': ('PROPOSED-payload', 'يرجى زيارة https://frappecloud.com/docs/sites/migrate-an-existing-site#encryption-key لمزيد من المعلومات.'),
    'Post it here, our mentors will help you out.': ('PROPOSED-payload', 'انشرها هنا، وسيساعدك موجهونا.'),
    'Precision ({0}) for {1} cannot be greater than its length ({2}).': ('PROPOSED-payload', 'لا يمكن أن تكون دقة ({0}) لـ {1} أكبر من طولها ({2}).'),
    'Prepend the template to the email message': ('PROPOSED-payload', 'إلحاق القالب في بداية رسالة البريد الإلكتروني'),
    'Primary key of doctype {0} can not be changed as there are existing values.': ('PROPOSED-payload', 'لا يمكن تغيير المفتاح الأساسي لنوع المستند {0} لوجود قيم حالية.'),
    'Property Setter overrides a standard DocType or Field property': ('PROPOSED-payload', 'يقوم معدل الخصائص بتجاوز خاصية قياسية لنوع المستند أو الحقل'),
    'Query analysis complete. Check suggested indexes.': ('PROPOSED-payload', 'اكتمل تحليل الاستعلام. تحقق من الفهارس المقترحة.'),
    'Query must be of SELECT or read-only WITH type.': ('PROPOSED-payload', 'يجب أن يكون الاستعلام من نوع SELECT أو WITH للقراءة فقط.'),
    'Queued for Submission. You can track the progress over {0}.': ('PROPOSED-payload', 'تمت الإضافة إلى قائمة انتظار الإرسال. يمكنك متابعة التقدم عبر {0}.'),
    'Rebuilding of tree is not supported for {}': ('PROPOSED-payload', 'إعادة بناء الشجرة غير مدعومة لـ {}'),
    'Records for following doctypes will be filtered': ('PROPOSED-payload', 'سيتم تصفية سجلات أنواع المستندات التالية'),
    'Redirect to this URL after successful confirmation.': ('PROPOSED-payload', 'إعادة التوجيه إلى عنوان URL هذا بعد التأكيد الناجح.'),
    'Render labels to the left and values to the right in this section': ('PROPOSED-payload', 'عرض التسميات على اليسار والقيم على اليمين في هذا القسم'),
    'Represents the states allowed in one document and role assigned to change the state.': ('PROPOSED-payload', 'يمثل الحالات المسموح بها في مستند واحد والدور المعين لتغيير الحالة.'),
    'Requires any valid fdn path. i.e. ou=groups,dc=example,dc=com': ('PROPOSED-payload', 'يتطلب أي مسار fdn صالح، مثل: ou=groups,dc=example,dc=com'),
    'Requires any valid fdn path. i.e. ou=users,dc=example,dc=com': ('PROPOSED-payload', 'يتطلب أي مسار fdn صالح، مثل: ou=users,dc=example,dc=com'),
    "Role 'All' will be given to all system + website users.": ('PROPOSED-payload', "سيتم منح دور 'الكل' لجميع مستخدمي النظام وموقع الويب."),
    "Role 'Desk User' will be given to all system users.": ('PROPOSED-payload', "سيتم منح دور 'مستخدم المكتب' لجميع مستخدمي النظام."),
    'Role has been set as per the user type {0}': ('PROPOSED-payload', 'تم تعيين الدور وفقًا لنوع المستخدم {0}'),
    'Roles can be set for users from their User page.': ('PROPOSED-payload', 'يمكن تعيين الأدوار للمستخدمين من صفحة المستخدم الخاصة بهم.'),
    'Route: Example "/app"': ('PROPOSED-payload', 'المسار: مثال "/app"'),
    'Row # {0}: Non administrator user can not set the role {1} to the custom doctype': ('PROPOSED-payload', 'الصف رقم {0}: لا يمكن للمستخدم غير المسؤول تعيين الدور {1} لنوع المستند المخصص'),
    'Rule for this doctype, role, permlevel and if-owner combination already exists.': ('PROPOSED-payload', 'توجد قاعدة بالفعل لمجموعة نوع المستند والدور ومستوى الأذونات وحالة المالك هذه.'),
    'SMS was not sent. Please contact Administrator.': ('PROPOSED-payload', 'لم يتم إرسال الرسالة النصية القصيرة. يرجى الاتصال بالمسؤول.'),
    "SQL functions are not allowed as strings in SELECT: {0}. Use dict syntax like {{'COUNT': '*'}} instead.": ('PROPOSED-payload', "دوال SQL غير مسموح بها كسلاسل نصية في SELECT: {0}. استخدم بناء جملة القاموس مثل {{'COUNT': '*'}} بدلاً من ذلك."),
    'Saving this will export this document as well as the steps linked here as json.': ('PROPOSED-payload', 'سيؤدي حفظ هذا إلى تصدير هذا المستند بالإضافة إلى الخطوات المرتبطة به كملف json.'),
    'Scheduler can not be re-enabled when maintenance mode is active.': ('PROPOSED-payload', 'لا يمكن إعادة تمكين المجدول عندما يكون وضع الصيانة نشطًا.'),
    'Scheduler is inactive. Cannot import data.': ('PROPOSED-payload', 'المجدول غير نشط. لا يمكن استيراد البيانات.'),
    'Select Document Types to set which User Permissions are used to limit access.': ('PROPOSED-payload', 'حدد أنواع المستندات لتعيين أذونات المستخدم المستخدمة لتقييد الوصول.'),
    'Select an existing format to edit or start a new format.': ('PROPOSED-payload', 'حدد تنسيقًا حاليًا لتعديله أو ابدأ تنسيقًا جديدًا.'),
    "Send alert if datetime matches this field's value": ('PROPOSED-payload', 'إرسال تنبيه إذا تطابق التاريخ والوقت مع قيمة هذا الحقل'),
    'Send email when document transitions to the state.': ('PROPOSED-payload', 'إرسال بريد إلكتروني عند انتقال المستند إلى هذه الحالة.'),
    'Series counter for {} updated to {} successfully': ('PROPOSED-payload', 'تم تحديث عداد السلسلة لـ {} إلى {} بنجاح'),
    'Server Scripts are disabled. Please enable server scripts from bench configuration.': ('PROPOSED-payload', 'البرامج النصية للخادم معطلة. يرجى تمكين البرامج النصية للخادم من تكوين bench.'),
    'Server Scripts feature is not available on this site.': ('PROPOSED-payload', 'ميزة البرامج النصية للخادم غير متوفرة في هذا الموقع.'),
    'Server failed to process this request because of a concurrent conflicting request. Please try again.': ('PROPOSED-payload', 'فشل الخادم في معالجة هذا الطلب بسبب تعارض مع طلب متزامن. يرجى المحاولة مرة أخرى.'),
    'Server was too busy to process this request. Please try again.': ('PROPOSED-payload', 'الخادم مشغول للغاية ولا يمكنه معالجة هذا الطلب. يرجى المحاولة مرة أخرى.'),
    'Set Naming Series options on your transactions.': ('PROPOSED-payload', 'تعيين خيارات سلسلة التسمية لمعاملاتك.'),
    'Set dynamic filter values in JavaScript for the required fields here.': ('PROPOSED-payload', 'عيّن قيم التصفية الديناميكية في JavaScript للحقول المطلوبة هنا.'),
    'Set non-standard precision for a Float, Currency or Percent field': ('PROPOSED-payload', 'تعيين دقة غير قياسية لحقل عشري أو عملة أو نسبة مئوية'),
    'Show Fieldname (click to copy on clipboard)': ('PROPOSED-payload', 'إظهار اسم الحقل (انقر للنسخ إلى الحافظة)'),
    'Show Social Login Key as Authorization Server': ('PROPOSED-payload', 'إظهار مفتاح تسجيل الدخول الاجتماعي كخادم تفويض'),
    'Show account deletion link in My Account page': ('PROPOSED-payload', 'إظهار رابط حذف الحساب في صفحة حسابي'),
    'Size exceeds the maximum allowed file size.': ('PROPOSED-payload', 'الحجم يتجاوز الحد الأقصى المسموح به لحجم الملف.'),
    'Skipping fixture syncing for doctype {0} from file {1}': ('PROPOSED-payload', 'تخطي مزامنة التركيبات لنوع المستند {0} من الملف {1}'),
    'Some columns might get cut off when printing to PDF. Try to keep number of columns under 10.': ('PROPOSED-payload', 'قد يتم اقتطاع بعض الأعمدة عند الطباعة إلى PDF. حاول الحفاظ على عدد الأعمدة أقل من 10.'),
    'Some mailboxes require a different Sent Folder Name e.g. "INBOX.Sent"': ('PROPOSED-payload', 'تتطلب بعض صناديق البريد اسمًا مختلفًا لمجلد العناصر المرسلة مثل "INBOX.Sent"'),
    'Specify a custom timeout, default timeout is 1500 seconds': ('PROPOSED-payload', 'تحديد مهلة مخصصة، المهلة الافتراضية هي 1500 ثانية'),
    'Standard Web Forms can not be modified, duplicate the Web Form instead.': ('PROPOSED-payload', 'لا يمكن تعديل نماذج الويب القياسية، قم بتكرار نموذج الويب بدلاً من ذلك.'),
    'Standard user type {0} can not be deleted.': ('PROPOSED-payload', 'لا يمكن حذف نوع المستخدم القياسي {0}.'),
    'Status Updated. The email will be picked up in the next scheduled run.': ('PROPOSED-payload', 'تم تحديث الحالة. سيتم التقاط البريد الإلكتروني في التشغيل المجدول التالي.'),
    "Store the API secret securely. It won't be displayed again.": ('PROPOSED-payload', 'احفظ سر واجهة برمجة التطبيقات بأمان. لن يتم عرضه مرة أخرى.'),
    'Stores the datetime when the last reset password key was generated.': ('PROPOSED-payload', 'يخزن التاريخ والوقت عند إنشاء آخر مفتاح لإعادة تعيين كلمة المرور.'),
    'Successfully imported {0} out of {1} records.': ('PROPOSED-payload', 'تم استيراد {0} من أصل {1} سجلاً بنجاح.'),
    'Successfully reset onboarding status for all users.': ('PROPOSED-payload', 'تمت إعادة تعيين حالة التهيئة لجميع المستخدمين بنجاح.'),
    'Successfully updated {0} out of {1} records.': ('PROPOSED-payload', 'تم تحديث {0} من أصل {1} سجلاً بنجاح.'),
    'Sync token was invalid and has been reset, Retry syncing.': ('PROPOSED-payload', 'رمز المزامنة غير صالح وتمت إعادة تعيينه، أعد محاولة المزامنة.'),
    'System Generated Fields can not be renamed': ('PROPOSED-payload', 'لا يمكن إعادة تسمية الحقول التي تم إنشاؤها بواسطة النظام'),
    'Thank you for spending your valuable time to fill this form': ('PROPOSED-payload', 'شكرًا لك على قضاء وقتك الثمين لملء هذا النموذج'),
    'The Next Scheduled Date cannot be later than the End Date.': ('PROPOSED-payload', 'لا يمكن أن يكون التاريخ المجدول التالي بعد تاريخ الانتهاء.'),
    'The Push Relay Server URL key (`push_relay_server_url`) is missing in your site config': ('PROPOSED-payload', 'مفتاح عنوان URL لخادم ترحيل الإشعارات (`push_relay_server_url`) مفقود في تكوين موقعك'),
    'The User record for this request has been auto-deleted due to inactivity by system admins.': ('PROPOSED-payload', 'تم حذف سجل المستخدم لهذا الطلب تلقائيًا بسبب عدم النشاط بواسطة مسؤولي النظام.'),
    'The application name will be used in the Login page.': ('PROPOSED-payload', 'سيتم استخدام اسم التطبيق في صفحة تسجيل الدخول.'),
    'The contents of this email are strictly confidential. Please do not forward this email to anyone.': ('PROPOSED-payload', 'محتويات هذا البريد الإلكتروني سرية للغاية. يرجى عدم إعادة توجيه هذا البريد الإلكتروني لأي شخص.'),
    'The count shown is an estimated count. Click here to see the accurate count.': ('PROPOSED-payload', 'العدد الموضح هو عدد تقديري. انقر هنا لرؤية العدد الدقيق.'),
    'The document type selected is a child table, so the parent document type is required.': ('PROPOSED-payload', 'نوع المستند المحدد هو جدول فرعي، لذا يلزم تحديد نوع المستند الرئيسي.'),
    'The field {0} in {1} does not allow ignoring user permissions': ('PROPOSED-payload', 'الحقل {0} في {1} لا يسمح بتجاهل أذونات المستخدم'),
    'The field {0} in {1} links to {2} and not {3}': ('PROPOSED-payload', 'الحقل {0} في {1} يرتبط بـ {2} وليس {3}'),
    "The fieldname you've specified in Attached To Field is invalid": ('PROPOSED-payload', 'اسم الحقل الذي حددته في حقل "مرفق بـ" غير صالح'),
    'The following Assignment Days have been repeated: {0}': ('PROPOSED-payload', 'تم تكرار أيام التعيين التالية: {0}'),
    "The following Header Script will add the current date to an element in 'Header HTML' with class 'header-content'": ('PROPOSED-payload', "سيقوم البرنامج النصي للترويسة التالي بإضافة التاريخ الحالي إلى عنصر في 'Header HTML' بفئة 'header-content'"),
    'The following values are invalid: {0}. Values must be one of {1}': ('PROPOSED-payload', 'القيم التالية غير صالحة: {0}. يجب أن تكون القيم واحدة من {1}'),
    'The following values do not exist for {0}: {1}': ('PROPOSED-payload', 'القيم التالية غير موجودة لـ {0}: {1}'),
    'The limit has not set for the user type {0} in the site config file.': ('PROPOSED-payload', 'لم يتم تعيين الحد لنوع المستخدم {0} في ملف تكوين الموقع.'),
    'The link you trying to login is invalid or expired.': ('PROPOSED-payload', 'الرابط الذي تحاول تسجيل الدخول منه غير صالح أو منتهي الصلاحية.'),
    'The next tour will start from where the user left off.': ('PROPOSED-payload', 'ستبدأ الجولة التالية من حيث توقف المستخدم.'),
    'The number of seconds until the request expires': ('PROPOSED-payload', 'عدد الثواني حتى انتهاء صلاحية الطلب'),
    'The reset password link has either been used before or is invalid': ('PROPOSED-payload', 'رابط إعادة تعيين كلمة المرور إما تم استخدامه من قبل أو أنه غير صالح'),
    'The system is being updated. Please refresh again after a few moments.': ('PROPOSED-payload', 'يتم تحديث النظام. يرجى التحديث مرة أخرى بعد لحظات.'),
    'The system provides many pre-defined roles. You can add new roles to set finer permissions.': ('PROPOSED-payload', 'يوفر النظام العديد من الأدوار المحددة مسبقًا. يمكنك إضافة أدوار جديدة لتعيين أذونات أكثر دقة.'),
    'The total number of user document types limit has been crossed.': ('PROPOSED-payload', 'تم تجاوز الحد الإجمالي لعدد أنواع مستندات المستخدم.'),
    'The value you pasted was {0} characters long. Max allowed characters is {1}.': ('PROPOSED-payload', 'القيمة التي قمت بلصقها كانت بطول {0} حرفًا. الحد الأقصى للأحرف المسموح بها هو {1}.'),
    "There are no {0} for this {1}, why don't you start one!": ('PROPOSED-payload', 'لا توجد {0} لـ {1} هذا، لمَ لا تبدأ واحدة!'),
    'There are {0} with the same filters already in the queue:': ('PROPOSED-payload', 'توجد {0} بنفس عوامل التصفية بالفعل في قائمة الانتظار:'),
    'There can be only 9 Page Break fields in a Web Form': ('PROPOSED-payload', 'يمكن أن يوجد 9 حقول فاصل صفحات فقط في نموذج الويب'),
    'There is no task called "{}"': ('PROPOSED-payload', 'لا توجد مهمة تسمى "{}"'),
    'There is nothing new to show you right now.': ('PROPOSED-payload', 'لا يوجد شيء جديد لعرضه لك الآن.'),
    'There is {0} with the same filters already in the queue:': ('PROPOSED-payload', 'يوجد {0} بنفس عوامل التصفية بالفعل في قائمة الانتظار:'),
    'There were errors while sending email. Please try again.': ('PROPOSED-payload', 'حدثت أخطاء أثناء إرسال البريد الإلكتروني. يرجى المحاولة مرة أخرى.'),
    'These announcements will appear inside a dismissible alert below the Navbar.': ('PROPOSED-payload', 'ستظهر هذه الإعلانات داخل تنبيه قابل للإغلاق أسفل شريط التنقل.'),
    "These settings are required if 'Custom' LDAP Directory is used": ('PROPOSED-payload', "هذه الإعدادات مطلوبة في حالة استخدام دليل LDAP 'مخصص'"),
    'This PDF cannot be uploaded as it contains unsafe content.': ('PROPOSED-payload', 'لا يمكن تحميل ملف PDF هذا لأنه يحتوي على محتوى غير آمن.'),
    'This action is irreversible. Do you wish to continue?': ('PROPOSED-payload', 'هذا الإجراء لا يمكن التراجع عنه. هل ترغب في الاستمرار؟'),
    'This doctype has no orphan fields to trim': ('PROPOSED-payload', 'لا يحتوي نوع المستند هذا على حقول مهملة لقصها'),
    "This doctype has pending migrations, run 'bench migrate' before modifying the doctype to avoid losing changes.": ('PROPOSED-payload', "يحتوي نوع المستند هذا على ترحيلات معلقة، قم بتشغيل 'bench migrate' قبل تعديل نوع المستند لتجنب فقدان التغييرات."),
    "This document can not be deleted right now as it's being modified by another user. Please try again after some time.": ('PROPOSED-payload', 'لا يمكن حذف هذا المستند الآن لأنه قيد التعديل بواسطة مستخدم آخر. يرجى المحاولة مرة أخرى بعد فترة.'),
    'This document has already been queued for submission. You can track the progress over {0}.': ('PROPOSED-payload', 'تمت إضافة هذا المستند بالفعل إلى قائمة انتظار الإرسال. يمكنك متابعة التقدم عبر {0}.'),
    'This document is currently locked and queued for execution. Please try again after some time.': ('PROPOSED-payload', 'هذا المستند مقفل حاليًا ومدرج في قائمة انتظار التنفيذ. يرجى المحاولة بعد بعض الوقت.'),
    'This feature is brand new and still experimental': ('PROPOSED-payload', 'هذه الميزة جديدة تمامًا ولا تزال تجريبية'),
    'This file is attached to a protected document and cannot be deleted.': ('PROPOSED-payload', 'هذا الملف مرفق بمستند محمي ولا يمكن حذفه.'),
    'This file is public and can be accessed by anyone, even without logging in. Mark it private to limit access.': ('PROPOSED-payload', 'هذا الملف عام ويمكن لأي شخص الوصول إليه حتى بدون تسجيل الدخول. قم بتعيينه كخاص لتقييد الوصول.'),
    'This file is public. It can be accessed without authentication.': ('PROPOSED-payload', 'هذا الملف عام. يمكن الوصول إليه بدون مصادقة.'),
    'This form is not editable due to a Workflow.': ('PROPOSED-payload', 'هذا النموذج غير قابل للتعديل بسبب مسار العمل.'),
    'This geolocation provider is not supported yet.': ('PROPOSED-payload', 'مزود الموقع الجغرافي هذا غير مدعوم بعد.'),
    'This is a virtual doctype and data is cleared periodically.': ('PROPOSED-payload', 'هذا نوع مستند افتراضي ويتم مسح البيانات بشكل دوري.'),
    'This report contains {0} rows and is too big to display in browser, you can {1} this report instead.': ('PROPOSED-payload', 'يحتوي هذا التقرير على {0} صفاً وهو كبير جدًا بحيث لا يمكن عرضه في المتصفح، يمكنك {1} هذا التقرير بدلاً من ذلك.'),
    'This site is in read only mode, full functionality will be restored soon.': ('PROPOSED-payload', 'هذا الموقع في وضع القراءة فقط، وستتم استعادة الوظائف الكاملة قريبًا.'),
    'This site is running in developer mode. Any change made here will be updated in code.': ('PROPOSED-payload', 'يعمل هذا الموقع في وضع المطور. أي تغيير يتم إجراؤه هنا سيتم تحديثه في الكود البرمجي.'),
    'This software is built on top of many open source packages.': ('PROPOSED-payload', 'تم بناء هذا البرنامج على العديد من الحزم مفتوحة المصدر.'),
    "This value is fetched from {0}'s {1} field": ('PROPOSED-payload', 'يتم جلب هذه القيمة من حقل {1} الخاص بـ {0}'),
    'This value specifies the max number of rows that can be rendered in report view.': ('PROPOSED-payload', 'تحدد هذه القيمة الحد الأقصى لعدد الصفوف التي يمكن عرضها في عرض التقرير.'),
    'This will reset this tour and show it to all users. Are you sure?': ('PROPOSED-payload', 'سيؤدي هذا إلى إعادة تعيين هذه الجولة وعرضها لجميع المستخدمين. هل أنت متأكد؟'),
    'This will terminate the job immediately and might be dangerous, are you sure?': ('PROPOSED-payload', 'سيؤدي هذا إلى إنهاء الوظيفة فورًا وقد يكون خطيرًا، هل أنت متأكد؟'),
    'To allow more reports update limit in System Settings.': ('PROPOSED-payload', 'للسماح بمزيد من التقارير، قم بتحديث الحد في إعدادات النظام.'),
    'To export this step as JSON, link it in a Onboarding document and save the document.': ('PROPOSED-payload', 'لتصدير هذه الخطوة كـ JSON، اربطها في مستند تهيئة واحفظ المستند.'),
    'To set the role {0} in the user {1}, kindly set the {2} field as {3} in one of the {4} record.': ('PROPOSED-payload', 'لتعيين الدور {0} للمستخدم {1}، يرجى تعيين الحقل {2} كـ {3} في أحد سجلات {4}.'),
    'Too many changes to database in single action.': ('PROPOSED-payload', 'تغييرات كثيرة جدًا على قاعدة البيانات في إجراء واحد.'),
    'Too many queued background jobs ({0}). Please retry after some time.': ('PROPOSED-payload', 'وظائف خلفية كثيرة جدًا في قائمة الانتظار ({0}). يرجى إعادة المحاولة بعد بعض الوقت.'),
    'Total number of emails to sync in initial sync process': ('PROPOSED-payload', 'إجمالي عدد رسائل البريد الإلكتروني المطلوب مزامنتها في عملية المزامنة الأولية'),
    'Tracking URL generated and copied to clipboard': ('PROPOSED-payload', 'تم إنشاء رابط التتبع ونسخه إلى الحافظة'),
    'URL of a human-readable page with info that developers might need.': ('PROPOSED-payload', 'عنوان URL لصفحة مقروءة تتضمن معلومات قد يحتاجها المطورون.'),
    'URL of a web page providing information about the client.': ('PROPOSED-payload', 'عنوان URL لصفحة ويب تقدم معلومات حول العميل.'),
    "URL of human-readable page with info about the protected resource's terms of service.": ('PROPOSED-payload', 'عنوان URL لصفحة مقروءة تتضمن معلومات حول شروط خدمة المورد المحمي.'),
    'URL of human-readable page with info on requirements about how the client can use the data.': ('PROPOSED-payload', 'عنوان URL لصفحة مقروءة تتضمن معلومات حول متطلبات كيفية استخدام العميل للبيانات.'),
    'URL that points to a human-readable policy document for the client. Should be shown to end-user before authorizing.': ('PROPOSED-payload', 'عنوان URL يشير إلى وثيقة سياسة مقروءة للعميل. ينبغي عرضها على المستخدم النهائي قبل التفويض.'),
    'URL that references a logo for the client.': ('PROPOSED-payload', 'عنوان URL يشير إلى شعار العميل.'),
    'Unable to send mail because of a missing email account. Please setup default Email Account from Settings > Email Account': ('PROPOSED-payload', 'تعذر إرسال البريد بسبب عدم وجود حساب بريد إلكتروني. يرجى إعداد حساب بريد إلكتروني افتراضي من الإعدادات > حساب البريد الإلكتروني'),
    'Updating Email Queue Statuses. The emails will be picked up in the next scheduled run.': ('PROPOSED-payload', 'جارٍ تحديث حالات قائمة انتظار البريد الإلكتروني. سيتم التقاط رسائل البريد الإلكتروني في التشغيل المجدول التالي.'),
    'Updating counter may lead to document name conflicts if not done properly': ('PROPOSED-payload', 'قد يؤدي تحديث العداد إلى تعارض في أسماء المستندات إذا لم يتم بشكل صحيح'),
    "Use if the default settings don't seem to detect your data correctly": ('PROPOSED-payload', 'استخدم هذا إذا كانت الإعدادات الافتراضية لا تكتشف بياناتك بشكل صحيح'),
    'Use this, for example, if all sent emails should also be send to an archive.': ('PROPOSED-payload', 'استخدم هذا، على سبيل المثال، إذا كان يجب أيضًا إرسال جميع رسائل البريد الإلكتروني المرسلة إلى الأرشيف.'),
    'User Id Field is mandatory in the user type {0}': ('PROPOSED-payload', 'حقل معرف المستخدم إلزامي في نوع المستخدم {0}'),
    'User Permissions are used to limit users to specific records.': ('PROPOSED-payload', 'تُستخدم أذونات المستخدم لتقييد المستخدمين بسجلات محددة.'),
    'User does not have permission to create the new {0}': ('PROPOSED-payload', 'لا يملك المستخدم الإذن لإنشاء {0} الجديد'),
    'User with email address {0} does not exist': ('PROPOSED-payload', 'المستخدم ذو عنوان البريد الإلكتروني {0} غير موجود'),
    "User with email: {0} does not exist in the system. Please ask 'System Administrator' to create the user for you.": ('PROPOSED-payload', "المستخدم ذو البريد الإلكتروني: {0} غير موجود في النظام. يرجى مطالبة 'مسؤول النظام' بإنشاء المستخدم لك."),
    'User {0} does not have the permission to create a Workspace.': ('PROPOSED-payload', 'لا يملك المستخدم {0} الإذن لإنشاء مساحة عمل.'),
    'User {0} is disabled. Please contact your System Manager.': ('PROPOSED-payload', 'المستخدم {0} معطل. يرجى الاتصال بمدير النظام.'),
    'User {0} is not permitted to access this document.': ('PROPOSED-payload', 'لا يُسمح للمستخدم {0} بالوصول إلى هذا المستند.'),
    "Uses system's theme to switch between light and dark mode": ('PROPOSED-payload', 'يستخدم سمة النظام للتبديل بين الوضع الفاتح والداكن'),
    'Verification code email not sent. Please contact Administrator.': ('PROPOSED-payload', 'لم يتم إرسال رسالة رمز التحقق عبر البريد الإلكتروني. يرجى الاتصال بالمسؤول.'),
    'Virtual DocType {} requires a static method called {} found {}': ('PROPOSED-payload', 'نوع المستند الافتراضي {} يتطلب دالة ثابتة تسمى {} تم العثور على {}'),
    'Virtual DocType {} requires overriding an instance method called {} found {}': ('PROPOSED-payload', 'نوع المستند الافتراضي {} يتطلب تجاوز دالة مثيل تسمى {} تم العثور على {}'),
    'Warning: DATA LOSS IMMINENT! Proceeding will permanently delete following database columns from doctype {0}:': ('PROPOSED-payload', 'تحذير: فقدان البيانات وشيك! المتابعة ستؤدي إلى حذف أعمدة قاعدة البيانات التالية نهائيًا من نوع المستند {0}:'),
    'Warning: Updating counter may lead to document name conflicts if not done properly': ('PROPOSED-payload', 'تحذير: قد يؤدي تحديث العداد إلى تعارض في أسماء المستندات إذا لم يتم بشكل صحيح'),
    "Warning: Usage of 'format:' is discouraged.": ('PROPOSED-payload', "تحذير: لا ينصح باستخدام 'format:'."),
    'We would like to thank the authors of these packages for their contribution.': ('PROPOSED-payload', 'نود أن نشكر مؤلفي هذه الحزم على مساهمتهم.'),
    'Will add "%" before and after the query': ('PROPOSED-payload', 'سيضيف "%" قبل الاستعلام وبعده'),
    'Will run scheduled jobs only once a day for inactive sites. Set it to 0 to avoid automatically disabling the scheduler.': ('PROPOSED-payload', 'سيتم تشغيل الوظائف المجدولة مرة واحدة فقط يوميًا للمواقع غير النشطة. عيّنها إلى 0 لتجنب تعطيل المجدول تلقائيًا.'),
    'Workflow state represents the current state of a document.': ('PROPOSED-payload', 'تمثل حالة مسار العمل الحالة الحالية للمستند.'),
    'Would you like to publish this comment? This means it will become visible to website/portal users.': ('PROPOSED-payload', 'هل ترغب في نشر هذا التعليق؟ هذا يعني أنه سيصبح مرئيًا لمستخدمي موقع الويب / البوابة.'),
    'Would you like to unpublish this comment? This means it will no longer be visible to website/portal users.': ('PROPOSED-payload', 'هل ترغب في إلغاء نشر هذا التعليق؟ هذا يعني أنه لن يعود مرئيًا لمستخدمي موقع الويب / البوابة.'),
    'You are about to open an external link. To confirm, click the link again.': ('PROPOSED-payload', 'أنت على وشك فتح رابط خارجي. للتأكيد، انقر على الرابط مرة أخرى.'),
    'You are not allowed to access this resource': ('PROPOSED-payload', 'غير مسموح لك بالوصول إلى هذا المورد'),
    "You are not allowed to access this {0} record because it is linked to {1} '{2}' in row {3}, field {4}": ('PROPOSED-payload', "لا يُسمح لك بالوصول إلى سجل {0} هذا لأنه مرتبط بـ {1} '{2}' في الصف {3}، الحقل {4}"),
    'You are not permitted to access this page without login.': ('PROPOSED-payload', 'لا يُسمح لك بالوصول إلى هذه الصفحة دون تسجيل الدخول.'),
    'You are not permitted to access this resource. Login to access': ('PROPOSED-payload', 'لا يُسمح لك بالوصول إلى هذا المورد. سجّل الدخول للوصول'),
    'You are only allowed to update order, do not remove or add apps.': ('PROPOSED-payload', 'يُسمح لك فقط بتحديث الترتيب، لا تحذف أو تضف تطبيقات.'),
    'You can also access wkhtmltopdf variables (valid only in PDF print):': ('PROPOSED-payload', 'يمكنك أيضًا الوصول إلى متغيرات wkhtmltopdf (صالحة فقط في طباعة PDF):'),
    'You can also copy-paste following link in your browser': ('PROPOSED-payload', 'يمكنك أيضًا نسخ الرابط التالي ولصقه في متصفحك'),
    "You can ask your team to resend the invitation if you'd still like to join.": ('PROPOSED-payload', 'يمكنك أن تطلب من فريقك إعادة إرسال الدعوة إذا كنت لا تزال ترغب في الانضمام.'),
    'You can change Submitted documents by cancelling them and then, amending them.': ('PROPOSED-payload', 'يمكنك تغيير المستندات المرسلة عن طريق إلغائها ثم تعديلها.'),
    'You can change the retention policy from {0}.': ('PROPOSED-payload', 'يمكنك تغيير سياسة الاحتفاظ من {0}.'),
    'You can continue with the onboarding after exploring this page': ('PROPOSED-payload', 'يمكنك متابعة التهيئة بعد استكشاف هذه الصفحة'),
    'You can disable this {0} instead of deleting it.': ('PROPOSED-payload', 'يمكنك تعطيل {0} هذا بدلاً من حذفه.'),
    'You can increase the limit from System Settings.': ('PROPOSED-payload', 'يمكنك زيادة الحد من إعدادات النظام.'),
    "You can manually remove the lock if you think it's safe: {}": ('PROPOSED-payload', 'يمكنك إزالة القفل يدويًا إذا كنت تعتقد أنه آمن: {}'),
    'You can only insert images in Markdown fields': ('PROPOSED-payload', 'يمكنك فقط إدراج الصور في حقول Markdown'),
    'You can only print upto {0} documents at a time': ('PROPOSED-payload', 'يمكنك فقط طباعة ما يصل إلى {0} من المستندات في المرة الواحدة'),
    'You can only set the 3 custom doctypes in the Document Types table.': ('PROPOSED-payload', 'يمكنك فقط تعيين أنواع المستندات المخصصة الثلاثة في جدول أنواع المستندات.'),
    'You can only upload JPG, PNG, GIF, PDF, TXT, CSV or Microsoft documents.': ('PROPOSED-payload', 'يمكنك فقط تحميل ملفات JPG أو PNG أو GIF أو PDF أو TXT أو CSV أو مستندات Microsoft.'),
    'You can set a high value here if multiple users will be logging in from the same network.': ('PROPOSED-payload', 'يمكنك تعيين قيمة عالية هنا إذا كان عدة مستخدمين سيسجلون الدخول من نفس الشبكة.'),
    'You can use Customize Form to set levels on fields.': ('PROPOSED-payload', 'يمكنك استخدام تخصيص النموذج لتعيين مستويات على الحقول.'),
    'You do not have Read or Select Permissions for {}': ('PROPOSED-payload', 'ليس لديك أذونات القراءة أو التحديد لـ {}'),
    'You do not have import permission for {0}': ('PROPOSED-payload', 'ليس لديك إذن استيراد لـ {0}'),
    'You do not have permission to access field: {0}': ('PROPOSED-payload', 'ليس لديك إذن للوصول إلى الحقل: {0}'),
    'You do not have permission to access {0}: {1}.': ('PROPOSED-payload', 'ليس لديك إذن للوصول إلى {0}: {1}.'),
    'You don\'t have permission to access the {0} DocType.': ('PROPOSED-payload', 'ليس لديك إذن للوصول إلى نوع المستند {0}.'),
    'You have hit the row size limit on database table: {0}': ('PROPOSED-payload', 'لقد وصلت إلى الحد الأقصى لحجم الصف في جدول قاعدة البيانات: {0}'),
    'You have not entered a value. The field will be set to empty.': ('PROPOSED-payload', 'لم تقم بإدخال قيمة. سيتم تعيين الحقل كفارغ.'),
    'You have to enable Two Factor Auth from System Settings.': ('PROPOSED-payload', 'يجب عليك تمكين المصادقة الثنائية من إعدادات النظام.'),
    'You hit the rate limit because of too many requests. Please try after sometime.': ('PROPOSED-payload', 'لقد تجاوزت حد المعدل بسبب كثرة الطلبات. يرجى المحاولة بعد بعض الوقت.'),
    "You need the '{0}' permission on {1} {2} to perform this action.": ('PROPOSED-payload', "تحتاج إلى إذن '{0}' على {1} {2} لتنفيذ هذا الإجراء."),
    'You need to be Workspace Manager to delete a public workspace.': ('PROPOSED-payload', 'يجب أن تكون مدير مساحة العمل لحذف مساحة عمل عامة.'),
    'You need to be Workspace Manager to edit this document': ('PROPOSED-payload', 'يجب أن تكون مدير مساحة العمل لتعديل هذا المستند'),
    'You need to be a system user to access this page.': ('PROPOSED-payload', 'يجب أن تكون مستخدم نظام للوصول إلى هذه الصفحة.'),
    'You need to select indexes you want to add first.': ('PROPOSED-payload', 'تحتاج إلى تحديد الفهارس التي تريد إضافتها أولاً.'),
    'You need write permission on {0} {1} to merge': ('PROPOSED-payload', 'تحتاج إلى إذن كتابة على {0} {1} للدمج'),
    'You need write permission on {0} {1} to rename': ('PROPOSED-payload', 'تحتاج إلى إذن كتابة على {0} {1} لإعادة التسمية'),
    'You need {0} permission to fetch values from {1} {2}': ('PROPOSED-payload', 'تحتاج إلى إذن {0} لجلب القيم من {1} {2}'),
    'You seem to have written your name instead of your email. Please enter a valid email address so that we can get back.': ('PROPOSED-payload', 'يبدو أنك كتبت اسمك بدلاً من بريدك الإلكتروني. يرجى إدخال عنوان بريد إلكتروني صالح حتى نتمكن من الرد.'),
    'Your browser does not support the audio element.': ('PROPOSED-payload', 'متصفحك لا يدعم عنصر الصوت.'),
    'Your browser does not support the video element.': ('PROPOSED-payload', 'متصفحك لا يدعم عنصر الفيديو.'),
    'Your invitation to join {0} has been cancelled by the site administrator.': ('PROPOSED-payload', 'تم إلغاء دعوتك للانضمام إلى {0} بواسطة مسؤول الموقع.'),
    'Your new password has been set successfully.': ('PROPOSED-payload', 'تم تعيين كلمة المرور الجديدة بنجاح.'),
    'Your site is undergoing maintenance or being updated.': ('PROPOSED-payload', 'موقعك يخضع للصيانة أو التحديث.'),
    '`as_iterator` only works with `as_list=True` or `as_dict=True`': ('PROPOSED-payload', 'يعمل `as_iterator` فقط مع `as_list=True` أو `as_dict=True`'),
    '`job_id` paramater is required for deduplication.': ('PROPOSED-payload', 'معلمة `job_id` مطلوبة لإلغاء التكرار.'),
    'gzip not found in PATH! This is required to take a backup.': ('PROPOSED-payload', 'لم يتم العثور على gzip في PATH! هذا مطلوب لأخذ نسخة احتياطية.'),
    'string value, i.e. {0} or uid={0},ou=users,dc=example,dc=com': ('PROPOSED-payload', 'قيمة نصية، أي {0} أو uid={0},ou=users,dc=example,dc=com'),
    'wants to access the following details from your account': ('PROPOSED-payload', 'يريد الوصول إلى التفاصيل التالية من حسابك'),
    'when clicked on element it will focus popover if present.': ('PROPOSED-payload', 'عند النقر فوق العنصر، سيتم التركيز على النافذة المنبثقة إذا كانت موجودة.'),
    '{0} ${skip_list ? "" : type}': ('EXCEPTION-technical', ''),
    '{0} Not allowed to change {1} after submission from {2} to {3}': ('PROPOSED-payload', '{0} غير مسموح بتغيير {1} بعد الإرسال من {2} إلى {3}'),
    '{0} cannot be amended because it is not cancelled. Please cancel the document before creating an amendment.': ('PROPOSED-payload', 'لا يمكن تعديل {0} لأنه لم يتم إلغاؤه. يرجى إلغاء المستند قبل إنشاء تعديل.'),
    '{0} cannot be hidden and mandatory without any default value': ('PROPOSED-payload', 'لا يمكن أن يكون {0} مخفيًا وإلزاميًا دون أي قيمة افتراضية'),
    "{0} contains an invalid Fetch From expression, Fetch From can't be self-referential.": ('PROPOSED-payload', 'يحتوي {0} على تعبير جلب من غير صالح، لا يمكن أن يكون "جلب من" مرجعيًا ذاتيًا.'),
    '{0} format could not be determined from the values in this column. Defaulting to {1}.': ('PROPOSED-payload', 'تعذر تحديد تنسيق {0} من القيم الموجودة في هذا العمود. تم الرجوع إلى القيمة الافتراضية {1}.'),
    '{0} if you are not redirected within {1} seconds': ('PROPOSED-payload', '{0} إذا لم تتم إعادة توجيهك خلال {1} ثوانٍ'),
    '{0} is not a valid Calendar. Redirecting to default Calendar.': ('PROPOSED-payload', '{0} ليس تقويمًا صالحًا. جارٍ إعادة التوجيه إلى التقويم الافتراضي.'),
    '{0} is not a valid ISO 3166 ALPHA-2 code.': ('PROPOSED-payload', '{0} ليس رمز ISO 3166 ALPHA-2 صالحًا.'),
    '{0} is not a valid parent DocType for {1}': ('PROPOSED-payload', '{0} ليس نوع مستند رئيسي صالح لـ {1}'),
    '{0} just impersonated as you. They gave this reason: {1}': ('PROPOSED-payload', '{0} قام بانتحال صفتك للتو. وأبدى هذا السبب: {1}'),
    '{0} must begin and end with a letter and can only contain letters, hyphen or underscore.': ('PROPOSED-payload', 'يجب أن يبدأ {0} وينتهي بحرف ولا يمكن أن يحتوي إلا على أحرف أو شرطة أو شرطة سفلية.'),
    '{0} records are not automatically deleted.': ('PROPOSED-payload', 'سجلات {0} لا يتم حذفها تلقائيًا.'),
    '{0} role does not have permission on any doctype': ('PROPOSED-payload', 'دور {0} ليس لديه إذن على أي نوع مستند'),
    "{0} should be indexed because it's referred in dashboard connections": ('PROPOSED-payload', 'يجب فهرسة {0} لأنه مشار إليه في اتصالات لوحة التحكم'),
    '{0}: Other permission rules may also apply': ('PROPOSED-payload', '{0}: قد تنطبق أيضًا قواعد أذونات أخرى'),
    '{0}: You can increase the limit for the field if required via {1}': ('PROPOSED-payload', '{0}: يمكنك زيادة الحد للحقل إذا لزم الأمر عبر {1}'),
    '{0}: fieldname cannot be set to reserved keyword {1}': ('PROPOSED-payload', '{0}: لا يمكن تعيين اسم الحقل إلى الكلمة المحجوزة {1}'),
    '{} does not support automated log clearing.': ('PROPOSED-payload', '{} لا يدعم المسح الآلي للسجلات.'),
    '{} has been disabled. It can only be enabled if {} is checked.': ('PROPOSED-payload', 'تم تعطيل {}. لا يمكن تمكينه إلا إذا تم تحديد {}.'),
    '{} not found in PATH! This is required to access the console.': ('PROPOSED-payload', 'لم يتم العثور على {} في PATH! هذا مطلوب للوصول إلى وحدة التحكم.'),
    '{} not found in PATH! This is required to restore the database.': ('PROPOSED-payload', 'لم يتم العثور على {} في PATH! هذا مطلوب لاستعادة قاعدة البيانات.'),
    '{} not found in PATH! This is required to take a backup.': ('PROPOSED-payload', 'لم يتم العثور على {} في PATH! هذا مطلوب لأخذ نسخة احتياطية.')
}


def main() -> None:
    with SCOPE_CSV.open(encoding="utf-8", newline="") as h:
        scope_rows = list(csv.DictReader(h))

    assert len(scope_rows) == 244, f"Expected 244 scope rows, got {len(scope_rows)}"
    scope_keys = [r["source_text"] for r in scope_rows]

    # Verify coverage
    missing_in_dict = set(scope_keys) - set(TRANSLATIONS.keys())
    assert not missing_in_dict, f"Missing translations for: {missing_in_dict}"

    extra_in_dict = set(TRANSLATIONS.keys()) - set(scope_keys)
    assert not extra_in_dict, f"Extra translations in dict: {extra_in_dict}"

    proposal_rows = []
    counts = {"preserved-site-override": 0, "EXCEPTION-technical": 0, "PROPOSED-payload": 0}

    for idx, r in enumerate(scope_rows):
        st = r["source_text"]
        disp, trans = TRANSLATIONS[st]
        counts[disp] += 1

        # Validation rules
        if disp == "EXCEPTION-technical":
            assert trans == "", f"Technical exception must have empty translation: {st}"
        else:
            assert trans, f"Payload translation cannot be empty: {st}"
            # Multiset placeholder check
            src_braces = sorted(RE_BRACES.findall(st))
            tr_braces = sorted(RE_BRACES.findall(trans))
            assert src_braces == tr_braces, f"Braces mismatch in row {idx+1}: {st} -> {src_braces} vs {tr_braces}"

            src_perc = sorted(RE_PERCENT.findall(st))
            tr_perc = sorted(RE_PERCENT.findall(trans))
            assert src_perc == tr_perc, f"Percent mismatch in row {idx+1}: {st} -> {src_perc} vs {tr_perc}"

            # Affix parity
            if st.endswith(":"):
                assert trans.endswith(":") or trans.endswith("："), f"Colon affix mismatch in row {idx+1}: {st}"
            if st.endswith("?"):
                assert trans.endswith("؟") or trans.endswith("?"), f"Question mark affix mismatch in row {idx+1}: {st}"

        proposal_rows.append({
            "source_text": st,
            "context": r.get("context", ""),
            "locations": r.get("locations", ""),
            "disposition": disp,
            "proposed_translation": trans,
        })

    # Write proposal CSV
    with PROPOSAL_CSV.open("w", encoding="utf-8", newline="") as h:
        fieldnames = ["source_text", "context", "locations", "disposition", "proposed_translation"]
        writer = csv.DictWriter(h, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(proposal_rows)

    scope_sha = hashlib.sha256(SCOPE_CSV.read_bytes()).hexdigest()
    prop_sha = hashlib.sha256(PROPOSAL_CSV.read_bytes()).hexdigest()

    print(f"Validation successful!")
    print(f"Scope CSV:    {SCOPE_CSV.name} ({len(scope_rows)} rows) SHA-256: {scope_sha}")
    print(f"Proposal CSV: {PROPOSAL_CSV.name} ({len(proposal_rows)} rows) SHA-256: {prop_sha}")
    print(f"Partition counts: {counts}")


if __name__ == "__main__":
    main()
