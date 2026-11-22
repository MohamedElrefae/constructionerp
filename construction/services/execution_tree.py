"""Transactional P1 Project Execution Tree service."""

from __future__ import annotations

import frappe

from construction.services import execution_tree_access as access
from construction.services import execution_tree_rules as rules

NODE_FIELDS = (
    "name",
    "title",
    "project",
    "company",
    "parent_node",
    "is_group",
    "disabled",
    "ebs_code",
    "modified",
)


class StaleWrite(Exception):
    pass


class TreeTooLarge(Exception):
    pass


class TreeNodeInvalid(Exception):
    pass


def _table_exists(doctype):
    return bool(frappe.db.table_exists(doctype))


def _locked_project(project):
    rows = frappe.db.sql(
        "SELECT name, company, cost_center, owner, modified FROM tabProject WHERE name=%s FOR UPDATE",
        (project,),
        as_dict=True,
    )
    if not rows:
        raise access.AccessDenied("Project is unavailable.")
    return rows[0]


def _locked_nodes(project):
    # MariaDB requires LIMIT to precede FOR UPDATE.
    rows = frappe.db.sql(
        "SELECT name, title, project, company, parent_node, is_group, disabled, ebs_code, modified "
        "FROM `tabExecution Breakdown Node` WHERE project=%s "
        "ORDER BY name LIMIT %s FOR UPDATE",
        (project, rules.MAX_NODES + 1),
        as_dict=True,
    )
    if len(rows) > rules.MAX_NODES:
        raise TreeTooLarge("The execution tree exceeds its node limit.")
    return [_node_dict(row) for row in rows]


def _snapshot_nodes(reader, project):
    rows = reader.query(
        "SELECT name, title, project, company, parent_node, is_group, disabled, ebs_code, modified "
        "FROM `tabExecution Breakdown Node` WHERE project=%s "
        "ORDER BY parent_node IS NOT NULL, parent_node, ebs_code, name LIMIT %s",
        (project, rules.MAX_NODES + 1),
    )
    if len(rows) > rules.MAX_NODES:
        raise TreeTooLarge("The execution tree exceeds its node limit.")
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


def _summary(doc):
    return rules.node_summary(_node_dict(doc if isinstance(doc, dict) else doc.as_dict()))


def _translate(error):
    if isinstance(error, access.AccessDenied):
        frappe.throw(frappe._("Not permitted."), frappe.PermissionError)
    if isinstance(error, access.UnsupportedProfile | access.IntegrityFailure):
        frappe.throw(frappe._("Not permitted."), frappe.PermissionError)
    if isinstance(error, StaleWrite):
        frappe.throw(frappe._("This record changed. Reload the tree and try again."), frappe.ValidationError)
    if isinstance(error, TreeTooLarge):
        frappe.throw(
            frappe._("The execution tree exceeds its supported size."),
            frappe.ValidationError,
        )
    if isinstance(error, rules.RuleViolation):
        frappe.throw(frappe._(error.message), frappe.ValidationError)
    raise error


def get_tree(project):
    project = rules.validate_identifier(project, field="Project")

    def read_snapshot(reader):
        return _snapshot_nodes(reader, project)

    try:
        decision, nodes = access.authorize(project, "read", read_snapshot)
        ordered = rules.build_tree(nodes, project=project)
    except Exception as error:
        _translate(error)
    return {
        "project": decision["project"],
        "company": decision["company"],
        "actions": decision["actions"],
        "nodes": rules.summarize_tree(ordered),
    }


def _authorize_locked(project, operation):
    if not _table_exists(rules.NODE_DOCTYPE) or not _table_exists(rules.COUNTER_DOCTYPE):
        raise access.IntegrityFailure("Execution tree schema is not installed.")
    project_row = _locked_project(project)
    decision, _payload = access.authorize(project, operation)
    if decision.get("project") != project_row.get("name"):
        raise access.IntegrityFailure("The authorized Project identity is inconsistent.")
    if (decision.get("company") or None) != (project_row.get("company") or None):
        raise access.IntegrityFailure("The authorized Company is inconsistent.")
    if (decision.get("cost_center") or None) != (project_row.get("cost_center") or None):
        raise access.IntegrityFailure("The authorized Cost Center is inconsistent.")
    return project_row, decision


