import frappe
from frappe.utils import flt


def execute():
    """Migrate existing data to the new Quantity Revision model.

    This patch:
    1. Sets original_qty and current_revised_qty for all existing BOQ Items
    2. Creates baseline BOQ Quantity Revisions for Locked BOQ Headers
    3. Creates revision records for existing variation items
    4. Handles legacy VO data
    """
    frappe.log_error("Starting quantity revision migration", "Migration v7.0")

    # 1. Set original_qty and current_revised_qty for all BOQ Items
    _migrate_boq_items()

    # 2. Create baseline revisions for Locked BOQ Headers
    _create_baseline_revisions()

    # 3. Create revision records for existing variation items
    _migrate_variation_items()

    # 4. Handle legacy VO lines
    _migrate_legacy_vo_lines()

    # 5. Update BOQ Header total_revised_value
    _update_header_totals()

    frappe.log_error("Quantity revision migration completed", "Migration v7.0")


def _migrate_boq_items():
    """Set original_qty and current_revised_qty for all existing BOQ Items."""
    items = frappe.get_all(
        "BOQ Item", fields=["name", "quantity", "is_variation_item", "contract_unit_price"]
    )

    for item in items:
        if item.is_variation_item:
            original_qty = 0
        else:
            original_qty = item.quantity

        frappe.db.set_value(
            "BOQ Item",
            item.name,
            {
                "original_qty": original_qty,
                "current_revised_qty": item.quantity,
                "current_revised_unit_price": item.contract_unit_price,
            },
            update_modified=False,
        )

    frappe.db.commit()
    frappe.log_error(f"Migrated {len(items)} BOQ Items", "Migration v7.0")


def _create_baseline_revisions():
    """Create baseline BOQ Quantity Revisions for all Locked BOQ Headers."""
    from construction.services.quantity_revisions import create_lock_baseline

    headers = frappe.get_all("BOQ Header", filters={"status": "Locked"}, pluck="name")

    for header in headers:
        try:
            result = create_lock_baseline(header)
            if result.get("success"):
                frappe.log_error(
                    f"Created baseline for {header}: {result.get('created', 0)} revisions", "Migration v7.0"
                )
        except Exception as e:
            frappe.log_error(f"Error creating baseline for {header}: {str(e)}", "Migration v7.0")

    frappe.db.commit()


def _migrate_variation_items():
    """Create revision records for existing variation items created by VOs."""
    variation_items = frappe.get_all(
        "BOQ Item",
        filters={"is_variation_item": 1},
        fields=["name", "structure", "boq_header", "quantity", "contract_unit_price", "variation_order"],
    )

    for item in variation_items:
        # Check if revision already exists
        existing = frappe.db.get_value(
            "BOQ Quantity Revision", {"boq_item": item.name, "revision_type": "New Variation Item"}, "name"
        )

        if existing:
            continue

        try:
            revision = frappe.get_doc(
                {
                    "doctype": "BOQ Quantity Revision",
                    "boq_header": item.boq_header,
                    "boq_structure": item.structure,
                    "boq_item": item.name,
                    "variation_order": item.variation_order,
                    "revision_date": frappe.utils.nowdate(),
                    "revision_type": "New Variation Item",
                    "previous_qty": 0,
                    "revised_qty": item.quantity,
                    "contract_unit_price": 0,
                    "revised_unit_price": item.contract_unit_price,
                    "status": "Approved",
                    "approved_by": "Administrator",
                    "approved_on": frappe.utils.now(),
                }
            )
            revision.insert(ignore_permissions=True)

            # Link to BOQ Item
            frappe.db.set_value(
                "BOQ Item", item.name, "last_quantity_revision", revision.name, update_modified=False
            )
        except Exception as e:
            frappe.log_error(f"Error creating variation revision for {item.name}: {str(e)}", "Migration v7.0")

    frappe.db.commit()
    frappe.log_error(f"Migrated {len(variation_items)} variation items", "Migration v7.0")


def _migrate_legacy_vo_lines():
    """Mark legacy VO lines that have created_boq_item but no created_quantity_revision."""
    legacy_lines = frappe.get_all(
        "VO Line",
        filters={"created_boq_item": ["!=", ""], "created_quantity_revision": ["", None]},
        fields=["name", "created_boq_item", "parent"],
    )

    for line in legacy_lines:
        # Try to link to existing New Variation Item revision
        revision = frappe.db.get_value(
            "BOQ Quantity Revision",
            {"boq_item": line.created_boq_item, "revision_type": "New Variation Item"},
            "name",
        )

        if revision:
            frappe.db.set_value(
                "VO Line", line.name, "created_quantity_revision", revision, update_modified=False
            )

    frappe.db.commit()
    frappe.log_error(f"Linked {len(legacy_lines)} legacy VO lines to revisions", "Migration v7.0")


def _update_header_totals():
    """Update total_revised_value for all BOQ Headers."""
    headers = frappe.get_all("BOQ Header", fields=["name"])

    for header in headers:
        try:
            totals = frappe.db.sql(
                """
                SELECT
                    COALESCE(SUM(COALESCE(current_revised_qty, quantity) * COALESCE(current_revised_unit_price, contract_unit_price) * COALESCE(factor, 1.0)), 0)
                FROM `tabBOQ Item`
                WHERE boq_header = %s
            """,
                header.name,
            )

            total_revised = totals[0][0] if totals else 0
            frappe.db.set_value(
                "BOQ Header", header.name, "total_revised_value", total_revised, update_modified=False
            )
        except Exception as e:
            frappe.log_error(f"Error updating header {header.name}: {str(e)}", "Migration v7.0")

    frappe.db.commit()
    frappe.log_error(f"Updated {len(headers)} BOQ Header totals", "Migration v7.0")
