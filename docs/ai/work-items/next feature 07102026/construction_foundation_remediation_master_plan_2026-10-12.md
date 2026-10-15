# Construction ERP — Foundation remediation and enhancement master plan

**For:** Mohamed / General Manager  
**Perspective:** Head of Engineering  
**Date:** 12 October 2026  
**Status:** Planning complete; remediation and acceptance execution not started by this document  
**Source reviewed:** `develop`, `c9e6803c5ac63073aeb0b166c779844d29051d8d`  
**Market:** Egyptian small and mid-sized contractors first, then separately qualified Gulf expansion  
**Classification:** Confidential — internal

## 1. Objective and management decision

**Establish a reliable, usable and maintainable foundation before implementing new business modules.** This requires closing existing defects and evidence gaps, completing essential usability of existing services, improving engineering and operating practices, and then passing Mohamed's personal UI acceptance.

The previous [69-group UI plan](existing_features_owner_ui_acceptance_plan_2026-10-12.md) remains useful but is only the acceptance workstream. This master plan is the controlling plan for **all identified foundation work**, including remediation and enhancements that must precede new modules. It replaces the narrower “prepare tests, then decide” sequence. It does not claim that every unknown defect is already identified: deployed inventory and continuing triage must add newly discovered work to the register.

The immediate program is **45 work packages across nine workstreams**. Each has scope, priority, accountable role, dependencies and measurable completion evidence. Use the [foundation work register](construction_foundation_work_register_2026-10-12.md) for assignment and status; use the [UI results workbook](owner_ui_test_results_2026-10-12.md) and [defect register](owner_ui_defect_register_2026-10-12.md) for execution evidence.

### Scope boundary

**Included before foundation sign-off:** existing commercial correctness, access control, imports/exports, supported reports and bilingual UI, completion of current service workflows through usable UI, existing transaction integrations, legacy-data safety, dependencies, compatible upgrades, bounded performance, repeatable testing, role workspaces, assisted setup, documentation, packaging hygiene and operational rehearsal.

**Later business modules:** Payment Certificates, automated retention/advance recovery, subcontract commercial lifecycle, new committed/actual/earned-value/forecast engines, plant lifecycle, Site Diary/offline operation, new contract-currency policy and country connectors. They remain visible in section 6 and require separate scope after the foundation gate. A genuine defect in an existing native ERPNext process is still fixed now.

Completing a UI for an already implemented import/report service is an **existing-capability enhancement in this revised plan**. The earlier UI plan's backend-only classification describes today's evidence; it is not a permanent exclusion. F18/F19 deliberately close this usability gap. Avoid expanding those tasks into new financial definitions or speculative dashboards.

No implementation, migration, remote publication, license change or deployment is performed by issuing this plan. During later execution, routine engineering decisions belong to the engineering lead; only missing business rules or actions outside existing authority require an owner decision.

## 2. What is known and what must be verified

| Category | Current planning position | Treatment |
|---|---|---|
| Implemented controls | Positive factors, additive pricing, approval/manual restoration, immutable history, transaction guards, workbook limits, Option B switch and internal rollup audit exist | Retain and qualify; fix demonstrated gaps rather than rebuild from outdated assertions |
| Likely wiring defect | BOQ Import Excel omits dry_run while API defaults to preview and UI can say “Import successful” | F16 reproduces against deployed candidate and repairs the promised workflow if confirmed |
| Tooling schema mismatch | Bridge get_boq_header iterates header `items`, while BOQ Items are separate documents | F27 repairs with scoped, bounded lookup and tests; exact runtime symptom still to reproduce |
| Documentation defects | Template-like README, stale cost-projection and role expectations, mixed dated readiness statements | F01/F29/F39–41 create coherent current guidance |
| Required existing-capability enhancements | Cost-database service UI, existing cost-report views, restricted integrity view, role shortcuts and assisted setup | Implement narrowly in F18/F19/F21/F34 and add owner acceptance cases |
| Remaining qualification | Exact deployed permissions, security/runtime, capacity, legacy data, recovery and full UI evidence | Candidate-bound tasks, not inferred failures or automatic passes |
| Optional architecture proposals | Broad repo split, wholesale wildcard replacement, deprecated-source deletion, universal asset rewrite | Evaluate narrowly; no automatic mass change or prerequisite without demonstrated need |

The dated G01–G16 assessment, later correction ledger and consultant review describe different evidence moments. F01 reconciles these; neither “everything open” nor “everything ready” is acceptable. A task may close through existing equivalent evidence only after the exact source/configuration and claimed scope are checked. A changed consumer or environment requires the relevant new verification.

## 3. Priorities, ownership and completion rules

- **P0:** correctness, authorization, data safety or acceptance blocker. Stabilize before exposing the affected path to ordinary UAT; all must close before foundation sign-off.
- **P1:** required foundation enhancement or readiness work. Complete before sign-off. Reclassification needs an explicit reason and owner decision, not silent deferral.
- **Later:** new domain capability or optional large redesign listed in section 6. Planning/discovery may inform scope now; implementation starts after the foundation decision.

Roles are responsibilities, not a claim that a staffed department exists. Name actual people at kickoff. Mohamed remains product/domain and final UI acceptance owner; engineering owns implementation, technical review and evidence; Finance/QS reviews accounting/commercial examples; an operator owns environment/recovery. A solo engineer may hold several roles, but self-review must not be called independent human review. Seek proportionate qualified review for consequential finance/security/data changes.

**Every work package starts Proposed.** Completion requires a defined deliverable, reviewed changes if any, appropriate tests, exact candidate/configuration, evidence link and named reviewer. Relevant UI changes also require Mohamed's acceptance. “Code exists,” “unit tests passed,” and “owner accepted the workflow” are distinct facts.

Dependencies below are prerequisites for completion; discovery and document drafts can proceed earlier. F38 (defects) operates continuously once testing starts and is not postponed until its final prerequisite list closes. F35 can set up CI early, then qualifies the final candidate.

## 4. Work breakdown and acceptance criteria

### A. Establish one reliable baseline

#### F01 — Kickoff assignments, candidate and gap reconciliation

**Priority:** P0 · **Accountable:** Mohamed for appointments; named engineering lead for reconciliation · **Dependencies:** None  
**Starting evidence:** Conflicting dated release summaries.

**Work:** In execution week 1, Mohamed names the accountable engineering lead, Finance/QS reviewer and operator; record accepted responsibilities and the intended UAT site/URL in the register. F02 validates and prepares that named environment. The engineering lead reconciles G01–G16 against one named Construction/Frappe/ERPNext candidate, actual runtime and retained evidence. Record source hashes and uncommitted changes; replace blanket open/closed labels with residual work.

**Execution record (2026-10-12, source-level only):** [Gap ledger](construction_foundation_gap_ledger_2026-10-12.md) produced at `c9e6803c…`; K-01 and new UAT-D005 reproduced at source with records in the [defect register](owner_ui_defect_register_2026-10-12.md). Kickoff names/UAT site remain the open F01 blocker.

