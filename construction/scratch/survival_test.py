import frappe

from construction.api.theme_api import whitelabel_patch
from construction.install import create_system_themes


def simulate_migration_survival():
    print("--- Simulating Update Survival Test ---")

    # 1. Run the patch
    print("Running whitelabel_patch...")
    whitelabel_patch()

    # 2. Check if Frappe branding is gone
    welcome_page = frappe.db.exists("Page", "welcome-to-erpnext")
    print(f"Frappe Welcome Page exists: {bool(welcome_page)} (Expected: False)")

    # 3. Check if Construction Themes exist
    themes = frappe.get_all("Construction Theme", filters={"is_system_theme": 1})
    print(f"System Themes found: {len(themes)} (Expected: >0)")

    # 4. Check hooks
    print("Checking hooks configuration...")
    import construction.hooks as hooks

    print(f"email_css hook present: {'email_css' in dir(hooks)}")
    print(f"pdf_header_html hook present: {'pdf_header_html' in dir(hooks)}")

    print("--- Survival Test Complete ---")


if __name__ == "__main__":
    frappe.connect()
    simulate_migration_survival()
