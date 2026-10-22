# Foundation gap ledger — single candidate reconciliation

**F03 follow-up:** [Feature/route source inventory](construction_foundation_feature_route_inventory_2026-10-12.md) maps source routes and identifies additional coverage. It also corrects UAT-D005: local `Document.get` expression returns None and iteration raises TypeError, rather than proving empty items. Actual UI/bridge reproductions remain pending; source-only interpretation is not a deployed pass.

**Created:** 12 October 2026 (F01 execution, source-level reconciliation only)
**Program:** [Foundation remediation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [Work register](construction_foundation_work_register_2026-10-12.md)
**Status of this document:** F01 deliverable 1 of 3 (ledger; reproductions recorded in the [defect register](owner_ui_defect_register_2026-10-12.md); kickoff naming still pending).

## 1. Candidate identity (recorded, not assumed)

| Field | Value |
|---|---|
| Checkout | `/home/mohamed/frappe-bench/apps/construction` |
| Branch | `develop` (in sync with `origin/develop`: 0 ahead / 0 behind at recording time) |
| HEAD | `c9e6803c5ac63073aeb0b166c779844d29051d8d` |
| HEAD subject | `ci: add cost-analysis modules and quality linters to smoke tier` (2026-10-07) |
| Working tree | `SESSION_MEMORY.md` modified; `docs/ai/work-items/next feature 07102026/` untracked (planning documents). No application source modified. |
| Local checks at recording time | `schema_drift_checker.py`: 21 schema-owning DocTypes + 1 override, facts match. `ai_context_check.py`: 11 passed / 0 failed. |
| Environment / site / assets | **Not yet identified for this program** — F02 work |
| Names (lead / reviewer / operator / QS-Finance) | **Awaiting kickoff** |

The October documents describe different evidence moments. This ledger replaces blanket open/closed labels with the residual action per gate. **Historical green CI, past "SATISFIED" headings and byte-comparison results describe their own candidates and conditions; none is a pass for this candidate.**

## 2. Evidence moments reconciled

| Evidence | Date | Candidate it describes | Standing in this ledger |
|---|---|---|---|
| Dated G01–G16 assessment (`docs/ai/CUSTOMER_RELEASE_GAPS_2026-10-04.md`) | 2026-10-04 | `48f370f6a50689258d1d400c27886618186387f7` (working tree, modified) | Original problem definitions; all listed open at that moment |
| Correction ledger (`customer-release-gap-fixes/STATUS.md`) | 2026-10-05/06 | `f63d739…` / `a6bc51c…` (release-candidate worktree; private CI Run 11) | Records fixes landed and gates G10/G12/G14/G15/G16 marked satisfied for that candidate |
| Candidate summary (`CUSTOMER_RELEASE_CANDIDATE_SUMMARY.md`) | 2026-10-06 | release candidate | Historical release-summary assertions; not a fresh audit |
| Consultant line-by-line reconciliation | 2026-10-12 | `c9e6803c…` (this HEAD), 7 files byte-compared to tag `v6.8.0-rc1` (`79bfdcc…`) | Reconciled positions per gate; weakest-evidence items qualified |
| **This ledger** | 2026-10-12 | `c9e6803c…` | Source-level spot checks only (below); no suite, site or UI execution |

## 3. Reconciliation method and its limit

For each gate this ledger records: the original requirement, the implementation evidence claimed by later documents, and what remains candidate-bound. Where marked **source-verified today**, the named file at HEAD was inspected in this session and the described construct is present. That establishes code presence, **not** behaviour: no business suite, HTTP, browser, concurrency, migration or recovery run was executed for this ledger. Every gate still requires its mapped F-package qualification before closure.

## 4. Gate-by-gate reconciled position

| Gate | Original requirement (2026-10-04) | Implementation evidence claimed | Verified today at `c9e6803c` | Residual action → packages |
|---|---|---|---|---|
| G01 | Direct BOQ Item deletion leaves stale totals | Fixed 2026-10-05 ("commercial integrity G01, G02, G04"); named v16 copy zero rollup discrepancies | **Source-verified:** `boq_item.py` has `on_trash()` and `after_delete()` rollup paths | F05 qualifies deletion/last-item/cascade across UI/import/export; F10 read-only legacy audit; F31 upgrade replay; F35/F44 regressions + owner UI-10–14 |
| G02 | Approved quantity revision mutable | Fixed 2026-10-05; 219 old revisions preserved | **Source-verified:** `validate_approval_integrity()` refuses approved-field changes ("Create a new revision for a correction"); deletion guard present | F06 proves document/HTTP/import bypasses fail; F11 ordinary-role matrix; F44 UI-29–36 |
| G03 | Cancelling sole approved analysis leaves cost in place | Prior-analysis/manual-snapshot restoration exists with owner rule recorded | **Source-verified:** `on_cancel()` + `restore_prior_analysis_if_any()` + validated `manual_cost_snapshot` restore path | F07 qualifies sole/prior/zero/superseded cancellation on candidate; legacy provenance cases in F10; owner policy already recorded — do not reopen (consultant C1 rejected) |
| G04 | Zero factor inconsistent (Python `or 1.0` vs SQL `COALESCE`) | Positive-factor rule implemented 2026-10-05; browser zero refusal | **Source-verified:** `validate_input_guards()` applies `positive_factor()`; DocType description states "must be greater than zero; missing defaults to 1" | F04 fixes worked examples; F05/F14 verify consumers (API/import accept nothing UI rejects); F31 legacy factor inventory; F44 UI-16–23 |
| G05 | Shared header total update protocol unproven (race model 310 vs 330) | Current-read/NOWAIT guards + 12 real-two-connection tests recorded | **File present:** `boq_transactions.py`, `test_boq_transactions.py`; suite results are historical for the earlier candidate | F08 re-runs against this candidate on the selected stack; precise description: not all 12 cases are simultaneous threaded approvals; F37 stack-level contention |
| G06 | Margin applied at two levels; define pricing | Additive direct-cost pricing owner-recorded and implemented | **Rules document:** `FINANCIAL_RULES.md` retained (positive factor; missing→1; additive on direct cost; recoverable manual/prior cost) | F04 independent worked examples; F07 no double margin; F19/F40 report/guide agreement; F44 UI-16–23 |
| G07 | CI did not run Python business tests | Tiered `ci.yml` with "Run Python Business Regression Tests"; private CI Run 11 green (17 modules / 234 tests / 35 JS) | **Config present:** business-test step in `ci.yml` at HEAD; **run identity is historical**, none on this candidate | F35 candidate-bound runs in authorized private CI; record skips/flakes; F45 final mapping |
| G08 | Scope/authorization needs customer-role proof | Non-admin native BOQ/HTTP boundaries; 11 native HTTP checks recorded | Controls cited (`scope_query.py`, report guard, `boq_api` access helper); **not re-executed** | F11 full role × action × route matrix; F12 Option B + report dispositions; F15 privileged actions; F44 ordinary identities |
| G09 | Cost database workbook path lacked equivalent bounds | Shared prescan + byte/sheet/row/traversal limits recorded | **Source-verified:** `cost_database_service.py` reuses `BOQImportService._prescan_xlsx` and defines its own limits (2,000 imported / 50,000 traversed rows) | F14 just-over-limit and malformed fixtures through transport; F37 worker/queue behaviour; **do not raise the 2,000-row bound to meet the old 5,000-row proposal** |
| G10 | Dependency audit/version evidence incomplete | Later ledger marks satisfied (Session 3A, develop): v16.36.1 alignment, compensating guards, 33/33 tests | **Not re-verified today**; evidence spans candidates/runtimes | F13 inventories installed stack on the F02 target, rebuilds exact candidate, reviews current advisories; F25 runtime policy |
| G11 | Capacity unproven | Bounded probes: 20,025-pair fixture; 2,000-row XLSX 659.9 ms; 15 concurrent reads (Administrator) | Recorded in `CAPACITY_PROTOCOL.md`; measured as Administrator, not customer authoring | F37 agreed Egypt-SME workload, ordinary-role mixed reads/writes, p50/p95; no extrapolated SLA |
| G12 | Fresh install / legacy upgrade candidate evidence | Named v16 copy: two migrations compared; rehearsal evidence | Recorded (restore drill, repeated migration); bound to earlier candidate | F31 clean install + representative upgrade on F02 target; idempotent replay; F32 recovery rehearsal; F34 onboarding |
| G13 | Global overrides / version claims | Exact Frappe 16.18.1 / ERPNext 16.18.3 source qualification recorded | Override register obligation acknowledged; **no v15 claim** exists | F24 hook/override register + compatibility checks on declared versions; F25 runtime policy; F26 deprecated-path inventory |
| G14 | Backend vs actual UI wiring divergence | Later summary: 10/10 bilingual commercial UAT, 4 print formats, 7 reports | **Two wiring defects found today** (below) — the divergence class is live | F16 (K-01) and F27 (MCP); F03 full route inventory; F17–F23 complete existing-service UIs; F44 owner journeys |
| G15 | Operations/recovery delivery plan | Restore rehearsal 8.62 s (backup validation) / 117.892 s (restored-site drill) recorded separately | **Never generalize either number**; ownership pending | F02/F32 rehearsal on target; F33 named support, RPO/RTO proposal, monitoring; F41 runbooks |
| G16 | Readiness claims not tied to one candidate | Manifest governance 40/423 zero drift recorded for release candidate | This ledger + F45 bundle are the new binding mechanism | F01→F45 chain; F38 daily defect loop; F45 final manifest with named reviewer |

## 5. Defects found in this reconciliation (source-level, this candidate)

| ID | Finding | Evidence | Treatment |
|---|---|---|---|
| K-01 / UAT-D001 | BOQ Header "Import Excel" Desk route calls `import_boq_excel` without `dry_run`; API defaults to preview (`dry_run=1`); handler shows "Import successful" on preview success with no records committed | `construction/construction/doctype/boq_header/boq_header.js:461–478`; `construction/api/boq_api.py:232–245`; `boq_import_service.py:113–135, 226–239` (preview returns `success: not errors`, `dry_run: True`) | **Confirmed at source; deployed-UI reproduction still owed in F16.** Reproduction record: defect register §UAT-D001 |
| New / UAT-D005 | MCP bridge `get_boq_header` builds its response from a non-existent `items` child field; BOQ Header JSON has no child tables and BOQ Item is a separate document with a `boq_header` Link. **F03 correction (supersedes F01 wording):** the exact symptom is not "empty items" — Frappe's `BaseDocument.get(key, [])` treats the second argument as filters, so the local expression returns `None` and iteration raises `TypeError` in the isolated probe. Deployed bridge outcome: Not Run | `erpnext-mcp-server/server.py:157–184`; BOQ Header schema fields listed (no Table fields); BOQ Item has `boq_header` Link field; local `frappe/model/base_document.py:327` reference in F03 inventory §10 | **Schema mismatch confirmed at source; runtime symptom to reproduce in F27.** Fix path: scoped, bounded `get_all("BOQ Item", filters={"boq_header": name})`; F27. Related observation: `tool_get_boq_structure_tree` (`server.py:187–197`) runs `get_all` with `guard_doctype` allowlist only — no per-user authorization/scope filter |

## 6. Standing ledger rules

1. A gate closes only when the mapped package produces candidate-bound evidence; "code exists", "historical CI green" and "owner accepted" remain three distinct facts.
2. Any newly discovered gap receives an issue ID and a parent F-package; it is never closed by an undocumented workaround.
3. Historical fixes stay credited at their own candidate; re-verification cost is budgeted, not assumed free.
4. The 2,000-row cost-import bound, the additive pricing rule, the prior/manual restoration policy and the progress-billing/Direct Labor Designation consumers are **retained**, not reopened, by this reconciliation.

## 7. Verification performed for this ledger

- git identity recorded (HEAD, sync state, working-tree changes); no application file modified by this session.
- `scripts/schema_drift_checker.py` and `scripts/ai_context_check.py` executed: both pass.
- Source inspection of: `boq_item.py`, `boq_quantity_revision.py`, `boq_cost_analysis.py`, `boq_import_service.py` (preview/commit paths and limits), `cost_database_service.py` bounds, `boq_api.py`, `boq_header.js` import dialog, `boq_item.json`/`boq_header.json` schemas, `erpnext-mcp-server/server.py`.
- SHA-256 recorded for the seven inspected files (reproduction record in the defect register).
- **Not performed:** any test suite, site query, migration, deployment, commit or push.
