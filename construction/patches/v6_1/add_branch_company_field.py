"""One-time patch: create Branch.company Custom Field for pre-existing installs.

Fresh installs get this field via install.py::setup_branch_company_field()
(after_install hook). This patch covers pre-existing installs that were
set up before the field existed (manually created via UI, never in VCS).

Uses the same shared function from install.py but adds explicit commit
since patches manage their own transaction boundary.
"""

import frappe

from construction.install import setup_branch_company_field


def execute():
    if not frappe.db.table_exists("tabBranch"):
        return

    setup_branch_company_field()
    frappe.db.commit()
