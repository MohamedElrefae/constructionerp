import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class BOQStructure(NestedSet):
    nsm_parent_field = "parent_structure"

    def validate(self):
        self.enforce_boq_status()

    def before_insert(self):
        self.wbs_code = self.generate_wbs_code()

    def after_insert(self):
        if not self.is_group:
            self.create_boq_item()

    def on_update(self):
        super().on_update()

    def on_trash(self):
        if not self.is_group:
            self.delete_boq_item()
        super().on_trash()

    def generate_wbs_code(self):
        """Generate hierarchical WBS code."""
        filters = {"boq_header": self.boq_header}
        if self.parent_structure:
            filters["parent_structure"] = self.parent_structure
        else:
            filters["parent_structure"] = ("is", "not set")

        seq = frappe.db.count("BOQ Structure", filters) + 1

        if not self.parent_structure:
            return f"{seq:02d}"

        parent_wbs = frappe.db.get_value("BOQ Structure", self.parent_structure, "wbs_code")
        if self.is_group:
            return f"{parent_wbs}.{seq:02d}"
        return f"{parent_wbs}.{seq:03d}"

    def create_boq_item(self):
        if frappe.db.exists("BOQ Item", {"structure": self.name}):
            return
        item = frappe.new_doc("BOQ Item")
        item.structure = self.name
        item.boq_header = self.boq_header
        item.insert(ignore_permissions=True)

    def delete_boq_item(self):
        item_name = frappe.db.get_value("BOQ Item", {"structure": self.name}, "name")
        if item_name:
            frappe.delete_doc("BOQ Item", item_name, force=True, ignore_permissions=True)

    def enforce_boq_status(self):
        status = frappe.db.get_value("BOQ Header", self.boq_header, "status")
        if status in ("Frozen", "Locked"):
            frappe.throw(_("Cannot modify BOQ Structure: BOQ is {0}.").format(status))

    @frappe.whitelist()
    def convert_group_to_ledger(self):
        if self.check_if_child_exists():
            frappe.throw(_("Cannot convert to leaf: node has child nodes."))
        self.is_group = 0
        self.save()
        return 1

    @frappe.whitelist()
    def convert_ledger_to_group(self):
        self.is_group = 1
        self.save()
        return 1

    def check_if_child_exists(self):
        return frappe.db.sql(
            "select name from `tabBOQ Structure` where parent_structure = %s and docstatus != 2",
            self.name,
        )


def on_doctype_update():
    frappe.db.add_index("BOQ Structure", ["lft", "rgt"])
