import frappe

def execute():
    translations = {
        "Save": "حفظ",
        "Edit": "تعديل",
        "Delete": "حذف",
        "New": "جديد",
        "Search": "بحث",
        "Submit": "تقديم",
        "From": "من",
        "To": "إلى",
        "Apply": "تطبيق",
        "Download": "تحميل",
        "Print": "طباعة",
        "Create": "إنشاء",
        "Update": "تحديث",
        "Settings": "إعدادات",
        "Actions": "إجراءات",
        "Refresh": "تحديث",
        "Reset": "إعادة تعيين",
        "Email": "بريد إلكتروني",
        "Filter By...": "تصفية حسب...",
        "Clear": "مسح",
        "Menu": "القائمة",
        "Yes": "نعم",
        "No": "لا",
        "Cancel": "إلغاء",
        "Status": "الحالة",
        "Company": "الشركة",
        "Date": "التاريخ",
        "Description": "الوصف",
        "Project": "المشروع",
        "Account": "الحساب",
        "Customer": "العميل",
        "Supplier": "المورد",
        "Add": "إضافة",
        "Add Row": "إضافة صف",
        "Filters": "تصفية",
        "Select": "تحديد",
        "Loading...": "جاري التحميل..."
    }

    count = 0
    for source_text, translated_text in translations.items():
        # Check if translation already exists
        exists = frappe.db.exists("Translation", {
            "language": "ar",
            "source_text": source_text
        })

        if not exists:
            doc = frappe.get_doc({
                "doctype": "Translation",
                "language": "ar",
                "source_text": source_text,
                "translated_text": translated_text
            })
            doc.insert(ignore_permissions=True)
            count += 1
            print(f"Added translation for: {source_text}")
        else:
            # Update existing if necessary
            doc = frappe.get_doc("Translation", exists)
            if doc.translated_text != translated_text:
                doc.translated_text = translated_text
                doc.save(ignore_permissions=True)
                count += 1
                print(f"Updated translation for: {source_text}")

    frappe.db.commit()
    print(f"Successfully processed {count} translations.")

    # Reload frappe message cache
    frappe.cache().delete_key('lang_full_dict')