**Done when:** The register contains actual agreed names for all three responsibilities and an identified UAT site/URL, with no unowned “To assign” field for these kickoff items. One gap ledger names every gate, implementation evidence, remaining action, candidate and responsible person. Historical green CI is identified as historical. If a person/site cannot be confirmed in week 1, record the blocker, decision owner and next decision date rather than inventing an assignment or silently delaying the program.

#### F02 — Isolated environment and baseline recovery

**Priority:** P0 · **Accountable:** Engineering + operator · **Dependencies:** F01  
**Starting evidence:** Environment not identified for this program.

**Work:** Select isolated development/UAT target; inventory all sites sharing code; prepare baseline backup, restore target and sandboxed outbound integrations. Record actual site/schema/assets before work.

**Done when:** UAT manifest and tested restoration path exist; no shared-site upgrade occurs implicitly; ordinary users can log in safely.

#### F03 — Installed feature and route inventory

**Priority:** P0 · **Accountable:** Engineering + Mohamed · **Dependencies:** F01  
**Starting evidence:** Coverage baseline exists; installed inventory pending.

**Work:** Inventory all active DocTypes, hooks, customizations, pages, APIs, reports, prints, import/export paths and feature flags. Map 21 schemas, Journal Entry override and eight transaction integrations; extend for installed customizations.

**Done when:** Every active capability has a route, owner, permission expectation, UI/service classification and test ID; required existing workflows cannot be excluded merely because broken.

#### F04 — Financial fixtures and ordinary roles

**Priority:** P0 · **Accountable:** Engineering + Finance/QS · **Dependencies:** F02,F03  
**Starting evidence:** Financial rules confirmed; reference pack to prepare.

**Work:** Produce versioned synthetic/reference fixtures, ordinary-role matrix and independent financial worksheets. Retain current positive-factor/additive-pricing/manual-restoration rules; clarify only genuinely unresolved business cases.

**Done when:** Worked examples cover direct 100 → sell 120/125, factor 0.5, zero manual restoration, revisions and finance postings; reviewers and fixture IDs recorded.

### B. Financial integrity and commercial history

#### F05 — BOQ totals, deletion and factors

**Priority:** P0 · **Accountable:** Backend engineer · **Dependencies:** F04  
**Starting evidence:** G01/G04 corrections exist; qualify consumers/data.

**Work:** Verify deletion after commit, last-item/cascade deletion, item/structure/header totals, factor >0, missing-factor defaults and failure rollback. Correct defects found across UI/import/export/read paths.

**Done when:** Affected regressions and owner UI-10–14 pass; independent sums equal stored and exported totals; failed deletion leaves rows and totals unchanged.

#### F06 — Variation and approval-history protection

**Priority:** P0 · **Accountable:** Backend engineer + QS · **Dependencies:** F04  
**Starting evidence:** G02 protections exist.

**Work:** Verify locked/frozen basis, approved quantity revision immutability, VO actors, PDF linkage, rate justification and repeated-save behavior. Fix any bypass in document/HTTP/import paths.

**Done when:** UI-29–36 and denied/server paths pass; approved history cannot be rewritten, duplicated or detached from current projection.

#### F07 — Cost projection and cancellation

**Priority:** P0 · **Accountable:** Backend engineer + Finance · **Dependencies:** F04  
**Starting evidence:** G03/G06 policy and implementation exist.

**Work:** Qualify direct-cost versus selling-rate projection, additive percentages, batch normalization, wastage and sole/prior/zero/superseded cancellation. Correct remaining consumers; retain contract price independently.

**Done when:** UI-16–23 pass with independent values; manual provenance is restored correctly; no margin is applied twice and cancelled history cannot become a silent active basis.

#### F08 — Concurrency and atomicity

**Priority:** P0 · **Accountable:** Backend engineer + QA · **Dependencies:** F05,F06,F07  
**Starting evidence:** Existing transaction protocol and 12 real-connection tests.

**Work:** Review locking with native Frappe lifecycle; exercise concurrent approval/cancel/item update/import/rollback through selected HTTP/worker/database stack. Extend existing tests only where invariants lack evidence.

**Done when:** No lost total, duplicate active approval or partial commit; contention, retry and rollback outcomes documented. Do not replace with a second naive lock protocol.

#### F09 — Stage planning and correction paths

**Priority:** P0 · **Accountable:** Backend engineer + QS · **Dependencies:** F04  
**Starting evidence:** Stage controls exist; post-VO usability needs proof.

**Work:** Validate planned distribution, measured/certified bounds, certifier role and immutable certified records. Resolve blocked legitimate correction/reallocation paths after quantity changes without rewriting certified evidence.

**Done when:** UI-24–28 pass; supported adjustment procedure is documented and usable. If a new domain rule is required, QS/Mohamed approves its worked example before implementation.

#### F10 — Legacy data and integrity reconciliation

**Priority:** P0 · **Accountable:** Engineering + data steward · **Dependencies:** F05,F06,F07  
**Starting evidence:** Internal rollup audit and legacy-review controls exist.

**Work:** Run read-only integrity inventory on authorized copied data: WBS hierarchy, orphan/mismatched links, factors, approval chains, legacy basis and aggregates. Prepare reviewed, reversible corrections with before/after evidence.

**Done when:** No unexplained discrepancy in in-scope operational fixtures; historical/test exclusions are explicit and preserved. No guessed manual cost, blanket SQL repair or deletion of history.

### C. Permissions, dependencies and bounded execution

#### F11 — Authorization across all routes

**Priority:** P0 · **Accountable:** Security/backend engineer · **Dependencies:** F03,F04  
**Starting evidence:** G08 partial route evidence exists.

**Work:** Complete ordinary-user role × action × company/project × route matrix, including document URLs, link queries, share rules, reports, private attachments, imports and exports. Correct server authorization gaps.

**Done when:** Allowed workflows succeed; denied paths reveal no protected data and cannot mutate it; UI hiding alone never closes the task.

#### F12 — Scope, report controls and Option B

**Priority:** P0 · **Accountable:** Framework engineer · **Dependencies:** F11  
**Starting evidence:** Scope registry, query guards and Option B toggle exist.

**Work:** Verify selected scope versus authorization, scope drift, exclusions, descendant cost centers and Option B enabled/disabled behavior. Measure broader scope-query coverage before any wildcard change.

**Done when:** No cross-company/report bypass; all 15 protected reports have disposition; switch states tested; no duplicate toggle and no unmeasured replacement with the transaction-only registry.

#### F13 — Dependency and security remediation

**Priority:** P0 · **Accountable:** Security + release engineer · **Dependencies:** F01,F02  
**Starting evidence:** G10 closure notes span different runtimes.

**Work:** Inventory actual installed dependencies, rebuild exact candidate, review current advisories against that runtime, verify reachable mitigations and perform compatible upgrades where required. Recheck dependency metadata and affected functionality.

**Done when:** Runtime manifest and supported-version matrix agree; applicable high-impact unresolved findings are remediated or technically contained with evidence. Installation success or historical audit headings are insufficient.

#### F14 — Bounded imports, exports and PDFs

