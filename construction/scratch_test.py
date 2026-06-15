import frappe

def run_test():
    tiny_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": "test_login_bg_private.png",
            "content": tiny_png,
            "is_private": 1,
        }
    )
    file_doc.insert()
    print("1. file name:", file_doc.name)

    theme = frappe.get_doc(
        {
            "doctype": "Construction Theme",
            "theme_name": "Test Theme Debug",
            "theme_type": "Custom Light",
            "accent_primary": "#2076FF",
            "navbar_bg": "#ffffff",
            "sidebar_bg": "#f1f5f9",
            "surface_bg": "#ffffff",
            "body_bg": "#f8fafc",
            "text_primary": "#111827",
            "login_page_bg_type": "Background Image",
            "login_page_bg_image": file_doc.file_url,
        }
    )
    theme.insert()

    print("2. after theme insert, file in db:", frappe.db.get_value("File", file_doc.name, "is_private"))
    frappe.db.rollback()
