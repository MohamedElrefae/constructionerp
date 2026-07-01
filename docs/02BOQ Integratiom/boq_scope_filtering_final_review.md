# BOQ Scope Context Filtering — Final Technical Review & Recommendation

**Reviewer:** Architecture Review (Antigravity)  
**Date:** 2026-05-26  
**Documents reviewed:**
- [boq_scope_context_filtering_implementation_plan.md](file:///home/mohamed/frappe-bench/apps/construction/docs/boq_scope_context_filtering_implementation_plan.md)
- [boq_scope_context_filtering_enhancement_directive.md](file:///home/mohamed/frappe-bench/apps/construction/docs/boq_scope_context_filtering_enhancement_directive.md)
- **Original BOQ Integration Design Report (May 23, 2026)** — GM Approval Document, v1.1

---

## 1. Overall Assessment

The **Implementation Plan** is well-structured and architecturally sound. The "Prevent First, Reject Last" posture is the correct enterprise model. The cascade chain (Company → Cost Center → Project → BOQ Header → BOQ Structure → BOQ Item → BOQ Item Stage) is logically correct and aligns with the existing codebase structure observed in [boq_link_queries.py](file:///home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py) and [boq_filters.js](file:///home/mohamed/frappe-bench/apps/construction/construction/public/js/boq_filters.js).

The **Enhancement Directive** is also high quality and raises legitimate production-readiness concerns. However, some of its requirements add significant scope and should be evaluated carefully before being treated as hard pre-conditions to implementation start.

**Verdict: Approved for implementation with the conditions listed in Section 5.**

---

## 2. Alignment Between Plan and Directive

### ✅ Fully Aligned

| Plan Item | Directive Requirement | Status |
|---|---|---|
| `ALLOWED_TRANSACTION_BOQ_STATUSES` constant | Upgrade to include `EXCLUDED_*` companion + explicit comments | Minor wording delta — trivially resolved |
| `get_scope_token` using MD5 | Replace with SHA-256 + `modified` timestamp | **Mandatory fix** — MD5 is unacceptable |
| f-string SQL conditions with `frappe.db.escape()` | Mandate dict parameter binding `%(key)s` | Already correct in existing code; new code must follow same pattern |
| Single `boq_scope_filters.py` | Split into `scope_resolution.py` (pure Python) + `boq_scope_filters.py` (SQL-aware) | Good testability improvement — adopt |
| Basic field definitions (`depends_on` only) | Add `read_only_depends_on` to all BOQ cascade fields | **Mandatory** — prevents edits when conditions not met |
| Generic `_resolve_insert_after` fallback | Use `BOQ_CASCADE_INSERT_AFTER` mapping per DocType | **Mandatory** — Journal Entry Account has no `expense_category` field |
| No feature flag | Add `Construction Settings.enable_boq_cascade_filtering` (Off/On/Strict) | **Mandatory** — essential for safe rollout and rollback |
| No rollback patch | Add `v6_6/revert_boq_cascade_fields.py` | **Mandatory** |
| No audit field | Add hidden `boq_selection_scope_type` field | Recommended — low effort, high audit value |
| No pre-save scope drift guard | Add `guardSaveAgainstScopeDrift(frm)` | **Mandatory** — prevents the multi-tab race condition |

### ⚠️ Directive Requirements That Need Scoping Decision

| Directive Requirement | Concern | Recommendation |
|---|---|---|
| Performance SLIs + Locust load test | Good target, but load test infrastructure may not exist yet | Define SLIs in plan. Make load test a pre-`Strict` gate, not a pre-`On` gate. |
| `boq_data_quality_report` (`Phase 6.5`) | A full Frappe Report DocType is non-trivial to build correctly | Implement as a simple Python script first; promote to Report DocType in Phase 2 |
| Mobile/offline compatibility note | Acceptable degradation already documented | Add to Out of Scope. No change needed. |
| Real-time collaborative editing out of scope | Already excluded | Confirm in Out of Scope list |
| `enforce_scope` optional param with deprecation warning | Good for external integrations. Adds complexity. | Implement. Low risk. |
| `aria-live="polite"` notification containers | Accessibility requirement is valid | Implement in Phase 3 JS. Low effort. |

---

## 3. Critical Issues Found — Must Fix Before Implementation Start

### 3.1 SHA-256 vs MD5 in `get_scope_token`

The plan defines `get_scope_token` using `hashlib.md5`. The directive correctly mandates SHA-256.
Additionally, the plan version hashes a tuple representation, which is fragile (Python tuple `str()` includes quotes and commas). The directive's version using `|`-delimited f-string is more robust.

**Required replacement (from directive — verbatim):**

```python
def get_scope_token(user):
    """Return a deterministic token representing the user's active scope.
    
    Includes the User Scope Context `modified` timestamp so in-place
    updates invalidate the token without requiring a value change.
    """
    scope = frappe.db.get_value(
        "User Scope Context",
        {"user": user},
        ["company", "cost_center", "project", "modified"],
        as_dict=True,
    )
    if not scope:
        return None
    payload = f"{scope.company}|{scope.cost_center}|{scope.project}|{scope.modified}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]
```

**Impact:** Security and compliance. Zero functional regression.

---

### 3.2 `BOQ_CASCADE_INSERT_AFTER` Map is Missing

The current [install.py](file:///home/mohamed/frappe-bench/apps/construction/construction/install.py#L127-L136) uses `_resolve_insert_after` with a generic fallback list. On `Journal Entry Account`, this would resolve to `account` (correct) only by coincidence. For `Timesheet Detail`, the fallback is `activity_type`, which may not be adjacent to `expense_category`.

The directive's `BOQ_CASCADE_INSERT_AFTER` per-DocType map is not optional — it is **required for correct field placement**:

```python
BOQ_CASCADE_INSERT_AFTER = {
    "Purchase Order Item": "expense_category",
    "Purchase Receipt Item": "expense_category",
    "Purchase Invoice Item": "expense_category",
    "Stock Entry Detail": "expense_category",
    "Timesheet Detail": "expense_category",
    "Journal Entry Account": "account",
    "Sales Invoice Item": "expense_category",
    "Material Request Item": "expense_category",
}
```

**Impact:** Data model correctness. Wrong `insert_after` causes BOQ cascade fields to appear in the wrong location on child tables.

---

### 3.3 Feature Flag is Non-Negotiable

The plan has no feature flag. Deploying the full cascade without a feature flag means there is no safe rollback path short of running the revert patch. The directive's three-state flag (`Off` / `On` / `Strict`) must be added to `Construction Settings`. This also enables the pilot rollout sequence described in Phase 7.

Replication of the existing [scope_enforcement.py](file:///home/mohamed/frappe-bench/apps/construction/construction/overrides/scope_enforcement.py#L28-L33) try/except pattern is required:

```python
try:
    cascade_mode = frappe.db.get_single_value(
        "Construction Settings", "enable_boq_cascade_filtering"
    ) or "Off"
except Exception:
    cascade_mode = "Off"
```

**Impact:** Deployment safety. This is a production-readiness gate.

---

### 3.4 `read_only_depends_on` Missing from All BOQ Cascade Fields

The plan specifies `depends_on` but not `read_only_depends_on` for the four cascade fields. Without `read_only_depends_on`, a user can click into the field when the parent field is empty because the field is still editable in Frappe's form engine — only its visibility is controlled by `depends_on`.

The directive's field definitions with `read_only_depends_on` are **mandatory** for all four fields.

**Impact:** UX correctness. Field visibility ≠ field editability in Frappe.

---

### 3.5 Pre-Save Scope Drift Guard is Missing from the Plan

The plan describes client-side scope token polling but does not define the pre-save intercept. The directive's `guardSaveAgainstScopeDrift` function is not optional — it is the only mechanism that closes the multi-tab race condition where a user opens a Purchase Invoice in Tab A, changes Scope Context in Tab B, then saves in Tab A with stale BOQ data.

```javascript
async function guardSaveAgainstScopeDrift(frm) {
    const currentToken = await fetchScopeToken();
    if (currentToken && currentToken !== lastKnownScopeToken) {
        frappe.show_alert({
            message: __("Your scope context has changed. Reloading form to prevent invalid attribution."),
            indicator: "orange"
        });
        frm.reload_doc();
        return Promise.reject("scope_drift");
    }
}
```

This guard must wrap `frm.save` and `frm.submit` for all transaction DocTypes.

**Impact:** Data integrity. Without this, backend validation alone catches the error after a failed save — poor UX and creates failed document versions.

---

### 3.6 Sales Invoice Item — Wrong Cascade Gate (`expense_category` vs. `is_progress_billing`)

> [!IMPORTANT]
> This is a **newly identified critical issue** surfaced by reviewing the original BOQ Integration Design Report (v1.1).

**Confirmed intent:** BOQ attribution on `Sales Invoice Item` is **intentional and architecturally required**. The original design report (Section 4.2C) explicitly establishes it as the **revenue side** of the BOQ margin equation:

> *"Revenue per BOQ Item vs. Cost per BOQ Item = Gross Margin per work item. Enables client-facing progress billing reports."*

**The problem:** The current implementation plan applies the same `expense_category == 'Direct'` gate uniformly to all child doctypes — including `Sales Invoice Item`. This is wrong. Sales Invoices are **revenue documents**, not expense documents. A Sales Invoice line will never have `expense_category = 'Direct'`; therefore the BOQ cascade fields on `Sales Invoice Item` will never become visible under the current `depends_on` logic.

**The correct gate from the original design:**
```python
# Sales Invoice Item — BOQ is mandatory for progress billing invoices only
mandatory_depends_on: eval:doc.is_progress_billing
```

**Required fix:** `Sales Invoice Item` must have its own `depends_on` / `read_only_depends_on` in the `BOQ_CASCADE_INSERT_AFTER` logic — separate from the `expense_category`-based gate used by procurement and JE doctypes.

Update `install.py` to apply per-DocType `depends_on` overrides:

```python
BOQ_CASCADE_DEPENDS_ON = {
    # All procurement/expense doctypes
    "Purchase Order Item":      "eval:doc.expense_category == 'Direct'",
    "Purchase Receipt Item":    "eval:doc.expense_category == 'Direct'",
    "Purchase Invoice Item":    "eval:doc.expense_category == 'Direct'",
    "Stock Entry Detail":       "eval:doc.expense_category == 'Direct'",
    "Timesheet Detail":         "eval:doc.expense_category == 'Direct'",
    "Journal Entry Account":    "eval:doc.expense_category == 'Direct'",
    "Material Request Item":    "eval:doc.expense_category == 'Direct'",
    # Revenue doctype — different gate entirely
    "Sales Invoice Item":       "eval:doc.is_progress_billing",
}
```

The `read_only_depends_on`, `boq_structure.depends_on`, `boq_item.depends_on`, and `boq_item_stage.depends_on` for `Sales Invoice Item` must all cascade from `is_progress_billing`, not `expense_category`.

**Impact:** Without this fix, BOQ attribution on Sales Invoices will be invisible to users. The entire progress billing and gross margin per work-item reporting capability (a stated GM-approved business outcome) will be silently broken.

**Add to mandatory pre-conditions list as item #9.**

---

## 4. Lower-Priority Items — Implement but Not Pre-Conditions

### 4.1 Structured Logging in Backend Rejection

The directive requires every backend rejection to emit a structured log event:

```python
frappe.logger("boq_validation").warning({
    "event": "boq_backend_rejection",
    "user": frappe.session.user,
    ...
})
```

This is not a pre-condition for implementation but is required before `Strict` mode is enabled. Add to Phase 5 implementation checklist.

### 4.2 `boq_selection_scope_type` Audit Field

Low effort to add in the migration. Provides an immutable audit trail of whether the BOQ selection was Project-scoped or Company+Cost Center-scoped. **Implement in Phase 1 migration** alongside the other cascade fields.

### 4.3 Module Split: `scope_resolution.py` vs `boq_scope_filters.py`

This is a testability improvement. The split is correct: pure Python scope resolution in one module, SQL-building in another. The SQL-aware module inherits the security mandate for dict parameter binding.

### 4.4 Warning UI Standard

The directive mandates `frm.dashboard.add_comment()` or `frappe.show_alert()` for scope warnings — not `frappe.msgprint()`. This is already the right approach for non-blocking guidance. Enforce in code review.

### 4.5 Accessibility (`aria-live="polite"`)

Add `aria-live="polite"` container for cascade clear notifications. 5-second minimum display duration. Low effort in Phase 3 JS.

---

## 5. Final Recommendation

### ✅ APPROVED for implementation with the following mandatory pre-conditions:

> [!IMPORTANT]
> The following items must be incorporated into the plan document **and** into the first commit before any implementation begins. They are not optional post-release fixes.

1. **Replace MD5 with SHA-256 in `get_scope_token`** — include `modified` timestamp in payload.
2. **Add `BOQ_CASCADE_INSERT_AFTER` per-DocType map** to `install.py` — remove generic `_resolve_insert_after` for this feature.
3. **Add `Construction Settings.enable_boq_cascade_filtering`** (Off/On/Strict, default Off) — expose via `frappe.boot`.
4. **Add `read_only_depends_on`** to all four cascade custom field definitions.
5. **Add pre-save `guardSaveAgainstScopeDrift`** function to `boq_filters.js`, wired to `frm.save` and `frm.submit`.
6. **Add revert patch** `construction/patches/v6_6/revert_boq_cascade_fields.py` and test it for idempotency.
7. **Add `EXCLUDED_TRANSACTION_BOQ_STATUSES`** companion constant alongside `ALLOWED_TRANSACTION_BOQ_STATUSES`.
8. **Split `boq_scope_filters.py`** into `scope_resolution.py` (pure Python) + `boq_scope_filters.py` (SQL-aware).
9. **Add per-DocType `depends_on` override map (`BOQ_CASCADE_DEPENDS_ON`)** — `Sales Invoice Item` must be gated on `is_progress_billing`, not `expense_category`. Apply the same override to `read_only_depends_on` for all four cascade fields on that DocType.

> [!WARNING]
> Do not enable `Strict` mode in production until the Data Quality Gate (Phase 6.5) passes with zero `CRITICAL` findings. Run the data quality check as a script before building the full Frappe Report DocType.

### Phased Rollout Sequence (Mandatory)

| Phase | Action | Gate |
|---|---|---|
| Migration | Run `v6_6` patch — fields hidden, flag `= Off` | Patch idempotency test passes |
| Pilot On | Set flag `= On` for pilot user group | Monitor `boq_validation` log for 48 hours |
| Full On | Enable flag `= On` site-wide | Zero backend rejections in pilot window |
| Strict | Set flag `= Strict` | Data Quality Gate passes + 48h zero-rejection window under `On` |

---

## 6. Files Expected to Change (Consolidated)

### New Files

| File | Purpose |
|---|---|
| `construction/services/scope_resolution.py` | Pure Python scope helpers |
| `construction/services/boq_scope_filters.py` | SQL condition builders |
| `construction/patches/v6_6/add_boq_cascade_transaction_fields.py` | Migration + indexes |
| `construction/patches/v6_6/revert_boq_cascade_fields.py` | Rollback patch |
| `construction/tests/test_boq_link_queries.py` | Query API tests |
| `construction/tests/test_boq_scope_cascade.py` | Cascade + pre-save guard tests |
| `construction/tests/test_boq_transaction_validation.py` | Backend validation tests |
| `construction/tests/load/test_boq_cascade_load.py` | Locust perf tests (pre-Strict gate) |
| `construction/construction/report/boq_data_quality_report/` | Data quality check (can start as script) |

### Modified Files

| File | Key Change |
|---|---|
| [install.py](file:///home/mohamed/frappe-bench/apps/construction/construction/install.py) | Add `boq_header`, `boq_structure`, `boq_selection_scope_type` fields; add `BOQ_CASCADE_INSERT_AFTER` map; add `read_only_depends_on` |
| [boq_link_queries.py](file:///home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py) | Add `enforce_scope` param; inject scope constraints; add `get_boq_scope_token` endpoint |
| [boq_accounting.py](file:///home/mohamed/frappe-bench/apps/construction/construction/services/boq_accounting.py) | Add cross-chain validations; replace inline status strings with constant; add structured logging; populate `boq_selection_scope_type` |
| [boq_filters.js](file:///home/mohamed/frappe-bench/apps/construction/construction/public/js/boq_filters.js) | Full cascade controller rewrite; add `boq_header`/`boq_structure` queries; add pre-save guard; add scope token polling; add `aria-live` notification container |
| [scope_context_form_defaults.js](file:///home/mohamed/frappe-bench/apps/construction/construction/public/js/scope_context_form_defaults.js) | Add child-row defaults for `project`, `cost_center`, `company` on new rows |
| `construction/patches.txt` | Add v6_6 entries |
| `construction/boot.py` | Expose `enable_boq_cascade_filtering` to client via `frappe.boot` |

---

## 7. Open Questions — All Resolved

| # | Question | Resolution |
|---|---|---|
| 1 | **`Journal Entry Account`** has no `expense_category` | ✅ **Resolved — Add `expense_category` to JE Account.** See §7.1 below. |
| 2 | **Timesheet Detail** BOQ attribution trigger | ✅ **Resolved — Designation-based mandatory rule.** See §7.2 below. |
| 3 | **`Sales Invoice Item`** BOQ attribution intent | ✅ **Resolved — Intentional.** Gate = `is_progress_billing`. See critical issue §3.6. |
| 4 | **Data Quality Report** implementation form | ✅ **Resolved — Python script first, Frappe Report DocType in follow-on sprint.** |
| 5 | **Load test** — production-scale staging DB available? | ✅ **Resolved — Local seed-based SLI test.** See §7.3 below. |

---

### 7.1 Journal Entry Account — Recommendation: Add `expense_category` as Custom Field

**Enterprise best practice: consistency wins.**

Every other child DocType in the BOQ cascade already carries `expense_category`. The cleanest and most maintainable enterprise design is to add the same field to `Journal Entry Account` so the pattern is uniform across all eight target DocTypes. This means:

- Users entering manual journal entries see the same familiar field.
- Backend validation logic uses a single code path for all DocTypes.
- Reporting on direct vs. indirect costs by DocType type is consistent.
- No special-casing in `boq_filters.js` for JE Account.

**Add to `BOQ_CASCADE_INSERT_AFTER`:**
```python
"Journal Entry Account": "account",   # insert_after = account (no project field on JE Account)
```

**Add to `BOQ_CASCADE_DEPENDS_ON`:**
```python
"Journal Entry Account": "eval:doc.expense_category == 'Direct'",
```

**The `expense_category` custom field on JE Account** should be the same `Select` field (`Direct / Indirect / Overhead / Capital`) with `default = ""` (blank, not `Direct`) because not all journal entries are project cost entries. The BOQ cascade fields will be hidden until the accountant explicitly sets `expense_category = Direct`.

> [!NOTE]
> This is the same pattern used by enterprise construction finance platforms: the cost classification field is the user's explicit signal, not inferred. On Journal Entries it is especially important to be explicit because JEs are also used for accruals, corrections, and inter-company transfers that should never carry a BOQ reference.

---

### 7.2 Timesheet Detail — Recommendation: Designation-Based Mandatory Rule

**Enterprise standard: role determines obligation, not a manually-entered category.**

Oracle Primavera, Procore, and SAP PS all determine whether a time entry must carry a work item reference based on the employee's role/designation, not a field the employee manually fills in. Asking a Site Worker to set `expense_category = Direct` on every timesheet row introduces friction and invites mistakes. The worker may set it to `Indirect` to skip the BOQ field.

**Recommended implementation:**

Add a `Construction Settings` configuration table: **"Direct Labor Designations"** — a list of employee designations whose time entries are always direct-cost BOQ-mandatory. Default seed list:

| Designation | BOQ Item |
|---|---|
| Site Worker | Mandatory |
| Mason | Mandatory |
| Carpenter | Mandatory |
| Steel Fixer | Mandatory |
| Operator | Mandatory |
| Electrician | Mandatory |
| Plumber | Mandatory |
| Site Engineer | Optional |
| Site Supervisor | Optional |
| Project Manager | Not applicable |
| Foreman | Optional |

**Backend validation logic:**
```python
def _validate_timesheet_row(row, parent_doc):
    if not row.get("employee"):
        return
    designation = frappe.db.get_value("Employee", row.employee, "designation")
    direct_designations = frappe.db.get_all(
        "Direct Labor Designation",   # child table in Construction Settings
        filters={"parenttype": "Construction Settings"},
        pluck="designation",
    )
    if designation in direct_designations:
        if not row.get("boq_item"):
            frappe.throw(
                _("Row {0}: Direct labor ({1}) must be assigned to a BOQ Item.").format(
                    row.idx, designation
                )
            )
```

**Client-side (`boq_filters.js`):**
- On `Timesheet Detail`, the `boq_header` → `boq_structure` → `boq_item` cascade becomes visible when the employee's designation is in the direct list (fetched once on form load).
- `expense_category` field is **not used on Timesheet Detail** — omit it from `BOQ_CASCADE_DEPENDS_ON` for this DocType; the visibility gate is `eval:frappe.boot.direct_labor_designations.includes(doc.designation)`.
- Expose `frappe.boot.direct_labor_designations` from `boot.py` (same pattern as `enable_boq_cascade_filtering`).

> [!IMPORTANT]
> Add `Timesheet Detail` to `BOQ_CASCADE_DEPENDS_ON` with a special marker so `install.py` knows to use the designation gate instead of the `expense_category` gate:
> ```python
> "Timesheet Detail": "eval:frappe.boot.direct_labor_designations.includes(doc.designation)",
> ```
> This also means `expense_category` is **not added** to `Timesheet Detail` as a custom field — reducing noise on the timesheet form.

---

### 7.3 Load Testing — Recommendation: Local Seed-Based SLI Test (No Locust Required)

**Practical approach for teams without dedicated load-test infrastructure.**

Locust requires a staging server, test orchestration, and data engineering. Instead, implement a **local DB seed + timing test** that any developer can run before deployment:

**Add to `construction/tests/load/test_boq_cascade_load.py`:**

```python
import time
import frappe
import unittest

class TestBOQCascadePerformance(unittest.TestCase):
    """Performance SLI tests using a seeded local database.
    Run: bench --site <site> run-tests --module construction.tests.load.test_boq_cascade_load
    """

    @classmethod
    def setUpClass(cls):
        """Seed 5,000 BOQ Headers and 50,000 BOQ Items for realistic load."""
        cls._seed_boq_data(n_headers=5000, n_items=50000)

    def test_boq_header_query_under_300ms(self):
        start = time.perf_counter()
        from construction.api.boq_link_queries import get_boq_headers
        get_boq_headers("BOQ Header", "", "name", 0, 20,
                        {"project": "LOAD-TEST-PROJECT-001"})
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertLess(elapsed_ms, 300, f"BOQ Header query took {elapsed_ms:.0f}ms (SLI: <300ms)")

    def test_boq_item_query_under_300ms(self):
        start = time.perf_counter()
        from construction.api.boq_link_queries import get_boq_items
        get_boq_items("BOQ Item", "", "name", 0, 20,
                      {"boq_header": "LOAD-TEST-HEADER-001",
                       "structure": "LOAD-TEST-STRUCT-001"})
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertLess(elapsed_ms, 300, f"BOQ Item query took {elapsed_ms:.0f}ms (SLI: <300ms)")

    def test_scope_token_endpoint_under_50ms(self):
        start = time.perf_counter()
        from construction.services.scope_resolution import get_scope_token
        get_scope_token(frappe.session.user)
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertLess(elapsed_ms, 50, f"Scope token took {elapsed_ms:.0f}ms (SLI: <50ms)")
```

**SLI thresholds (unchanged from directive — now enforced by automated test):**

| Metric | Target | Test Dataset | Verified By |
|---|---|---|---|
| BOQ Header dropdown | < 300 ms | 5,000 headers | `test_boq_header_query_under_300ms` |
| BOQ Item dropdown | < 300 ms | 50,000 items | `test_boq_item_query_under_300ms` |
| Scope token endpoint | < 50 ms | Any | `test_scope_token_endpoint_under_50ms` |
| Save validation (100 rows) | < 200 ms | Seed document | Add to `test_boq_transaction_validation.py` |

**Gate rule:** These tests must pass locally before the `On` flag is enabled site-wide. They run as part of the standard `bench run-tests` suite — no separate infrastructure needed.

> [!TIP]
> After the seed tests pass locally, run the same `bench run-tests` suite on a copy of the production database (with anonymized data) before enabling `Strict` mode. This covers real-world data skew that synthetic seeds cannot simulate.

---

## 8. Summary Scorecard

| Dimension | Plan | Plan + Directive | Ready? |
|---|---|---|---|
| Cascade UX design | ✅ Solid | ✅ Solid | ✅ Yes |
| Backend validation | ✅ Present | ✅ Enhanced | ✅ Yes |
| Security (SQL injection) | ✅ Correct pattern already | ✅ Mandated for new code | ✅ Yes |
| Security (hash algorithm) | ❌ MD5 | ✅ SHA-256 + modified | Fix required |
| Feature flag / rollback | ❌ Missing | ✅ Defined | Fix required |
| Field editability control | ❌ Missing `read_only_depends_on` | ✅ Defined | Fix required |
| Pre-save race condition | ❌ Missing | ✅ Defined | Fix required |
| Insert-after correctness | ⚠️ Generic fallback | ✅ Per-DocType map | Fix required |
| **Sales Invoice cascade gate** | ❌ Wrong gate (`expense_category`) | ✅ Correct gate (`is_progress_billing`) | **Fix required** |
| Module testability | ⚠️ Single module | ✅ Split for purity | Adopt |
| Audit trail | ❌ Missing | ✅ `boq_selection_scope_type` | Adopt |
| Performance SLIs | ❌ Not defined | ✅ Defined | Adopt |
| Accessibility | ❌ Not addressed | ✅ `aria-live` | Adopt |
| Data quality gate | ❌ Not defined | ✅ Defined | Adopt |
| Mobile degradation | ❌ Not addressed | ✅ Documented | Adopt |