**Priority:** P0 · **Accountable:** Backend/security engineer · **Dependencies:** F02,F03  
**Starting evidence:** G09 file/parser bounds already implemented.

**Work:** Verify authentication, request methods, ownership, file type, archive/XML, numeric, row/sheet/byte/time limits and rate/queue controls across imports/exports/PDFs. Add missing controls only after path inventory.

**Done when:** Safe just-over-limit and malformed fixtures fail early without writes; admitted workloads complete; errors explain limits. Existing 2,000-row cost-import bound is not silently raised to meet an old 5,000-row proposal.

#### F15 — Secrets, privileged actions and audit

**Priority:** P1 · **Accountable:** Engineering + operator · **Dependencies:** F11,F13  
**Starting evidence:** Operational safeguards require target proof.

**Work:** Verify secrets/config separation, safe logs, session handling, least-privilege administration and audit events for approval, export, settings and privileged operations. Check theme preference writes are narrowly authorized.

**Done when:** No credentials in repository/outputs; critical changes attributable; logs avoid sensitive payloads and have access/retention policy. Privileged roles do not substitute for ordinary-role proof.

### D. Finish usability of existing functionality

#### F16 — Repair BOQ import completion

**Priority:** P0 · **Accountable:** UI/backend engineer · **Dependencies:** F03,F04,F14  
**Starting evidence:** K-01 source-level preview/success mismatch.

**Work:** Reproduce actual BOQ Import Excel route. Repair advertised preview/commit flow, status messaging, error display and saved-record refresh; handle cancellation and uncertain retry without duplicates.

**Done when:** User can preview, understand errors, explicitly commit and reopen correct rows; no success message for unsaved preview. UI-50/51/53 pass with persisted counts and traceability.

#### F17 — Import review, error files and traceability

**Priority:** P1 · **Accountable:** UI/backend engineer · **Dependencies:** F14,F16  
**Starting evidence:** Import parser features exist; interface coverage incomplete.

**Work:** Complete review/resolution of supported structured, semi-structured/flat and multi-sheet inputs where the service supports them; expose downloadable error review and source-row traceability. Document supported format limits.

**Done when:** Each offered mode has UI fixture and outcome; ambiguous rows cannot commit silently; unsupported formats are clearly refused. New parsing algorithms are separate scope, not assumed present.

#### F18 — Cost database and repricing UI

**Priority:** P1 · **Accountable:** UI/backend engineer + estimator · **Dependencies:** F03,F07,F14  
**Starting evidence:** Cost database import/reprice services exist; customer UI unproven.

**Work:** Provide a minimal permission-controlled Desk workflow for existing template download, dry-run import, validation, commit/result inspection and draft-only bulk repricing. Reuse the services and keep submitted templates/analyses protected.

**Done when:** An authorized user completes the existing service workflow without API/console commands; retry/source counts, Arabic headers, company/date/UOM/currency and unchanged approvals are demonstrated. Default part of foundation scope; retain no hidden backend-only claim.

#### F19 — Existing reports and integrity visibility

**Priority:** P1 · **Accountable:** Reports engineer + Finance · **Dependencies:** F03,F07,F11  
**Starting evidence:** Five estimation services and internal audit exist.

**Work:** Expose usable read-only views for existing analysis summary, cost vs contract, resource requirements, price history and missing analyses; provide an appropriately restricted integrity-exception view/export using the audit service.

**Done when:** Saved UI filters, role/scope controls, pagination/limits and export match service results; resource requirements explicitly use contract quantity. Audit access remains administrator-controlled unless a narrower reviewed role is approved.

#### F20 — Native transaction handoff improvements

**Priority:** P1 · **Accountable:** UI/backend engineer · **Dependencies:** F06,F07,F09,F16  
**Starting evidence:** Eight transaction integrations exist.

**Work:** Repair missing/misleading defaults, cascade messages, stale dependent fields and lost mapping in native MR/PO/PR/PI/SI/SE/Timesheet/JE handoffs; give users clear correction steps.

**Done when:** All eight common row matrices and valid native lifecycles pass; attribution survives reopen/downstream mapping; used progress-billing flag and Direct Labor Designations remain active.

#### F21 — Role workspaces

**Priority:** P1 · **Accountable:** UI engineer + product owner · **Dependencies:** F03,F11,F20  
**Starting evidence:** Role-workspace recommendation accepted.

**Work:** Configure concise role workspaces using existing forms/reports: site work, estimating/commercial, procurement/stores, finance and PM/owner. Add relevant shortcuts and help, respecting installed permissions.

**Done when:** Each role reaches its routine actions without admin privileges or hidden essential menus; quick-start tasks can be completed independently. No new business engine is introduced.

**Status 2026-10-14 — engineering verified, owner UI acceptance pending:** 5 role workspaces with role rows; per-persona reach 7/7 exact; app-shipped Sidebar fixture replaced the site-made row so navigation ships from the repo. One scope leak found and fixed (F21-D002, price history), one open owner decision (F21-D001, F19 Company-read gating), one CI environment gap (F21-D003). Evidence: [F21 evidence](construction_foundation_f21_evidence_2026-10-14.md).

#### F22 — Arabic and everyday UI usability

**Priority:** P1 · **Accountable:** UI engineer + Arabic reviewer · **Dependencies:** F16,F18,F19,F21  
**Starting evidence:** Localization/native UI implemented; route qualification needed.

**Work:** Correct Arabic/English terminology, RTL, search, printable reports and clipped Save/Submit controls; complete empty/loading/error states, keyboard navigation and intended mobile-browser usability for existing forms.

**Done when:** Owner report/print/theme/layout cases pass; amounts agree across viewer/native/export; no stale values after errors. Photo capture/offline/site diary additions remain later features.

**Status 2026-10-14 — engineering verified, owner acceptance pending:** Arabic/RTL verified with two ordinary personas (PM 19/19, buyer 8/8) across navigation, work areas, workspace cards, list tables, mixed-direction cells, translated errors, the K-01 dialog, the export menu and the print-settings dialog. Six defects fixed (D001–D006 in the register): an empty framework translation that made a validation error half-English, untranslated sidebar chrome, a K-01 dialog whose strings were hardcoded rather than `__()`, export/print column labels hardcoded English, sidebar/workspace labels with no translation entries at all, and a 403 dialog on every BOQ Header form for personas without Project read. Translation coverage is now a regression test (187 strings scanned, 0 missing Arabic). Evidence: [F22 evidence](construction_foundation_f22_evidence_2026-10-14.md).

#### F23 — VFC and theme stabilization

**Priority:** P1 · **Accountable:** Framework/UI engineer · **Dependencies:** F03,F22  
**Starting evidence:** Native/VFC architecture established.

**Work:** Stabilize personal/role/default profile selection, own-profile reset, supported presets, dependency-hidden/unknown fields and native fallback. Correct stale applicability comments and theme preference behavior.

