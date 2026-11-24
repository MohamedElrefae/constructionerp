"""Dedicated RPC surface for WBS P2 execution-location mapping (Slices 1 & 2)."""

from __future__ import annotations

import frappe

from construction.services import execution_mapping as service
from construction.services import execution_tree_rules as rules

_FRAMEWORK_ARGUMENTS = frozenset({"cmd", "_"})


def _reject_extra(kwargs):
    extra = {key: value for key, value in kwargs.items() if key not in _FRAMEWORK_ARGUMENTS}
    if extra:
        frappe.throw(frappe._("Unknown request argument."), frappe.ValidationError)


def _finish(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except rules.RuleViolation as error:
        frappe.throw(frappe._(error.message), frappe.ValidationError)


@frappe.whitelist(methods=["GET"])
def get_eligible_execution_nodes(project=None, txt=None, **kwargs):
    _reject_extra(kwargs)
    payload = {"project": project, "txt": txt or ""}
    rules.validate_request_size(payload)
    return _finish(service.get_eligible_execution_nodes, **payload)


@frappe.whitelist(methods=["GET"])
def get_mapping_display_context(doctype=None, name=None, **kwargs):
    _reject_extra(kwargs)
    payload = {"doctype": doctype, "name": name}
    rules.validate_request_size(payload)
    return _finish(service.get_mapping_display_context, **payload)


@frappe.whitelist(methods=["GET"])
def get_new_stage_default_preview(boq_item=None, **kwargs):
    _reject_extra(kwargs)
    payload = {"boq_item": boq_item}
    rules.validate_request_size(payload)
    return _finish(service.get_new_stage_default_preview, **payload)


@frappe.whitelist(methods=["POST"])
def set_item_planned_execution_node(
    boq_item=None,
    execution_node=None,
    reason=None,
    expected_modified=None,
    **kwargs,
):
    _reject_extra(kwargs)
    payload = {
        "boq_item": boq_item,
        "execution_node": execution_node,
        "reason": reason,
        "expected_modified": expected_modified,
    }
    rules.validate_request_size(payload)
    return _finish(service.set_item_planned_execution_node, **payload)


@frappe.whitelist(methods=["POST"])
def set_stage_execution_node(
    boq_item_stage=None,
    execution_node=None,
    reason=None,
    expected_modified=None,
    **kwargs,
):
    _reject_extra(kwargs)
    payload = {
        "boq_item_stage": boq_item_stage,
        "execution_node": execution_node,
        "reason": reason,
        "expected_modified": expected_modified,
    }
    rules.validate_request_size(payload)
    return _finish(service.set_stage_execution_node, **payload)


@frappe.whitelist(methods=["GET"])
def get_execution_mapping_audit(target_doctype=None, target_name=None, **kwargs):
    _reject_extra(kwargs)
    payload = {"target_doctype": target_doctype, "target_name": target_name}
    rules.validate_request_size(payload)
    return _finish(service.get_execution_mapping_audit, **payload)