def _validate_counter_consistency(counter, nodes):
    if counter is None:
        return
    last_issued = rules.validate_counter_value(counter.get("last_issued"))
    for node in nodes:
        code = node.get("ebs_code")
        if not code:
            raise access.IntegrityFailure("A retained node has no execution code.")
        number = rules.parse_execution_code(code)
        if number > last_issued:
            raise access.IntegrityFailure("The execution code counter is behind a retained node.")


def _load_node(project, name):
    rows = frappe.db.sql(
        "SELECT name, title, project, company, parent_node, is_group, disabled, ebs_code, modified "
        "FROM `tabExecution Breakdown Node` WHERE project=%s AND name=%s FOR UPDATE",
        (project, name),
        as_dict=True,
    )
    if not rows:
        raise access.AccessDenied("Node is unavailable.")
    return _node_dict(rows[0])


def _check_expected(row, expected_modified):
    expected = rules.validate_expected_modified(expected_modified, required=True)
    if rules.stale_version(row.get("modified"), expected):
        raise StaleWrite("The record version is stale.")


def _load_counter(project, create_if_missing):
    rows = frappe.db.sql(
        "SELECT name, project, last_issued FROM `tabExecution Code Counter` "
        "WHERE project=%s ORDER BY name LIMIT 1 FOR UPDATE",
        (project,),
        as_dict=True,
    )
    if rows:
        return rows[0]
    existing_node = frappe.db.sql(
        "SELECT name FROM `tabExecution Breakdown Node` WHERE project=%s " "ORDER BY name LIMIT 1 FOR UPDATE",
        (project,),
        as_dict=True,
    )
    if existing_node:
        raise access.IntegrityFailure("Nodes exist without their execution code counter.")
    if not create_if_missing:
        return None
    counter = frappe.get_doc(
        {
            "doctype": rules.COUNTER_DOCTYPE,
            "project": project,
            "last_issued": 0,
        }
    )
    with access.establish_guard(
        actor=frappe.session.user,
        operation="counter",
        project=project,
        doctype=rules.COUNTER_DOCTYPE,
        document=counter,
        from_value=None,
        to_value=0,
        targets={"last_issued": 0},
    ):
        counter.insert(ignore_permissions=True)
    return {"name": counter.name, "project": project, "last_issued": 0}


def _allocate_code(project):
    counter = _load_counter(project, create_if_missing=True)
    from_value = rules.validate_counter_value(counter.get("last_issued"))
    next_value = rules.next_counter_value(from_value)
    # A current locking read: an older main-transaction consistent snapshot
    # must not feed the protected allocation decision.
    doc = frappe.get_doc(rules.COUNTER_DOCTYPE, counter["name"], for_update=True)
    if rules.validate_counter_value(doc.last_issued) != from_value:
        raise access.IntegrityFailure("The execution code counter changed unexpectedly.")
    with access.establish_guard(
        actor=frappe.session.user,
        operation="counter",
        project=project,
        doctype=rules.COUNTER_DOCTYPE,
        document=doc,
        name=counter.get("name"),
        from_value=from_value,
        to_value=next_value,
        targets={"last_issued": next_value},
    ):
        doc.last_issued = next_value
        doc.save(ignore_permissions=True)
    return rules.format_execution_code(next_value)


def create_node(project, title, is_group, parent_node=None, expected_parent_modified=None):
    project = rules.validate_identifier(project, field="Project")
    title = rules.validate_title(title)
    is_group = rules.validate_boolean(is_group, field="is_group")
    parent_node = rules.validate_identifier(parent_node, field="Parent node") if parent_node else None
    if parent_node and not expected_parent_modified:
        raise rules.RuleViolation("missing_version", "The parent version is required.")
    try:
        project_row, _decision = _authorize_locked(project, "create")
        nodes = _locked_nodes(project)
        _validate_counter_consistency(_load_counter(project, create_if_missing=False), nodes)
        rules.validate_create_parent(nodes, project=project, parent_node=parent_node)
        if parent_node:
            parent = next((node for node in nodes if node["name"] == parent_node), None)
            if parent is None:
                raise access.AccessDenied("Parent is unavailable.")
            _check_expected(parent, expected_parent_modified)
        code = _allocate_code(project)
        company = project_row.get("company")
        doc = frappe.get_doc(
            {
                "doctype": rules.NODE_DOCTYPE,
                "project": project,
                "company": company,
                "title": title,
                "parent_node": parent_node,
                "is_group": 1 if is_group else 0,
                "disabled": 0,
                "ebs_code": code,
            }
        )
        with access.establish_guard(
            actor=frappe.session.user,
            operation="create",
            project=project,
            doctype=rules.NODE_DOCTYPE,
            document=doc,
            company=company,
            code=code,
            targets={
                "company": company,
                "ebs_code": code,
                "title": title,
                "parent_node": parent_node,
                "is_group": 1 if is_group else 0,
                "disabled": 0,
            },
        ):
            doc.insert(ignore_permissions=True)
        return _summary(doc)
    except Exception as error:
        _translate(error)