**Status 2026-10-14 — engineering verified, owner acceptance pending:** 18/18 browser checks across two ordinary personas (f04-pm Arabic/RTL 13/13, f04-engineer English/LTR 5/5) covering light/dark theme application and persistence, VFC density persistence and reset, field-visibility persistence through the documented flow, dependent fields and a permission-controlled field (`certified_qty`: PM editable, engineer disabled). One open usability finding, F23-D002: visibility changes apply live but persist only via "Apply & Save" with no unsaved-changes indication — the panel's two halves have different durability rules. Evidence: [F23 evidence](construction_foundation_f23_evidence_2026-10-14.md).

### E. Maintainability, tooling and delivery hygiene

#### F24 — Framework override compatibility

**Priority:** P1 · **Accountable:** Framework maintainer · **Dependencies:** F01,F03  
**Starting evidence:** Global overrides carry compatibility obligations.

**Work:** Refresh hook/override register with purpose, upstream target/signature, owner, fallback and tests. Add focused compatibility checks for supported vendor bumps, including search, reports, translation/account governance and theme controls.

**Done when:** Every shipped override is accounted for and tested on declared versions; upstream mismatch fails clearly. No blanket promise of v15/v16 support.

**Status 2026-10-14 — engineering verified on the working tree, owner acceptance pending:** all six whitelisted overrides checked signature-compatible with the installed frappe 16.51.1 / erpnext 16.50.0 (three exact, three compatible supersets); Translation subclass chains; report wrapper healthy; permission/query/doc-event hooks match their fail-closed contracts; F19 adapters confirmed as a bounded RPC surface; Sidebar fixture app-backed with the site row matching. Evidence: [F24 evidence](construction_foundation_f24_evidence_2026-10-14.md). Carried: per-patch JS target list (F24-D001); security-audit teardown hygiene (F24-D002).

#### F25 — Runtime and asset consistency

**Priority:** P1 · **Accountable:** Release engineer · **Dependencies:** F01,F13,F24  
**Starting evidence:** Runtime and conservative syntax constraints differ.

**Work:** Document intentional Python runtime/syntax policy, align packaging/install/CI documentation and reproduce assets. Audit registered CSS/JS, duplicates and stale cache behavior; retain established cache strategy unless migration is justified.

**Done when:** Clean build and browser assets match candidate; runtime constraints consistent; conservative owner syntax rule preserved unless explicitly revised. Bundle changes include asset/hash/cache rollback evidence.

**Status 2026-10-14 — engineering verified, owner acceptance pending:** JS compat targets inventoried with per-patch regression checks at installed rev `2871914` (four live, two guarded-dead — the vendor-bump prerequisite, closing F24-D001); `test_security_audit_remediation` teardown repaired without touching product guards (24/24, closing F24-D002); 5/5 assets load 200 with expected `?v=` after clear-cache; hooks live; source and served bytes identical; the five dependency ranges align with installed frappe 16.51.1; bump-then-clear-cache procedure recorded. Evidence: [F25 evidence](construction_foundation_f25_evidence_2026-10-14.md).

#### F26 — Deprecated paths and scaffolds

**Priority:** P1 · **Accountable:** Engineering lead · **Dependencies:** F03,F25  
**Starting evidence:** Retained deprecated React and reference scaffolds.

**Work:** Inventory consumers of deprecated APIs/components and CostItem/PlantResource data. Keep inactive code restricted and unadvertised; isolate dead assets only after references/tests prove safe. Record deprecation path.

**Done when:** No unsupported reachable mutation or confusing workspace entry; no removal of active Direct Labor Designation/progress flag; no destructive schema deletion as housekeeping. ADR-008 remains respected.

**Status 2026-10-14 — engineering verified (classification, no deletions), owner acceptance pending:** CostItem/PlantResource deliberately retained (empty tables, patch contract preserved); React 8 JSX + `modern_form_api.py` deliberately retained and unadvertised (unloaded / System-Manager-only); two dead compat patches, superseded `switch_theme.py` and two `.bak` fixtures queued for F30; Direct Labor Designation and approved history preserved. Evidence: [F26 evidence](construction_foundation_f26_evidence_2026-10-14.md).

#### F27 — Repair BOQ retrieval tooling

**Priority:** P1 · **Accountable:** Tooling engineer · **Dependencies:** F03,F11  
**Starting evidence:** Original E11 confirmed as source mismatch.

**Work:** Repair get_boq_header bridge to query separately stored BOQ Items, preserve schema and caller authorization, handle no items/missing/forbidden headers and bound results. Review adjacent unfiltered tree helper access.

**Done when:** Bridge returns correct items for allowed header and none for forbidden scope, with meaningful tests. Reproduce exact runtime symptom rather than assume the old report’s exception text.

#### F28 — Delivery artifact hygiene

**Priority:** P1 · **Accountable:** Release engineer · **Dependencies:** F03,F25  
**Starting evidence:** Repository checkout differs from distribution artifact.

**Work:** Inspect actual wheel/sdist, private deployment checkout/export and installation paths for private evidence, devtools, secrets and fixtures. Tighten safe packaging/export exclusions; verify essential hooks/templates/migrations remain included.

**Done when:** Artifact inventory contains required app only plus intentional dependencies/docs; confidential material is excluded from the chosen delivery path. Packaging exclusions do not hide files from a full Git checkout.

#### F29 — Documentation and repository organization

**Priority:** P1 · **Accountable:** Engineering lead · **Dependencies:** F03,F28  
**Starting evidence:** Repository sprawl; reference preservation required.

**Work:** Index docs by customer/operator/developer/historical evidence; consolidate duplicate status summaries and archive superseded narratives with redirects. Inventory scratch scripts/screenshots/backups/branches and their references.

**Done when:** Canonical docs and entry points clear; required AGENTS/workflow paths preserved; no branch, backup, evidence or unmerged-work deletion. Large repo split is a separately justified decision, not a prerequisite.

#### F30 — Bounded refactoring and ownership

**Priority:** P1 · **Accountable:** Engineering lead · **Dependencies:** F03,F24  
**Starting evidence:** Maintainability risks need evidence-based boundaries.

**Work:** Create ownership/service map, identify high-change/high-risk code, and perform small refactors only where required by a documented defect or testability problem. Keep orchestration/tooling changes out of financial fixes.

**Done when:** Affected code has clear contract and tests; one bounded purpose per change; no whole-app rewrite, blanket CSS !important removal or speculative framework migration.

### F. Installation, data migration and recovery

#### F31 — Clean install and representative upgrade

**Priority:** P0 · **Accountable:** Release + data engineer · **Dependencies:** F05,F06,F07,F10,F13,F25  
**Starting evidence:** G12 historical rehearsal exists.

**Work:** Prove clean install and supported upgrade on isolated representative data, including legacy approved analyses absent from some earlier copies; repeat migrations and compare before/after data/files/history.

**Done when:** Install/upgrade/replay succeed without business-data drift; unmapped legacy records held for review; supported origins and excluded test remnants documented.

#### F32 — Recovery and rollback rehearsal

**Priority:** P0 · **Accountable:** Operator + release engineer · **Dependencies:** F02,F31  
**Starting evidence:** Cutover/restore tooling already present.

**Work:** Rehearse failed-upgrade recovery of matching code, database, files, configuration and encrypted secrets on isolated target; verify financial samples and private-file access after recovery.

