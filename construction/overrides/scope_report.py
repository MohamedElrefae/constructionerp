# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""
Scope Context enforcement for Query Reports (Option A+).

Monkey-patches ``frappe.desk.query_report.run`` so that restricted users
cannot bypass the active Scope Context when running the **allowlisted**
financial / operational reports.

Rules:

- If scope context is disabled, the user is Administrator, or the user
  has a finance / system role: bypass entirely.
- If the report name is **not** in :data:`ALLOWED_REPORTS`: bypass
  entirely. Only the 10 plan-specified financial reports (plus
  Project-wise Profitability if installed) are gated. Everything else
  keeps Frappe's default behaviour.
- For a restricted user running an allowlisted report: rewrite the
  filter dict to **strictly** match the active Scope Context. The
  user cannot pick a different allowed company / project / cost
  center / department than what the top-bar scope context is set to.
  This is a deliberate, conservative policy: the top bar is the
  single source of truth, the report cannot widen it.
- Filters may arrive as positional or keyword args, and as a dict,
  a JSON string, or ``None``. All four cases are normalised.
- The rewritten filter is written back in the SAME form (positional
  or keyword) the caller used. The wrapper never passes ``filters``
  to the original in both forms (which would raise
  ``TypeError: got multiple values for argument 'filters'``).
