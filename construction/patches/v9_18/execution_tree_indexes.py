import frappe

from construction.services import execution_tree_rules as rules
from construction.setup.execution_tree_schema import ensure_execution_tree_schema


def execute():
    # This app's patches.txt uses the plain (pre-model-sync) format. On a fresh
    # site the DocTypes may not be synchronized yet; the after-install and
    # after-migrate installers verify and index the tables post-sync. Only
    # reconcile an already-synchronized schema here.
    if not frappe.db.table_exists(rules.NODE_DOCTYPE):
        return
    if not frappe.db.table_exists(rules.COUNTER_DOCTYPE):
        return
    ensure_execution_tree_schema()