def update_node(project, name, expected_modified, title=None, is_group=None):
    project = rules.validate_identifier(project, field="Project")
    name = rules.validate_identifier(name, field="Node name")
    if title is None and is_group is None:
        raise rules.RuleViolation("no_changes", "No editable field was supplied.")
    try:
        _project_row, _decision = _authorize_locked(project, "update")
        nodes = _locked_nodes(project)
        row = _load_node(project, name)
        _check_expected(row, expected_modified)
        if title is not None:
            title = rules.validate_title(title)
        if is_group is not None:
            is_group = rules.validate_group_change(nodes, project=project, name=name, new_is_group=is_group)
        doc = frappe.get_doc(rules.NODE_DOCTYPE, name, for_update=True)
        if doc.project != project:
            raise access.IntegrityFailure("The node belongs to a different Project.")
        targets = {}
        if title is not None:
            targets["title"] = title
        if is_group is not None:
            targets["is_group"] = 1 if is_group else 0
        with access.establish_guard(
            actor=frappe.session.user,
            operation="update",
            project=project,
            doctype=rules.NODE_DOCTYPE,
            document=doc,
            name=name,
            targets=targets,
        ):
            if title is not None:
                doc.title = title
            if is_group is not None:
                doc.is_group = 1 if is_group else 0
            doc.save(ignore_permissions=True)
        return _summary(doc)
    except Exception as error:
        _translate(error)


def move_node(project, name, expected_modified, parent_node=None, expected_parent_modified=None):
    project = rules.validate_identifier(project, field="Project")
    name = rules.validate_identifier(name, field="Node name")
    parent_node = rules.validate_identifier(parent_node, field="Parent node") if parent_node else None
    if parent_node and not expected_parent_modified:
        raise rules.RuleViolation("missing_version", "The destination parent version is required.")
    try:
        _project_row, _decision = _authorize_locked(project, "move")
        nodes = _locked_nodes(project)
        row = _load_node(project, name)
        _check_expected(row, expected_modified)
        rules.validate_move(nodes, project=project, name=name, new_parent=parent_node)
        if parent_node:
            parent = next((node for node in nodes if node["name"] == parent_node), None)
            if parent is None:
                raise access.AccessDenied("Parent is unavailable.")
            _check_expected(parent, expected_parent_modified)
        doc = frappe.get_doc(rules.NODE_DOCTYPE, name, for_update=True)
        if doc.project != project:
            raise access.IntegrityFailure("The node belongs to a different Project.")
        with access.establish_guard(
            actor=frappe.session.user,
            operation="move",
            project=project,
            doctype=rules.NODE_DOCTYPE,
            document=doc,
            name=name,
            targets={"parent_node": parent_node},
        ):
            doc.parent_node = parent_node
            doc.save(ignore_permissions=True)
        return _summary(doc)
    except Exception as error:
        _translate(error)


def set_disabled(project, name, expected_modified, disabled):
    project = rules.validate_identifier(project, field="Project")
    name = rules.validate_identifier(name, field="Node name")
    disabled = rules.validate_boolean(disabled, field="disabled")
    try:
        _project_row, _decision = _authorize_locked(project, "set_disabled")
        row = _load_node(project, name)
        _check_expected(row, expected_modified)
        doc = frappe.get_doc(rules.NODE_DOCTYPE, name, for_update=True)
        if doc.project != project:
            raise access.IntegrityFailure("The node belongs to a different Project.")
        with access.establish_guard(
            actor=frappe.session.user,
            operation="set_disabled",
            project=project,
            doctype=rules.NODE_DOCTYPE,
            document=doc,
            name=name,
            targets={"disabled": 1 if disabled else 0},
        ):
            doc.disabled = 1 if disabled else 0
            doc.save(ignore_permissions=True)
        return _summary(doc)
    except Exception as error:
        _translate(error)


