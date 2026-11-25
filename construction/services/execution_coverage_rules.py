"""Framework-independent rules for WBS P3 Execution Coverage & Export.

This module must not import ``frappe``, ``erpnext`` or ``construction`` so
offline test vectors can load it in isolation. It owns:
- filter normalization and incompatible-filter detection,
- disjoint Stage link classification (with disabled-link vs integrity-issue
  sub-breakdown and zero fallback to ``BOQ Item.planned_execution_node``),
- BOQ Item grouping that preserves the authorized BOQ denominator (an Item
  whose Stages are hidden by Stage filters classifies as ``filtered_out`` and
  never becomes ``no_stages``),
- deterministic total sort order across paginated views and exports,
- pure export table construction shared identically by CSV and XLSX downloads.
"""

from __future__ import annotations

import re

PAGE_DEFAULT = 50
PAGE_MAX = 200
EXPORT_MAX = 2000
MAX_IDENTIFIER_LENGTH = 140
MAX_SEARCH_LENGTH = 140

MAX_POPULATION_HEADERS = 500
MAX_POPULATION_STRUCTURES = 5000
MAX_POPULATION_ITEMS = 2000
MAX_POPULATION_STAGES = 3000

VALID_MAPPING_STATES = frozenset({"all", "healthy_linked", "unlinked", "link_issues"})
VALID_STAGE_STATUSES = frozenset({"Not Started", "In Progress", "Completed", "Certified", "On Hold"})
VALID_VIEW_MODES = frozenset({"stages", "items", "no_stages"})
VALID_EXPORT_FORMATS = frozenset({"csv", "xlsx"})

DISABLED_ISSUE_CODES = frozenset({"disabled_node", "disabled_ancestor"})
INTEGRITY_ISSUE_CODES = frozenset({"missing_node", "project_mismatch", "group_node", "broken_parent", "cycle"})

DISCLAIMER_TEXT = (
    "Mapping completeness reflects Stage-to-location link counts only — "
    "it does not represent quantity balance, physical execution, certification, or financial completion."
)

NODE_WITH_UNLINKED_MESSAGE = (
    "Filtering by both an Execution Location and Unmapped Stages cannot match any Stage "
    "because unmapped Stages have no Execution Location."
)

DEFAULT_LABELS = {
    # Stage mapping_state visible labels (frozen P2 contract: unlinked -> "Unmapped")
    "state_healthy_linked": "Healthy Linked",
    "state_unlinked": "Unmapped",
    "state_link_issues": "Needs Review",
    # Stage issue_code visible labels
    "issue_disabled_node": "Disabled Location",
    "issue_disabled_ancestor": "Disabled Ancestor",
    "issue_missing_node": "Missing Location",
    "issue_project_mismatch": "Project Mismatch",
    "issue_group_node": "Group Node Link",
    "issue_broken_parent": "Broken Ancestor Link",
    "issue_cycle": "Execution Tree Cycle",
    # BOQ Item group visible labels
    "group_full": "Full",
    "group_partial": "Partial",
    "group_unmapped": "Unmapped",
    "group_needs_review": "Needs Review",
    "group_filtered_out": "Zero Matching Stages",
    "group_no_stages": "No Stages",
    "group_no_visible_stages": "No visible Stages",
    # View names
    "view_stages": "Stages",
    "view_items": "Items Summary",
    # Filter conflict & disclaimer
    "conflict_node_with_unlinked": NODE_WITH_UNLINKED_MESSAGE,
    "disclaimer": DISCLAIMER_TEXT,
    # Export metadata labels
    "meta_report": "Report",
    "meta_report_value": "Execution Coverage",
    "meta_project": "Project",
    "meta_view": "View",
    "meta_exported_rows": "Exported Rows",
    "meta_total_matching_rows": "Total Matching Rows",
    "meta_truncated": "Truncated",
    "meta_yes": "Yes",
    "meta_no": "No",
    "meta_truncation_notice": "Truncation Notice",
    "meta_summary_total_stages": "Summary — Matching Stages",
    "meta_summary_healthy_linked": "Summary — Healthy Linked",
    "meta_summary_unmapped": "Summary — Unmapped",
    "meta_summary_needs_review": "Summary — Needs Review",
    "meta_summary_disabled_links": "Summary — Disabled Links",
    "meta_summary_integrity_issues": "Summary — Integrity Issues",
    "meta_summary_completeness": "Summary — Mapping Completeness",
    "meta_summary_items_total": "Summary — BOQ Items in Scope",
    "meta_summary_items_no_stages": "Summary — Items Without Stages",
    "meta_summary_items_filtered_out": "Summary — Items With Zero Matching Stages",
    "meta_notice": "Notice",
    # Export column headers
    "col_stage": "Stage",
    "col_stage_code": "Stage Code",
    "col_stage_name": "Stage Name",
    "col_stage_status": "Stage Status",
    "col_mapping_status": "Mapping Status",
    "col_issue_detail": "Issue Detail",
    "col_ebs_code": "Execution Code",
    "col_node_title": "Execution Location",
    "col_node_path": "Execution Path",
    "col_planned_qty": "Planned Qty",
    "col_uom": "UOM",
    "col_boq_item": "BOQ Item",
    "col_wbs_code": "Commercial WBS Code",
    "col_item_title": "Item Title",
    "col_boq_header": "BOQ Header",
    "col_header_type": "Header Type",
    "col_header_status": "Header Status",
    "col_item_planning_default": "Item Planning Default",
    "col_item_group": "Item Group",
    "col_total_item_stages": "Total Item Stages",
    "col_matching_stages": "Matching Stages",
    "col_healthy_linked": "Healthy Linked",
    "col_unmapped": "Unmapped",
    "col_needs_review": "Needs Review",
    "col_disabled_links": "Disabled Links",
    "col_integrity_issues": "Integrity Issues",
    "col_item_qty": "Item Qty",
    "col_stage_planned_qty_sum": "Stage Planned Qty Sum (Single Item)",
    "col_status": "Status",
}

