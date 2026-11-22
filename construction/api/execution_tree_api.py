"""Dedicated RPC surface for the P1 Project Execution Tree."""

from __future__ import annotations

import frappe

from construction.services import execution_tree as service
from construction.services import execution_tree_rules as rules


def _finish(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except rules.RuleViolation as error:
        frappe.throw(error.message, frappe.ValidationError)


_FRAMEWORK_ARGUMENTS = frozenset({"cmd", "_"})
_BOOLEAN_ARGUMENTS = ("is_group", "disabled")


def _as_boolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    return value


def _prepare(payload):
    # ``frappe.call`` form-encodes top-level booleans, so "true"/"false" arrive
    # as strings. Coerce the declared boolean arguments and leave anything else
    # for the rule layer to reject.
    for key in _BOOLEAN_ARGUMENTS:
        if key in payload:
            payload[key] = _as_boolean(payload[key])
    rules.validate_request_size(payload)
    return payload


def _reject_extra(kwargs):
    # Frappe injects framework keys into the call arguments: ``cmd`` from the
    # route and ``_`` from the client cache buster. They are not caller payload.
    extra = {key: value for key, value in kwargs.items() if key not in _FRAMEWORK_ARGUMENTS}
    if extra:
        frappe.throw(frappe._("Unknown request argument."), frappe.ValidationError)


@frappe.whitelist(methods=["GET"])
def get_tree(project=None, **kwargs):
    _reject_extra(kwargs)
    payload = _prepare({"project": project})
    return _finish(service.get_tree, **payload)


@frappe.whitelist(methods=["POST"])
def create_node(
    project=None,
    title=None,
    is_group=None,
    parent_node=None,
    expected_parent_modified=None,
    **kwargs,
):
    _reject_extra(kwargs)
    payload = _prepare(
        {
            "project": project,
            "title": title,
            "is_group": is_group,
            "parent_node": parent_node,
            "expected_parent_modified": expected_parent_modified,
        }
    )
    return _finish(service.create_node, **payload)


@frappe.whitelist(methods=["POST"])
def update_node(
    project=None,
    name=None,
    expected_modified=None,
    title=None,
    is_group=None,
    **kwargs,
):
    _reject_extra(kwargs)
    payload = _prepare(
        {
            "project": project,
            "name": name,
            "expected_modified": expected_modified,
            "title": title,
            "is_group": is_group,
        }
    )
    return _finish(service.update_node, **payload)


@frappe.whitelist(methods=["POST"])
def move_node(
    project=None,
    name=None,
    expected_modified=None,
    parent_node=None,
    expected_parent_modified=None,
    **kwargs,
):
    _reject_extra(kwargs)
    payload = _prepare(
        {
            "project": project,
            "name": name,
            "expected_modified": expected_modified,
            "parent_node": parent_node,
            "expected_parent_modified": expected_parent_modified,
        }
    )
    return _finish(service.move_node, **payload)


@frappe.whitelist(methods=["POST"])
def set_disabled(project=None, name=None, expected_modified=None, disabled=None, **kwargs):
    _reject_extra(kwargs)
    payload = _prepare(
        {
            "project": project,
            "name": name,
            "expected_modified": expected_modified,
            "disabled": disabled,
        }
    )
    return _finish(service.set_disabled, **payload)


@frappe.whitelist(methods=["POST"])
def delete_node(project=None, name=None, expected_modified=None, **kwargs):
    _reject_extra(kwargs)
    payload = _prepare({"project": project, "name": name, "expected_modified": expected_modified})
    return _finish(service.delete_node, **payload)
