"""Five VOs in mixed states on a dedicated header (lab fresh site)."""

import io
import sys

sys.path.insert(0, "/tmp/opencode")
from lab_console import connect

frappe = connect("f31fresh-clean.localhost")
CO = "ACC Acceptance Co"
proj = frappe.db.get_value("Project", {"project_name": "ACC-001"}, "name")

h = frappe.get_doc(
    {
        "doctype": "BOQ Header",
        "project": proj,
        "title": "ACC VO Header",
        "status": "Draft",
        "boq_type": "Tender",
    }
).insert(ignore_permissions=True)
sec = frappe.get_doc(
    {"doctype": "BOQ Structure", "boq_header": h.name, "title": "ACC VO Sec", "project": proj, "is_group": 1}
).insert(ignore_permissions=True)
items = []
for k in range(2):
    leaf = frappe.get_doc(
        {
            "doctype": "BOQ Structure",
            "boq_header": h.name,
            "title": f"ACC VO Leaf {k}",
            "project": proj,
            "parent_structure": sec.name,
            "is_group": 0,
        }
    ).insert(ignore_permissions=True)
    it = frappe.get_doc("BOQ Item", {"structure": leaf.name})
    it.update(
        {
            "cost_item": f"ACC VO item {k}",
            "quantity": 50,
            "unit": "Nos",
            "factor": 1,
            "est_unit_cost": 60,
            "contract_unit_price": 70,
        }
    )
    it.save(ignore_permissions=True)
    items.append(it.name)
for st in ("Pricing", "Frozen", "Locked"):
    hh = frappe.get_doc("BOQ Header", h.name)
    hh.status = st
    hh.save(ignore_permissions=True)
frappe.db.commit()
print("locked header:", h.name)

from pypdf import PdfWriter

from construction.api.boq_api import create_variation_order, transition_variation_order


def pdf():
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    w.write(buf)
    f = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": "ACC-vo.pdf",
            "attached_to_doctype": "Variation Order",
            "attached_to_name": "pending",
            "is_private": 1,
        }
    )
    f.content = buf.getvalue()
    return f.save(ignore_permissions=True)


states = ["Draft", "Submitted", "Approved by Engineer", "Approved by Client", "Approved by Client"]
results = []
for idx, target in enumerate(states):
    frappe.set_user("f31-pm@qualification.invalid")
    frappe.local._boq_perm_scope_dims = {}
    r = create_variation_order(
        boq_header=h.name, reason=f"ACC VO {idx}", description="workload", engineer_name="Engineer"
    )
    vn = (
        r.get("vo") or r.get("name") or frappe.db.get_value("Variation Order", {"boq_header": h.name}, "name")
    )
    vo = frappe.get_doc("Variation Order", vn)
    vo.append(
        "lines",
        {
            "line_type": "Quantity Change",
            "boq_item": items[idx % 2],
            "revised_qty": 52,
            "revised_unit_price": 75,
            "rate_change_justification": "ACC workload: minor quantity growth",
        },
    )
    vo.save()
    if target in ("Submitted", "Approved by Engineer", "Approved by Client"):
        transition_variation_order(vo_name=vn, new_status="Submitted")
    if target in ("Approved by Engineer", "Approved by Client"):
        frappe.set_user("acc-eng@qualification.invalid")
        frappe.local._boq_perm_scope_dims = {}
        transition_variation_order(vo_name=vn, new_status="Approved by Engineer")
    if target == "Approved by Client":
        frappe.set_user("f31-pm@qualification.invalid")
        frappe.local._boq_perm_scope_dims = {}
        # owner approval needs Construction Owner; use admin-created owner? use PM? No — SoD.
        # The lab has no owner persona; document and use Administrator for the client step.
        frappe.set_user("Administrator")
        fdoc = pdf()
        fdoc.attached_to_name = vn
        fdoc.save(ignore_permissions=True)
        frappe.db.commit()
        transition_variation_order(
            vo_name=vn, new_status="Approved by Client", client_approval_document=fdoc.name
        )
    frappe.set_user("Administrator")
    results.append((vn, frappe.db.get_value("Variation Order", vn, "status")))
    frappe.db.commit()
for vn, st in results:
    print(" ", vn, "->", st)
