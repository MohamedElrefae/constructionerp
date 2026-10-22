# Stage 6 — W6-7 Frappe Framework Remainder Batch 02 Proposal (2026-09-27)

**Status:** PROPOSAL ONLY — owner approval pending. No quorum review, no runtime import, no catalog update, no evidence re-pin, no git commit, no git push.

---

## 1. Scope and Artifacts

| Artifact | Path | SHA-256 | Rows |
| :--- | :--- | :--- | :---: |
| **Scope CSV** | `docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv` | `cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3` | 244 |
| **Proposal CSV** | `docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv` | `ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a` | 244 |
| **Site Recon JSON** | `docs/translation/stage6_w607_frappe_batch02_site_recon_2026-09-27.json` | Live reconciliation on `v16.localhost` | 244 |

---

## 2. Partition Summary

| Disposition | Count | Description |
| :--- | :---: | :--- |
| **`preserved-site-override`** | 0 | No active site overrides on `v16.localhost` (all 244 keys missing in runtime `tabTranslation`) |
| **`EXCEPTION-technical`** | 1 | Unresolved JS template literal expression (`{0} ${skip_list ? "" : type}`); empty translation |
| **`PROPOSED-payload`** | 243 | Candidate Arabic translations for Frappe framework UI strings |
| **Total** | **244** | **0 + 1 + 243 = 244** |

---

## 3. Structural Validation Notes

- **Placeholder Multiset Parity:** All placeholders (`{0}`, `{1}`, `{2}`, `{3}`, `{4}`, `{}`, `%s`, `%d`) have exact multiset parity between source and proposed translation.
- **Whitespace & Punctuation Parity:** Colons (`:`), ellipses (`...`), question marks (`؟`/`?`), and whitespace strictly match the source strings.
- **Strict Environmental Isolation:** Non-production test site only (`v16.localhost`). Stage 8 and production remain untouched and gated.

---

## 4. Full 244-Row Proposal Table

