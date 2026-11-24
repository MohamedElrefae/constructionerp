"""Transactional WBS P2 execution-location mapping service (Slice 1).

Implements Choice B:
- ``BOQ Item.planned_execution_node`` is the planning default.
- ``BOQ Item Stage.execution_node`` is the operational assignment.
- One-time inheritance copies an eligible Item default onto newly created
  Stages; changing the Item default never modifies existing Stages.

Lock order (aligned with ``execution_tree.py``):
1. ``tabProject`` (``FOR UPDATE``)
2. ``tabExecution Breakdown Node`` for the project (``ORDER BY name FOR UPDATE``)
3. ``tabBOQ Item`` (``FOR UPDATE NOWAIT`` on write, ``LOCK IN SHARE MODE`` on
   Stage inheritance)
"""

from __future__ import annotations

import contextlib
import contextvars

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from construction.services import execution_tree_access as access
from construction.services import execution_tree_rules as rules
from construction.services.boq_transactions import current_boq_sql

_MAPPING_GUARD: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "execution_mapping_guard", default=None
)
_AUDIT_INSERT_GUARD: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "execution_mapping_audit_insert_guard", default=None
)

ALLOWED_TARGET_DOCTYPES = frozenset({"BOQ Item", "BOQ Item Stage"})
ITEM_MAPPING_IGNORED_DIFF_FIELDS = frozenset({"planned_execution_node", "modified", "modified_by"})


def _translate(error):
    if isinstance(error, access.AccessDenied | access.UnsupportedProfile | access.IntegrityFailure):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if isinstance(error, rules.RuleViolation):
        frappe.throw(_(error.message), frappe.ValidationError)
    raise error


def require_mapping_table(doctype):
    """Fail-closed table check: never swallow DB/metadata lookup failures."""
    exists = bool(frappe.db.table_exists(doctype))
    if exists:
        return True
    # If the audit table is installed, this is a P2 site: a missing core table is an integrity error.
    if doctype != rules.AUDIT_DOCTYPE and bool(frappe.db.table_exists(rules.AUDIT_DOCTYPE)):
        frappe.throw(
            _("Execution mapping schema is incomplete: table for {0} is missing.").format(doctype),
            frappe.ValidationError,
        )
    return False


def require_mapping_column(doctype, column):
    """Fail-closed column check distinguishing pre-migration sites from lookup errors.

    Never catches exceptions so metadata lookup failures abort writes instead of
    silently disabling guards. On a P2-installed site (where ``Execution Mapping Audit``
    exists), a missing mapping column aborts the write.
    """
    table_ok = bool(frappe.db.table_exists(doctype))
    col_ok = bool(table_ok and frappe.db.has_column(doctype, column))
    if col_ok:
        return True
    if bool(frappe.db.table_exists(rules.AUDIT_DOCTYPE)):
        frappe.throw(
            _("Execution mapping schema is incomplete: {0}.{1} is missing. Run bench migrate.").format(
                doctype, column
            ),
            frappe.ValidationError,
        )
    return False


