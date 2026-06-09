import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet


class BOQStructure(NestedSet):
    nsm_parent_field = "parent_structure"

    def validate(self):
        self.enforce_boq_status()

    def before_insert(self):
        if not self.flags.get("ignore_wbs_generation"):
            self.wbs_code = self.generate_wbs_code()

    def after_insert(self):
        if not self.is_group:
            self.create_boq_item()

    def on_update(self):
        super().on_update()

    def on_trash(self):
        if not self.is_group:
            from construction.services.boq_lifecycle import validate_boq_structure_leaf_delete_safety

            validate_boq_structure_leaf_delete_safety(self)
            self.delete_boq_item()
        super().on_trash()

    def generate_wbs_code(self):
        """Generate hierarchical WBS code under a transaction lock."""
        if not self.boq_header:
            frappe.throw(_("BOQ Header is required before generating WBS code."))

        parent_wbs = self._lock_wbs_sequence_scope()
        sibling_wbs_codes = self._get_locked_sibling_wbs_codes()
        seq = self._get_next_wbs_sequence(sibling_wbs_codes)

        if not self.parent_structure:
            return f"{seq:02d}"

        width = 2 if self.is_group else 3
        return f"{parent_wbs}.{seq:0{width}d}"

    def _lock_wbs_sequence_scope(self):
        if not self.parent_structure:
            frappe.db.sql(
                "select name from `tabBOQ Header` where name = %s for update",
                self.boq_header,
            )
            return None

        parent = frappe.db.sql(
            """
            select name, boq_header, wbs_code, is_group
            from `tabBOQ Structure`
            where name = %s
            for update
            """,
            self.parent_structure,
            as_dict=True,
        )
        if not parent:
            frappe.throw(_("Parent BOQ Structure {0} was not found.").format(self.parent_structure))

        parent = parent[0]
        if parent.boq_header != self.boq_header:
            frappe.throw(_("Parent BOQ Structure belongs to another BOQ Header."))
        if not parent.is_group:
            frappe.throw(_("Parent BOQ Structure must be a group node."))
        if not parent.wbs_code:
            frappe.throw(_("Parent BOQ Structure must have a WBS code before adding children."))

        return parent.wbs_code

    def _get_locked_sibling_wbs_codes(self):
        if self.parent_structure:
            return frappe.db.sql(
                """
                select wbs_code
                from `tabBOQ Structure`
                where boq_header = %s
                  and parent_structure = %s
                  and docstatus != 2
                for update
                """,
                (self.boq_header, self.parent_structure),
                pluck="wbs_code",
            )

        return frappe.db.sql(
            """
            select wbs_code
            from `tabBOQ Structure`
            where boq_header = %s
              and ifnull(parent_structure, '') = ''
              and docstatus != 2
            for update
            """,
            self.boq_header,
            pluck="wbs_code",
        )

    def _get_next_wbs_sequence(self, sibling_wbs_codes):
        max_seq = 0
        for wbs_code in sibling_wbs_codes:
            if not wbs_code:
                continue
            segment = str(wbs_code).split(".")[-1]
            if not segment.isdigit():
                continue
            max_seq = max(max_seq, cint(segment))
        return max_seq + 1

    def create_boq_item(self):
        if frappe.db.exists("BOQ Item", {"structure": self.name}):
            return
        item = frappe.new_doc("BOQ Item")
        item.flags.ignore_boq_status_for_variation = self.flags.get("ignore_boq_status_for_variation")
        item.structure = self.name
        item.boq_header = self.boq_header
        item.is_variation_item = self.is_variation_item
        item.variation_order = self.variation_order
        item.insert(ignore_permissions=True)

    def delete_boq_item(self):
        item_name = frappe.db.get_value("BOQ Item", {"structure": self.name}, "name")
        if item_name:
            frappe.delete_doc("BOQ Item", item_name, ignore_permissions=True)

    def enforce_boq_status(self):
        if self.flags.get("ignore_boq_status_for_variation") and self.is_variation_item:
            return
        status = frappe.db.get_value("BOQ Header", self.boq_header, "status")
        if status in ("Frozen", "Locked"):
            frappe.throw(_("Cannot modify BOQ Structure: BOQ is {0}.").format(status))

    @frappe.whitelist()
    def convert_group_to_ledger(self):
        self.ensure_draft_for_conversion()
        if not self.is_group:
            return 1
        if self.check_if_child_exists():
            frappe.throw(_("Cannot convert to leaf: node has child nodes."))
        self.is_group = 0
        self.save()
        self.create_boq_item()
        return 1

    @frappe.whitelist()
    def convert_ledger_to_group(self):
        self.ensure_draft_for_conversion()
        if self.is_group:
            return 1
        from construction.services.boq_lifecycle import validate_boq_structure_leaf_delete_safety

        validate_boq_structure_leaf_delete_safety(self)
        self.is_group = 1
        self.save()
        self.delete_boq_item()
        return 1

    def check_if_child_exists(self):
        return frappe.db.sql(
            "select name from `tabBOQ Structure` where parent_structure = %s and docstatus != 2",
            self.name,
        )

    def ensure_draft_for_conversion(self):
        status = frappe.db.get_value("BOQ Header", self.boq_header, "status")
        if status != "Draft":
            frappe.throw(_("Cannot convert BOQ Structure nodes unless BOQ Header is Draft."))


def on_doctype_update():
    frappe.db.add_index("BOQ Structure", ["lft", "rgt"])
    from construction.services.boq_wbs_health import ensure_wbs_unique_constraint

    ensure_wbs_unique_constraint()