| # | Source Text | Proposed Translation | Disposition | Notes |
| :-: | :--- | :--- | :--- | :--- |
| 1 | Please attach an image file to set HTML for Footer. | يرجى إرفاق ملف صورة لتعيين HTML للتذييل. | `PROPOSED-payload` | Valid payload |
| 2 | Please attach an image file to set HTML for Letter Head. | يرجى إرفاق ملف صورة لتعيين HTML للترويسة. | `PROPOSED-payload` | Valid payload |
| 3 | Please check your email login credentials. | يرجى التحقق من بيانات اعتماد تسجيل الدخول إلى بريدك الإلكتروني. | `PROPOSED-payload` | Valid payload |
| 4 | Please click on the following link and follow the instructions on the page. {0} | يرجى النقر فوق الرابط التالي واتباع التعليمات الموجودة في الصفحة. {0} | `PROPOSED-payload` | Valid payload |
| 5 | Please contact your system manager to install correct version. | يرجى الاتصال بمدير النظام لتثبيت الإصدار الصحيح. | `PROPOSED-payload` | Valid payload |
| 6 | Please delete the field from {0} or add the required doctype. | يرجى حذف الحقل من {0} أو إضافة نوع المستند المطلوب. | `PROPOSED-payload` | Valid payload |
| 7 | Please enter both your email and message so that we can get back to you. Thanks! | يرجى إدخال بريدك الإلكتروني ورسالتك حتى نتمكن من الرد عليك. شكرًا! | `PROPOSED-payload` | Valid payload |
| 8 | Please remove the printer mapping in Printer Settings and try again. | يرجى إزالة تعيين الطابعة في إعدادات الطابعة والمحاولة مرة أخرى. | `PROPOSED-payload` | Valid payload |
| 9 | Please save the form before previewing the message | يرجى حفظ النموذج قبل معاينة الرسالة | `PROPOSED-payload` | Valid payload |
| 10 | Please select a DocType in options before setting filters | يرجى تحديد نوع المستند في الخيارات قبل تعيين عوامل التصفية | `PROPOSED-payload` | Valid payload |
| 11 | Please select a country code for field {1}. | يرجى تحديد رمز البلد للحقل {1}. | `PROPOSED-payload` | Valid payload |
| 12 | Please select the LDAP Directory being used | يرجى تحديد دليل LDAP المستخدم | `PROPOSED-payload` | Valid payload |
| 13 | Please setup default outgoing Email Account from Settings > Email Account | يرجى إعداد حساب البريد الإلكتروني الصادر الافتراضي من الإعدادات > حساب البريد الإلكتروني | `PROPOSED-payload` | Valid payload |
| 14 | Please setup default outgoing Email Account from Tools > Email Account | يرجى إعداد حساب البريد الإلكتروني الصادر الافتراضي من أدوات > حساب البريد الإلكتروني | `PROPOSED-payload` | Valid payload |
| 15 | Please specify a valid parent DocType for {0} | يرجى تحديد نوع مستند رئيسي صالح لـ {0} | `PROPOSED-payload` | Valid payload |
| 16 | Please specify at least 10 minutes due to the trigger cadence of the scheduler | يرجى تحديد 10 دقائق على الأقل بسبب وتيرة تشغيل المجدول | `PROPOSED-payload` | Valid payload |
| 17 | Please specify the field from which to attach files | يرجى تحديد الحقل الذي سيتم إرفاق الملفات منه | `PROPOSED-payload` | Valid payload |
| 18 | Please specify which datetime field must be checked | يرجى تحديد حقل التاريخ والوقت الذي يجب التحقق منه | `PROPOSED-payload` | Valid payload |
| 19 | Please use following links to download file backup. | يرجى استخدام الروابط التالية لتنزيل النسخة الاحتياطية للملف. | `PROPOSED-payload` | Valid payload |
| 20 | Please visit https://frappecloud.com/docs/sites/migrate-an-existing-site#encryption-key for more information. | يرجى زيارة https://frappecloud.com/docs/sites/migrate-an-existing-site#encryption-key لمزيد من المعلومات. | `PROPOSED-payload` | Valid payload |
| 21 | Post it here, our mentors will help you out. | انشرها هنا، وسيساعدك موجهونا. | `PROPOSED-payload` | Valid payload |
| 22 | Precision ({0}) for {1} cannot be greater than its length ({2}). | لا يمكن أن تكون دقة ({0}) لـ {1} أكبر من طولها ({2}). | `PROPOSED-payload` | Valid payload |
| 23 | Prepend the template to the email message | إلحاق القالب في بداية رسالة البريد الإلكتروني | `PROPOSED-payload` | Valid payload |
| 24 | Primary key of doctype {0} can not be changed as there are existing values. | لا يمكن تغيير المفتاح الأساسي لنوع المستند {0} لوجود قيم حالية. | `PROPOSED-payload` | Valid payload |
| 25 | Property Setter overrides a standard DocType or Field property | يقوم معدل الخصائص بتجاوز خاصية قياسية لنوع المستند أو الحقل | `PROPOSED-payload` | Valid payload |
| 26 | Query analysis complete. Check suggested indexes. | اكتمل تحليل الاستعلام. تحقق من الفهارس المقترحة. | `PROPOSED-payload` | Valid payload |
| 27 | Query must be of SELECT or read-only WITH type. | يجب أن يكون الاستعلام من نوع SELECT أو WITH للقراءة فقط. | `PROPOSED-payload` | Valid payload |
| 28 | Queued for Submission. You can track the progress over {0}. | تمت الإضافة إلى قائمة انتظار الإرسال. يمكنك متابعة التقدم عبر {0}. | `PROPOSED-payload` | Valid payload |
| 29 | Rebuilding of tree is not supported for {} | إعادة بناء الشجرة غير مدعومة لـ {} | `PROPOSED-payload` | Valid payload |
| 30 | Records for following doctypes will be filtered | سيتم تصفية سجلات أنواع المستندات التالية | `PROPOSED-payload` | Valid payload |
| 31 | Redirect to this URL after successful confirmation. | إعادة التوجيه إلى عنوان URL هذا بعد التأكيد الناجح. | `PROPOSED-payload` | Valid payload |
| 32 | Render labels to the left and values to the right in this section | عرض التسميات على اليسار والقيم على اليمين في هذا القسم | `PROPOSED-payload` | Valid payload |
| 33 | Represents the states allowed in one document and role assigned to change the state. | يمثل الحالات المسموح بها في مستند واحد والدور المعين لتغيير الحالة. | `PROPOSED-payload` | Valid payload |
| 34 | Requires any valid fdn path. i.e. ou=groups,dc=example,dc=com | يتطلب أي مسار fdn صالح، مثل: ou=groups,dc=example,dc=com | `PROPOSED-payload` | Valid payload |
| 35 | Requires any valid fdn path. i.e. ou=users,dc=example,dc=com | يتطلب أي مسار fdn صالح، مثل: ou=users,dc=example,dc=com | `PROPOSED-payload` | Valid payload |
| 36 | Role 'All' will be given to all system + website users. | سيتم منح دور 'الكل' لجميع مستخدمي النظام وموقع الويب. | `PROPOSED-payload` | Valid payload |
| 37 | Role 'Desk User' will be given to all system users. | سيتم منح دور 'مستخدم المكتب' لجميع مستخدمي النظام. | `PROPOSED-payload` | Valid payload |
| 38 | Role has been set as per the user type {0} | تم تعيين الدور وفقًا لنوع المستخدم {0} | `PROPOSED-payload` | Valid payload |
| 39 | Roles can be set for users from their User page. | يمكن تعيين الأدوار للمستخدمين من صفحة المستخدم الخاصة بهم. | `PROPOSED-payload` | Valid payload |
| 40 | Route: Example "/app" | المسار: مثال "/app" | `PROPOSED-payload` | Valid payload |
| 41 | Row # {0}: Non administrator user can not set the role {1} to the custom doctype | الصف رقم {0}: لا يمكن للمستخدم غير المسؤول تعيين الدور {1} لنوع المستند المخصص | `PROPOSED-payload` | Valid payload |
| 42 | Rule for this doctype, role, permlevel and if-owner combination already exists. | توجد قاعدة بالفعل لمجموعة نوع المستند والدور ومستوى الأذونات وحالة المالك هذه. | `PROPOSED-payload` | Valid payload |
| 43 | SMS was not sent. Please contact Administrator. | لم يتم إرسال الرسالة النصية القصيرة. يرجى الاتصال بالمسؤول. | `PROPOSED-payload` | Valid payload |
| 44 | SQL functions are not allowed as strings in SELECT: {0}. Use dict syntax like {{'COUNT': '*'}} instead. | دوال SQL غير مسموح بها كسلاسل نصية في SELECT: {0}. استخدم بناء جملة القاموس مثل {{'COUNT': '*'}} بدلاً من ذلك. | `PROPOSED-payload` | Valid payload |
| 45 | Saving this will export this document as well as the steps linked here as json. | سيؤدي حفظ هذا إلى تصدير هذا المستند بالإضافة إلى الخطوات المرتبطة به كملف json. | `PROPOSED-payload` | Valid payload |
| 46 | Scheduler can not be re-enabled when maintenance mode is active. | لا يمكن إعادة تمكين المجدول عندما يكون وضع الصيانة نشطًا. | `PROPOSED-payload` | Valid payload |
| 47 | Scheduler is inactive. Cannot import data. | المجدول غير نشط. لا يمكن استيراد البيانات. | `PROPOSED-payload` | Valid payload |
| 48 | Select Document Types to set which User Permissions are used to limit access. | حدد أنواع المستندات لتعيين أذونات المستخدم المستخدمة لتقييد الوصول. | `PROPOSED-payload` | Valid payload |
| 49 | Select an existing format to edit or start a new format. | حدد تنسيقًا حاليًا لتعديله أو ابدأ تنسيقًا جديدًا. | `PROPOSED-payload` | Valid payload |
| 50 | Send alert if datetime matches this field's value | إرسال تنبيه إذا تطابق التاريخ والوقت مع قيمة هذا الحقل | `PROPOSED-payload` | Valid payload |
| 51 | Send email when document transitions to the state. | إرسال بريد إلكتروني عند انتقال المستند إلى هذه الحالة. | `PROPOSED-payload` | Valid payload |
| 52 | Series counter for {} updated to {} successfully | تم تحديث عداد السلسلة لـ {} إلى {} بنجاح | `PROPOSED-payload` | Valid payload |
| 53 | Server Scripts are disabled. Please enable server scripts from bench configuration. | البرامج النصية للخادم معطلة. يرجى تمكين البرامج النصية للخادم من تكوين bench. | `PROPOSED-payload` | Valid payload |
| 54 | Server Scripts feature is not available on this site. | ميزة البرامج النصية للخادم غير متوفرة في هذا الموقع. | `PROPOSED-payload` | Valid payload |
| 55 | Server failed to process this request because of a concurrent conflicting request. Please try again. | فشل الخادم في معالجة هذا الطلب بسبب تعارض مع طلب متزامن. يرجى المحاولة مرة أخرى. | `PROPOSED-payload` | Valid payload |
| 56 | Server was too busy to process this request. Please try again. | الخادم مشغول للغاية ولا يمكنه معالجة هذا الطلب. يرجى المحاولة مرة أخرى. | `PROPOSED-payload` | Valid payload |
| 57 | Set Naming Series options on your transactions. | تعيين خيارات سلسلة التسمية لمعاملاتك. | `PROPOSED-payload` | Valid payload |
| 58 | Set dynamic filter values in JavaScript for the required fields here. | عيّن قيم التصفية الديناميكية في JavaScript للحقول المطلوبة هنا. | `PROPOSED-payload` | Valid payload |
| 59 | Set non-standard precision for a Float, Currency or Percent field | تعيين دقة غير قياسية لحقل عشري أو عملة أو نسبة مئوية | `PROPOSED-payload` | Valid payload |
| 60 | Show Fieldname (click to copy on clipboard) | إظهار اسم الحقل (انقر للنسخ إلى الحافظة) | `PROPOSED-payload` | Valid payload |
| 61 | Show Social Login Key as Authorization Server | إظهار مفتاح تسجيل الدخول الاجتماعي كخادم تفويض | `PROPOSED-payload` | Valid payload |
| 62 | Show account deletion link in My Account page | إظهار رابط حذف الحساب في صفحة حسابي | `PROPOSED-payload` | Valid payload |
| 63 | Size exceeds the maximum allowed file size. | الحجم يتجاوز الحد الأقصى المسموح به لحجم الملف. | `PROPOSED-payload` | Valid payload |
| 64 | Skipping fixture syncing for doctype {0} from file {1} | تخطي مزامنة التركيبات لنوع المستند {0} من الملف {1} | `PROPOSED-payload` | Valid payload |
| 65 | Some columns might get cut off when printing to PDF. Try to keep number of columns under 10. | قد يتم اقتطاع بعض الأعمدة عند الطباعة إلى PDF. حاول الحفاظ على عدد الأعمدة أقل من 10. | `PROPOSED-payload` | Valid payload |
| 66 | Some mailboxes require a different Sent Folder Name e.g. "INBOX.Sent" | تتطلب بعض صناديق البريد اسمًا مختلفًا لمجلد العناصر المرسلة مثل "INBOX.Sent" | `PROPOSED-payload` | Valid payload |
| 67 | Specify a custom timeout, default timeout is 1500 seconds | تحديد مهلة مخصصة، المهلة الافتراضية هي 1500 ثانية | `PROPOSED-payload` | Valid payload |
| 68 | Standard Web Forms can not be modified, duplicate the Web Form instead. | لا يمكن تعديل نماذج الويب القياسية، قم بتكرار نموذج الويب بدلاً من ذلك. | `PROPOSED-payload` | Valid payload |
| 69 | Standard user type {0} can not be deleted. | لا يمكن حذف نوع المستخدم القياسي {0}. | `PROPOSED-payload` | Valid payload |
| 70 | Status Updated. The email will be picked up in the next scheduled run. | تم تحديث الحالة. سيتم التقاط البريد الإلكتروني في التشغيل المجدول التالي. | `PROPOSED-payload` | Valid payload |
| 71 | Store the API secret securely. It won't be displayed again. | احفظ سر واجهة برمجة التطبيقات بأمان. لن يتم عرضه مرة أخرى. | `PROPOSED-payload` | Valid payload |
| 72 | Stores the datetime when the last reset password key was generated. | يخزن التاريخ والوقت عند إنشاء آخر مفتاح لإعادة تعيين كلمة المرور. | `PROPOSED-payload` | Valid payload |
| 73 | Successfully imported {0} out of {1} records. | تم استيراد {0} من أصل {1} سجلاً بنجاح. | `PROPOSED-payload` | Valid payload |
| 74 | Successfully reset onboarding status for all users. | تمت إعادة تعيين حالة التهيئة لجميع المستخدمين بنجاح. | `PROPOSED-payload` | Valid payload |
| 75 | Successfully updated {0} out of {1} records. | تم تحديث {0} من أصل {1} سجلاً بنجاح. | `PROPOSED-payload` | Valid payload |
| 76 | Sync token was invalid and has been reset, Retry syncing. | رمز المزامنة غير صالح وتمت إعادة تعيينه، أعد محاولة المزامنة. | `PROPOSED-payload` | Valid payload |
| 77 | System Generated Fields can not be renamed | لا يمكن إعادة تسمية الحقول التي تم إنشاؤها بواسطة النظام | `PROPOSED-payload` | Valid payload |
| 78 | Thank you for spending your valuable time to fill this form | شكرًا لك على قضاء وقتك الثمين لملء هذا النموذج | `PROPOSED-payload` | Valid payload |
| 79 | The Next Scheduled Date cannot be later than the End Date. | لا يمكن أن يكون التاريخ المجدول التالي بعد تاريخ الانتهاء. | `PROPOSED-payload` | Valid payload |
| 80 | The Push Relay Server URL key (`push_relay_server_url`) is missing in your site config | مفتاح عنوان URL لخادم ترحيل الإشعارات (`push_relay_server_url`) مفقود في تكوين موقعك | `PROPOSED-payload` | Valid payload |
| 81 | The User record for this request has been auto-deleted due to inactivity by system admins. | تم حذف سجل المستخدم لهذا الطلب تلقائيًا بسبب عدم النشاط بواسطة مسؤولي النظام. | `PROPOSED-payload` | Valid payload |
| 82 | The application name will be used in the Login page. | سيتم استخدام اسم التطبيق في صفحة تسجيل الدخول. | `PROPOSED-payload` | Valid payload |
| 83 | The contents of this email are strictly confidential. Please do not forward this email to anyone. | محتويات هذا البريد الإلكتروني سرية للغاية. يرجى عدم إعادة توجيه هذا البريد الإلكتروني لأي شخص. | `PROPOSED-payload` | Valid payload |
| 84 | The count shown is an estimated count. Click here to see the accurate count. | العدد الموضح هو عدد تقديري. انقر هنا لرؤية العدد الدقيق. | `PROPOSED-payload` | Valid payload |
| 85 | The document type selected is a child table, so the parent document type is required. | نوع المستند المحدد هو جدول فرعي، لذا يلزم تحديد نوع المستند الرئيسي. | `PROPOSED-payload` | Valid payload |
| 86 | The field {0} in {1} does not allow ignoring user permissions | الحقل {0} في {1} لا يسمح بتجاهل أذونات المستخدم | `PROPOSED-payload` | Valid payload |
| 87 | The field {0} in {1} links to {2} and not {3} | الحقل {0} في {1} يرتبط بـ {2} وليس {3} | `PROPOSED-payload` | Valid payload |
| 88 | The fieldname you've specified in Attached To Field is invalid | اسم الحقل الذي حددته في حقل "مرفق بـ" غير صالح | `PROPOSED-payload` | Valid payload |
| 89 | The following Assignment Days have been repeated: {0} | تم تكرار أيام التعيين التالية: {0} | `PROPOSED-payload` | Valid payload |
| 90 | The following Header Script will add the current date to an element in 'Header HTML' with class 'header-content' | سيقوم البرنامج النصي للترويسة التالي بإضافة التاريخ الحالي إلى عنصر في 'Header HTML' بفئة 'header-content' | `PROPOSED-payload` | Valid payload |
| 91 | The following values are invalid: {0}. Values must be one of {1} | القيم التالية غير صالحة: {0}. يجب أن تكون القيم واحدة من {1} | `PROPOSED-payload` | Valid payload |
| 92 | The following values do not exist for {0}: {1} | القيم التالية غير موجودة لـ {0}: {1} | `PROPOSED-payload` | Valid payload |
| 93 | The limit has not set for the user type {0} in the site config file. | لم يتم تعيين الحد لنوع المستخدم {0} في ملف تكوين الموقع. | `PROPOSED-payload` | Valid payload |
| 94 | The link you trying to login is invalid or expired. | الرابط الذي تحاول تسجيل الدخول منه غير صالح أو منتهي الصلاحية. | `PROPOSED-payload` | Valid payload |
| 95 | The next tour will start from where the user left off. | ستبدأ الجولة التالية من حيث توقف المستخدم. | `PROPOSED-payload` | Valid payload |
| 96 | The number of seconds until the request expires | عدد الثواني حتى انتهاء صلاحية الطلب | `PROPOSED-payload` | Valid payload |
| 97 | The reset password link has either been used before or is invalid | رابط إعادة تعيين كلمة المرور إما تم استخدامه من قبل أو أنه غير صالح | `PROPOSED-payload` | Valid payload |
| 98 | The system is being updated. Please refresh again after a few moments. | يتم تحديث النظام. يرجى التحديث مرة أخرى بعد لحظات. | `PROPOSED-payload` | Valid payload |
| 99 | The system provides many pre-defined roles. You can add new roles to set finer permissions. | يوفر النظام العديد من الأدوار المحددة مسبقًا. يمكنك إضافة أدوار جديدة لتعيين أذونات أكثر دقة. | `PROPOSED-payload` | Valid payload |
| 100 | The total number of user document types limit has been crossed. | تم تجاوز الحد الإجمالي لعدد أنواع مستندات المستخدم. | `PROPOSED-payload` | Valid payload |
| 101 | The value you pasted was {0} characters long. Max allowed characters is {1}. | القيمة التي قمت بلصقها كانت بطول {0} حرفًا. الحد الأقصى للأحرف المسموح بها هو {1}. | `PROPOSED-payload` | Valid payload |
| 102 | There are no {0} for this {1}, why don't you start one! | لا توجد {0} لـ {1} هذا، لمَ لا تبدأ واحدة! | `PROPOSED-payload` | Valid payload |
| 103 | There are {0} with the same filters already in the queue: | توجد {0} بنفس عوامل التصفية بالفعل في قائمة الانتظار: | `PROPOSED-payload` | Valid payload |
| 104 | There can be only 9 Page Break fields in a Web Form | يمكن أن يوجد 9 حقول فاصل صفحات فقط في نموذج الويب | `PROPOSED-payload` | Valid payload |
| 105 | There is no task called "{}" | لا توجد مهمة تسمى "{}" | `PROPOSED-payload` | Valid payload |
| 106 | There is nothing new to show you right now. | لا يوجد شيء جديد لعرضه لك الآن. | `PROPOSED-payload` | Valid payload |
| 107 | There is {0} with the same filters already in the queue: | يوجد {0} بنفس عوامل التصفية بالفعل في قائمة الانتظار: | `PROPOSED-payload` | Valid payload |
| 108 | There were errors while sending email. Please try again. | حدثت أخطاء أثناء إرسال البريد الإلكتروني. يرجى المحاولة مرة أخرى. | `PROPOSED-payload` | Valid payload |
| 109 | These announcements will appear inside a dismissible alert below the Navbar. | ستظهر هذه الإعلانات داخل تنبيه قابل للإغلاق أسفل شريط التنقل. | `PROPOSED-payload` | Valid payload |
| 110 | These settings are required if 'Custom' LDAP Directory is used | هذه الإعدادات مطلوبة في حالة استخدام دليل LDAP 'مخصص' | `PROPOSED-payload` | Valid payload |
| 111 | This PDF cannot be uploaded as it contains unsafe content. | لا يمكن تحميل ملف PDF هذا لأنه يحتوي على محتوى غير آمن. | `PROPOSED-payload` | Valid payload |
| 112 | This action is irreversible. Do you wish to continue? | هذا الإجراء لا يمكن التراجع عنه. هل ترغب في الاستمرار؟ | `PROPOSED-payload` | Valid payload |
| 113 | This doctype has no orphan fields to trim | لا يحتوي نوع المستند هذا على حقول مهملة لقصها | `PROPOSED-payload` | Valid payload |
| 114 | This doctype has pending migrations, run 'bench migrate' before modifying the doctype to avoid losing changes. | يحتوي نوع المستند هذا على ترحيلات معلقة، قم بتشغيل 'bench migrate' قبل تعديل نوع المستند لتجنب فقدان التغييرات. | `PROPOSED-payload` | Valid payload |
| 115 | This document can not be deleted right now as it's being modified by another user. Please try again after some time. | لا يمكن حذف هذا المستند الآن لأنه قيد التعديل بواسطة مستخدم آخر. يرجى المحاولة مرة أخرى بعد فترة. | `PROPOSED-payload` | Valid payload |
| 116 | This document has already been queued for submission. You can track the progress over {0}. | تمت إضافة هذا المستند بالفعل إلى قائمة انتظار الإرسال. يمكنك متابعة التقدم عبر {0}. | `PROPOSED-payload` | Valid payload |
| 117 | This document is currently locked and queued for execution. Please try again after some time. | هذا المستند مقفل حاليًا ومدرج في قائمة انتظار التنفيذ. يرجى المحاولة بعد بعض الوقت. | `PROPOSED-payload` | Valid payload |
| 118 | This feature is brand new and still experimental | هذه الميزة جديدة تمامًا ولا تزال تجريبية | `PROPOSED-payload` | Valid payload |
| 119 | This file is attached to a protected document and cannot be deleted. | هذا الملف مرفق بمستند محمي ولا يمكن حذفه. | `PROPOSED-payload` | Valid payload |
| 120 | This file is public and can be accessed by anyone, even without logging in. Mark it private to limit access. | هذا الملف عام ويمكن لأي شخص الوصول إليه حتى بدون تسجيل الدخول. قم بتعيينه كخاص لتقييد الوصول. | `PROPOSED-payload` | Valid payload |
| 121 | This file is public. It can be accessed without authentication. | هذا الملف عام. يمكن الوصول إليه بدون مصادقة. | `PROPOSED-payload` | Valid payload |
| 122 | This form is not editable due to a Workflow. | هذا النموذج غير قابل للتعديل بسبب مسار العمل. | `PROPOSED-payload` | Valid payload |
| 123 | This geolocation provider is not supported yet. | مزود الموقع الجغرافي هذا غير مدعوم بعد. | `PROPOSED-payload` | Valid payload |
| 124 | This is a virtual doctype and data is cleared periodically. | هذا نوع مستند افتراضي ويتم مسح البيانات بشكل دوري. | `PROPOSED-payload` | Valid payload |
| 125 | This report contains {0} rows and is too big to display in browser, you can {1} this report instead. | يحتوي هذا التقرير على {0} صفاً وهو كبير جدًا بحيث لا يمكن عرضه في المتصفح، يمكنك {1} هذا التقرير بدلاً من ذلك. | `PROPOSED-payload` | Valid payload |
| 126 | This site is in read only mode, full functionality will be restored soon. | هذا الموقع في وضع القراءة فقط، وستتم استعادة الوظائف الكاملة قريبًا. | `PROPOSED-payload` | Valid payload |
| 127 | This site is running in developer mode. Any change made here will be updated in code. | يعمل هذا الموقع في وضع المطور. أي تغيير يتم إجراؤه هنا سيتم تحديثه في الكود البرمجي. | `PROPOSED-payload` | Valid payload |
| 128 | This software is built on top of many open source packages. | تم بناء هذا البرنامج على العديد من الحزم مفتوحة المصدر. | `PROPOSED-payload` | Valid payload |
| 129 | This value is fetched from {0}'s {1} field | يتم جلب هذه القيمة من حقل {1} الخاص بـ {0} | `PROPOSED-payload` | Valid payload |
| 130 | This value specifies the max number of rows that can be rendered in report view. | تحدد هذه القيمة الحد الأقصى لعدد الصفوف التي يمكن عرضها في عرض التقرير. | `PROPOSED-payload` | Valid payload |
| 131 | This will reset this tour and show it to all users. Are you sure? | سيؤدي هذا إلى إعادة تعيين هذه الجولة وعرضها لجميع المستخدمين. هل أنت متأكد؟ | `PROPOSED-payload` | Valid payload |
| 132 | This will terminate the job immediately and might be dangerous, are you sure? | سيؤدي هذا إلى إنهاء الوظيفة فورًا وقد يكون خطيرًا، هل أنت متأكد؟ | `PROPOSED-payload` | Valid payload |
| 133 | To allow more reports update limit in System Settings. | للسماح بمزيد من التقارير، قم بتحديث الحد في إعدادات النظام. | `PROPOSED-payload` | Valid payload |
| 134 | To export this step as JSON, link it in a Onboarding document and save the document. | لتصدير هذه الخطوة كـ JSON، اربطها في مستند تهيئة واحفظ المستند. | `PROPOSED-payload` | Valid payload |
| 135 | To set the role {0} in the user {1}, kindly set the {2} field as {3} in one of the {4} record. | لتعيين الدور {0} للمستخدم {1}، يرجى تعيين الحقل {2} كـ {3} في أحد سجلات {4}. | `PROPOSED-payload` | Valid payload |
| 136 | Too many changes to database in single action. | تغييرات كثيرة جدًا على قاعدة البيانات في إجراء واحد. | `PROPOSED-payload` | Valid payload |
| 137 | Too many queued background jobs ({0}). Please retry after some time. | وظائف خلفية كثيرة جدًا في قائمة الانتظار ({0}). يرجى إعادة المحاولة بعد بعض الوقت. | `PROPOSED-payload` | Valid payload |
| 138 | Total number of emails to sync in initial sync process | إجمالي عدد رسائل البريد الإلكتروني المطلوب مزامنتها في عملية المزامنة الأولية | `PROPOSED-payload` | Valid payload |
| 139 | Tracking URL generated and copied to clipboard | تم إنشاء رابط التتبع ونسخه إلى الحافظة | `PROPOSED-payload` | Valid payload |
| 140 | URL of a human-readable page with info that developers might need. | عنوان URL لصفحة مقروءة تتضمن معلومات قد يحتاجها المطورون. | `PROPOSED-payload` | Valid payload |
| 141 | URL of a web page providing information about the client. | عنوان URL لصفحة ويب تقدم معلومات حول العميل. | `PROPOSED-payload` | Valid payload |
| 142 | URL of human-readable page with info about the protected resource's terms of service. | عنوان URL لصفحة مقروءة تتضمن معلومات حول شروط خدمة المورد المحمي. | `PROPOSED-payload` | Valid payload |
| 143 | URL of human-readable page with info on requirements about how the client can use the data. | عنوان URL لصفحة مقروءة تتضمن معلومات حول متطلبات كيفية استخدام العميل للبيانات. | `PROPOSED-payload` | Valid payload |
| 144 | URL that points to a human-readable policy document for the client. Should be shown to end-user before authorizing. | عنوان URL يشير إلى وثيقة سياسة مقروءة للعميل. ينبغي عرضها على المستخدم النهائي قبل التفويض. | `PROPOSED-payload` | Valid payload |
| 145 | URL that references a logo for the client. | عنوان URL يشير إلى شعار العميل. | `PROPOSED-payload` | Valid payload |
| 146 | Unable to send mail because of a missing email account. Please setup default Email Account from Settings > Email Account | تعذر إرسال البريد بسبب عدم وجود حساب بريد إلكتروني. يرجى إعداد حساب بريد إلكتروني افتراضي من الإعدادات > حساب البريد الإلكتروني | `PROPOSED-payload` | Valid payload |
| 147 | Updating Email Queue Statuses. The emails will be picked up in the next scheduled run. | جارٍ تحديث حالات قائمة انتظار البريد الإلكتروني. سيتم التقاط رسائل البريد الإلكتروني في التشغيل المجدول التالي. | `PROPOSED-payload` | Valid payload |
| 148 | Updating counter may lead to document name conflicts if not done properly | قد يؤدي تحديث العداد إلى تعارض في أسماء المستندات إذا لم يتم بشكل صحيح | `PROPOSED-payload` | Valid payload |
| 149 | Use if the default settings don't seem to detect your data correctly | استخدم هذا إذا كانت الإعدادات الافتراضية لا تكتشف بياناتك بشكل صحيح | `PROPOSED-payload` | Valid payload |
| 150 | Use this, for example, if all sent emails should also be send to an archive. | استخدم هذا، على سبيل المثال، إذا كان يجب أيضًا إرسال جميع رسائل البريد الإلكتروني المرسلة إلى الأرشيف. | `PROPOSED-payload` | Valid payload |
| 151 | User Id Field is mandatory in the user type {0} | حقل معرف المستخدم إلزامي في نوع المستخدم {0} | `PROPOSED-payload` | Valid payload |
| 152 | User Permissions are used to limit users to specific records. | تُستخدم أذونات المستخدم لتقييد المستخدمين بسجلات محددة. | `PROPOSED-payload` | Valid payload |
| 153 | User does not have permission to create the new {0} | لا يملك المستخدم الإذن لإنشاء {0} الجديد | `PROPOSED-payload` | Valid payload |
| 154 | User with email address {0} does not exist | المستخدم ذو عنوان البريد الإلكتروني {0} غير موجود | `PROPOSED-payload` | Valid payload |
| 155 | User with email: {0} does not exist in the system. Please ask 'System Administrator' to create the user for you. | المستخدم ذو البريد الإلكتروني: {0} غير موجود في النظام. يرجى مطالبة 'مسؤول النظام' بإنشاء المستخدم لك. | `PROPOSED-payload` | Valid payload |
| 156 | User {0} does not have the permission to create a Workspace. | لا يملك المستخدم {0} الإذن لإنشاء مساحة عمل. | `PROPOSED-payload` | Valid payload |
| 157 | User {0} is disabled. Please contact your System Manager. | المستخدم {0} معطل. يرجى الاتصال بمدير النظام. | `PROPOSED-payload` | Valid payload |
| 158 | User {0} is not permitted to access this document. | لا يُسمح للمستخدم {0} بالوصول إلى هذا المستند. | `PROPOSED-payload` | Valid payload |
| 159 | Uses system's theme to switch between light and dark mode | يستخدم سمة النظام للتبديل بين الوضع الفاتح والداكن | `PROPOSED-payload` | Valid payload |
| 160 | Verification code email not sent. Please contact Administrator. | لم يتم إرسال رسالة رمز التحقق عبر البريد الإلكتروني. يرجى الاتصال بالمسؤول. | `PROPOSED-payload` | Valid payload |
| 161 | Virtual DocType {} requires a static method called {} found {} | نوع المستند الافتراضي {} يتطلب دالة ثابتة تسمى {} تم العثور على {} | `PROPOSED-payload` | Valid payload |
| 162 | Virtual DocType {} requires overriding an instance method called {} found {} | نوع المستند الافتراضي {} يتطلب تجاوز دالة مثيل تسمى {} تم العثور على {} | `PROPOSED-payload` | Valid payload |
| 163 | Warning: DATA LOSS IMMINENT! Proceeding will permanently delete following database columns from doctype {0}: | تحذير: فقدان البيانات وشيك! المتابعة ستؤدي إلى حذف أعمدة قاعدة البيانات التالية نهائيًا من نوع المستند {0}: | `PROPOSED-payload` | Valid payload |
| 164 | Warning: Updating counter may lead to document name conflicts if not done properly | تحذير: قد يؤدي تحديث العداد إلى تعارض في أسماء المستندات إذا لم يتم بشكل صحيح | `PROPOSED-payload` | Valid payload |
| 165 | Warning: Usage of 'format:' is discouraged. | تحذير: لا ينصح باستخدام 'format:'. | `PROPOSED-payload` | Valid payload |
| 166 | We would like to thank the authors of these packages for their contribution. | نود أن نشكر مؤلفي هذه الحزم على مساهمتهم. | `PROPOSED-payload` | Valid payload |
| 167 | Will add "%" before and after the query | سيضيف "%" قبل الاستعلام وبعده | `PROPOSED-payload` | Valid payload |
| 168 | Will run scheduled jobs only once a day for inactive sites. Set it to 0 to avoid automatically disabling the scheduler. | سيتم تشغيل الوظائف المجدولة مرة واحدة فقط يوميًا للمواقع غير النشطة. عيّنها إلى 0 لتجنب تعطيل المجدول تلقائيًا. | `PROPOSED-payload` | Valid payload |
| 169 | Workflow state represents the current state of a document. | تمثل حالة مسار العمل الحالة الحالية للمستند. | `PROPOSED-payload` | Valid payload |
| 170 | Would you like to publish this comment? This means it will become visible to website/portal users. | هل ترغب في نشر هذا التعليق؟ هذا يعني أنه سيصبح مرئيًا لمستخدمي موقع الويب / البوابة. | `PROPOSED-payload` | Valid payload |
| 171 | Would you like to unpublish this comment? This means it will no longer be visible to website/portal users. | هل ترغب في إلغاء نشر هذا التعليق؟ هذا يعني أنه لن يعود مرئيًا لمستخدمي موقع الويب / البوابة. | `PROPOSED-payload` | Valid payload |
| 172 | You are about to open an external link. To confirm, click the link again. | أنت على وشك فتح رابط خارجي. للتأكيد، انقر على الرابط مرة أخرى. | `PROPOSED-payload` | Valid payload |
| 173 | You are not allowed to access this resource | غير مسموح لك بالوصول إلى هذا المورد | `PROPOSED-payload` | Valid payload |
| 174 | You are not allowed to access this {0} record because it is linked to {1} '{2}' in row {3}, field {4} | لا يُسمح لك بالوصول إلى سجل {0} هذا لأنه مرتبط بـ {1} '{2}' في الصف {3}، الحقل {4} | `PROPOSED-payload` | Valid payload |
| 175 | You are not permitted to access this page without login. | لا يُسمح لك بالوصول إلى هذه الصفحة دون تسجيل الدخول. | `PROPOSED-payload` | Valid payload |
| 176 | You are not permitted to access this resource. Login to access | لا يُسمح لك بالوصول إلى هذا المورد. سجّل الدخول للوصول | `PROPOSED-payload` | Valid payload |
| 177 | You are only allowed to update order, do not remove or add apps. | يُسمح لك فقط بتحديث الترتيب، لا تحذف أو تضف تطبيقات. | `PROPOSED-payload` | Valid payload |
| 178 | You can also access wkhtmltopdf variables (valid only in PDF print): | يمكنك أيضًا الوصول إلى متغيرات wkhtmltopdf (صالحة فقط في طباعة PDF): | `PROPOSED-payload` | Valid payload |
| 179 | You can also copy-paste following link in your browser | يمكنك أيضًا نسخ الرابط التالي ولصقه في متصفحك | `PROPOSED-payload` | Valid payload |
| 180 | You can ask your team to resend the invitation if you'd still like to join. | يمكنك أن تطلب من فريقك إعادة إرسال الدعوة إذا كنت لا تزال ترغب في الانضمام. | `PROPOSED-payload` | Valid payload |
| 181 | You can change Submitted documents by cancelling them and then, amending them. | يمكنك تغيير المستندات المرسلة عن طريق إلغائها ثم تعديلها. | `PROPOSED-payload` | Valid payload |
| 182 | You can change the retention policy from {0}. | يمكنك تغيير سياسة الاحتفاظ من {0}. | `PROPOSED-payload` | Valid payload |
| 183 | You can continue with the onboarding after exploring this page | يمكنك متابعة التهيئة بعد استكشاف هذه الصفحة | `PROPOSED-payload` | Valid payload |
| 184 | You can disable this {0} instead of deleting it. | يمكنك تعطيل {0} هذا بدلاً من حذفه. | `PROPOSED-payload` | Valid payload |
| 185 | You can increase the limit from System Settings. | يمكنك زيادة الحد من إعدادات النظام. | `PROPOSED-payload` | Valid payload |
| 186 | You can manually remove the lock if you think it's safe: {} | يمكنك إزالة القفل يدويًا إذا كنت تعتقد أنه آمن: {} | `PROPOSED-payload` | Valid payload |
| 187 | You can only insert images in Markdown fields | يمكنك فقط إدراج الصور في حقول Markdown | `PROPOSED-payload` | Valid payload |
| 188 | You can only print upto {0} documents at a time | يمكنك فقط طباعة ما يصل إلى {0} من المستندات في المرة الواحدة | `PROPOSED-payload` | Valid payload |
| 189 | You can only set the 3 custom doctypes in the Document Types table. | يمكنك فقط تعيين أنواع المستندات المخصصة الثلاثة في جدول أنواع المستندات. | `PROPOSED-payload` | Valid payload |
| 190 | You can only upload JPG, PNG, GIF, PDF, TXT, CSV or Microsoft documents. | يمكنك فقط تحميل ملفات JPG أو PNG أو GIF أو PDF أو TXT أو CSV أو مستندات Microsoft. | `PROPOSED-payload` | Valid payload |
| 191 | You can set a high value here if multiple users will be logging in from the same network. | يمكنك تعيين قيمة عالية هنا إذا كان عدة مستخدمين سيسجلون الدخول من نفس الشبكة. | `PROPOSED-payload` | Valid payload |
| 192 | You can use Customize Form to set levels on fields. | يمكنك استخدام تخصيص النموذج لتعيين مستويات على الحقول. | `PROPOSED-payload` | Valid payload |
| 193 | You do not have Read or Select Permissions for {} | ليس لديك أذونات القراءة أو التحديد لـ {} | `PROPOSED-payload` | Valid payload |
| 194 | You do not have import permission for {0} | ليس لديك إذن استيراد لـ {0} | `PROPOSED-payload` | Valid payload |
| 195 | You do not have permission to access field: {0} | ليس لديك إذن للوصول إلى الحقل: {0} | `PROPOSED-payload` | Valid payload |
| 196 | You do not have permission to access {0}: {1}. | ليس لديك إذن للوصول إلى {0}: {1}. | `PROPOSED-payload` | Valid payload |
| 197 | You don't have permission to access the {0} DocType. | ليس لديك إذن للوصول إلى نوع المستند {0}. | `PROPOSED-payload` | Valid payload |
| 198 | You have hit the row size limit on database table: {0} | لقد وصلت إلى الحد الأقصى لحجم الصف في جدول قاعدة البيانات: {0} | `PROPOSED-payload` | Valid payload |
| 199 | You have not entered a value. The field will be set to empty. | لم تقم بإدخال قيمة. سيتم تعيين الحقل كفارغ. | `PROPOSED-payload` | Valid payload |
| 200 | You have to enable Two Factor Auth from System Settings. | يجب عليك تمكين المصادقة الثنائية من إعدادات النظام. | `PROPOSED-payload` | Valid payload |
| 201 | You hit the rate limit because of too many requests. Please try after sometime. | لقد تجاوزت حد المعدل بسبب كثرة الطلبات. يرجى المحاولة بعد بعض الوقت. | `PROPOSED-payload` | Valid payload |
| 202 | You need the '{0}' permission on {1} {2} to perform this action. | تحتاج إلى إذن '{0}' على {1} {2} لتنفيذ هذا الإجراء. | `PROPOSED-payload` | Valid payload |
| 203 | You need to be Workspace Manager to delete a public workspace. | يجب أن تكون مدير مساحة العمل لحذف مساحة عمل عامة. | `PROPOSED-payload` | Valid payload |
| 204 | You need to be Workspace Manager to edit this document | يجب أن تكون مدير مساحة العمل لتعديل هذا المستند | `PROPOSED-payload` | Valid payload |
| 205 | You need to be a system user to access this page. | يجب أن تكون مستخدم نظام للوصول إلى هذه الصفحة. | `PROPOSED-payload` | Valid payload |
| 206 | You need to select indexes you want to add first. | تحتاج إلى تحديد الفهارس التي تريد إضافتها أولاً. | `PROPOSED-payload` | Valid payload |
| 207 | You need write permission on {0} {1} to merge | تحتاج إلى إذن كتابة على {0} {1} للدمج | `PROPOSED-payload` | Valid payload |
| 208 | You need write permission on {0} {1} to rename | تحتاج إلى إذن كتابة على {0} {1} لإعادة التسمية | `PROPOSED-payload` | Valid payload |
| 209 | You need {0} permission to fetch values from {1} {2} | تحتاج إلى إذن {0} لجلب القيم من {1} {2} | `PROPOSED-payload` | Valid payload |
| 210 | You seem to have written your name instead of your email. Please enter a valid email address so that we can get back. | يبدو أنك كتبت اسمك بدلاً من بريدك الإلكتروني. يرجى إدخال عنوان بريد إلكتروني صالح حتى نتمكن من الرد. | `PROPOSED-payload` | Valid payload |
| 211 | Your browser does not support the audio element. | متصفحك لا يدعم عنصر الصوت. | `PROPOSED-payload` | Valid payload |
| 212 | Your browser does not support the video element. | متصفحك لا يدعم عنصر الفيديو. | `PROPOSED-payload` | Valid payload |
| 213 | Your invitation to join {0} has been cancelled by the site administrator. | تم إلغاء دعوتك للانضمام إلى {0} بواسطة مسؤول الموقع. | `PROPOSED-payload` | Valid payload |
| 214 | Your new password has been set successfully. | تم تعيين كلمة المرور الجديدة بنجاح. | `PROPOSED-payload` | Valid payload |
| 215 | Your site is undergoing maintenance or being updated. | موقعك يخضع للصيانة أو التحديث. | `PROPOSED-payload` | Valid payload |
| 216 | `as_iterator` only works with `as_list=True` or `as_dict=True` | يعمل `as_iterator` فقط مع `as_list=True` أو `as_dict=True` | `PROPOSED-payload` | Valid payload |
| 217 | `job_id` paramater is required for deduplication. | معلمة `job_id` مطلوبة لإلغاء التكرار. | `PROPOSED-payload` | Valid payload |
| 218 | gzip not found in PATH! This is required to take a backup. | لم يتم العثور على gzip في PATH! هذا مطلوب لأخذ نسخة احتياطية. | `PROPOSED-payload` | Valid payload |
| 219 | string value, i.e. {0} or uid={0},ou=users,dc=example,dc=com | قيمة نصية، أي {0} أو uid={0},ou=users,dc=example,dc=com | `PROPOSED-payload` | Valid payload |
| 220 | wants to access the following details from your account | يريد الوصول إلى التفاصيل التالية من حسابك | `PROPOSED-payload` | Valid payload |
| 221 | when clicked on element it will focus popover if present. | عند النقر فوق العنصر، سيتم التركيز على النافذة المنبثقة إذا كانت موجودة. | `PROPOSED-payload` | Valid payload |
| 222 | {0} ${skip_list ? "" : type} |  | `EXCEPTION-technical` | Technical exclusion |
| 223 | {0} Not allowed to change {1} after submission from {2} to {3} | {0} غير مسموح بتغيير {1} بعد الإرسال من {2} إلى {3} | `PROPOSED-payload` | Valid payload |
| 224 | {0} cannot be amended because it is not cancelled. Please cancel the document before creating an amendment. | لا يمكن تعديل {0} لأنه لم يتم إلغاؤه. يرجى إلغاء المستند قبل إنشاء تعديل. | `PROPOSED-payload` | Valid payload |
| 225 | {0} cannot be hidden and mandatory without any default value | لا يمكن أن يكون {0} مخفيًا وإلزاميًا دون أي قيمة افتراضية | `PROPOSED-payload` | Valid payload |
| 226 | {0} contains an invalid Fetch From expression, Fetch From can't be self-referential. | يحتوي {0} على تعبير جلب من غير صالح، لا يمكن أن يكون "جلب من" مرجعيًا ذاتيًا. | `PROPOSED-payload` | Valid payload |
| 227 | {0} format could not be determined from the values in this column. Defaulting to {1}. | تعذر تحديد تنسيق {0} من القيم الموجودة في هذا العمود. تم الرجوع إلى القيمة الافتراضية {1}. | `PROPOSED-payload` | Valid payload |
| 228 | {0} if you are not redirected within {1} seconds | {0} إذا لم تتم إعادة توجيهك خلال {1} ثوانٍ | `PROPOSED-payload` | Valid payload |
| 229 | {0} is not a valid Calendar. Redirecting to default Calendar. | {0} ليس تقويمًا صالحًا. جارٍ إعادة التوجيه إلى التقويم الافتراضي. | `PROPOSED-payload` | Valid payload |
| 230 | {0} is not a valid ISO 3166 ALPHA-2 code. | {0} ليس رمز ISO 3166 ALPHA-2 صالحًا. | `PROPOSED-payload` | Valid payload |
| 231 | {0} is not a valid parent DocType for {1} | {0} ليس نوع مستند رئيسي صالح لـ {1} | `PROPOSED-payload` | Valid payload |
| 232 | {0} just impersonated as you. They gave this reason: {1} | {0} قام بانتحال صفتك للتو. وأبدى هذا السبب: {1} | `PROPOSED-payload` | Valid payload |
| 233 | {0} must begin and end with a letter and can only contain letters, hyphen or underscore. | يجب أن يبدأ {0} وينتهي بحرف ولا يمكن أن يحتوي إلا على أحرف أو شرطة أو شرطة سفلية. | `PROPOSED-payload` | Valid payload |
| 234 | {0} records are not automatically deleted. | سجلات {0} لا يتم حذفها تلقائيًا. | `PROPOSED-payload` | Valid payload |
| 235 | {0} role does not have permission on any doctype | دور {0} ليس لديه إذن على أي نوع مستند | `PROPOSED-payload` | Valid payload |
| 236 | {0} should be indexed because it's referred in dashboard connections | يجب فهرسة {0} لأنه مشار إليه في اتصالات لوحة التحكم | `PROPOSED-payload` | Valid payload |
| 237 | {0}: Other permission rules may also apply | {0}: قد تنطبق أيضًا قواعد أذونات أخرى | `PROPOSED-payload` | Valid payload |
| 238 | {0}: You can increase the limit for the field if required via {1} | {0}: يمكنك زيادة الحد للحقل إذا لزم الأمر عبر {1} | `PROPOSED-payload` | Valid payload |
| 239 | {0}: fieldname cannot be set to reserved keyword {1} | {0}: لا يمكن تعيين اسم الحقل إلى الكلمة المحجوزة {1} | `PROPOSED-payload` | Valid payload |
| 240 | {} does not support automated log clearing. | {} لا يدعم المسح الآلي للسجلات. | `PROPOSED-payload` | Valid payload |
| 241 | {} has been disabled. It can only be enabled if {} is checked. | تم تعطيل {}. لا يمكن تمكينه إلا إذا تم تحديد {}. | `PROPOSED-payload` | Valid payload |
| 242 | {} not found in PATH! This is required to access the console. | لم يتم العثور على {} في PATH! هذا مطلوب للوصول إلى وحدة التحكم. | `PROPOSED-payload` | Valid payload |
| 243 | {} not found in PATH! This is required to restore the database. | لم يتم العثور على {} في PATH! هذا مطلوب لاستعادة قاعدة البيانات. | `PROPOSED-payload` | Valid payload |
| 244 | {} not found in PATH! This is required to take a backup. | لم يتم العثور على {} في PATH! هذا مطلوب لأخذ نسخة احتياطية. | `PROPOSED-payload` | Valid payload |
