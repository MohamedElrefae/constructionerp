# أدلة المهام / Task Guides (Arabic / English)

Core tasks in both languages, using the reviewed Arabic terminology shipped in the app.
Tested behavior on the rehearsal site; internal engineering evidence is tracked separately.

---

## 1. استيراد جدول الكميات من Excel / Importing a BOQ from Excel

**EN:** Open a Draft BOQ Header → Actions → **Import Excel** → attach the workbook → **Validate**.
The preview shows row, section, item and warning counts and nothing is saved yet. Check the
detected layout (Structured / Semi-Structured / Flat), confirm the mode, then choose
**Confirm Import**. The dialog closes on success; the items appear under the header.
Re-importing the same file is refused with "already exists" — no duplicates are created.

**AR:** افتح رأس جدول كميات بحالة مسودة ← الإجراءات ← **استيراد من Excel** ← أرفق المصنف ←
**تحقَّق**. تعرض المعاينة أعداد الصفوف والأقسام والبنود والتحذيرات ولا يُحفظ أي شيء بعد.
تحقق من التخطيط المكتشف (منظَّم / شبه منظَّم / مسطَّح)، وأكِّد الطريقة، ثم اختر **تأكيد
الاستيراد**. يُغلق الحوار عند النجاح وتظهر البنود تحت الرأس. إعادة استيراد الملف نفسه
مرفوضة برسالة وجود مسبق — لا تُنشأ أي تكرارات.

## 2. إدخال القياسات والاعتماد / Recording measurements and certification

**EN:** A site engineer records executed quantities on a BOQ Item Stage (measurement only).
Certification (`certified_qty`) is limited to Project Manager roles — the field is disabled
for everyone else, and the server enforces the same rule. Certified records are permanent:
corrections go through an adjustment stage, never by editing the certified record.

**AR:** يُدخل مهندس الموقع الكميات المنفذة في مرحلة بند جدول الكميات (قياس فقط). الاعتماد
(كمية معتمدة) مقتصر على أدوار مدير المشروع — الحقل معطَّل لغيرهم ويفرض الخادم القاعدة
نفسها. السجلات المعتمدة دائمة: التصحيحات تتم عبر مرحلة تعديل، وليس بتحرير السجل المعتمد
أبدًا.

## 3. أوامر التغيير / Variation orders

**EN:** Draft → Submitted (Project Manager) → Approved by Engineer (Site Engineer) →
Approved by Client (Construction Owner, with the signed client approval PDF attached).
Each step records who approved it. An approved order projects revised quantities; further
corrections need a new order.

**AR:** مسودة ← مُرسل (مدير المشروع) ← معتمَد من المهندس (مهندس الموقع) ← معتمَد من العميل
(مالك الإنشاء، مع إرفاق ملف موافقة العميل الموقّع). تسجَّل هوية كل معتمِد في كل خطوة. أمر
التغيير المعتمد يُسقط الكميات المعدّلة؛ أي تصحيحات لاحقة تحتاج أمرًا جديدًا.

## 4. التقارير / Reports

**EN:** Open the Construction Report Viewer, set the Company filter first — the view runs
only inside your permitted company. Cost-data reports additionally require cost-database
rights; without them you get zero rows, never someone else's rates. Exports carry at most
2,000 rows into a private file attached to the BOQ Header.

**AR:** افتح عارض تقارير الإنشاءات، وحدد مرشح الشركة أولًا — يعمل العرض فقط داخل شركتك
المصرَّح بها. تقارير بيانات التكلفة تتطلب صلاحيات قاعدة بيانات التكلفة أيضًا؛ بدونها تحصل
على صفر صفوف، وليس على أسعار غيرك أبدًا. تحمل الصادرات ٢٠٠٠ صف كحد أقصى إلى ملف خاص
مرفق برأس جدول الكميات.

## 5. استكشاف الأخطاء / Troubleshooting

| What you see / ما تراه | What it means / معناه | What to do / الإجراء |
|---|---|---|
| يرجى تعبئة الحقول الإلزامية قبل الحفظ / Please fill the mandatory fields | A required field is empty | Fill the marked field and save again / املأ الحقل المحدد واحفظ مجددًا |
| WBS code already exists / رمز WBS موجود مسبقًا | The file (or rows) were already imported | Do not re-import; check the existing items / لا تعِد الاستيراد؛ تحقق من البنود الموجودة |
| Not authorized / غير مسموح | Your role, company permission or scope does not cover this | Ask your administrator — do not share passwords / راجع المسؤول ولا تشارك كلمات المرور |
| Quantity must be non-negative / الكمية يجب ألا تكون سالبة | The entered value is invalid | Correct the value; the saved record is unchanged / صحح القيمة؛ السجل المحفوظ لم يتغير |
| Unsaved changes / تغييرات غير محفوظة (form layout panel) | Visibility edits are staged until Apply & Save | Press Apply & Save, or close and confirm discarding / اضغط تطبيق وحفظ، أو أغلق وأكِّد التجاهل |