**Done when:** Observed restoration duration/data coverage recorded; operator can follow the runbook. Git revert alone is not counted as a data rollback.

#### F33 — Monitoring and support operation

**Priority:** P1 · **Accountable:** Operator + owner · **Dependencies:** F02,F13,F32  
**Starting evidence:** Operating profile exists; actual ownership pending.

**Work:** Implement and demonstrate staging monitoring for failed jobs, queues, disk, backups and errors; define named support/incident responsibility, maintenance process, RPO/RTO proposal and protected backup retention.

**Done when:** Alert reaches designated test channel, backup failure detected, recovery owner identified, measured objectives recorded. Production hosting purchase or live rollout remains a separate action.

#### F34 — Assisted setup and data onboarding

**Priority:** P1 · **Accountable:** Engineering + Finance · **Dependencies:** F04,F16,F31  
**Starting evidence:** Customer onboarding must become repeatable.

**Work:** Prepare guided native setup for company, fiscal year, accounts, cost centers, project, roles, resources and first BOQ; validate migration mapping and opening balances. Add lightweight checks/help where existing setup is incomplete.

**Done when:** A fresh synthetic contractor can be configured using documented UI steps without undocumented SQL; business/reference data validated. Prefer a checklist and existing setup screens before building a new wizard.

### G. Repeatable verification and realistic workload

#### F35 — Candidate-bound CI and coverage

**Priority:** P0 · **Accountable:** QA/release engineer · **Dependencies:** F01,F04  
**Starting evidence:** Business CI and historical pass exist.

**Work:** Bind module→feature→business-risk coverage to candidate; run affected regressions, full required release tier and reproducible build in authorized private CI. Record skips, flaky fixtures and exact runs.

**Done when:** Current candidate has real test outcomes, not install-only success; skipped required tests fail readiness; private destination/content authority checked before any upload.

#### F36 — Critical browser regressions

**Priority:** P1 · **Accountable:** QA/UI engineer · **Dependencies:** F16,F18,F19,F20,F23  
**Starting evidence:** Manual/bilingual evidence exists; automation coverage to extend.

**Work:** Automate a small stable set of critical browser journeys, including denied user, failed save, import persistence, costing cancellation, VO approval, native transaction handoff and Arabic output. Reuse current tooling first.

**Done when:** Automated tests detect meaningful regression and run against pinned fixtures/candidate; screenshots alone are not assertions. Owner manual acceptance remains separate.

#### F37 — Realistic workload qualification

**Priority:** P1 · **Accountable:** Performance engineer + owner · **Dependencies:** F08,F14,F20,F31  
**Starting evidence:** G11 bounded probes exist.

**Work:** Agree representative Egypt-SME workload and response expectations, then measure ordinary-role mixed reads/writes, reports, imports, PDF and queue behavior. Diagnose bottlenecks and make bounded optimizations.

**Done when:** Recorded concurrency, project/item counts, p50/p95 or equivalent samples, errors, resource/queue metrics and accepted limits; no extrapolated unlimited capacity or unsupported SLA.

#### F38 — Defect correction and retest loop

**Priority:** P0 · **Accountable:** QA + engineering lead · **Dependencies:** F05,F06,F07,F08,F09,F11,F12,F13,F14,F31,F35  
**Starting evidence:** Ongoing defects will emerge.

**Work:** Operate one linked defect register; triage daily, fix reproducible issues, test cause/denied path and repeat impacted consumers. Review final candidate diff and invalidate stale evidence selectively.

**Done when:** No open critical/high defect in scope; every fix has cause, candidate and regression; minor deferrals have owner/date and no safety/financial impact. Newly discovered gaps get a task, not an undocumented workaround.

### H. Product documentation and team continuity

#### F39 — Customer README

**Priority:** P1 · **Accountable:** Engineering + product owner · **Dependencies:** F03,F25,F28  
**Starting evidence:** README currently template-like.

**Work:** Rewrite customer README around actual capabilities, limits, supported installation/upgrade, privacy/delivery assumptions and support entry point. Correct copied counts and inappropriate readiness statements.

**Done when:** A reader understands what exists and how to obtain supported setup; no future certificate/plant/offline capability advertised as ready; license remains unchanged.

#### F40 — Bilingual task guides

**Priority:** P1 · **Accountable:** Documentation + Finance/QS · **Dependencies:** F04,F16,F18,F19,F20,F22,F34  
**Starting evidence:** K-02/K-03 stale pricing/role instructions.

**Work:** Update English/Arabic user guides, task cards and troubleshooting with actual menu labels, worked examples, role boundaries, imports, pricing/cancellation and correction flows. Separate customer guides from engineer APIs.

**Done when:** Mohamed can follow guides unaided; direct-cost projection and effective-role matrix correct. Print/export formats are optional deliverables only if needed; canonical Markdown remains maintained.

#### F41 — Developer and operator handover

**Priority:** P1 · **Accountable:** Engineering + operator · **Dependencies:** F24,F29,F31,F32,F33  
**Starting evidence:** Onboarding/runbooks exist but need reconciliation.

**Work:** Refresh developer onboarding, service/hook map, dependency policy, incident/update/restore playbook and handover checklist. Establish canonical current status and link historical evidence instead of erasing it.

**Done when:** Another qualified maintainer can build, test, diagnose and restore the recorded candidate; responsibilities and known limits are clear.

#### F42 — Customer need and productivity baseline

**Priority:** P1 · **Accountable:** Mohamed + Finance/Product · **Dependencies:** F03,F04  
**Starting evidence:** Market comparison is evidence, not client validation.

**Work:** Record present contractor workflows, repeated entry, spreadsheet workarounds and the expected productivity baseline. Gather approved client input and identify legal/invoice integration discovery requirements without implementing the connector.

**Done when:** Current acceptance scope and prioritized future needs have evidence and owner; no unverified market share, tax rules or promised ROI. External outreach occurs only when explicitly authorized.

### I. Owner acceptance and foundation sign-off

#### F43 — Prepare expanded owner UAT

**Priority:** P0 · **Accountable:** Engineering + Mohamed · **Dependencies:** F02,F04,F11,F16,F34,F40  
**Starting evidence:** 69-case UI pack already created.

**Work:** Refresh UI readiness gate and test scripts for all completed foundation changes. Add cases for cost-database Desk workflow, five report views, restricted integrity view, role workspaces, setup guidance and any other new surface.

**Done when:** No foundation enhancement is outside test inventory; accounts, fixtures, guides and expected values ready. Per owner decision 2026-10-12, the prepared pack then executes as one consolidated block at the last step; unfinished or unbuilt slices stay held and are listed with owners, never counted as passed.

#### F44 — Owner-led acceptance and retesting

**Priority:** P0 · **Accountable:** Mohamed + Finance/QS · **Dependencies:** F43  
**Starting evidence:** Owner tests all Not Run.

**Work:** Execute original 69 UI groups and every added case/role/report/print/transaction variant; use ordinary identities and realistic contractor journey. Feed failures into F38.

