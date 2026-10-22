# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""
Construction ERP — Login page controller override.
Re-exports Frappe's login context so our construction/www/login.html
template override receives the full context (app_name, logo, etc.).
"""

from frappe.www.login import (
    get_context,
    get_login_with_email_link_ratelimit,
    login_via_key,
    login_via_token,
    sanitize_redirect,
    send_login_link,
)

# Make get_context available for TemplatePage.set_pymodule()
# This ensures app_name = "Construction ERP" flows into the template.