_WBS_SPLIT_RE = re.compile(r"[.\-/\s]+")


class CoverageRuleViolation(ValueError):
    """Caller input violates a P3 coverage validation rule."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _resolve_labels(labels=None):
    merged = dict(DEFAULT_LABELS)
    if labels:
        merged.update({k: v for k, v in labels.items() if v is not None})
    return merged


def validate_identifier(value, *, field="identifier", required=True, max_length=MAX_IDENTIFIER_LENGTH):
    if value is None:
        if required:
            raise CoverageRuleViolation("invalid_identifier", f"{field} is required.")
        return None
    if not isinstance(value, str):
        raise CoverageRuleViolation("invalid_identifier", f"{field} must be text.")
    text = value.strip()
    if not text:
        if required:
            raise CoverageRuleViolation("invalid_identifier", f"{field} is required.")
        return None
    if len(text) > max_length:
        raise CoverageRuleViolation("invalid_identifier", f"{field} is too long.")
    if any(ord(ch) < 32 for ch in text):
        raise CoverageRuleViolation("invalid_identifier", f"{field} contains control characters.")
    return text


def validate_positive_int(value, *, field, default, min_value=1, max_value=None):
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    if isinstance(value, bool):
        raise CoverageRuleViolation("invalid_integer", f"{field} must be an integer.")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        raw = value.strip()
        try:
            number = int(raw, 10)
        except ValueError as exc:
            raise CoverageRuleViolation("invalid_integer", f"{field} must be an integer.") from exc
    else:
        raise CoverageRuleViolation("invalid_integer", f"{field} must be an integer.")
    if number < min_value:
        raise CoverageRuleViolation("invalid_integer", f"{field} must be at least {min_value}.")
    if max_value is not None and number > max_value:
        raise CoverageRuleViolation("invalid_integer", f"{field} cannot exceed {max_value}.")
    return number


def normalize_filters(
    *,
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
    export_format=None,
):
    """Validate and normalize all P3 coverage query/export parameters."""
    norm_project = validate_identifier(project, field="Project", required=True)
    norm_header = validate_identifier(boq_header, field="BOQ Header", required=False)
    norm_structure = validate_identifier(boq_structure, field="BOQ Structure", required=False)
    norm_item = validate_identifier(boq_item, field="BOQ Item", required=False)
    norm_node = validate_identifier(execution_node, field="Execution Location", required=False)

    if mapping_state is None or (isinstance(mapping_state, str) and not mapping_state.strip()):
        norm_state = "all"
    elif isinstance(mapping_state, str):
        norm_state = mapping_state.strip()
    else:
        raise CoverageRuleViolation("invalid_mapping_state", "Unsupported mapping state filter.")
    if norm_state not in VALID_MAPPING_STATES:
        raise CoverageRuleViolation("invalid_mapping_state", "Unsupported mapping state filter.")

    if stage_status is None or (isinstance(stage_status, str) and not stage_status.strip()):
        norm_stage_status = None
    elif isinstance(stage_status, str):
        norm_stage_status = stage_status.strip()
        if norm_stage_status not in VALID_STAGE_STATUSES:
            raise CoverageRuleViolation("invalid_stage_status", "Unsupported stage status filter.")
    else:
        raise CoverageRuleViolation("invalid_stage_status", "Unsupported stage status filter.")

    norm_search = validate_identifier(
        search, field="Search", required=False, max_length=MAX_SEARCH_LENGTH
    )

    if view_mode is None or (isinstance(view_mode, str) and not view_mode.strip()):
        norm_view = "stages"
    elif isinstance(view_mode, str):
        norm_view = view_mode.strip()
    else:
        raise CoverageRuleViolation("invalid_view_mode", "Unsupported view mode.")
    if norm_view not in VALID_VIEW_MODES:
        raise CoverageRuleViolation("invalid_view_mode", "Unsupported view mode.")

    norm_page = validate_positive_int(page, field="Page", default=1, min_value=1, max_value=100000)
    norm_page_size = validate_positive_int(
        page_size, field="Page size", default=PAGE_DEFAULT, min_value=1, max_value=PAGE_MAX
    )

    if export_format is None or (isinstance(export_format, str) and not export_format.strip()):
        norm_format = "csv"
    elif isinstance(export_format, str):
        norm_format = export_format.strip().lower()
    else:
        raise CoverageRuleViolation("invalid_export_format", "Unsupported export format.")
    if norm_format not in VALID_EXPORT_FORMATS:
        raise CoverageRuleViolation("invalid_export_format", "Unsupported export format.")

    return {
        "project": norm_project,
        "boq_header": norm_header,
        "boq_structure": norm_structure,
        "boq_item": norm_item,
        "execution_node": norm_node,
        "mapping_state": norm_state,
        "stage_status": norm_stage_status,
        "search": norm_search,
        "view_mode": norm_view,
        "page": norm_page,
        "page_size": norm_page_size,
        "export_format": norm_format,
    }


def detect_filter_conflict(execution_node, mapping_state, *, labels=None):
    """Detect logically contradictory Stage filter combinations."""
    if execution_node and mapping_state == "unlinked":
        resolved = _resolve_labels(labels)
        return {
            "code": "node_with_unlinked",
            "message": resolved["conflict_node_with_unlinked"],
        }
    return None


def index_nodes_by_name(nodes):
    indexed = {}
    for node in nodes or ():
        name = node.get("name")
        if name:
            indexed[name] = node
    return indexed


def collect_subtree(nodes, root_name):
    """Return ``frozenset`` of ``root_name`` and all transitive descendants."""
    if not root_name:
        return frozenset()
    children_by_parent = {}
    for node in nodes or ():
        name = node.get("name")
        parent = node.get("parent_node") or None
        if name and parent:
            children_by_parent.setdefault(parent, []).append(name)
    subtree = set()
    stack = [root_name]
    while stack:
        current = stack.pop()
        if current in subtree:
            continue
        subtree.add(current)
        stack.extend(children_by_parent.get(current, ()))
    return frozenset(subtree)


def inspect_node_chain(nodes_by_name, node_name):
    """Safely walk root-to-node ancestor chain without raising.

    Returns ``(chain, error_code)`` where ``error_code`` is one of
    ``None``, ``"missing_node"``, ``"broken_parent"``, or ``"cycle"``.
    """
    if not node_name or node_name not in nodes_by_name:
        return [], "missing_node"
    chain = []
    seen = set()
    cursor = node_name
    while cursor:
        if cursor in seen:
            return [], "cycle"
        if cursor not in nodes_by_name:
            return [], "broken_parent"
        seen.add(cursor)
        node = nodes_by_name[cursor]
        chain.append(node)
        cursor = node.get("parent_node") or None
    chain.reverse()
    return chain, None


def format_node_display(nodes_by_name, node_name, separator=" / "):
    """Return display metadata ``(ebs_code, title, path, display_text)`` for a node."""
    cleaned = (str(node_name).strip() if node_name is not None else "") or None
    if not cleaned:
        return "", "", "", ""
    node = nodes_by_name.get(cleaned)
    if node is None:
        return "", cleaned, "", cleaned
    ebs_code = str(node.get("ebs_code") or "").strip()
    title = str(node.get("title") or cleaned).strip()
    chain, err = inspect_node_chain(nodes_by_name, cleaned)
    if err is None and chain:
        parts = [
            str(item.get("title") or item.get("ebs_code") or item.get("name") or "").strip()
            for item in chain
        ]
        path = separator.join(part for part in parts if part)
    else:
        path = title
    display_text = f"{ebs_code} — {path}" if ebs_code else path
    return ebs_code, title, path, display_text


def classify_stage_link(execution_node, nodes_by_name, resolved_project):
    """Classify a Stage's ``execution_node`` into a disjoint mapping state.

    NEVER inspects or falls back to ``BOQ Item.planned_execution_node``.

    Returns ``(mapping_state, issue_code, issue_bucket)``:
    - ``("unlinked", None, None)`` when ``execution_node`` is blank
    - ``("healthy_linked", None, None)`` when node exists in ``resolved_project``,
      is a leaf (``is_group == 0``), and has no disabled node or disabled ancestor
    - ``("link_issues", issue_code, "disabled_links" | "integrity_issues")``
      otherwise.
    """
    cleaned = (str(execution_node).strip() if execution_node is not None else "") or None
    if not cleaned:
        return "unlinked", None, None

    node = nodes_by_name.get(cleaned)
    if node is None:
        return "link_issues", "missing_node", "integrity_issues"
    if (node.get("project") or "") != resolved_project:
        return "link_issues", "project_mismatch", "integrity_issues"
    if int(node.get("is_group") or 0):
        return "link_issues", "group_node", "integrity_issues"

    chain, err = inspect_node_chain(nodes_by_name, cleaned)
    if err == "cycle":
        return "link_issues", "cycle", "integrity_issues"
    if err == "broken_parent":
        return "link_issues", "broken_parent", "integrity_issues"

    if int(node.get("disabled") or 0):
        return "link_issues", "disabled_node", "disabled_links"
    for ancestor in chain[:-1]:
        if int(ancestor.get("disabled") or 0):
            return "link_issues", "disabled_ancestor", "disabled_links"

    return "healthy_linked", None, None


def _wbs_sort_key(wbs_code):
    text = str(wbs_code or "").strip()
    if not text:
        return (1, ())
    tokens = []
    for part in _WBS_SPLIT_RE.split(text):
        if not part:
            continue
        if part.isdigit():
            tokens.append((0, int(part, 10), ""))
        else:
            tokens.append((1, 0, part.lower()))
    return (0, tuple(tokens))


def item_sort_key(row):
    """Deterministic total sort order for BOQ Item rows."""
    return (
        str(row.get("boq_header") or ""),
        _wbs_sort_key(row.get("wbs_code")),
        str(row.get("name") or ""),
    )


def stage_sort_key(row):
    """Deterministic total sort order for BOQ Item Stage rows."""
    return (
        str(row.get("boq_header") or ""),
        _wbs_sort_key(row.get("wbs_code")),
        str(row.get("boq_item") or ""),
        str(row.get("stage_code") or ""),
        str(row.get("name") or ""),
    )


def classify_item_stage_list(stage_rows):
    """Classify a BOQ Item given a list of its classified Stage rows.

    Returns one of ``"no_stages"``, ``"needs_review"``, ``"full"``,
    ``"partial"``, or ``"unmapped"``.
    """
    if not stage_rows:
        return "no_stages"
    has_issue = False
    has_healthy = False
    has_unlinked = False
    for stage in stage_rows:
        state = stage.get("mapping_state")
        if state == "link_issues":
            has_issue = True
        elif state == "healthy_linked":
            has_healthy = True
        elif state == "unlinked":
            has_unlinked = True
    if has_issue:
        return "needs_review"
    if has_healthy and not has_unlinked:
        return "full"
    if has_healthy and has_unlinked:
        return "partial"
    return "unmapped"


def compute_stage_summary(stage_rows):
    """Compute reconciling count-based coverage KPIs over ``stage_rows``.

    Invariants:
    - ``total_stages == healthy_linked + unlinked + link_issues``
    - ``link_issues == disabled_links + integrity_issues``
    - ``coverage_pct`` is ``None`` (``"N/A"``) whenever ``total_stages == 0``
    """
    healthy = 0
    unlinked = 0
    link_issues = 0
    disabled_links = 0
    integrity_issues = 0
    for stage in stage_rows:
        state = stage.get("mapping_state")
        if state == "healthy_linked":
            healthy += 1
        elif state == "unlinked":
            unlinked += 1
        elif state == "link_issues":
            link_issues += 1
            if stage.get("issue_bucket") == "disabled_links":
                disabled_links += 1
            else:
                integrity_issues += 1
    total = healthy + unlinked + link_issues
    if total > 0:
        pct = round((healthy / total) * 100.0, 1)
        pct_display = f"{pct:.1f}%"
    else:
        pct = None
        pct_display = "N/A"
    return {
        "total_stages": total,
        "healthy_linked": healthy,
        "unlinked": unlinked,
        "link_issues": link_issues,
        "disabled_links": disabled_links,
        "integrity_issues": integrity_issues,
        "coverage_pct": pct,
        "coverage_pct_display": pct_display,
    }


def _stage_matches_search(stage_row, needle_lower):
    haystacks = (
        stage_row.get("name"),
        stage_row.get("stage_code"),
        stage_row.get("stage_name"),
        stage_row.get("boq_item"),
        stage_row.get("wbs_code"),
        stage_row.get("item_title"),
        stage_row.get("item_description"),
        stage_row.get("boq_header"),
        stage_row.get("header_title"),
        stage_row.get("ebs_code"),
        stage_row.get("node_title"),
        stage_row.get("node_path"),
    )
    for text in haystacks:
        if text and needle_lower in str(text).lower():
            return True
    return False


def paginate_rows(rows, page, page_size):
    total_rows = len(rows)
    total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1
    start = (page - 1) * page_size
    end = start + page_size
    sliced = rows[start:end]
    return sliced, {
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def _safe_float(value):
    if value is None or value == "":
        return 0.0
    return float(value)


def _mapping_state_label(mapping_state, labels):
    return labels.get(f"state_{mapping_state}", mapping_state)


def _issue_label(issue_code, labels):
    if not issue_code:
        return ""
    return labels.get(f"issue_{issue_code}", issue_code)


def _group_label(group_key, *, partial_visibility, labels):
    if group_key == "no_stages":
        return labels["group_no_visible_stages"] if partial_visibility else labels["group_no_stages"]
    return labels.get(f"group_{group_key}", group_key)


def evaluate_coverage(
    *,
    project,
    items,
    stages,
    project_nodes,
    extra_nodes=None,
    filters=None,
    partial_visibility=False,
    labels=None,
):
    """Evaluate WBS P3 Execution Coverage over an already-authorized BOQ population.

    ``items`` and ``stages`` must already be restricted to the authorized BOQ
    population defined by ``project``, ``boq_header``, ``boq_structure``, and
    ``boq_item``. This function applies Stage result filters (``execution_node``
    subtree, ``mapping_state``, ``stage_status``, ``search``) strictly to the
    Stage results while keeping the BOQ Item denominator intact.
    """
    resolved_labels = _resolve_labels(labels)
    norm_filters = filters or normalize_filters(project=project)

    # Index project nodes + any referenced cross-project nodes (for project_mismatch vs missing_node)
    all_nodes_index = index_nodes_by_name(list(extra_nodes or ()) + list(project_nodes or ()))
    project_nodes_list = list(project_nodes or ())

    items_by_name = {}
    for raw_item in items or ():
        item_name = raw_item.get("name")
        if not item_name:
            continue
        planned_node = (str(raw_item.get("planned_execution_node") or "").strip()) or None
        p_code, p_title, p_path, p_display = format_node_display(all_nodes_index, planned_node)
        items_by_name[item_name] = {
            "name": item_name,
            "boq_header": raw_item.get("boq_header") or "",
            "header_title": raw_item.get("header_title") or raw_item.get("boq_header") or "",
            "header_type": raw_item.get("header_type") or "",
            "header_status": raw_item.get("header_status") or "",
            "structure": raw_item.get("structure") or "",
            "wbs_code": raw_item.get("wbs_code") or "",
            "item_title": raw_item.get("item_title") or item_name,
            "item_description": raw_item.get("item_description") or "",
            "item_quantity": _safe_float(raw_item.get("quantity")),
            "uom": raw_item.get("unit") or raw_item.get("uom") or "",
            "planned_execution_node": planned_node,
            "planned_ebs_code": p_code,
            "planned_node_title": p_title,
            "planned_node_path": p_path,
            "planned_node_display": p_display,
        }

    # Classify every authorized Stage in the BOQ population (zero fallback to planned_execution_node!)
    all_stages_by_item = {name: [] for name in items_by_name}
    all_classified_stages = []
    for raw_stage in stages or ():
        item_name = raw_stage.get("boq_item")
        parent_item = items_by_name.get(item_name)
        if parent_item is None:
            continue
        exec_node = (str(raw_stage.get("execution_node") or "").strip()) or None
        mapping_state, issue_code, issue_bucket = classify_stage_link(
            exec_node, all_nodes_index, project
        )
        ebs_code, node_title, node_path, node_display = format_node_display(all_nodes_index, exec_node)
        stage_row = {
            "name": raw_stage.get("name") or "",
            "stage_code": raw_stage.get("stage_code") or "",
            "stage_name": raw_stage.get("stage_name") or raw_stage.get("name") or "",
            "stage_status": raw_stage.get("stage_status") or "",
            "planned_qty": _safe_float(raw_stage.get("planned_qty")),
            "uom": parent_item["uom"],
            "execution_node": exec_node,
            "ebs_code": ebs_code,
            "node_title": node_title,
            "node_path": node_path,
            "node_display": node_display,
            "mapping_state": mapping_state,
            "mapping_state_label": _mapping_state_label(mapping_state, resolved_labels),
            "issue_code": issue_code,
            "issue_bucket": issue_bucket,
            "issue_label": _issue_label(issue_code, resolved_labels),
            "boq_item": item_name,
            "structure": raw_stage.get("boq_structure") or parent_item["structure"],
            "wbs_code": parent_item["wbs_code"],
            "item_title": parent_item["item_title"],
            "item_description": parent_item["item_description"],
            "boq_header": parent_item["boq_header"],
            "header_title": parent_item["header_title"],
            "header_type": parent_item["header_type"],
            "header_status": parent_item["header_status"],
            "item_planned_execution_node": parent_item["planned_execution_node"],
            "item_planned_node_display": parent_item["planned_node_display"],
        }
        all_classified_stages.append(stage_row)
        all_stages_by_item[item_name].append(stage_row)

    # Apply Stage result filters
    exec_filter = norm_filters["execution_node"]
    state_filter = norm_filters["mapping_state"]
    status_filter = norm_filters["stage_status"]
    search_filter = norm_filters["search"]

    filter_conflict = detect_filter_conflict(exec_filter, state_filter, labels=resolved_labels)
    subtree_nodes = collect_subtree(project_nodes_list, exec_filter) if exec_filter else None
    needle_lower = search_filter.lower() if search_filter else None

    matching_stages = []
    if filter_conflict is None:
        for stage_row in all_classified_stages:
            if subtree_nodes is not None and stage_row["execution_node"] not in subtree_nodes:
                continue
            if state_filter != "all" and stage_row["mapping_state"] != state_filter:
                continue
            if status_filter is not None and stage_row["stage_status"] != status_filter:
                continue
            if needle_lower is not None and not _stage_matches_search(stage_row, needle_lower):
                continue
            matching_stages.append(stage_row)

    matching_stages.sort(key=stage_sort_key)

    matching_stages_by_item = {name: [] for name in items_by_name}
    for stage_row in matching_stages:
        matching_stages_by_item[stage_row["boq_item"]].append(stage_row)

    summary = compute_stage_summary(matching_stages)

    # Build deterministic Item rows & No Stages rows
    no_stages_label = (
        resolved_labels["group_no_visible_stages"]
        if partial_visibility
        else resolved_labels["group_no_stages"]
    )

    population_item_groups = {
        "full": 0,
        "partial": 0,
        "unmapped": 0,
        "needs_review": 0,
        "no_stages": 0,
    }
    item_group_counts = {
        "full": 0,
        "partial": 0,
        "unmapped": 0,
        "needs_review": 0,
        "filtered_out": 0,
        "no_stages": 0,
    }

    all_item_rows = []
    all_no_stages_rows = []
    items_with_stages = 0
    items_without_stages = 0
    items_with_matching_stages = 0
    items_hidden_by_stage_filters = 0

    for item_name, item_info in items_by_name.items():
        pop_stages = all_stages_by_item[item_name]
        match_stages = matching_stages_by_item[item_name]
        total_item_stages = len(pop_stages)
        matching_count = len(match_stages)

        pop_group = classify_item_stage_list(pop_stages)
        population_item_groups[pop_group] += 1

        if total_item_stages == 0:
            items_without_stages += 1
            filtered_group = "no_stages"
        else:
            items_with_stages += 1
            if matching_count == 0:
                items_hidden_by_stage_filters += 1
                filtered_group = "filtered_out"
            else:
                items_with_matching_stages += 1
                filtered_group = classify_item_stage_list(match_stages)

        item_group_counts[filtered_group] += 1
        item_stage_summary = compute_stage_summary(match_stages)
        # Single-item planned qty sum only (same Item, same UOM — never cross-item!)
        stage_planned_qty_sum = round(sum(s["planned_qty"] for s in match_stages), 6)

        item_row = {
            "name": item_name,
            "boq_header": item_info["boq_header"],
            "header_title": item_info["header_title"],
            "header_type": item_info["header_type"],
            "header_status": item_info["header_status"],
            "structure": item_info["structure"],
            "wbs_code": item_info["wbs_code"],
            "item_title": item_info["item_title"],
            "item_quantity": item_info["item_quantity"],
            "stage_planned_qty_sum": stage_planned_qty_sum,
            "uom": item_info["uom"],
            "planned_execution_node": item_info["planned_execution_node"],
            "planned_ebs_code": item_info["planned_ebs_code"],
            "planned_node_title": item_info["planned_node_title"],
            "planned_node_path": item_info["planned_node_path"],
            "planned_node_display": item_info["planned_node_display"],
            "total_item_stages": total_item_stages,
            "matching_stages": matching_count,
            "healthy_linked": item_stage_summary["healthy_linked"],
            "unlinked": item_stage_summary["unlinked"],
            "link_issues": item_stage_summary["link_issues"],
            "disabled_links": item_stage_summary["disabled_links"],
            "integrity_issues": item_stage_summary["integrity_issues"],
            "population_group": pop_group,
            "population_group_label": _group_label(
                pop_group, partial_visibility=partial_visibility, labels=resolved_labels
            ),
            "filtered_group": filtered_group,
            "filtered_group_label": _group_label(
                filtered_group, partial_visibility=partial_visibility, labels=resolved_labels
            ),
        }
        all_item_rows.append(item_row)

        if total_item_stages == 0:
            all_no_stages_rows.append(
                {
                    "name": item_name,
                    "boq_header": item_info["boq_header"],
                    "header_title": item_info["header_title"],
                    "header_type": item_info["header_type"],
                    "header_status": item_info["header_status"],
                    "structure": item_info["structure"],
                    "wbs_code": item_info["wbs_code"],
                    "item_title": item_info["item_title"],
                    "item_quantity": item_info["item_quantity"],
                    "uom": item_info["uom"],
                    "planned_execution_node": item_info["planned_execution_node"],
                    "planned_node_display": item_info["planned_node_display"],
                    "status_label": no_stages_label,
                }
            )

    all_item_rows.sort(key=item_sort_key)
    all_no_stages_rows.sort(key=item_sort_key)

    population_summary = {
        "total_items": len(all_item_rows),
        "total_stages": len(all_classified_stages),
        "items_with_stages": items_with_stages,
        "items_without_stages": items_without_stages,
        "items_with_matching_stages": items_with_matching_stages,
        "items_hidden_by_stage_filters": items_hidden_by_stage_filters,
        "partial_visibility": bool(partial_visibility),
        "no_stages_label": no_stages_label,
        "population_item_groups": population_item_groups,
    }

    view_mode = norm_filters["view_mode"]
    if view_mode == "stages":
        active_rows = matching_stages
    elif view_mode == "items":
        active_rows = all_item_rows
    else:
        active_rows = all_no_stages_rows

    paged_rows, pagination = paginate_rows(
        active_rows, norm_filters["page"], norm_filters["page_size"]
    )

    return {
        "ok": True,
        "limit_exceeded": False,
        "project": project,
        "filters": norm_filters,
        "has_stage_filters": bool(
            exec_filter or state_filter != "all" or status_filter or search_filter
        ),
        "filter_conflict": filter_conflict,
        "disclaimer": resolved_labels["disclaimer"],
        "summary": summary,
        "population_summary": population_summary,
        "item_group_counts": item_group_counts,
        "view_mode": view_mode,
        "rows": paged_rows,
        "pagination": pagination,
        # Full ordered sets for internal callers (e.g. export); stripped before API JSON response
        "_all_stage_rows": matching_stages,
        "_all_item_rows": all_item_rows,
        "_all_no_stages_rows": all_no_stages_rows,
    }


def build_export_table(coverage_result, *, view_mode=None, max_rows=EXPORT_MAX, labels=None):
    """Build one canonical export table shared identically by CSV and XLSX.

    Preserves numeric ``int``/``float`` values for count and quantity cells and
    embeds exported count, total matching count, truncation status/notice,
    reconciling summary counts, and the non-financial disclaimer inside the
    exported rows.
    """
    resolved_labels = _resolve_labels(labels)
    mode = view_mode or coverage_result["view_mode"]
    if mode not in VALID_VIEW_MODES:
        raise CoverageRuleViolation("invalid_view_mode", "Unsupported view mode.")

    summary = coverage_result["summary"]
    pop = coverage_result["population_summary"]
    no_stages_label = pop["no_stages_label"]

    if mode == "stages":
        source_rows = coverage_result["_all_stage_rows"]
        view_label = resolved_labels["view_stages"]
        headers = [
            resolved_labels["col_stage"],
            resolved_labels["col_stage_code"],
            resolved_labels["col_stage_name"],
            resolved_labels["col_stage_status"],
            resolved_labels["col_mapping_status"],
            resolved_labels["col_issue_detail"],
            resolved_labels["col_ebs_code"],
            resolved_labels["col_node_title"],
            resolved_labels["col_node_path"],
            resolved_labels["col_planned_qty"],
            resolved_labels["col_uom"],
            resolved_labels["col_boq_item"],
            resolved_labels["col_wbs_code"],
            resolved_labels["col_item_title"],
            resolved_labels["col_boq_header"],
            resolved_labels["col_header_type"],
            resolved_labels["col_header_status"],
            resolved_labels["col_item_planning_default"],
        ]

        def serialize_row(row):
            return [
                row["name"],
                row["stage_code"],
                row["stage_name"],
                row["stage_status"],
                row["mapping_state_label"],
                row["issue_label"],
                row["ebs_code"],
                row["node_title"],
                row["node_path"],
                row["planned_qty"],  # numeric float
                row["uom"],
                row["boq_item"],
                row["wbs_code"],
                row["item_title"],
                row["boq_header"],
                row["header_type"],
                row["header_status"],
                row["item_planned_node_display"],
            ]

    elif mode == "items":
        source_rows = coverage_result["_all_item_rows"]
        view_label = resolved_labels["view_items"]
        headers = [
            resolved_labels["col_boq_item"],
            resolved_labels["col_wbs_code"],
            resolved_labels["col_item_title"],
            resolved_labels["col_boq_header"],
            resolved_labels["col_header_type"],
            resolved_labels["col_header_status"],
            resolved_labels["col_item_group"],
            resolved_labels["col_total_item_stages"],
            resolved_labels["col_matching_stages"],
            resolved_labels["col_healthy_linked"],
            resolved_labels["col_unmapped"],
            resolved_labels["col_needs_review"],
            resolved_labels["col_disabled_links"],
            resolved_labels["col_integrity_issues"],
            resolved_labels["col_item_qty"],
            resolved_labels["col_stage_planned_qty_sum"],
            resolved_labels["col_uom"],
            resolved_labels["col_item_planning_default"],
        ]

        def serialize_row(row):
            return [
                row["name"],
                row["wbs_code"],
                row["item_title"],
                row["boq_header"],
                row["header_type"],
                row["header_status"],
                row["filtered_group_label"],
                row["total_item_stages"],  # numeric int
                row["matching_stages"],  # numeric int
                row["healthy_linked"],  # numeric int
                row["unlinked"],  # numeric int
                row["link_issues"],  # numeric int
                row["disabled_links"],  # numeric int
                row["integrity_issues"],  # numeric int
                row["item_quantity"],  # numeric float
                row["stage_planned_qty_sum"],  # numeric float (single item only)
                row["uom"],
                row["planned_node_display"],
            ]

    else:
        source_rows = coverage_result["_all_no_stages_rows"]
        view_label = no_stages_label
        headers = [
            resolved_labels["col_boq_item"],
            resolved_labels["col_wbs_code"],
            resolved_labels["col_item_title"],
            resolved_labels["col_boq_header"],
            resolved_labels["col_header_type"],
            resolved_labels["col_header_status"],
            resolved_labels["col_item_qty"],
            resolved_labels["col_uom"],
            resolved_labels["col_item_planning_default"],
            resolved_labels["col_status"],
        ]

        def serialize_row(row):
            return [
                row["name"],
                row["wbs_code"],
                row["item_title"],
                row["boq_header"],
                row["header_type"],
                row["header_status"],
                row["item_quantity"],  # numeric float
                row["uom"],
                row["planned_node_display"],
                row["status_label"],
            ]

    total_matching_rows = len(source_rows)
    sliced = source_rows[:max_rows]
    exported_rows = len(sliced)
    truncated = total_matching_rows > max_rows
    omitted_rows = max(0, total_matching_rows - exported_rows)

    metadata_rows = [
        [resolved_labels["meta_report"], resolved_labels["meta_report_value"]],
        [resolved_labels["meta_project"], coverage_result["project"]],
        [resolved_labels["meta_view"], view_label],
        [resolved_labels["meta_exported_rows"], exported_rows],
        [resolved_labels["meta_total_matching_rows"], total_matching_rows],
        [
            resolved_labels["meta_truncated"],
            resolved_labels["meta_yes"] if truncated else resolved_labels["meta_no"],
        ],
    ]
    if truncated:
        truncation_msg = resolved_labels.get("truncation_notice_value") or (
            f"Export capped at {max_rows} rows; {omitted_rows} additional matching rows were omitted. "
            "Narrow filters to export all rows."
        )
        metadata_rows.append([resolved_labels["meta_truncation_notice"], truncation_msg])

    metadata_rows.extend(
        [
            [resolved_labels["meta_summary_total_stages"], summary["total_stages"]],
            [resolved_labels["meta_summary_healthy_linked"], summary["healthy_linked"]],
            [resolved_labels["meta_summary_unmapped"], summary["unlinked"]],
            [resolved_labels["meta_summary_needs_review"], summary["link_issues"]],
            [resolved_labels["meta_summary_disabled_links"], summary["disabled_links"]],
            [resolved_labels["meta_summary_integrity_issues"], summary["integrity_issues"]],
            [resolved_labels["meta_summary_completeness"], summary["coverage_pct_display"]],
            [resolved_labels["meta_summary_items_total"], pop["total_items"]],
            [resolved_labels["meta_summary_items_no_stages"], pop["items_without_stages"]],
            [
                resolved_labels["meta_summary_items_filtered_out"],
                pop["items_hidden_by_stage_filters"],
            ],
            [resolved_labels["meta_notice"], coverage_result["disclaimer"]],
        ]
    )

    data_rows = [serialize_row(row) for row in sliced]
    all_rows = list(metadata_rows) + [[]] + [headers] + data_rows

    return {
        "view_mode": mode,
        "exported_rows": exported_rows,
        "total_matching_rows": total_matching_rows,
        "truncated": truncated,
        "omitted_rows": omitted_rows,
        "max_rows": max_rows,
        "metadata_rows": metadata_rows,
        "headers": headers,
        "data_rows": data_rows,
        "all_rows": all_rows,
    }