**Owner decision 2026-10-12 — consolidated execution:** the owner's UI testing runs as **one block at the last step**, after engineering foundation work and F43 preparation, rather than as staged slices during the program. Plan the calendar for the full load (69 groups plus added cases plus retest capacity within the initial 12–16-session allowance, extended as needed). Consequences accepted by this decision: defect discovery concentrates at the end, so F38's retest window lands immediately before F45 and the final-candidate date depends on it; interim correctness signal is carried by engineering evidence (F35 CI, F36 browser regressions), which does not substitute for owner acceptance. F44 remains P0: no foundation closure, and no new-feature scope decision, without it.

**Done when:** Actual results, evidence and signed financial comparisons exist; no console/API substitution for missing UI; mandatory failures are fixed and retested.

#### F45 — Final foundation decision

**Priority:** P0 · **Accountable:** Engineering lead + Mohamed · **Dependencies:** F15,F17,F18,F19,F20,F21,F22,F23,F26,F27,F28,F29,F30,F32,F33,F35,F36,F37,F38,F39,F40,F41,F42,F44  
**Starting evidence:** Single-candidate closure not established by this plan.

**Work:** Assemble final candidate manifest, completed task evidence, supported capability/version/limit matrix, defect decisions, data/recovery evidence and final independent owner rehearsal. Record technical and business sign-off.

**Done when:** Foundation gate below passes. Only then request/record the owner’s next-feature scope decision; foundation acceptance is not production deployment approval.

## 5. Traceability: all sixteen original release gaps

These references identify work to close remaining candidate-specific gaps, not a claim that historical corrections are absent.

| Gap | Foundation packages | Required closure evidence |
|---|---|---|
| G01 — deletion/aggregate integrity | F05,F10,F35,F44 | Correct totals after allowed deletion; failed operations roll back; data audit reconciles |
| G02 — approval/revision immutability | F06,F09,F11,F31,F44 | Server refusal of forbidden history changes; correct projections and preserved migrated history |
| G03 — cost cancellation/restoration | F07,F10,F31,F44 | Prior/manual/zero/superseded paths and representative legacy evidence |
| G04 — factor semantics | F04,F05,F14,F16,F31 | Positive/missing/invalid input and legacy behavior consistent across consumers |
| G05 — concurrent aggregates | F08,F35,F37 | Real independent-connection and stack-level contention/retry/rollback evidence |
| G06 — direct cost and margins | F04,F07,F19,F40,F44 | Independent pricing examples and reports/exports match owner-approved rules |
| G07 — actual business CI | F25,F35,F36,F45 | Current candidate test/run mapping with no silent required skips |
| G08 — authorization and isolation | F11,F12,F15,F19,F27,F44 | Ordinary-role allow/deny matrix covers UI/API/report/file/import/export |
| G09 — bounded workbook work | F14,F16,F17,F18,F37 | Safe rejection and admitted-workload evidence through transport/workers |
| G10 — dependency/security runtime | F13,F15,F25,F35 | Exact supported runtime and applicable findings/mitigations reviewed |
| G11 — capacity | F37,F33,F45 | Agreed workload measured, bottlenecks corrected and limits published internally |
| G12 — fresh install/upgrade | F10,F31,F32,F34 | Install, representative conversion, repeated migration and recovery proof |
| G13 — overrides/compatibility | F23,F24,F25,F26 | Supported version matrix, hook contracts and native regression |
| G14 — real UI wiring | F16–F23,F34,F36,F40,F43,F44 | Complete user journeys including the new interfaces for existing services |
| G15 — operating/recovery model | F02,F15,F32,F33,F41 | Named ownership, backup/restore, alerts and usable runbooks |
| G16 — single-candidate readiness | F01,F35,F38,F45 | One evidence bundle and distinct technical/domain acceptance |

## 6. Disposition of enhancements from all reports

The original reports contain both foundation improvements and proposals for new modules. Keep all recommendations traceable without turning “solid basis” into an unlimited rebuild.

### External consultant recommendations

| Reference | Disposition in this plan |
|---|---|
| C1 — cancellation policy | F07 verifies the already agreed prior/manual restoration rule; do not substitute Awaiting Approved Basis |
| C2 — locking | F08 extends existing guards; do not introduce competing lock order blindly |
| C3 — pricing specification | F04/F40 publish existing confirmed rules with independent examples |
| C4 — integrity report | F10/F19 reuse internal audit and deliver an appropriately restricted readable view |
| C5 — workbook bounds | F14 verifies existing controls and addresses missing endpoint protections |
| A1 — wildcard scope replacement | F12 measures coverage/performance first; retain correct guards unless a proven replacement preserves all scope behavior |
| A2 — override compatibility | F24 records/test contracts and upgrade ownership |
| A3 — delete React path | F26 inventories/restricts retained legacy paths; no blanket deletion against ADR-008 |
| A4 — VFC completion | F23 stabilizes supported behavior and documentation; existing guards/tests acknowledged |
| A5 — theme/assets rewrite | F22/F25 fix actual usability/cache defects; full hashed-bundle migration only if justified with rollback/tests |
| A6 — scaffold removal | F26 inventories data/consumers; safely hide unsupported product promises, preserve schema/data until a separate migration decision |
| A7 — hide progress-billing flag | Rejected as written; F20 retains/tests existing consumers |
| A8 — Python alignment | F25 explains supported runtime versus intentional conservative syntax; preserve owner convention |
| R1/R6 — process/docs relocation | F29/F41 consolidate/index with stable mandatory entry paths and preserved evidence |
| R2 — devtools repository split | F28 secures actual delivery artifacts first; separate repo remains optional, with dependencies and private destination authority reviewed |
| R3/R4 — screenshots/scripts/backups cleanup | F28/F29 inventory references and package exclusions; only proven safe relocation later, no blanket deletion |
| R5 — delete branches | Not included; no technical need established and unmerged work must be preserved |
| R7 — README | F39 required foundation improvement |
| R8 — license change | Separate commercial/legal decision; no license alteration or mandatory engineering blocker inferred |
| T1 — coverage map | F35 ties modules and paths to business risks |
| T2 — concurrency harness | F08 reuses and extends existing independent-connection suite |
| T3 — capacity | F37 chooses realistic bounded workload; no blind 5,000-row import increase |
| T4 — browser automation | F36 adds meaningful critical-journey regression; owner UAT remains F44 |
| T5 — upgrade regression | F31 proves supported origin/current candidate; recurring weekly automation is not created by this plan |
| S1 — HTTP role matrix | F11 mandatory server-side authorization proof |
| S2 — Option B toggle | F12 verifies existing toggle; no duplicate feature |
| S3 — endpoint limits | F14 includes missing size/rate/queue limits based on actual risk and workload |
| S4 — theme preference exceptions | F15/F23 verify narrow permitted fields and audit requirements |
| U1 — role workspaces | F21 required existing-workflow enhancement |
| U2 — mobile/photo field workflow | F22 fixes existing-form usability; new photo/dated capture/offline workflow stays later domain scope |
| U3 — onboarding wizard | F34 first delivers guided native setup/checks; custom wizard only if documented failure cannot be solved by current setup |
| U4 — bilingual customer guide | F40 required; publishing externally needs an approved destination and is not necessary for local Markdown delivery |

