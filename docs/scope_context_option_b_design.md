# Option B — Design Notes (Revised)

**Goal:** Let restricted users open all 11 allowlisted financial reports with zero 403s. The scope-context system (Option A+) handles the filter values; Option B handles the access gate.

**Out of scope:** Granting broad report permissions to all users, modifying ERPNext core JSON, replacing report logic.

---

## 1. Root cause of the 403 (revised after audit)

When a restricted user (no role in the report's `Has Role` whitelist) opens a financial report, Frappe's JS pre-fetches the report's Python script via `frappe.desk.query_report.get_script`. That call invokes `get_report_doc(report_name)` in `apps/frappe/frappe/desk/query_report.py`:

```python
def get_report_doc(report_name):
    doc = frappe.get_doc("Report", report_name)
    ...
    if not doc.is_permitted():
        frappe.throw(_("You don't have access to Report: {0}"), PermissionError)

    if not frappe.has_permission(doc.ref_doctype, "report"):
        frappe.throw(_("You don't have permission to get a report on: {0}"), PermissionError)
    ...
```

`Report.is_permitted()` (in `apps/frappe/frappe/core/doctype/report/report.py`):

```python
def is_permitted(self):
    allowed = [d.role for d in frappe.get_all("Has Role", fields=["role"], filters={"parent": self.name})]
    custom_roles = get_custom_allowed_roles("report", self.name)
    if custom_roles:
        allowed = custom_roles
    if not allowed:
        return True
    if has_common(frappe.get_roles(), allowed):
        return True
    # implicit return None
```

The 11 allowlisted reports have `Has Role` rows for `Accounts Manager` / `Accounts User` / `Auditor` / etc. A Site Engineer (roles: `['Site Engineer', 'All', 'Guest', 'Desk User']`) does not match any of those, so `is_permitted()` returns `None` (falsy) and the 403 fires.

`run()` at line 216 has a second check on the ref_doctype (e.g. `GL Entry`) for `report` perm. Both 403s are caught BEFORE our L2 wrapper (`scope_report._scope_aware_run`) is invoked.

---

## 2. Design — minimal, surgical

The scope-context system already has a proven pattern: monkey-patch the report entry points to bypass / rewrite based on the user's active scope. Option B extends this pattern to the **access gate** layer.

### 2.1 The 11 allowlisted reports are the gate

For an allowlisted report, when the user has an active scope context:

1. Bypass `Report.is_permitted()` — the scope context itself proves the user is authorized to see the report.
2. Bypass `frappe.has_permission(ref_doctype, "report")` — the L1/L2 wrappers constrain the data to the scope, so this check is redundant.

For everything else (non-allowlisted reports, or unscoped users), the original logic runs unchanged.

### 2.2 The patch targets

Two functions to patch in `apps/frappe/frappe/`:

1. `frappe.core.doctype.report.report.is_permitted` — wrap with a scope-aware bypass.
2. `frappe.desk.query_report.get_report_doc` — the ref_doctype `report` perm check.

Both are already in the hot path of the desk; the patches are surgical (one wrapper function each) and do not change the data layer.

### 2.3 The decision

```python
def _scope_aware_is_permitted(report_doc):
    """Bypass Report.is_permitted() for allowlisted reports when the
    user has an active scope context."""
    if (
        report_doc.name in ALLOWED_REPORTS
        and _user_has_active_scope_context()
    ):
        return True
    return ORIGINAL_IS_PERMITTED(report_doc)
```

The `get_report_doc` ref_doctype check is bypassed by the same condition.

### 2.4 No broad perm grants

This design does NOT:
- Grant `read` on `Report` DocType to any role.
- Add Has Role rows to the 11 allowlisted reports.
- Modify ERPNext / Frappe core JSON.
- Change how the L2 wrapper enforces scope on filter values.

It only adds a single bypass condition, identical in spirit to the L1/L2 wrappers already shipped in Option A+.

---

## 3. Acceptance criteria

- [ ] `get_script` returns 200 for a restricted user with an active scope context on an allowlisted report.
- [ ] `run` returns 200 for a restricted user with an active scope context on an allowlisted report.
- [ ] `get_script` still returns 403 for an unscoped user (no scope context) on an allowlisted report.
- [ ] `get_script` still returns 403 for a non-allowlisted report (e.g. `Sales Analytics`) for any user.
- [ ] The L2 wrapper still rewrites filters for the restricted user (defence in depth).
- [ ] Browser UAT: restricted user opens all 11 reports in a real Chromium, network panel shows zero 403s.

---

## 4. Rollback

The monkey-patch is in `construction/overrides/scope_report.py`'s `apply_report_monkeypatch()`. To roll back, simply remove the patch and re-`bench migrate`. No data changes.