def delete_node(project, name, expected_modified):
    project = rules.validate_identifier(project, field="Project")
    name = rules.validate_identifier(name, field="Node name")
    try:
        _project_row, _decision = _authorize_locked(project, "delete")
        nodes = _locked_nodes(project)
        row = _load_node(project, name)
        _check_expected(row, expected_modified)
        rules.validate_delete(nodes, project=project, name=name)
        doc = frappe.get_doc(rules.NODE_DOCTYPE, name, for_update=True)
        if doc.project != project:
            raise access.IntegrityFailure("The node belongs to a different Project.")
        with access.establish_guard(
            actor=frappe.session.user,
            operation="delete",
            project=project,
            doctype=rules.NODE_DOCTYPE,
            document=doc,
            name=name,
        ):
            doc.delete(ignore_permissions=True, force=False)
        return {"name": name}
    except Exception as error:
        _translate(error)


def _lock_project(project):
    rows = frappe.db.sql(
        "SELECT name, company FROM tabProject WHERE name=%s FOR UPDATE",
        (project,),
        as_dict=True,
    )
    return rows[0] if rows else None


def _has_nodes(project):
    rows = frappe.db.sql(
        "SELECT name FROM `tabExecution Breakdown Node` WHERE project=%s " "ORDER BY name LIMIT 1 FOR UPDATE",
        (project,),
        as_dict=True,
    )
    return bool(rows)


def _locked_counter(project):
    rows = frappe.db.sql(
        "SELECT name, last_issued FROM `tabExecution Code Counter` "
        "WHERE project=%s ORDER BY name LIMIT 1 FOR UPDATE",
        (project,),
        as_dict=True,
    )
    return rows[0] if rows else None


def _state_exists(project):
    if not _table_exists(rules.NODE_DOCTYPE) or not _table_exists(rules.COUNTER_DOCTYPE):
        return False
    return bool(_has_nodes(project) or _locked_counter(project))


def _counter_state(project):
    if not _table_exists(rules.COUNTER_DOCTYPE):
        return None
    return _locked_counter(project)


def project_validate(doc, method=None):
    if doc.is_new():
        return
    if not _table_exists(rules.NODE_DOCTYPE) or not _table_exists(rules.COUNTER_DOCTYPE):
        return
    locked = _lock_project(doc.name)
    if not locked:
        return
    before = doc.get_doc_before_save()
    previous_company = before.company if before is not None else locked.get("company")
    counter = _counter_state(doc.name)
    nodes_exist = _has_nodes(doc.name)
    if nodes_exist and not counter:
        frappe.throw(
            frappe._("Execution tree integrity failure: nodes exist without a counter."),
            frappe.ValidationError,
        )
    if counter:
        try:
            last_issued = rules.validate_counter_value(counter.get("last_issued"))
        except rules.RuleViolation as error:
            frappe.throw(frappe._(error.message), frappe.ValidationError)
        if last_issued > 0 and (doc.company or None) != (previous_company or None):
            frappe.throw(
                frappe._("The Project Company cannot change after the first execution code was issued."),
                frappe.ValidationError,
            )


def project_before_rename(doc, method=None, old=None, new=None, merge=None):
    if not _table_exists(rules.NODE_DOCTYPE) or not _table_exists(rules.COUNTER_DOCTYPE):
        return
    old_name = old or doc.name
    project_names = [old_name]
    if merge and new and new != old_name:
        project_names = sorted({old_name, new})
    # Ordinary rename and merge both acquire Project control deterministically
    # before reading retained state on the main connection.
    for project in project_names:
        _lock_project(project)
    if any(_state_exists(project) for project in project_names):
        frappe.throw(
            frappe._("A Project with execution tree history cannot be renamed, merged or deleted."),
            frappe.ValidationError,
        )


def project_on_trash(doc, method=None):
    if not _table_exists(rules.NODE_DOCTYPE) or not _table_exists(rules.COUNTER_DOCTYPE):
        return
    _lock_project(doc.name)
    if _state_exists(doc.name):
        frappe.throw(
            frappe._("A Project with execution tree history cannot be deleted."),
            frappe.ValidationError,
        )