### Original enhancement backlog and market-driven additions

| Original item / later recommendation | Now: foundation action | Later domain implementation |
|---|---|---|
| E01 — period-based certification | F09 verifies stage quantities, roles and adjustment limitations | Dated period evidence/allocation belongs with certificate design; do not simply add mutable cumulative fields |
| E02 — measurement attachments | F11 verifies current file permissions; F40 states current evidence limits | New measurement child-table/photo workflow after its business/evidence model is agreed |
| E03 — committed cost rollup | F20 verifies PO attribution; F42 defines customer need | New commitment definition/report with cancellation, currency and partial receipt rules |
| E04 — actual cost rollup | F07/F20 verify existing postings/links; F19 exposes existing service results only | New PI/SE/TS/JE cost model must prevent double counting |
| E05 — earned value | F04 preserves quantity/rate/factor semantics | New earned-value definition/report; certified value is not automatically a complete EVM method |
| E06 — cost to complete | F42 records forecasting need | Forecast model after reliable commitment/actual data and owner-approved assumptions |
| E07 — plant lifecycle | F26 classifies PlantResource scaffold | Equipment ownership, mobilization, utilization and maintenance lifecycle |
| E08 — CostItem master link | F26 inventories current reference use | Do not replace free-text BOQ specification with new master linkage during foundation repair |
| E09/E10 — retention release and certificate print | F22/F40 stabilize existing commercial prints | Deliver with certificate commercial rules and lifecycle |
| E11 — MCP BOQ retrieval | F27 fixes current tooling schema mismatch | No new MCP platform required |
| Customer certificate/retention/advance | F04/F06/F09 assure reliable input semantics; F42 collects requirements | Separate next-feature scope after F45, with dated evidence, allocations and accounting sign-off |
| Subcontract agreements/certificates/final account | F20/F44 prove native purchasing/invoice/payment baseline | New supplier-side domain; not a simple customer/supplier switch |
| Procurement/cost visibility prototype | F19 provides current report-service UI; F20 validates base ERP handoffs | New committed/actual/forecast analytics after definitions and source reconciliation |
| Site diary/productivity/offline | F22 validates current forms on intended devices; F42 records time/input problems | New field data and offline synchronization workflows |
| Egypt invoice integration | F42 records applicable client requirements and qualified discovery ownership | Build/qualify integration before any customer launch that requires it; no fixed future-year deferral |
| Gulf, multi-currency, document/scheduling integration | F25 declares supported technical baseline; F42 records demand | Country/contract-specific scope and verification; no generic MENA-compliant claim |

No regulatory rate, deadline or vendor capability has been newly verified for this planning revision. Those research decisions must use current authoritative evidence when the relevant later scope is defined.

## 7. Execution sequence and effort

### Sequence

1. **Baseline and triage, execution week 1:** F01 appoints the named team and identifies the UAT site; F02 establishes the safe target. Front-load K-01/F16 and E11/F27 reproductions using small dedicated fixtures, alongside F03 inventory and before waiting for the full F04 fixture pack. Then complete F04 and the single gap list.
2. **Make the core safe:** F05–F15. Start CI setup F35 and documentation corrections concurrently where dependencies allow. Block unsafe paths while continuing independent work.
3. **Complete current workflows:** F16–F23 and F34. Prioritize import persistence, report/service access and transaction handoffs over cosmetic theme customization. Add acceptance scripts for every enhanced interface.
4. **Strengthen delivery and maintenance:** F24–F33. Packaging/docs inventory can start early; upgrade and recovery rehearsal use the corrected candidate. No broad rewrite or destructive cleanup.
5. **Prove and explain:** F35–F42. Finish browser regressions, realistic capacity, defect correction and accurate bilingual guidance. Documentation is updated alongside each functional change, not left to the last day.
6. **Owner acceptance and closure:** F43–F45. **Owner decision 2026-10-12:** owner UI execution is consolidated into one block after engineering completion instead of staged mid-program sessions — F43 prepares the expanded pack (original 69 groups plus the F18/F19 and other added cases), then F44 runs the full consolidated journey against the final candidate and feeds failures into F38 before F45. The consolidated block is a deliberate scheduling choice, not a scope reduction: no case may be marked passed without the owner's actual execution, and retests are not compressible to protect dates. New-module implementation waits for foundation sign-off.

The dependency graph, not numerical ID alone, controls execution. For a small team, independent documentation, fixture preparation and packaging inventory can overlap. With one engineer, use the same order without pretending there is parallel staffing. Review progress weekly and retest after relevant changes, not after every unrelated edit.

### Provisional effort envelope

These are planning allowances for the named work packages, **not quotes or validated estimates**. Validate after F01–F04. Already proven equivalent controls may reduce effort; legacy/data/security remediation or expanded customer scope may increase it.

| Workstream | Engineering working days |
|---|---:|
| A — baseline | 2–4 |
| B — financial integrity | 5–9 |
| C — security/bounds | 4–8 |
| D — existing-capability UX completion | 8–14 |
| E — maintenance/tooling/packaging | 4–7 |
| F — installation/data/recovery | 4–8 |
| G — verification/performance/defect closure | 3–6 |
| H — documentation/continuity | 3–5 |
| I — UAT support/final closure | 3–6 |
| **Initial envelope** | **36–67 engineering days** |

That is roughly 8–14 working weeks for one engineer at five full engineering days per week, before interruptions and business-review waiting. It is not a promise of customer release in that period. QA/review/operator input and Mohamed/Finance/QS effort must be budgeted separately; activities cannot be assumed free because one person holds several roles. The prior 12–16 owner sessions are only a starting reservation: add time for F18/F19 and other new interface cases, defects and retests.

At the end of F04, replace allowances with task estimates, named assignees and dates. If required scope exceeds capacity, explicitly phase or revise it with the owner; do not quietly remove integrity, permissions or mandatory owner acceptance.

### First work queue

| Order | Concrete output |
|---|---|
| 1 | Week 1: F01 names engineering lead, Finance/QS reviewer and operator, identifies intended UAT site, and records candidate/G01–G16 ledger |
| 2 | Week 1: F02 validates isolated UAT target and recoverable baseline |
| 3 | Week 1: reproduce K-01/F16 and E11/F27 on minimal fixtures; record actual outcomes and bounded correction proposals |
| 4 | Complete F03 installed inventory and F04 full role/financial fixture pack alongside those reproductions |
| 5 | F05–F15 financial/security verification; fix actual blockers; F35 candidate CI baseline |
| 6 | F18/F19 existing-service UI design using current service contracts; define additional owner test cases |
| 7 | Re-estimated remaining delivery queue and session calendar |

### Week-one reproductions — early substeps, unchanged package scope

