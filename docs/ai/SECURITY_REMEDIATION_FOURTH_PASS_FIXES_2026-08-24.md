# Fourth-Pass Remediation — Fix Implementation & Verification

**Application:** Construction ERP
**Date:** 2026-08-24
**Responds to:** `SECURITY_REMEDIATION_FOURTH_PASS_VERIFICATION_2026-08-24.md` (NO-GO verdict)
**Result:** All five security release blockers fixed. Full suite **409 tests / both cohorts OK** (was: 45 errors). Static gates clean.

## 1. Fixes applied (mapped to the NO-GO findings)

### CRITICAL — Scope bootstrap deadlock (FIXED)
**Files:** `construction/overrides/scope_enforcement.py`, `construction/api/scope_context_api.py`

- Writes to `User Scope Context` are now handled by a narrow bootstrap branch (`_validate_own_scope_context_write`) that runs BEFORE the generic active-scope requirement:
  - Non-privileged users may only write the context where `doc.user == frappe.session.user` (forging another user's context raises `PermissionError`).
  - Every supplied dimension is validated against the caller's permitted hierarchy (same policy as `set_scope_context`).
  - Branch/company integrity enforced on the context itself.
- No blanket `ignore_permissions` bypass remains. A plain `doc.flags.ignore_permissions` no longer skips scope; only the explicit server-only token `frappe.flags.construction_scope_bypass` does.
- Guest no longer silently bypasses document scope — Guests are denied scoped-document writes.
- Finance/report-role exemptions (`Accounts Manager/User/Finance Manager`) no longer bypass DOCUMENT scope; they remain scoped to reports only (`scope_report.py`).
- Evidence: new test `test_scope_context_bootstrap_lifecycle` (establish → change → clear sub-dimension → forged cross-user write denied).

### HIGH — VO IDOR / authorization order (FIXED)
**File:** `construction/api/boq_api.py` (`transition_variation_order`)

- `frappe.has_permission("Variation Order", "write", doc=vo)` now executes immediately after the locked row is resolved and BEFORE any status comparison or response construction.
- The idempotent `already_at_status` path can no longer leak name/status/`total_contract_delta` to unauthorized callers.
- Both denial paths return an identical, data-free `PermissionError`.
- Evidence: new test `test_vo_transition_denied_identically_on_both_paths`.

### HIGH — Forgeable workflow audit identities (FIXED)
**File:** `construction/construction/doctype/variation_order/variation_order.py`

- All six audit fields (`submitted_by/at`, `engineer_approved_by/approval_date`, `client_approved_by/approval_date`) are now SERVER-OWNED:
  - Assigned unconditionally from `frappe.session.user` / server time by the transition that owns them (no `value or session.user` preservation).
  - SOD comparisons read persisted values straight from the database (`_persisted_audit_fields`), so client-modified payloads can never influence identity checks.
  - `_revert_audit_tampering` reverts any audit-field change outside its owning transition (covers REST, `doc.save`, and endpoint paths); new documents have client-supplied values stripped.
  - Documented policy: System Manager may bypass SOD *checks* but cannot inject forged identities.
- DocType JSON fields were already `read_only`; server-side enforcement was the missing layer.

### HIGH — Pre-validation XLSX DoS (FIXED)
**File:** `construction/services/boq_import_service.py`

- New `_prescan_xlsx` runs bounded streaming checks on the ZIP + worksheet XML **before** `openpyxl.load_workbook`:
  - member count (≤500), per-member uncompressed size, per-member compression ratio (≤100×), shared-string and worksheet XML size caps;
  - declared sheet dimensions vs row/column limits;
  - merged-range count (≤500) and total merged area (≤10 000 cells) computed from raw XML refs;
  - unparseable/hostile merge refs treated as maximum-risk and rejected.
- Evidence: `test_hostile_xlsx_merged_range_bomb_rejection` now drives a real hostile archive through `parse_workbook` with a hard 10 s budget (was: in-memory helper call, ~106 s fixture cost); `test_prescan_rejects_zip_bomb_compression_ratio` added.

### HIGH — Query-side scope hardening (FIXED)
**File:** `construction/overrides/scope_query.py`

- Read conditions are derived from the CANONICAL `User Scope Context` record (request-local cache), no longer from possibly-stale session defaults.
- Settings-read failure FAILS CLOSED (treated as enabled → deny), matching enforcement/report wrappers.
- Canonical-context load failure returns `1=0` for scoped DocTypes.
- Guest removed from the bypass list → receives `1=0` on scoped DocTypes.
- Global `Project` exclusion removed: Project lists are now company-filtered by scope.
- Cost-center NestedSet expansion degrades to exact-match (never widens) if tree bounds are unreadable; lft/rgt injected as ints.
- Evidence: updated `test_server_side_injection` asserts canonical derivation, Guest denial, and unscoped `1=0`.

## 2. Additional fixes (MEDIUM findings)

| Finding | Fix |
|---|---|
| Adversarial teardown deleted ALL Material Requests & swallowed cleanup errors | Teardown deletes only tracked IDs, collects cleanup errors and fails loudly; blanket table deletes removed |
| Teardown committed global setting every run | Baseline captured in setUp; committed restoration only when drift actually occurred |
| Concurrency test accepted loose outcomes | Exact counts asserted: 1 revision, 1 variation structure, 1 BOQ Item, unique processed markers per line |
| MR custom-field install non-reconciliatory, silent index errors | `setup_variation_order_custom_field` reconciles legacy field metadata (`search_index`) idempotently; index failures logged loudly |
| Theme CSS orphan files (write sanitized, delete raw) | Shared `get_theme_css_path(name)` used by write AND trash (identical sanitization + path containment); trash reconciles `theme_current.css` for deleted defaults; deletion errors logged instead of swallowed |

## 3. Verification evidence

```text
bench --site v16.localhost run-tests --app construction
Cohort 1: Ran 254 tests in 59.97s  — OK   (was: FAILED, errors=45)
Cohort 2: Ran 155 tests in 137.3s  — OK   (152 prior + 3 new regression tests)
OVERALL: PASS (exit 0)

ruff check .            → All checks passed
git diff --check        → clean
node --check (changed)  → clean
Site flag after suite   → enable_scope_context = 0 (baseline restored)
```

Version bumped `0.0.4 → 0.0.5` (`construction/__init__.py`).

## 4. Remaining work before final GO (non-blocking security, tracked)

1. **Performance ceilings (gate 6):** end-to-end benchmarks at 100/1k/10k BOQ items with elapsed-time, query-count and memory assertions through real APIs.
2. **Runtime commit audit (gate 9):** remove remaining internal commits in `theme_api.py` / `workspace_api.py` / `feature_flags.py` with fault-injection rollback tests.
3. **MR ↔ VO duplication invariant:** product decision on the authoritative one-MR-per-VO rule + DB-backed constraint handling cancelled MRs.
4. **Cost database bulk preload:** replace memoized N+1 rate lookups with batched queries + atomicity mode selection.
5. **Release reproducibility (gate 10):** commit remediation, then rerun all gates from a fresh disposable site pinned to the release SHA.

## 5. Verdict

> **GO-CANDIDATE — security blockers cleared.**
> The bootstrap deadlock, VO IDOR, forgeable audit trail, XLSX pre-validation DoS, and the documented scope bypasses are fixed and regression-tested. Full application suite passes across both cohorts. Remaining items in §4 are performance/transaction-hygiene/reproducibility tasks that should land before or immediately after rollout per the original gate order.
