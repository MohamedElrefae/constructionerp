"""Construction download policy layered over native File resolution.

Native resolution checks File owner/share/parent access. This wrapper adds
construction parent/scope constraints and live authorization for generated
standalone exports, then delegates byte delivery to the native endpoint.
Unrelated files retain native behavior.
"""

import frappe
from frappe import _
from frappe.core.doctype.file.utils import find_file_by_url
from frappe.handler import download_file as _vendor_download_file

from construction.overrides.file_permissions import (
    has_file_parent_permission,
    is_boq_attached,
    is_construction_export,
)


# nosemgrep: guest-whitelisted-method -- Preserve native public-file downloads while construction attachments remain parent-permission guarded; covered by test_native_download_denies_guest_and_unrelated_user_but_keeps_public_files.
@frappe.whitelist(allow_guest=True)
def download_file(file_url: str):
    file_doc = find_file_by_url(file_url)
    if file_doc is not None and (is_boq_attached(file_doc) or is_construction_export(file_doc)):
        allowed = has_file_parent_permission(file_doc, "read")
        if not allowed:
            frappe.throw(
                _("You are not permitted to access this file."),
                frappe.PermissionError,
            )
    return _vendor_download_file(file_url)
