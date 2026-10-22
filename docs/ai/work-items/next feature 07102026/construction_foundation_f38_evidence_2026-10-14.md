# F38 — Final diff and defect review (evidence)

Date: 2026-10-14 · HEAD: `fa38022` · Snapshot diff sha `940c9f64…` (2,475 lines) + 89 hashed
untracked files. **F38 stays OPEN** — F31/F32 site qualification, matching F35 execution,
and other required gates remain outstanding.

> **Update 2026-10-15:** candidate review completed and frozen (diff sha
> `d716f071da508f67…`, 159 entries / 107 untracked / 174 hashed); F37 evidence, F43 pack
> and the [authorization request](construction_foundation_f38_authorization_request_2026-10-15.md)
> (commit / private CI / installation route — delivery approval separate) are written.
> F38 remains OPEN pending the three authorizations, F44 acceptance and F45.

## 1. Reconciliation: every changed file → task → test → remaining finding

### Product code (ships)

| File | Task / finding | Test evidence | Remaining |
|---|---|---|---|
| `construction/services/boq_report_service.py` | F21-D002: select `RPH.name` | `test_f21_price_history_row_auth` 10/10 (incl. D001 grant tests + no-data-in-any-form) | none |
| `construction/api/construction_reports.py` (new) | F19 adapters; F21-D002 `_readable_rph` refuses unidentified rows | same suite; F36 R5/R6 denials live | none |
| `construction/overrides/boq_permissions.py` | F06-D001 VO parent-read; F11-D003 stage measurement; F18 maintainer analysis-read | `test_vo_approval_parent_gate` 5/5; `test_scope_and_measurement_policy` 5/5; F36 L2 chain | none |
| `construction/overrides/file_permissions.py` + `file_download.py` (new) | F11/F12 BOQ attachment boundary | `test_security_audit_remediation` 24/24 | none |
| `construction/overrides/scope_enforcement.py` (uncommitted? verify) | scope containment | scope suites | — (see §3) |
| `construction/api/scope_context_api.py` | F22-D006 project-display fallback | `test_project_display_name_authorization` 6/6; browser 403-dialog gone | none |
| `construction/construction/doctype/boq_header/boq_header.js` | F22-D003 `__()` wrapping; F36-D003 preview guards (d.doc init, post-refresh restores, English enum codes) | `test_f22_arabic_coverage` 5/5 (incl. new guards test); F36 import 8/8 | none |
| `construction/services/boq_import_service.py` | K-01 two-step + idempotency | `test_boq_import_idempotency`; F36 I4/I5 | none |
| `construction/services/cost_database_service.py` | F18 narrowing (reuse-or-refuse, company-match); **F35 UOM idempotency fix** (framework stores canonical Link case — exact-compare false-conflicted on re-import; now case-insensitive, names/type/stream stay exact) | `test_cost_database_isolation`; `test_cost_database_api` 23/23; F36 R2 | none |
| `construction/construction/doctype/boq_item_stage/boq_item_stage.py` | F11-D003 measurement-only UI | F23 A10/B5 permission field checks | none |
| `construction/construction/doctype/variation_order/variation_order.py` | VO workflow + SoD | F36 L2 full chain | none |
| `construction/construction/doctype/boq_cost_analysis_detail/*.json` | F18 rate_source option | engine suite 38/38 | none |
| `construction/public/js/vite_layout_controls.js` + `vite_form_override.css` | F23-D002 unsaved indicator, close/leave warnings, density label | F23 18/18 + D002 retest 10/10 | owner acceptance pending (not a defect) |
| `construction/construction/sidebar/construction_home/construction_home.json` (new) | F21 app-backed Sidebar (30 items, standard=1) | F21 reach 7/7; F22 N2 sidebar Arabic | F22-D007 closed as unsupported slug |
| `construction/config/workspace_sidebar_items.json` | ENV-D001 title fix | Sidebar re-save + migrate on both sites | none |
| `construction/hooks.py` | `?v=` bumps (1.22/1.6); download override registration | F25 asset 200s; staged verification | none |
| `construction/construction/page/{construction_report_viewer,cost_database_workbench}/` (new) | F19 viewer pages | F19 10/10; F22/F36 browser | none |
| `erpnext-mcp-server/server.py` | F27 UAT-D005 bridge items fix | verified 3/3 rows | bridge scoping stays open (F27) |
| `pyproject.toml` | F28 sdist map exclusion (10-line diff, CRLF preserved) | clean Flit rebuild 1,239 members, 0 maps | none |

### Tests (ship in package per Frappe convention)

`test_f21_price_history_row_auth` (10), `test_f22_arabic_coverage` (5),
`test_project_display_name_authorization` (6), `test_scope_and_measurement_policy` (5),
`test_vo_approval_parent_gate` (5), `test_boq_import_idempotency`, `test_cost_database_isolation`
— all green. `test_cost_analysis_engine` 38/38. `test_security_audit_remediation` 24/24
(after F24-D002 teardown fix).

### Scripts (ship; operator tooling)

`permission_reconciliation.py` (+ checked-in baseline), `apply_report_audience_company_read.py`
(idempotent, refuses first-write), `stage_distribution.py`, `verify_distribution.py`,
`verify_staged_distribution.py` — all pass.

### Docs & guides (customer set where marked)

`README.md` (packaging note), `docs/CUSTOMER_ONBOARDING.md` + `docs/MAINTENANCE.md` (new),
`docs/DISTRIBUTION.md` (new), `docs/runbook.md` (§0.3–0.6), F21–F26/F28/F31/F36 evidence,
register, SESSION_MEMORY. Internal evidence (`docs/ai/`) stays out of any customer route.

### Deletions / moves

`setup.py` removed (Flit canonical; CI keys updated); 2 Sidebar `.bak` removed; 12 test PNGs
relocated to docs evidence; `.map` uncommitted-excluded.

## 2. Explicitly NOT in this batch

- `orchestrator/engine.py` (+3, opencode binary paths): environment tooling, predates this
  program. Must be stashed or committed separately — never as part of F38.
- `CI_READINESS.md`, `PLAN.md`, `PRIVATE_CI.md`, `STATUS.md`, `VERIFICATION.md`,
  `docs/ai/CONTEXT_INDEX.md`, `SCHEMA_FACTS.md`, `USER_GUIDE.md`, `docs/handover/INDEX.md`:
  pre-existing living docs with program-adjacent edits; owner to confirm scope at commit time.

## 3. To verify before listing as clean

- `construction/overrides/scope_enforcement.py`, `scope_query.py`, `scope_report.py`,
  `report_guard.py`, `translation.py`, `switch_theme*.py`, bilingual/sanitizer services show
  no worktree diff — confirm intentional (untouched by this program) vs missed change. Checked
  2026-10-14: only `boq_permissions.py` differs among overrides; the rest match HEAD by design.

## 4. Gates outstanding (F38 stays open)

F31/F32 site qualification (DBA blocker) · matching F35 CI execution (pins prepared,
unlabeled-until-run) · F27 bridge authorization · delivery-route approval (F28-D003) ·
F29 full guides · owner UI acceptance block (F43/F44) · F45 decision.
