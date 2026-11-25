"""Dedicated read-only RPC surface for WBS P3 Execution Coverage & Export."""

from __future__ import annotations

import frappe
from frappe import _

from construction.services import execution_coverage as service
from construction.services import execution_tree_rules as tree_rules

_FRAMEWORK_ARGUMENTS = frozenset({"cmd", "_"})


def _reject_extra(kwargs):
    extra = {key: value for key, value in kwargs.items() if key not in _FRAMEWORK_ARGUMENTS}
    if extra:
        frappe.throw(_("Unknown request argument."), frappe.ValidationError)


def _validate_size(payload):
    try:
        tree_rules.validate_request_size(payload)
    except tree_rules.RuleViolation:
        frappe.throw(_("Request payload is too large."), frappe.ValidationError)


@frappe.whitelist(methods=["GET"])
def get_execution_coverage(
    project=None,
    boq_header=None,
    boq_structure=None,
    boq_item=None,
    execution_node=None,
    mapping_state=None,
    stage_status=None,
    search=None,
    view_mode=None,
    page=None,
    page_size=None,
    **kwargs,
):
    _reject_extra(kwargs)
    payload = {
        "project": project,
        "boq_header": boq_header,
        "boq_structure": boq_structure,
        "boq_item": boq_item,
        "execution_node": execution_node,
        "mapping_state": mapping_state,
        "stage_status": stage_status,
        "search": search,
        "view_mode": view_mode,
        "page": page,
        "page_size": page_size,
    }
    _validate_size(payload)
    return service.get_execution_coverage(**payload)


@frappe.whitelist(methods=["GET"])
def export_execution_coverage(
    project=None,
    boq_header=None,
    boq_structure=None,
    boq_item=None,
    execution_node=None,
    mapping_state=None,
    stage_status=None,
    search=None,
    view_mode=None,
    export_format=None,
    **kwargs,
):
    _reject_extra(kwargs)
    payload = {
        "project": project,
        "boq_header": boq_header,
        "boq_structure": boq_structure,
        "boq_item": boq_item,
        "execution_node": execution_node,
        "mapping_state": mapping_state,
        "stage_status": stage_status,
        "search": search,
        "view_mode": view_mode,
        "export_format": export_format,
    }
    _validate_size(payload)
    exported = service.build_execution_coverage_export(**payload)
    frappe.response["type"] = "download"
    frappe.response["filename"] = exported["filename"]
    frappe.response["filecontent"] = exported["filecontent"]
    frappe.response["content_type"] = exported["content_type"]
    frappe.response["display_content_as"] = "attachment"