Reserve these diagnostic substeps in week 1, immediately after F02 confirms a safe isolated target and the relevant F03 routes are identified. Do not wait for F04's full financial dataset, the full F11 authorization matrix or F14's complete limit suite. Use authorized test accounts and harmless minimal fixtures. Their parent completion dependencies remain unchanged: early reproduction is not permission to skip security, regression or owner acceptance before closure.

| Substep | Minimal fixture / action | Required output |
|---|---|---|
| F16-R / K-01 | Fresh Draft header and a three-row workbook; use actual Import Excel button; compare saved records before/after reload | Candidate/site, steps, UI message, persisted counts and confirmed/not-reproduced outcome; link UAT-D001 |
| F27-R / E11 | One permitted header with a separately stored BOQ Item and one empty header; exercise the existing bridge on the isolated target | Candidate/site, actual response or exception, expected item list and bounded correction proposal; full denied-scope testing remains required for F27 closure |

If the environment is unavailable, record the failed prerequisite and reschedule explicitly in the register; a repeated static inspection is not a completed runtime reproduction.

### Owner session reservations from Gate 1

At Gate 1, the engineering lead and Mohamed confirm calendar slots for stable-slice acceptance and reserve separate F18 and F19 sessions plus retest capacity. Use the owner-session table in the register; all bookings remain Pending until Mohamed confirms dates. F43/F44 operate incrementally for each ready slice: their listed dependencies govern complete-package closure, not a requirement to wait for all implementation before booking or testing an independent safe slice. Supply the slice's role checks, minimal fixtures and current guide before its session.

Retain the initial 12–16 session allowance and add slots as required; the register groups sessions by scope rather than limiting testing to one slot per group. Reconfirm readiness and candidate before each session. If a slice slips, swap in another verified slice or reschedule with a named action; preserve the separate final independent rehearsal. No calendar invitations or automations are created by this document.

## 8. Execution tracking and change control

Use one task row per F-package and child rows for discovered defects. Keep the UI defect IDs K-01/UAT-D001 etc. and reference them rather than copying divergent issue descriptions. Assign a unique issue ID to every newly found gap and map it to a workstream.

Task states: **Proposed → Ready → In progress → Engineering verified → Owner verified (when UI/business relevant) → Closed**. Use **Blocked** with dependency, responsible person and next action. A later/deferred task has a written scope decision and does not count as completed. Record evidence-only closure separately from implemented correction.

For each change: define failure/business expectation → implement bounded correction → run appropriate regressions → review diff → capture candidate and artifacts → update guide → obtain owner retest where relevant. Commit/push/deploy only through the authorized workflow and destination. Keep unpublished source and evidence private. Preserve originals, history and unrelated work.

Weekly review output is brief: completed deliverables with evidence, open critical/high defects, upcoming tasks, blocked dependencies, owner test sessions and revised effort. Progress is measured by accepted deliverables, not lines of code, count of screenshots or a fabricated readiness percentage.

## 9. Definition of a solid foundation

### Gate 1 — safe candidate for business testing

F01–F04 are complete, with actual kickoff assignments and the named UAT target recorded; relevant financial/security paths are verified; preparation prerequisites for the session pass. Each tested slice has usable routes, ordinary accounts and known expected values. Gate 1 certifies **engineering readiness for owner testing**; per owner decision 2026-10-12 the owner’s UI execution itself runs as one consolidated block after engineering completion (F43/F44), so Gate 1 requires no interim owner sessions — the consolidated block’s start date is confirmed instead. A remaining blocker on another isolated slice does not prevent safe engineering verification.

### Gate 2 — engineering foundation complete

- [ ] All applicable F01–F42 deliverables are closed or have an explicit approved scope reclassification; mandatory P0/P1 work is not silently deferred.
- [ ] G01–G16 have candidate-specific closure or a clearly separated production-only obligation; historic claims have been reconciled.
- [ ] No known wrong-money, approval-history corruption, lost/duplicate transaction, unauthorized access or destructive migration issue remains in scope.
- [ ] Existing import/report services required by F18/F19 have working UI and accurate documentation; new surfaces have role and acceptance coverage.
- [ ] Build/runtime/overrides, upgrade/replay, recovery, capacity and private CI evidence match the candidate.
- [ ] Supported features, versions, workload limits, operational owners and remaining exclusions are clear.

### Gate 3 — owner acceptance and permission to start the next module

- [ ] F43/F44 completed: all mandatory original and added UI cases/variants passed; no required Not Run/Blocked case remains.
- [ ] Mohamed completed the realistic journey independently and Finance/QS verified quantities, money and outputs.
- [ ] Every critical/high defect is fixed and retested. Any accepted minor issue has a workaround if needed, owner and due date; no security/financial/history issue may be relabeled cosmetic.
- [ ] F45 final bundle names candidate, evidence, known limits, technical reviewer and Mohamed's business acceptance.
- [ ] GM/owner selects the next feature and explicitly approves its scope/business rules after this foundation decision.

**Production deployment remains a separate decision.** Actual customer hosting, real credentials, customer migration and applicable country-invoice qualification must be completed before that customer's go-live. Foundation staging rehearsals do not assert those actions occurred. The new-feature hold ends only through the owner decision above, not automatically when a developer marks a task complete.

## 10. Source basis and verification of this plan

Read together:

- [Revised engineering report](construction_platform_engineering_review_for_gm.md).
- [Egypt/MENA benchmark](construction_erp_egypt_mena_market_benchmark.md), used as previously researched context rather than new vendor/legal verification.
- [Line-by-line external report reconciliation](consultant_review_line_by_line_reconciliation_2026-10-12.md) and [unchanged external report](/home/mohamed/Downloads/ConstructionERP_Consultant_Review_2026-10-09.md).
- [Original platform analysis](construction_platform_analysis_report.md), including E01–E11.
- [Dated G01–G16 assessment](../../CUSTOMER_RELEASE_GAPS_2026-10-04.md), [correction ledger](../customer-release-gap-fixes/STATUS.md), [financial rules](../customer-release-gap-fixes/FINANCIAL_RULES.md) and [operating profile](../customer-release-gap-fixes/RELEASE_OPERATING_PROFILE.md).
- [UI plan](existing_features_owner_ui_acceptance_plan_2026-10-12.md), [test results](owner_ui_test_results_2026-10-12.md), [defects](owner_ui_defect_register_2026-10-12.md) and [master work register](construction_foundation_work_register_2026-10-12.md).

Files read for planning: repository AGENTS.md, Professional Engineering Standard, CONTEXT_INDEX.md, AGENT_WORKFLOW.md, SCHEMA_FACTS.md summary, relevant SESSION_MEMORY.md sections, the reports above and current release ledger; relevant README/onboarding, bridge `server.py`, packaging configuration and source/guide references from the prior UI-plan investigation. Attachments supplied recommendations for review, not authority to delete branches, move governance files, change licenses or publish source.

Local verification: checkout/branch/HEAD and modifications inspected; schema checker passed 21 schema-owning DocTypes plus one override; context checker passed 11 checks with zero failures. Plan/work-register IDs, dependencies, source links, table structure and complete G01–G16 mapping were checked. No business/UI tests, remediation, site changes or deployment were executed for this planning revision. All execution tasks start Proposed.
