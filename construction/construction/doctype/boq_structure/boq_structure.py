import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet


class BOQStructure(NestedSet):
    nsm_parent_field = "parent_structure"

    def validate(self):
        self.enforce_boq_status()
        self.sync_rollup_fields()

    def before_insert(self):
        if not self.flags.get("ignore_wbs_generation"):
            self.wbs_code = self.generate_wbs_code()

    def after_insert(self):
        if not self.is_group:
            self.create_boq_item()
        self._trigger_header_rollup()

    def on_update(self):
        super().on_update()
        self._trigger_header_rollup()

    def on_trash(self):
        if not self.is_group:
            from construction.services.boq_lifecycle import validate_boq_structure_leaf_delete_safety

            validate_boq_structure_leaf_delete_safety(self)
            self.delete_boq_item()
        super().on_trash()
        self._trigger_header_rollup()

    def _trigger_header_rollup(self):
        if getattr(frappe.flags, "defer_boq_rollups", False) or getattr(self.flags, "defer_boq_rollups", False):
            return
        if not self.boq_header:
            return
        header = frappe.get_doc("BOQ Header", self.boq_header)
        header.recalculate_phase1_totals()

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

    def sync_rollup_fields(self):
        if not self.boq_header:
            self.item_count = 0
            self.total_contract_value = 0
            self.total_budgeted_cost = 0
            return

        if not self.name:
            self.item_count = 0
            self.total_contract_value = 0
            self.total_budgeted_cost = 0
            return

        if not self.lft or not self.rgt:
            self.item_count = 0
            self.total_contract_value = 0
            self.total_budgeted_cost = 0
            return

        rollup = frappe.db.sql(
            """
            SELECT
                COUNT(DISTINCT i.name) AS item_count,
                COALESCE(SUM(CASE WHEN i.docstatus < 2 THEN i.line_total ELSE 0 END), 0) AS total_contract_value,
                COALESCE(
                    SUM(
                        CASE
                            WHEN i.docstatus < 2 THEN i.quantity * i.est_unit_cost * COALESCE(i.factor, 1.0)
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_budgeted_cost
            FROM `tabBOQ Structure` d
            LEFT JOIN `tabBOQ Item` i
                ON i.structure = d.name
               AND i.docstatus < 2
            WHERE d.boq_header = %s
              AND d.lft >= %s
              AND d.rgt <= %s
              AND d.docstatus < 2
            """,
            (self.boq_header, self.lft, self.rgt),
            as_dict=True,
        )
        rollup = rollup[0] if rollup else {}
        self.item_count = rollup.get("item_count") or 0
        self.total_contract_value = rollup.get("total_contract_value") or 0
        self.total_budgeted_cost = rollup.get("total_budgeted_cost") or 0

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
        self.check_permission("write")
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
        self.check_permission("write")
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