"""

import inspect
import json
import logging
from typing import Any

import frappe
from frappe import _

from construction.api.scope_context_api import (
    get_user_scope_context,
    get_user_scope_hierarchy,
)

logger = logging.getLogger(__name__)

# The 10 plan-specified financial reports + Project-wise Profitability.
# These are the only reports the backend wrapper mutates. All other
# reports pass through to the original `run` unchanged.
ALLOWED_REPORTS: frozenset[str] = frozenset(
    {
        "General Ledger",
        "Trial Balance",
        "Profit and Loss Statement",
        "Balance Sheet",
        "Accounts Payable",
        "Accounts Payable Summary",
        "Accounts Receivable",
        "Accounts Receivable Summary",
        "Budget Variance Report",
        "Cash Flow",
        "Project-wise Profitability",
    }
)

# Roles allowed to run reports without forced scope filters.
UNRESTRICTED_REPORT_ROLES: frozenset[str] = frozenset(
    {
        "System Manager",
        "Accounts Manager",
        "Accounts User",
        "Finance Manager",
    }
)

# Scope dimensions enforced by the wrapper. The keys are the canonical
# report-filter fieldnames used by ERPNext financial reports.
SCOPE_DIMENSIONS: tuple[str, ...] = (
    "company",
    "cost_center",
    "project",
    "department",
)

# Cached signature of the original run() so we can normalize positional
# args safely.
_ORIGINAL_RUN = None
_ORIGINAL_RUN_SIG = None


def apply_report_monkeypatch() -> None:
    """Install all scope-context report monkey-patches.

    Patches (Option A+):
      - ``frappe.desk.query_report.run`` → scope-aware wrapper that
        rewrites filters to the active scope.

    Patches (Option B):
      - ``frappe.core.doctype.report.report.is_permitted`` → bypass
        for allowlisted reports when the user has an active scope
        context.
      - ``frappe.desk.query_report.get_report_doc`` → bypass the
        ``report`` perm check (line 49 of the original) under the
        same condition.
      - ``frappe.permissions.has_permission`` → bypass for
        ``report``, ``select``, ``read`` ptypes when a structured
        bypass context is set and validated.
      - ``frappe.permissions.get_role_permissions`` → return the
        original perms dict with ONLY the allowlisted ptypes
        overridden to 1.
      - ``frappe.model.get_permitted_fields`` → return all valid
        columns when the structured context is set.

    All patches are additive: non-allowlisted reports and users
    without a scope context fall through to the original behaviour.
    """
    global _ORIGINAL_RUN, _ORIGINAL_RUN_SIG

    if _ORIGINAL_RUN is not None:
        return

    try:
        from frappe.desk import query_report
    except Exception:
        return

    # --- Option A+: report.run wrapper ---
    _ORIGINAL_RUN = query_report.run
    _ORIGINAL_RUN_SIG = inspect.signature(_ORIGINAL_RUN)
    query_report.run = _scope_aware_run

    # --- Option B: Report.is_permitted + get_report_doc ---
    _patch_report_access_gates()


def _user_has_active_scope_context(user: str | None = None) -> bool:
    """Return True if the user has a User Scope Context record with a company.

    This is the access-control signal: a scoped user is authorised to
    see the allowlisted reports (Option A+ L1+L2 constrain the data
    to the scope; Option B bypasses the report-access gate).
    """
    try:
        settings = frappe.get_single("Construction Settings")
        if not settings or not settings.enable_scope_context:
            return False
    except Exception:
        return False
    user = user or frappe.session.user
    if not user or user == "Administrator":
        return False
    if _has_unrestricted_report_role(user):
        return False
    scope_doc = get_user_scope_context(user)
    return bool(scope_doc and scope_doc.company)


def _bypass_context() -> dict | None:
    """Read the structured bypass context from `frappe.flags`.

    Returns the dict set by `set_bypass_context`, or None. Validates
    the structure and that the report is in the allowlist and the
    user has an active scope context.

    Security-critical: this is the SINGLE gate that allows
    `has_permission`, `get_role_permissions`, and
    `get_permitted_fields` to return permissive values. A bug here
    would over-grant permissions to scoped users globally.
    """
    try:
        ctx = getattr(frappe.flags, "scope_report_bypass", None)
    except Exception:
        return None
    if not isinstance(ctx, dict):
        return None
    report_name = ctx.get("report_name")
    user = ctx.get("user")
    if not report_name or report_name not in ALLOWED_REPORTS:
        return None
    if not user:
        return None
    # Cross-user leak guard: the flag must always identify the
    # current session user, never some other user.
    if user != frappe.session.user:
        return None
    # The user must still have an active scope context at the
    # moment the patch is consulted (in case scope was cleared
    # between flag-set and patch-eval).
    if not _user_has_active_scope_context(user):
        return None
    return ctx


def _bypass_should_apply(
    report_name: str | None = None,
    user: str | None = None,
    doctype: str | None = None,
    ptype: str | None = None,
) -> bool:
    """Return True if the report access bypass should apply for the
    given (report, user, doctype, ptype) combination.

    Validates:
    - The structured bypass context is present.
    - The report_name in the context matches the caller's report.
    - The user in the context matches the caller's user.
    - The ptype (if provided) is in the small allowlist of
      permission types that the report path actually needs.
      (report, select, read)

    Note: the `doctype` argument is accepted but NOT used as a
    filter. The bypass is report-scoped, not doctype-scoped: the
    report's SQL builder may query multiple secondary doctypes
    (e.g. AP queries Purchase Invoice, GL Entry, Journal Entry),
    and the data is constrained by the L1+L2 wrappers. The bypass
    only opens the perm gate for the report's own queries.
    """
    ctx = _bypass_context()
    if ctx is None:
        return False
    if report_name is not None and ctx.get("report_name") != report_name:
        return False
    if user is not None and ctx.get("user") != user:
        return False
    if ptype is not None and ptype not in _ALLOWED_PTYPES:
        return False
    return True


_ALLOWED_PTYPES = frozenset({"report", "select", "read"})


def set_bypass_context(report_name: str, user: str) -> None:
    """Set the structured bypass context for the current request.

    Caller MUST clear it via `clear_bypass_context` (in `finally`)
    to prevent flag leakage.
    """
    frappe.flags.scope_report_bypass = {
        "report_name": report_name,
        "user": user,
    }


def clear_bypass_context() -> None:
    """Remove the structured bypass context. Idempotent."""
    if getattr(frappe.flags, "scope_report_bypass", None) is not None:
        del frappe.flags.scope_report_bypass


def _patch_report_access_gates() -> None:
    """Install the Option B monkey-patches on Report access gates.

    Security model:
    - The bypass is gated on a STRUCTURED context
      (`frappe.flags.scope_report_bypass` is a dict with
      `report_name`, `user`), validated by `_bypass_should_apply`.
    - The bypass is REPORT-scoped, not doctype-scoped: a report's
      SQL builder may query multiple secondary doctypes, and the
      data is constrained by the L1+L2 wrappers. The bypass only
      opens the perm gate for the report's own queries.
    - `Report.is_permitted` returns True only when the report is in
      the allowlist AND the calling user has an active scope.
    - `get_report_doc` sets the structured context for the duration
      of the call. The L2 wrapper / `query_report.run` clears it in
      its own `finally`.
    - `has_permission` / `get_role_permissions` /
      `get_permitted_fields` only return permissive values when
      the structured context is present AND the ptype being checked
      is in the small allowlist (`report`, `select`, `read`). The
      bypass is gated on (report_name, user) and the user's active
      scope context; the `doctype` being checked is NOT a gate
      (see "report-scoped" above).
    - `get_role_permissions` returns the ORIGINAL perms dict with
      ONLY the allowlisted ptypes overridden to 1. Non-allowlisted
      ptypes (write, delete, create, etc.) retain their original
      values (0 for a scoped user with no role perm).

    The patches are additive: any unexpected condition falls
    through to Frappe's normal perm logic.
    """
    try:
        from frappe.core.doctype.report import report as report_module
    except Exception:
        return

    if getattr(report_module.Report, "is_permitted", None).__name__ == "_scope_aware_is_permitted":
        return  # already patched

    _ORIGINAL_IS_PERMITTED = report_module.Report.is_permitted

    def _scope_aware_is_permitted(self):
        try:
            if (
                self.name in ALLOWED_REPORTS
                and _user_has_active_scope_context()
            ):
                return True
        except Exception:
            pass
        return _ORIGINAL_IS_PERMITTED(self)

    _scope_aware_is_permitted.__name__ = "_scope_aware_is_permitted"
    report_module.Report.is_permitted = _scope_aware_is_permitted

    # --- Patch get_report_doc ---
    try:
        from frappe.desk import query_report as qr_module
    except Exception:
        return

    if getattr(qr_module, "_scope_patched_get_report_doc", False):
        return

    _ORIGINAL_GET_REPORT_DOC = qr_module.get_report_doc

    def _scope_aware_get_report_doc(report_name):
        # We CANNOT call _ORIGINAL_GET_REPORT_DOC first because it
        # would raise 403 before we can apply the bypass. Instead,
        # replicate the original logic here and apply the bypass
        # BEFORE the 403s.
        import json as _json

        from frappe.desk.query_report import (
            get_reference_report as _get_ref,
        )
        try:
            doc = frappe.get_doc("Report", report_name)
        except Exception:
            return _ORIGINAL_GET_REPORT_DOC(report_name)
        doc.custom_columns = []
        doc.custom_filters = []

        if doc.report_type == "Custom Report":
            custom_report_doc = doc
            doc = _get_ref(doc)
            doc.custom_report = report_name
            if custom_report_doc.json:
                data = _json.loads(custom_report_doc.json)
                if data:
                    doc.custom_columns = data.get("columns")
                    doc.custom_filters = data.get("filters")
            doc.is_custom_report = True
            doc.prepared_report = custom_report_doc.prepared_report

        if doc.disabled:
            from frappe import _ as _t
            frappe.throw(_t("Report {0} is disabled").format(_t(report_name)))

        # Bypass path: allowlisted report + scoped user → skip both
        # 403s. We deliberately do NOT set `frappe.flags.scope_report_bypass`
        # here. The downstream perm patches (`has_permission`,
        # `get_role_permissions`, `get_permitted_fields`) only fire
        # for requests that go through `_scope_aware_run` (i.e. the
        # `run` call path). The `get_script` call path does NOT
        # use those patches — it only needs the report doc back.
        # Setting the flag here would leave it active for the rest
        # of the request, allowing stale-flag perm grants via any
        # subsequent `has_permission` / `get_role_permissions` call.
        if (
            getattr(doc, "name", None) in ALLOWED_REPORTS
            and _user_has_active_scope_context()
        ):
            return doc

        # Original 403s for everyone else.
        if not doc.is_permitted():
            from frappe import _ as _t
            from frappe.exceptions import PermissionError as _PE
            raise _PE(
                _t("You don't have access to Report: {0}").format(_t(doc.name))
            )
        if not frappe.has_permission(doc.ref_doctype, "report"):
            from frappe import _ as _t
            from frappe.exceptions import PermissionError as _PE
            raise _PE(
                _t("You don't have permission to get a report on: {0}").format(
                    _t(doc.ref_doctype)
                )
            )
        return doc

    _scope_aware_get_report_doc._scope_patched_get_report_doc = True
    qr_module.get_report_doc = _scope_aware_get_report_doc

    # --- Patch frappe.permissions.has_permission ---
    try:
        import frappe.permissions as fp
    except Exception:
        return

    if getattr(fp, "has_permission", None).__name__ == "_scope_aware_permissions_has_permission":
        return  # already patched

    _ORIGINAL_PERMISSIONS_HAS_PERMISSION = fp.has_permission

    def _scope_aware_permissions_has_permission(
        doctype,
        ptype="read",
        doc=None,
        user=None,
        **kwargs,
    ):
        try:
            if _bypass_should_apply(
                doctype=doctype,
                ptype=ptype,
            ):
                return True
        except Exception:
            pass
        return _ORIGINAL_PERMISSIONS_HAS_PERMISSION(
            doctype,
            ptype=ptype,
            doc=doc,
            user=user,
            **kwargs,
        )

    _scope_aware_permissions_has_permission.__name__ = (
        "_scope_aware_permissions_has_permission"
    )
    fp.has_permission = _scope_aware_permissions_has_permission

    # --- Patch get_role_permissions ---
    if getattr(fp, "get_role_permissions", None).__name__ == "_scope_aware_get_role_permissions":
        return  # already patched

    _ORIGINAL_GET_ROLE_PERMISSIONS = fp.get_role_permissions

    def _scope_aware_get_role_permissions(doctype_meta, user=None, **kwargs):
        try:
            doctype_name = (
                doctype_meta.name
                if hasattr(doctype_meta, "name")
                else doctype_meta
            )
            if _bypass_should_apply(doctype=doctype_name):
                # Compute the user's real perms via the original
                # logic, then override ONLY the allowlisted ptypes
                # (report, select, read) to 1. This way, write,
                # delete, create, etc. remain 0 — the bypass does
                # NOT over-grant. The original has_permission reads
                # perms[ptype] and returns accordingly.
                perms = _ORIGINAL_GET_ROLE_PERMISSIONS(
                    doctype_meta, user=user, **kwargs
                )
                for ptype in _ALLOWED_PTYPES:
                    perms[ptype] = 1
                return perms
        except Exception:
            pass
        return _ORIGINAL_GET_ROLE_PERMISSIONS(doctype_meta, user=user, **kwargs)

    _scope_aware_get_role_permissions.__name__ = "_scope_aware_get_role_permissions"
    fp.get_role_permissions = _scope_aware_get_role_permissions

    # --- Patch get_permitted_fields ---
    try:
        import frappe.model as fm
    except Exception:
        fm = None

    if fm is not None and getattr(fm, "get_permitted_fields", None).__name__ == "_scope_aware_get_permitted_fields":
        pass  # already patched
    elif fm is not None:
        _ORIGINAL_GET_PERMITTED_FIELDS = fm.get_permitted_fields

        def _scope_aware_get_permitted_fields(
            doctype,
            parenttype=None,
            user=None,
            permission_type=None,
            **kwargs,
        ):
            try:
                if _bypass_should_apply(doctype=doctype):
                    meta = frappe.get_meta(doctype)
                    return meta.get_valid_columns()
            except Exception:
                pass
            return _ORIGINAL_GET_PERMITTED_FIELDS(
                doctype,
                parenttype=parenttype,
                user=user,
                permission_type=permission_type,
                **kwargs,
            )

        _scope_aware_get_permitted_fields.__name__ = "_scope_aware_get_permitted_fields"
        fm.get_permitted_fields = _scope_aware_get_permitted_fields


def _is_allowlisted_report_for_user(report_name: str, user: str | None) -> bool:
    """Return True if the report is in the allowlist and the user has
    an active scope context. This is the SINGLE condition that gates
    Option B's permissive perm responses.
    """
    try:
        if not report_name or report_name not in ALLOWED_REPORTS:
            return False
        return _user_has_active_scope_context(user)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Argument normalization
# ---------------------------------------------------------------------------


def _resolve_report_name(args: tuple, kwargs: dict) -> str | None:
    """Return the report name from either a positional or keyword arg."""
    if kwargs.get("report_name"):
        return kwargs["report_name"]
    if args:
        return args[0]
    return None


def _resolve_user(args: tuple, kwargs: dict) -> str:
    """
    Return the user from either a keyword or positional arg.

    Mirrors the real Frappe signature ``run(report_name, filters=None,
    user=None, ...)`` so that callers invoking positionally — e.g.
    ``run("General Ledger", filters, "some-user@example.com")`` —
    are honoured. Falls back to ``frappe.session.user`` only when no
    explicit value is supplied.
    """
    if kwargs.get("user"):
        return kwargs["user"]
    if _ORIGINAL_RUN_SIG is None:
        return frappe.session.user
    try:
        bound = _ORIGINAL_RUN_SIG.bind_partial(*args, **kwargs)
        bound_user = bound.arguments.get("user")
        if bound_user:
            return bound_user
    except TypeError:
        # Caller passed something we cannot bind; fall through to session.
        pass
    return frappe.session.user


def _normalize_filters(args: tuple, kwargs: dict):
    """
    Return ``(new_args, new_kwargs, filters_value)`` after parsing
    the caller's ``filters`` argument into a Python dict.

    Strategy: detect the original transport (positional or keyword)
    and pass `filters` back in the SAME form after rewriting.
    """
    sig = _ORIGINAL_RUN_SIG
    if sig is None:
        return args, kwargs, {}

    # Extract the known params and try to bind. Frappe's HTTP
    # handler may add extra kwargs (like `cmd`) that the function
    # signature does not declare. Pop the known params, bind the
    # rest, then merge back.
    filters_raw = kwargs.get("filters")
    other_kwargs = {k: v for k, v in kwargs.items() if k != "filters"}

    try:
        bound = sig.bind_partial(*args, **other_kwargs)
    except TypeError:
        # bind_partial failed (e.g. extra `cmd` kwarg). Fall back
        # to extracting filters from kwargs directly.
        if filters_raw is not None:
            if isinstance(filters_raw, str):
                try:
                    parsed = json.loads(filters_raw)
                    if not isinstance(parsed, dict):
                        parsed = {}
                except Exception:
                    parsed = {}
            elif isinstance(filters_raw, dict):
                parsed = dict(filters_raw)
            else:
                parsed = {}
            return args, {**other_kwargs, "filters": parsed}, parsed
        return args, kwargs, {}

    bound.apply_defaults()

    raw = bound.arguments.get("filters")
    if raw is None and filters_raw is not None:
        raw = filters_raw
    if raw is None:
        parsed: dict[str, Any] = {}
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                parsed = {}
        except Exception:
            parsed = {}
    elif isinstance(raw, dict):
        parsed = dict(raw)
    else:
        parsed = {}

    # Detect the underlying signature. If the function has a named
    # `filters` parameter, we must respect its slot. Otherwise (e.g.
    # `*args, **kwargs`), we can pass `filters` as a kwarg.
    filters_index = None
    for i, p in enumerate(sig.parameters.values()):
        if p.name == "filters":
            filters_index = i
            break

    new_args = bound.args
    new_kwargs = dict(bound.kwargs)

    if filters_index is not None and filters_index < len(new_args):
        # Strict signature. The filters value is in new_args at
        # filters_index. Keep it there. Do NOT also put it in new_kwargs.
        if new_args[filters_index] is not parsed:
            new_args = (
                *new_args[:filters_index],
                parsed,
                *new_args[filters_index + 1:],
            )
        new_kwargs = {k: v for k, v in new_kwargs.items() if k != "filters"}
    else:
        # *args, **kwargs signature. Pass `filters` only via kwargs.
        if "filters" in new_args:
            new_args = tuple(a for a in new_args if a is not raw and a is not parsed)
        new_kwargs["filters"] = parsed

    return new_args, new_kwargs, parsed


# ---------------------------------------------------------------------------
# Scope enforcement
# ---------------------------------------------------------------------------


def _has_unrestricted_report_role(user: str) -> bool:
    """Return True if the user has any role that bypasses report scope enforcement."""
    user_roles = set(frappe.get_roles(user))
    return bool(user_roles & UNRESTRICTED_REPORT_ROLES)


def _enforce_scope_filters_strict(filters: dict, user: str) -> dict:
    """
    Force scope-dimension filters to the user's **active** Scope Context.

    Policy:
      - Company: scalar, always the active scope value.
      - Cost Center: list, always `[scope.cost_center, *descendants]`.
      - Project: list, always `[scope.project]` (or `[]` if none).
      - Department: list, always `[scope.department]` (or `[]` if none).
      - A restricted user cannot widen any filter beyond the top bar.

    If the user has no Scope Context record at all, the dimension is
    left as `None` so the report's own validation (or its required
    filter) catches the missing value. This is the safe default.
    """
    scope_doc = get_user_scope_context(user)
    scope = {
        "company": scope_doc.company if scope_doc else None,
        "cost_center": scope_doc.cost_center if scope_doc else None,
        "project": scope_doc.project if scope_doc else None,
        "department": scope_doc.department if scope_doc else None,
    }

    # Hierarchy is consulted only for cost-center descendant expansion.
    hierarchy = get_user_scope_hierarchy(user) if scope_doc else {}
    cost_centers_index = {cc["name"]: cc for cc in hierarchy.get("cost_centers", [])}

    for dimension in SCOPE_DIMENSIONS:
        scoped_value = scope.get(dimension)

        if dimension == "cost_center" and scoped_value:
            # Build the strict list = scoped value + descendants via lft/rgt.
            scoped_node = cost_centers_index.get(scoped_value)
            if scoped_node:
                lft, rgt = scoped_node.get("lft"), scoped_node.get("rgt")
                if lft is not None and rgt is not None:
                    descendants = [
                        cc["name"]
                        for cc in hierarchy.get("cost_centers", [])
                        if cc.get("lft") is not None
                        and cc.get("rgt") is not None
                        and cc["lft"] >= lft
                        and cc["rgt"] <= rgt
                    ]
                else:
                    descendants = [scoped_value]
            else:
                descendants = [scoped_value]
            filters[dimension] = descendants
        elif dimension == "cost_center":
            # No scope or cost_center is empty — strict list is empty.
            filters[dimension] = []
        elif dimension == "company":
            # Company is always scalar (Link field) in ERPNext reports.
            filters[dimension] = scoped_value
        elif dimension == "project":
            # Project is MultiSelectList. Always present as a list.
            filters[dimension] = [scoped_value] if scoped_value else []
        elif dimension == "department":
            # Department is MultiSelectList.
            filters[dimension] = [scoped_value] if scoped_value else []

    return filters


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def _scope_aware_run(*args, **kwargs):
    """The patched entry point. Delegates to the original after filtering."""
    if _ORIGINAL_RUN is None:
        raise RuntimeError("Original query_report.run was not captured")

    # 1. Resolve the report name early so we can decide on enforcement.
    report_name = _resolve_report_name(args, kwargs)

    # 2. Bypass when scope context is disabled.
    try:
        settings = frappe.get_single("Construction Settings")
        if not settings or not settings.enable_scope_context:
            return _ORIGINAL_RUN(*args, **kwargs)
    except Exception:
        # If settings are unavailable, do not break the report.
        return _ORIGINAL_RUN(*args, **kwargs)

    # 3. Bypass for Administrator.
    user = _resolve_user(args, kwargs)
    if user == "Administrator":
        return _ORIGINAL_RUN(*args, **kwargs)

    # 4. Bypass for unrestricted finance / system roles.
    if _has_unrestricted_report_role(user):
        return _ORIGINAL_RUN(*args, **kwargs)

    # 5. Bypass for non-allowlisted reports. This is the critical
    #    Option A+ invariant: only the 10 plan-specified reports
    #    are gated. Everything else keeps Frappe's default behaviour.
    if report_name not in ALLOWED_REPORTS:
        return _ORIGINAL_RUN(*args, **kwargs)

    # 6. Normalise positional / keyword args so we can read filters
    #    regardless of how the caller invoked the function. The
    #    normalizer returns the location of the filters value so the
    #    rewritten value lands in exactly one place.
    new_args, new_kwargs, filters = _normalize_filters(args, kwargs)

    # 7. Enforce strict active-scope policy.
    filters = _enforce_scope_filters_strict(filters, user)

    # 8. Write the rewritten `filters` back to its proper slot. If the
    #    function has a strict signature with a named `filters`
    #    parameter, the value lives in new_args at filters_index; if
    #    not, it lives in new_kwargs. We always check both and
    #    update whichever is the canonical slot.
    sig = _ORIGINAL_RUN_SIG
    if sig is not None:
        filters_index = None
        for i, p in enumerate(sig.parameters.values()):
            if p.name == "filters":
                filters_index = i
                break
        if filters_index is not None and filters_index < len(new_args):
            new_args = (
                *new_args[:filters_index],
                filters,
                *new_args[filters_index + 1:],
            )
            if "filters" in new_kwargs:
                new_kwargs = {k: v for k, v in new_kwargs.items() if k != "filters"}
        else:
            new_kwargs["filters"] = filters

    # Option B: set the context-local bypass context (structured
    # dict) so the patched `frappe.permissions.has_permission` /
    # `get_role_permissions` / `get_permitted_fields` return
    # permissive values for the report's queries, and only for the
    # duration of this run call. We only set the context for
    # allowlisted reports with active scoped users. The bypass is
    # report-scoped (not doctype-scoped): the report's SQL builder
    # may query multiple secondary doctypes, and the data is
    # constrained by the L1+L2 wrappers.
    _bypass_active = report_name in ALLOWED_REPORTS and _user_has_active_scope_context(user)
    if _bypass_active:
        set_bypass_context(
            report_name=report_name,
            user=user,
        )
    try:
        return _ORIGINAL_RUN(*new_args, **new_kwargs)
    finally:
        if _bypass_active:
            clear_bypass_context()
