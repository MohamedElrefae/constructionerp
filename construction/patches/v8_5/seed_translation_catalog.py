"""Seed the Translation catalog workbench.

This patch:
1. Adds the custom fields required for catalog entries to the Translation DocType.
2. Runs a dry-run preview of the catalog sync so operators can see the scale.
3. Runs the actual catalog sync, creating a Translation row for every msgid in
   the Arabic .po files of frappe, erpnext and construction.

Catalog rows are excluded from the runtime translation cache by the
monkey-patch in construction.__init__, so worker memory stays flat while users
get a complete, editable translation list.
"""

import frappe

from construction.api.translation_tools import sync_translation_catalog
from construction.setup.translation_catalog_fields import apply as apply_custom_fields


def execute():
    # 1. Ensure custom fields exist before we touch catalog rows.
    apply_custom_fields()

    # 2. Preview counts without writing.
    preview = sync_translation_catalog(dry_run=True)
    print(f"[v8_5] Catalog sync preview: {preview}")

    # 3. Run the real sync.
    result = sync_translation_catalog(dry_run=False)
    print(f"[v8_5] Catalog sync completed: {result}")

    return result