def _caller_is_mapping_planner(user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    roles = set(frappe.get_roles(user))
    return bool(roles.intersection(rules.MAPPING_PLANNER_ROLES))


def _authorize_planner_mapping(target_doctype, target_name, boq_header, project, *, is_new=False):
    """Unified mapping authorization gate for set, change, clear, and create-with-node."""
    if not _caller_is_mapping_planner():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if not boq_header or not project:
        frappe.throw(_("A valid BOQ Header and Project are required."), frappe.ValidationError)
    if not frappe.has_permission("BOQ Header", "write", doc=boq_header):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if is_new:
        if not frappe.has_permission(target_doctype, "create"):
            frappe.throw(_("Not permitted."), frappe.PermissionError)
    else:
        if not frappe.has_permission(target_doctype, "write", doc=target_name):
            frappe.throw(_("Not permitted."), frappe.PermissionError)
    try:
        decision, _payload = access.authorize(project, "read")
    except Exception as error:
        _translate(error)
    return decision


def _lock_project(project):
    rows = current_boq_sql(
        "SELECT name, company, cost_center FROM `tabProject` WHERE name=%s FOR UPDATE",
        (project,),
        as_dict=True,
    )
    if not rows:
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    return rows[0]


def _lock_project_nodes(project):
    rows = current_boq_sql(
        "SELECT name, title, project, company, parent_node, is_group, disabled, ebs_code, modified "
        "FROM `tabExecution Breakdown Node` WHERE project=%s "
        "ORDER BY name LIMIT %s FOR UPDATE",
        (project, rules.MAX_NODES + 1),
        as_dict=True,
    )
    if len(rows) > rules.MAX_NODES:
        frappe.throw(_("The execution tree exceeds its supported size."), frappe.ValidationError)
    return [_node_dict(row) for row in rows]


def _read_project_nodes_unlocked(project):
    rows = frappe.db.sql(
        "SELECT name, title, project, company, parent_node, is_group, disabled, ebs_code, modified "
        "FROM `tabExecution Breakdown Node` WHERE project=%s "
        "ORDER BY name LIMIT %s",
        (project, rules.MAX_NODES + 1),
        as_dict=True,
    )
    return [_node_dict(row) for row in rows]


def _node_dict(row):
    return {
        "name": row.get("name"),
        "title": row.get("title"),
        "project": row.get("project"),
        "company": row.get("company"),
        "parent_node": row.get("parent_node") or None,
        "is_group": int(row.get("is_group") or 0),
        "disabled": int(row.get("disabled") or 0),
        "ebs_code": row.get("ebs_code"),
        "modified": str(row.get("modified")) if row.get("modified") is not None else None,
    }


def _snapshot_node(nodes_by_name, node_name):
    if not node_name:
        return {"node": None, "ebs_code": None, "title": None, "path": None}
    node = nodes_by_name.get(node_name)
    if node is None:
        return {"node": node_name, "ebs_code": None, "title": None, "path": None}
    try:
        path = rules.build_node_path(nodes_by_name, node_name)
    except rules.RuleViolation:
        path = node.get("title") or node.get("ebs_code") or node_name
    return {
        "node": node_name,
        "ebs_code": node.get("ebs_code"),
        "title": node.get("title"),
        "path": path,
    }


@contextlib.contextmanager
def _establish_audit_insert_guard(doc):
    if _AUDIT_INSERT_GUARD.get() is not None:
        frappe.throw(_("Nested audit guards are not permitted."), frappe.PermissionError)
    token = _AUDIT_INSERT_GUARD.set({"actor": frappe.session.user, "document": doc})
    try:
        yield
    finally:
        _AUDIT_INSERT_GUARD.reset(token)


def require_audit_insert_guard(doc):
    guard = _AUDIT_INSERT_GUARD.get()
    if guard is None:
        frappe.throw(_("Execution Mapping Audit records can only be created by the mapping service."), frappe.PermissionError)
    if guard["actor"] != frappe.session.user or guard["document"] is not doc:
        frappe.throw(_("Execution Mapping Audit guard mismatch."), frappe.PermissionError)


def is_guarded_audit_insert(doc):
    guard = _AUDIT_INSERT_GUARD.get()
    return bool(guard is not None and guard["actor"] == frappe.session.user and guard["document"] is doc)


def _insert_audit_row(
    *,
    target_doctype,
    target_name,
    project,
    boq_header,
    boq_item,
    action,
    old_snap,
    new_snap,
    reason="",
    is_historical_assignment=0,
    historical_trigger="",
    stage_status_snapshot=None,
    measured_qty_snapshot=None,
    certified_qty_snapshot=None,
    changed_on=None,
):
    doc = frappe.get_doc(
        {
            "doctype": rules.AUDIT_DOCTYPE,
            "target_doctype": target_doctype,
            "target_name": target_name,
            "project": project,
            "boq_header": boq_header,
            "boq_item": boq_item,
            "action": action,
            "is_historical_assignment": 1 if is_historical_assignment else 0,
            "historical_trigger": historical_trigger or "",
            "stage_status_snapshot": stage_status_snapshot or "",
            "measured_qty_snapshot": flt(measured_qty_snapshot) if measured_qty_snapshot is not None else None,
            "certified_qty_snapshot": flt(certified_qty_snapshot) if certified_qty_snapshot is not None else None,
            "old_node": old_snap.get("node") or "",
            "old_ebs_code": old_snap.get("ebs_code") or "",
            "old_title": old_snap.get("title") or "",
            "old_path_snapshot": old_snap.get("path") or "",
            "new_node": new_snap.get("node") or "",
            "new_ebs_code": new_snap.get("ebs_code") or "",
            "new_title": new_snap.get("title") or "",
            "new_path_snapshot": new_snap.get("path") or "",
            "reason": reason or "",
            "changed_by": frappe.session.user,
            "changed_on": changed_on or now_datetime(),
        }
    )
    with _establish_audit_insert_guard(doc):
        doc.insert(ignore_permissions=True)
    return doc.name


def get_eligible_execution_nodes(project, txt=""):
    """Return same-project, effectively-enabled leaf nodes authorized via P1 read."""
    project = rules.validate_identifier(project, field="Project")
    needle = (txt or "").strip().lower()

    def read_snapshot(reader):
        rows = reader.query(
            "SELECT name, title, project, company, parent_node, is_group, disabled, ebs_code, modified "
            "FROM `tabExecution Breakdown Node` WHERE project=%s "
            "ORDER BY ebs_code, name LIMIT %s",
            (project, rules.MAX_NODES + 1),
        )
        if len(rows) > rules.MAX_NODES:
            raise rules.RuleViolation("too_large", "The execution tree exceeds its supported size.")
        return [_node_dict(row) for row in rows]

    try:
        _decision, nodes = access.authorize(project, "read", read_snapshot)
    except Exception as error:
        _translate(error)

    nodes_by_name = rules.index_nodes_by_name(nodes)
    eligible = []
    for node in nodes:
        ok, _code, _msg = rules.is_eligible_execution_leaf(nodes_by_name, node["name"], project=project)
        if not ok:
            continue
        full_path = rules.build_node_path(nodes_by_name, node["name"])
        if needle:
            haystack = " ".join(
                (
                    str(node.get("ebs_code") or ""),
                    str(node.get("title") or ""),
                    full_path,
                    str(node.get("name") or ""),
                )
            ).lower()
            if needle not in haystack:
                continue
        eligible.append(
            {
                "name": node["name"],
                "ebs_code": node.get("ebs_code"),
                "title": node.get("title"),
                "full_path": full_path,
                "project": project,
            }
        )
    return eligible


def _build_node_display(nodes_by_name, node_name, project):
    if not node_name:
        return None
    node = nodes_by_name.get(node_name)
    if node is None:
        return {
            "node": node_name,
            "ebs_code": None,
            "title": None,
            "full_path": None,
            "is_effectively_disabled": True,
            "disabled_reason": "missing",
            "project_mismatch": True,
        }
    is_disabled, disabled_reason = rules.disabled_state(nodes_by_name, node_name)
    try:
        full_path = rules.build_node_path(nodes_by_name, node_name)
    except rules.RuleViolation:
        full_path = node.get("title") or node.get("ebs_code") or node_name
    return {
        "node": node_name,
        "ebs_code": node.get("ebs_code"),
        "title": node.get("title"),
        "full_path": full_path,
        "is_effectively_disabled": bool(is_disabled),
        "disabled_reason": disabled_reason,
        "project_mismatch": (node.get("project") != project),
    }


DISPLAY_CONTEXT_FIELDS = frozenset({"doctype", "name", "project", "assigned", "attribution"})
DISPLAY_ATTRIBUTION_FIELDS = frozenset({"action", "is_historical_assignment", "mapped_by", "mapped_on"})


def _display_attribution_summary(project, target_doctype, target_name):
    """Return minimal non-sensitive attribution metadata for ordinary BOQ readers.

    Planner ``reason``, ``historical_trigger``, and audit record IDs are intentionally
    excluded here and served exclusively through ``get_execution_mapping_audit``.
    """
    if not require_mapping_table(rules.AUDIT_DOCTYPE):
        return None
    rows = frappe.db.sql(
        "SELECT action, is_historical_assignment, changed_by, changed_on "
        "FROM `tabExecution Mapping Audit` "
        "WHERE project=%s AND target_doctype=%s AND target_name=%s "
        "ORDER BY changed_on DESC, name DESC LIMIT 1",
        (project, target_doctype, target_name),
        as_dict=True,
    )
    if not rows:
        return None
    row = rows[0]
    return {
        "action": row.get("action"),
        "is_historical_assignment": bool(int(row.get("is_historical_assignment") or 0)),
        "mapped_by": row.get("changed_by"),
        "mapped_on": str(row.get("changed_on")) if row.get("changed_on") else None,
    }


def get_mapping_display_context(doctype, name):
    """Record-bound display label lookup for any user who can read the BOQ record."""
    if doctype not in ALLOWED_TARGET_DOCTYPES:
        frappe.throw(_("Unsupported target document type."), frappe.ValidationError)
    name = rules.validate_identifier(name, field="Document name")
    if not frappe.db.exists(doctype, name):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if not frappe.has_permission(doctype, "read", doc=name):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    if doctype == "BOQ Item":
        row = frappe.db.get_value(
            "BOQ Item", name, ["name", "boq_header", "planned_execution_node"], as_dict=True
        )
        boq_header = row.boq_header if row else None
        project = frappe.db.get_value("BOQ Header", boq_header, "project") if boq_header else None
        assigned_node = (row.planned_execution_node or None) if row else None
        nodes_by_name = rules.index_nodes_by_name(_read_project_nodes_unlocked(project)) if project else {}
        return {
            "doctype": doctype,
            "name": name,
            "project": project,
            "assigned": _build_node_display(nodes_by_name, assigned_node, project),
            "attribution": _display_attribution_summary(project, doctype, name) if project else None,
        }

    row = frappe.db.get_value(
        "BOQ Item Stage",
        name,
        ["name", "boq_item", "boq_header", "project", "execution_node"],
        as_dict=True,
    )
    boq_header = row.boq_header if row else None
    project = (
        frappe.db.get_value("BOQ Header", boq_header, "project")
        if boq_header
        else (row.project if row else None)
    )
    assigned_node = (row.execution_node or None) if row else None
    nodes_by_name = rules.index_nodes_by_name(_read_project_nodes_unlocked(project)) if project else {}
    return {
        "doctype": doctype,
        "name": name,
        "project": project,
        "assigned": _build_node_display(nodes_by_name, assigned_node, project),
        "attribution": _display_attribution_summary(project, doctype, name) if project else None,
    }


def get_new_stage_default_preview(boq_item):
    """Record-bound preview of the Item's current planned_execution_node for a new Stage form."""
    boq_item = rules.validate_identifier(boq_item, field="BOQ Item")
    if not frappe.db.exists("BOQ Item", boq_item):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if not frappe.has_permission("BOQ Item", "read", doc=boq_item):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    row = frappe.db.get_value("BOQ Item", boq_item, ["boq_header", "planned_execution_node"], as_dict=True)
    boq_header = row.boq_header if row else None
    project = frappe.db.get_value("BOQ Header", boq_header, "project") if boq_header else None
    default_node = (row.planned_execution_node or None) if row else None
    if not default_node or not project:
        return {"boq_item": boq_item, "project": project, "will_inherit": False, "preview": None, "warning": None}
    nodes_by_name = rules.index_nodes_by_name(_read_project_nodes_unlocked(project))
    display = _build_node_display(nodes_by_name, default_node, project)
    ok, _code, msg = rules.is_eligible_execution_leaf(nodes_by_name, default_node, project=project)
    return {
        "boq_item": boq_item,
        "project": project,
        "will_inherit": bool(ok),
        "preview": display,
        "warning": None if ok else msg,
    }


def set_item_planned_execution_node(boq_item, execution_node=None, reason=None, expected_modified=None):
    """Narrow governed transaction to set, change, or clear ``BOQ Item.planned_execution_node``."""
    boq_item = rules.validate_identifier(boq_item, field="BOQ Item")
    try:
        expected = rules.validate_expected_modified(expected_modified, required=True)
    except rules.RuleViolation as error:
        _translate(error)

    new_node = None
    if execution_node is not None and str(execution_node).strip():
        try:
            new_node = rules.validate_identifier(str(execution_node).strip(), field="Execution location")
        except rules.RuleViolation as error:
            _translate(error)

    initial = frappe.db.get_value("BOQ Item", boq_item, ["name", "boq_header"], as_dict=True)
    if not initial or not initial.boq_header:
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    initial_project = frappe.db.get_value("BOQ Header", initial.boq_header, "project")
    if not initial_project:
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    # Pre-lock authorization check prevents unauthorized callers from contending on locks.
    _authorize_planner_mapping("BOQ Item", boq_item, initial.boq_header, initial_project, is_new=False)

    # Deterministic lock order: Project -> Execution Breakdown Nodes -> BOQ Item.
    _lock_project(initial_project)
    nodes = _lock_project_nodes(initial_project)
    locked_rows = current_boq_sql(
        "SELECT * FROM `tabBOQ Item` WHERE name=%s FOR UPDATE NOWAIT",
        (boq_item,),
        as_dict=True,
    )
    if not locked_rows:
        frappe.throw(_("BOQ Item {0} does not exist.").format(boq_item), frappe.DoesNotExistError)
    item_row = locked_rows[0]

    header_rows = current_boq_sql(
        "SELECT name, project FROM `tabBOQ Header` WHERE name=%s LOCK IN SHARE MODE",
        (item_row.get("boq_header"),),
        as_dict=True,
    )
    if not header_rows or header_rows[0].get("project") != initial_project:
        frappe.throw(_("BOQ Item project changed concurrently. Reload and try again."), frappe.ValidationError)
    boq_header = header_rows[0]["name"]
    project = header_rows[0]["project"]

    if rules.stale_version(item_row.get("modified"), expected):
        frappe.throw(_("This BOQ Item changed. Reload and try again."), frappe.ValidationError)

    # Re-verify unified permission gate under locks.
    _authorize_planner_mapping("BOQ Item", boq_item, boq_header, project, is_new=False)

    old_node = (item_row.get("planned_execution_node") or None)
    if old_node == new_node:
        return {
            "changed": False,
            "action": None,
            "boq_item": boq_item,
            "planned_execution_node": old_node,
            "modified": str(item_row.get("modified")),
            "audit_name": None,
        }

    if old_node is None and new_node is not None:
        action = "set"
    elif old_node is not None and new_node is None:
        action = "clear"
    else:
        action = "change"

    try:
        cleaned_reason = rules.validate_mapping_reason(action, reason)
    except rules.RuleViolation as error:
        _translate(error)

    nodes_by_name = rules.index_nodes_by_name(nodes)
    if new_node is not None:
        try:
            rules.validate_eligible_execution_leaf(nodes_by_name, new_node, project=project)
        except rules.RuleViolation as error:
            _translate(error)

    old_snap = _snapshot_node(nodes_by_name, old_node)
    new_snap = _snapshot_node(nodes_by_name, new_node)
    before_preserved = {
        key: value for key, value in item_row.items() if key not in ITEM_MAPPING_IGNORED_DIFF_FIELDS
    }

    now = now_datetime()
    frappe.db.sql(
        "UPDATE `tabBOQ Item` SET planned_execution_node=%s, modified=%s, modified_by=%s WHERE name=%s",
        (new_node, now, frappe.session.user, boq_item),
    )

    after_rows = current_boq_sql(
        "SELECT * FROM `tabBOQ Item` WHERE name=%s FOR UPDATE NOWAIT",
        (boq_item,),
        as_dict=True,
    )
    if not after_rows:
        frappe.throw(_("BOQ Item disappeared during mapping update."), frappe.ValidationError)
    after_row = after_rows[0]
    after_preserved = {
        key: value for key, value in after_row.items() if key not in ITEM_MAPPING_IGNORED_DIFF_FIELDS
    }
    if after_preserved != before_preserved:
        frappe.throw(
            _("Unexpected mutation detected on commercial BOQ Item fields; rolling back."),
            frappe.ValidationError,
        )

    audit_name = _insert_audit_row(
        target_doctype="BOQ Item",
        target_name=boq_item,
        project=project,
        boq_header=boq_header,
        boq_item=boq_item,
        action=action,
        old_snap=old_snap,
        new_snap=new_snap,
        reason=cleaned_reason,
        changed_on=now,
    )

    return {
        "changed": True,
        "action": action,
        "boq_item": boq_item,
        "planned_execution_node": new_node,
        "modified": str(after_row.get("modified")),
        "audit_name": audit_name,
        "node_summary": _build_node_display(nodes_by_name, new_node, project),
    }


def get_execution_mapping_audit(target_doctype, target_name):
    """Return immutable mapping audit rows scoped to an authorized BOQ Item or Stage."""
    if target_doctype not in ALLOWED_TARGET_DOCTYPES:
        frappe.throw(_("Unsupported target document type."), frappe.ValidationError)
    target_name = rules.validate_identifier(target_name, field="Target name")
    if not _caller_is_mapping_planner():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if not frappe.db.exists(target_doctype, target_name):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if not frappe.has_permission(target_doctype, "read", doc=target_name):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    boq_header = frappe.db.get_value(target_doctype, target_name, "boq_header")
    if not boq_header or not frappe.has_permission("BOQ Header", "read", doc=boq_header):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    project = frappe.db.get_value("BOQ Header", boq_header, "project")
    if not project:
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    try:
        access.authorize(project, "read")
    except Exception as error:
        _translate(error)

    rows = frappe.db.sql(
        "SELECT name, target_doctype, target_name, project, boq_header, boq_item, action, "
        "is_historical_assignment, historical_trigger, stage_status_snapshot, "
        "measured_qty_snapshot, certified_qty_snapshot, "
        "old_node, old_ebs_code, old_title, old_path_snapshot, "
        "new_node, new_ebs_code, new_title, new_path_snapshot, "
        "reason, changed_by, changed_on "
        "FROM `tabExecution Mapping Audit` "
        "WHERE project=%s AND target_doctype=%s AND target_name=%s "
        "ORDER BY changed_on ASC, name ASC",
        (project, target_doctype, target_name),
        as_dict=True,
    )
    for row in rows:
        if row.get("changed_on") is not None:
            row["changed_on"] = str(row["changed_on"])
    return rows


def enforce_boq_header_project_change_guard(doc):
    """Reject BOQ Header project change while any child Item or Stage has a mapping.

    Checks BOQ Item defaults and BOQ Item Stage assignments independently using
    current locking reads, including Stages that retained their location after
    their parent Item default was cleared.
    """
    if doc.is_new():
        return
    before = doc.get_doc_before_save()
    if before is None or (before.project or None) == (doc.project or None):
        return
    item_col_ready = require_mapping_column("BOQ Item", "planned_execution_node")
    stage_col_ready = require_mapping_column("BOQ Item Stage", "execution_node")
    if not item_col_ready and not stage_col_ready:
        return
    from construction.services.boq_transactions import lock_boq_header

    lock_boq_header(doc.name)
    if item_col_ready:
        mapped_item = current_boq_sql(
            "SELECT name FROM `tabBOQ Item` "
            "WHERE boq_header=%s AND planned_execution_node IS NOT NULL AND planned_execution_node != '' "
            "LIMIT 1 LOCK IN SHARE MODE",
            (doc.name,),
            as_dict=True,
        )
        if mapped_item:
            frappe.throw(
                _(
                    "Cannot change BOQ Header Project while BOQ Item {0} has a Planned Execution Location assigned."
                ).format(mapped_item[0]["name"]),
                frappe.ValidationError,
            )
    if stage_col_ready:
        mapped_stage = current_boq_sql(
            "SELECT name FROM `tabBOQ Item Stage` "
            "WHERE (boq_header=%s OR boq_item IN (SELECT name FROM `tabBOQ Item` WHERE boq_header=%s)) "
            "AND execution_node IS NOT NULL AND execution_node != '' "
            "LIMIT 1 LOCK IN SHARE MODE",
            (doc.name, doc.name),
            as_dict=True,
        )
        if mapped_stage:
            frappe.throw(
                _(
                    "Cannot change BOQ Header Project while BOQ Item Stage {0} has an Execution Location assigned."
                ).format(mapped_stage[0]["name"]),
                frappe.ValidationError,
            )


def _reread_locked_stage_parent_context(boq_item, expected_project):
    """Re-read parent BOQ Item + BOQ Header + Project under lock to prevent drift."""
    item_rows = current_boq_sql(
        "SELECT name, boq_header, structure, planned_execution_node "
        "FROM `tabBOQ Item` WHERE name=%s LOCK IN SHARE MODE",
        (boq_item,),
        as_dict=True,
    )
    if not item_rows:
        frappe.throw(_("BOQ Item {0} does not exist.").format(boq_item), frappe.DoesNotExistError)
    item_row = item_rows[0]
    header_rows = current_boq_sql(
        "SELECT name, project FROM `tabBOQ Header` WHERE name=%s LOCK IN SHARE MODE",
        (item_row.get("boq_header"),),
        as_dict=True,
    )
    if not header_rows or not header_rows[0].get("project"):
        frappe.throw(_("BOQ Header for BOQ Item {0} does not exist.").format(boq_item), frappe.ValidationError)
    header_row = header_rows[0]
    if header_row["project"] != expected_project:
        frappe.throw(
            _("BOQ Item project changed concurrently. Reload and try again."),
            frappe.ValidationError,
        )
    return item_row, header_row


AUDIT_SERIES_KEY = "EMA-"


def reconcile_audit_series_counter():
    """Repeat-safe monotonic reconciliation of the ``EMA-`` naming series counter.

    Sites that previously created ``Execution Mapping Audit`` rows under the
    shared empty-key ``format:EMA-{#######}`` series may have existing IDs
    higher than ``tabSeries(name='EMA-').current``. Advance ``EMA-`` to at
    least the highest existing numeric suffix without modifying any audit row.
    """
    if not frappe.db.table_exists(rules.AUDIT_DOCTYPE):
        return None
    rows = frappe.db.sql(
        "SELECT MAX(CAST(SUBSTRING(name, 5) AS UNSIGNED)) AS max_suffix "
        "FROM `tabExecution Mapping Audit` "
        "WHERE name REGEXP '^EMA-[0-9]+$'",
        as_dict=True,
    )
    max_existing = int((rows[0].get("max_suffix") or 0) if rows else 0)
    if max_existing <= 0:
        return 0
    series_rows = frappe.db.sql(
        "SELECT current FROM `tabSeries` WHERE name=%s FOR UPDATE",
        (AUDIT_SERIES_KEY,),
        as_dict=True,
    )
    if not series_rows:
        frappe.db.sql(
            "INSERT INTO `tabSeries` (`name`, `current`) VALUES (%s, %s)",
            (AUDIT_SERIES_KEY, max_existing),
        )
        return max_existing
    current = int(series_rows[0].get("current") or 0)
    if current < max_existing:
        frappe.db.sql(
            "UPDATE `tabSeries` SET `current`=%s WHERE `name`=%s",
            (max_existing, AUDIT_SERIES_KEY),
        )
        return max_existing
    return current


def enforce_boq_item_mapping_guard(doc):
    """Controller guard for ``BOQItem.validate()`` (all write paths: form/REST/import/bulk)."""
    if not require_mapping_column("BOQ Item", "planned_execution_node"):
        return
    if not doc.is_new():
        before = doc.get_doc_before_save()
        if before is not None:
            old_val = (before.get("planned_execution_node") or None)
            new_val = (doc.get("planned_execution_node") or None)
            if old_val != new_val:
                guard = _MAPPING_GUARD.get()
                if guard is None or guard.get("document") is not doc:
                    frappe.throw(
                        _("Use the authorized Execution Location action to change Planned Execution Location."),
                        frappe.PermissionError,
                    )
        # Resolve destination Header project under lock for reverse parent-chain checks.
        header_project = None
        if doc.boq_header:
            header_rows = current_boq_sql(
                "SELECT project FROM `tabBOQ Header` WHERE name=%s LOCK IN SHARE MODE",
                (doc.boq_header,),
                as_dict=True,
            )
            header_project = header_rows[0].get("project") if header_rows else None
        # Reverse parent-chain check #1: Item's own planned_execution_node must match Header project.
        current_node = doc.get("planned_execution_node") or None
        if current_node and doc.boq_header:
            node_project = frappe.db.get_value(rules.NODE_DOCTYPE, current_node, "project")
            if not node_project or node_project != header_project:
                frappe.throw(
                    _("Planned Execution Location {0} does not belong to Project {1}.").format(
                        current_node, header_project
                    ),
                    frappe.ValidationError,
                )
        # Reverse parent-chain check #2: if BOQ Item.boq_header changed, verify NO retained
        # child BOQ Item Stage mapping would be stranded in a different project.
        if before is not None and (before.get("boq_header") or None) != (doc.get("boq_header") or None):
            if require_mapping_column("BOQ Item Stage", "execution_node"):
                mapped_stages = current_boq_sql(
                    "SELECT s.name, s.execution_node, n.project AS node_project "
                    "FROM `tabBOQ Item Stage` s "
                    "LEFT JOIN `tabExecution Breakdown Node` n ON n.name = s.execution_node "
                    "WHERE s.boq_item = %s "
                    "AND s.execution_node IS NOT NULL AND s.execution_node != '' "
                    "LOCK IN SHARE MODE",
                    (doc.name,),
                    as_dict=True,
                )
                for stage_row in mapped_stages:
                    if not stage_row.get("node_project") or stage_row["node_project"] != header_project:
                        frappe.throw(
                            _(
                                "Cannot move BOQ Item {0} to Project {1} because BOQ Item Stage {2} is mapped to an execution location in Project {3}."
                            ).format(
                                doc.name,
                                header_project,
                                stage_row["name"],
                                stage_row.get("node_project") or _("unknown"),
                            ),
                            frappe.ValidationError,
                        )
        return

    # New BOQ Item with explicit planned_execution_node.
    chosen_node = (doc.get("planned_execution_node") or "").strip() or None
    doc.planned_execution_node = chosen_node
    if not chosen_node:
        return
    if not doc.boq_header:
        frappe.throw(_("BOQ Header is required before setting Planned Execution Location."), frappe.ValidationError)
    project = frappe.db.get_value("BOQ Header", doc.boq_header, "project")
    _authorize_planner_mapping("BOQ Item", None, doc.boq_header, project, is_new=True)
    _lock_project(project)
    nodes = _lock_project_nodes(project)
    header_rows = current_boq_sql(
        "SELECT name, project FROM `tabBOQ Header` WHERE name=%s LOCK IN SHARE MODE",
        (doc.boq_header,),
        as_dict=True,
    )
    if not header_rows or header_rows[0].get("project") != project:
        frappe.throw(_("BOQ Header project changed concurrently. Reload and try again."), frappe.ValidationError)
    nodes_by_name = rules.index_nodes_by_name(nodes)
    try:
        rules.validate_eligible_execution_leaf(nodes_by_name, chosen_node, project=project)
    except rules.RuleViolation as error:
        _translate(error)
    doc.flags._pending_mapping_audit = {
        "target_doctype": "BOQ Item",
        "project": project,
        "boq_header": doc.boq_header,
        "action": "set_on_create",
        "old_snap": _snapshot_node(nodes_by_name, None),
        "new_snap": _snapshot_node(nodes_by_name, chosen_node),
        "reason": "",
    }


def enforce_boq_stage_mapping_guard(doc):
    """Controller guard + one-time inheritance for ``BOQItemStage.validate()``."""
    if not require_mapping_column("BOQ Item Stage", "execution_node"):
        return
    if not doc.is_new():
        before = doc.get_doc_before_save()
        if before is not None:
            old_val = (before.get("execution_node") or None)
            new_val = (doc.get("execution_node") or None)
            if old_val != new_val:
                guard = _MAPPING_GUARD.get()
                if guard is None or guard.get("document") is not doc:
                    frappe.throw(
                        _("Use the authorized Execution Location action to change Execution Location."),
                        frappe.PermissionError,
                    )
        # Reverse parent-chain check: item/header project must still match stored node's project.
        current_node = doc.get("execution_node") or None
        if current_node:
            node_project = frappe.db.get_value(rules.NODE_DOCTYPE, current_node, "project")
            if not node_project or node_project != doc.project:
                frappe.throw(
                    _("Execution Location {0} does not belong to Project {1}.").format(
                        current_node, doc.project
                    ),
                    frappe.ValidationError,
                )
        return

    # New BOQ Item Stage creation.
    if not doc.boq_item or not doc.boq_header or not doc.project:
        return
    if not require_mapping_table(rules.NODE_DOCTYPE):
        return

    supplied_node = (doc.get("execution_node") or "").strip() or None
    if supplied_node:
        # Explicit node on Stage creation requires planner mapping authority (denies Site Engineer).
        _authorize_planner_mapping("BOQ Item Stage", None, doc.boq_header, doc.project, is_new=True)
        # Same lock order: Project -> Execution Breakdown Nodes -> BOQ Item -> BOQ Header (re-read).
        _lock_project(doc.project)
        nodes = _lock_project_nodes(doc.project)
        item_row, header_row = _reread_locked_stage_parent_context(doc.boq_item, doc.project)
        doc.boq_header = header_row["name"]
        doc.boq_structure = item_row.get("structure") or doc.boq_structure
        doc.project = header_row["project"]
        _authorize_planner_mapping("BOQ Item Stage", None, doc.boq_header, doc.project, is_new=True)
        nodes_by_name = rules.index_nodes_by_name(nodes)
        try:
            rules.validate_eligible_execution_leaf(nodes_by_name, supplied_node, project=doc.project)
        except rules.RuleViolation as error:
            _translate(error)
        doc.execution_node = supplied_node
        doc.flags._pending_mapping_audit = {
            "target_doctype": "BOQ Item Stage",
            "project": doc.project,
            "boq_header": doc.boq_header,
            "boq_item": doc.boq_item,
            "action": "set_on_create",
            "old_snap": _snapshot_node(nodes_by_name, None),
            "new_snap": _snapshot_node(nodes_by_name, supplied_node),
            "reason": "",
            "stage_status_snapshot": doc.stage_status,
            "measured_qty_snapshot": doc.measured_executed_qty,
            "certified_qty_snapshot": doc.certified_qty,
        }
        return

    # Blank execution_node on creation -> one-time inheritance from BOQ Item.planned_execution_node.
    if not require_mapping_column("BOQ Item", "planned_execution_node"):
        return

    # Same lock order: Project -> Execution Breakdown Nodes -> BOQ Item -> BOQ Header (re-read).
    _lock_project(doc.project)
    nodes = _lock_project_nodes(doc.project)
    item_row, header_row = _reread_locked_stage_parent_context(doc.boq_item, doc.project)
    doc.boq_header = header_row["name"]
    doc.boq_structure = item_row.get("structure") or doc.boq_structure
    doc.project = header_row["project"]
    parent_default = item_row.get("planned_execution_node") or None
    if not parent_default:
        doc.execution_node = None
        return

    nodes_by_name = rules.index_nodes_by_name(nodes)
    ok, code, _message = rules.is_eligible_execution_leaf(nodes_by_name, parent_default, project=doc.project)
    if ok:
        doc.execution_node = parent_default
        doc.flags._pending_mapping_audit = {
            "target_doctype": "BOQ Item Stage",
            "project": doc.project,
            "boq_header": doc.boq_header,
            "boq_item": doc.boq_item,
            "action": "inherit_on_create",
            "old_snap": _snapshot_node(nodes_by_name, None),
            "new_snap": _snapshot_node(nodes_by_name, parent_default),
            "reason": "",
            "stage_status_snapshot": doc.stage_status,
            "measured_qty_snapshot": doc.measured_executed_qty,
            "certified_qty_snapshot": doc.certified_qty,
        }
        return

    # Disabled leaf or disabled ancestor (Decision #1): save unmapped with a clear warning.
    doc.execution_node = None
    snap = _snapshot_node(nodes_by_name, parent_default)
    label = snap.get("ebs_code") or parent_default
    if code == "disabled_ancestor":
        doc.flags.execution_node_inheritance_warning = _(
            "The BOQ Item's planned execution location ({0}) is under a disabled ancestor branch and was not inherited. This stage was saved unmapped."
        ).format(label)
        frappe.msgprint(
            _(
                "The BOQ Item's planned execution location ({0}) is under a disabled ancestor branch and was not inherited. This stage was saved unmapped."
            ).format(label),
            indicator="orange",
        )
    else:
        doc.flags.execution_node_inheritance_warning = _(
            "The BOQ Item's planned execution location ({0}) is disabled or ineligible and was not inherited. This stage was saved unmapped."
        ).format(label)
        frappe.msgprint(
            _(
                "The BOQ Item's planned execution location ({0}) is disabled or ineligible and was not inherited. This stage was saved unmapped."
            ).format(label),
            indicator="orange",
        )


def record_pending_mapping_audit(doc):
    """Insert pending creation/inheritance audit row in the same transaction (``after_insert``)."""
    pending = getattr(doc.flags, "_pending_mapping_audit", None)
    if not pending:
        return
    doc.flags._pending_mapping_audit = None
    boq_item = pending.get("boq_item") or (doc.name if pending["target_doctype"] == "BOQ Item" else doc.boq_item)
    _insert_audit_row(
        target_doctype=pending["target_doctype"],
        target_name=doc.name,
        project=pending["project"],
        boq_header=pending["boq_header"],
        boq_item=boq_item,
        action=pending["action"],
        old_snap=pending["old_snap"],
        new_snap=pending["new_snap"],
        reason=pending.get("reason") or "",
        stage_status_snapshot=pending.get("stage_status_snapshot"),
        measured_qty_snapshot=pending.get("measured_qty_snapshot"),
        certified_qty_snapshot=pending.get("certified_qty_snapshot"),
    )
