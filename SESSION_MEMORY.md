# Session Memory — Construction ERP
**LAST UPDATED:** 2026-09-24 (W6-4 Projects + Subcontracting cycle closed)
**UPDATED BY:** Codex (W6-4 governed cycle and evidence closure)

---

## 1. Project Snapshot
- **Total commits:** 191
- **Current branch:** `develop`
- **Last session date:** 2026-06-21
- **Python version:** 3.14 (venv: `/home/mohamed/frappe-bench/env`)
- **AGENTS.md status:** Rewritten from Scope Context dev report → agent context file
- **New files created:** `SESSION_MEMORY.md`, `docs/ai/CONTEXT_INDEX.md`, `docs/ai/SCHEMA_FACTS.md`, `docs/ai/CODING_PATTERNS.md`, `scripts/ai_context_check.py`

---

## 2. Completed Work (Stable — Do Not Modify Without Approval)

### Theme System ✅
- 22 CSS files, 14,884 total lines
- Three-layer architecture: tokens → base → v16_adapter
- 54-token CSS variable system, dark/light modes, RTL support
- Server-side theme resolution via `boot_session` hook (no FOUC)
- 17 whitelisted endpoints / 34 functions total in `api/theme_api.py`
- Per-user: User Desk Theme DocType (25 fields); site-wide: Construction Theme DocType (94 fields)
- **Note:** Only 6 CSS files are registered in `hooks.py` `app_include_css`. The remaining 16 are generated themes, login/email/print themes, or test files.

### Scope Context ✅
- User Scope Context DocType: company, cost_center, project, department, branch
- Query injection via `permission_query_conditions` (`overrides/scope_query.py`)
- NestedSet lft/rgt expansion for cost center descendants
- Redis caching (5-min TTL), admin bypass, column guards
- 13 integration tests + 10 unit tests passing (documented in prior report)

### BOQ Foundation ✅
- BOQ Header, BOQ Item, BOQ Structure, BOQ Item Stage DocTypes
- 12 service modules: lifecycle, accounting, export, import, migration, operational, lookups, scope filters, transaction validation, scope resolution, WBS generator
- BOQ API (CRUD + tree operations) in `api/boq_api.py` (9 whitelisted endpoints)
- **WARNING:** BOQ Item uses `cost_item` (Data), NOT `item_code` (Link→Item)

### VO Quantity Revision ✅
- New DocType: `BOQ Quantity Revision` (non-submittable, 7 auto-computed revision types)
- Schema: `original_qty`, `current_revised_qty`, `current_revised_unit_price`, `last_quantity_revision` on BOQ Item; `total_revised_value` on BOQ Header; `previous_qty`, `delta_from_contract_qty`, `change_pct_from_contract`, `created_quantity_revision` on VO Line
- Service layer: `services/quantity_revisions.py` (lock baseline, revision lifecycle, approval, idempotency)
- Query layer: `services/revised_boq_queries.py` (5 report functions)
- Controller hooks: `boq_header.py` (lock → baseline), `vo_line.py` (revised_qty primary, FIDIC from contract), `variation_order.py` (atomic approval, line edit blocking after Engineer)
- 57/57 tests passing (custom runner)
- Evidence: EV-065 (Schema), EV-066 (Tests), EV-067 (Manual QA) completed

### Searchable Dropdown ✅
- Global override for all Link fields (`ct_link_control.js`)
- Global override for all Select fields (`ct_select_control.js`)
- SearchableDropdownEnhancer class auto-applies to all form fields

### Arabic Localization ✅
- Full RTL support, Arabic translations seeded via patches v6.0–v6.6
- `translated_doctypes` in `hooks.py` covers 12 DocTypes

### Form Layout Engine (VFC) ✅ Phase 1+2+3 (Stabilization Complete)
- Form Layout Profile DocType (12 fields, `for_user` personal override, `for_role` targeting, `is_system` seed guard)
- `vfc_layout_engine.js` (1,399 lines): runtime field re-parenting into named sections
- `vite_layout_controls.js` (1,771 lines): drag/resize panel + Sections Editor tab + density controls + revert
- `vfc_sections.css` (177 lines): section card styles
- `vfc_config.js` (23 lines): debug flag gating
- `construction/construction/api/layout_api.py` (330 lines, 6 endpoints): get/save/list/delete/validate + `delete_my_personal_layout`
- `construction/api/modern_form_api.py` (454 lines): React form API — **deprecated** (ADR-008), System Manager only
- Phase 3 stabilization (WP0–WP5) complete:
  - Cache TTL (60s client-side), revert-to-default button, full reset (density/hidden/preset/layout)
  - Project layout seed, BOQ Item Stage seed verified, BLOCKED_DOCTYPES audit
  - `hidden_due_to_dependency` guard, non-admin personal layout deletion
  - 39 backend tests + browser test suite

### Vite UI ✅ Phase 0+1+2
- Visual foundation (`vite_form_override.css`, `vite_list_override.css`)
- Form config panel redesigned as centered dialog modal
- Dynamic layout controls via `frappe.require`
- DraggablePanel.jsx with panel dragging/resizing
- Built bundle: `construction.bundle.XR6HIDAQ.js`

---

## 3. In Progress (Active Work — Updated After Every Session)

### Bilingual integration release validation (2026-09-20)
- `feature/bilingual-integration` was validated as a combined checkout rather than relying on the two feature branches' isolated results.
- Fixed historical Stage 4 adoption to bind the immutable initial-export manifest; the live governed manifest may advance after an authorized import without invalidating provenance.
- Removed the accidental repository-root `__init__.py`, restoring checkout-name-independent offline tests while retaining the real `construction/__init__.py` app package.
- Made Stage 4 account-language tests valid before and after import and isolated generated manifests/exports in a temporary directory.
- Corrected dashboard test configuration to use a secured temporary `DASHBOARD_TEST_ROOT` under the supported test-mode contract.
- Validation: orchestrator 236/236; dashboard 77/77; offline portability 67/67; bilingual schema 5/5, service 38/38, pilot 53/53, localization gates 89/89, Stage 4 account language 6/6, report extension 11/11, review bundle 36/36.

### Workflow orchestration plan — r5 coherence review (2026-09-11)
- Canonical plan and working handoff: `docs/ai/work-items/scope-context-portability/`. Five pre-Phase-0 corrections resolved; numbered contracts synchronized and locked owner decisions preserved.
- Consultant coherence sign-off recorded in §18. Phase 0 has not begun; runtime feasibility remains its explicit gate. No commit or ERP execution occurred.

**2026-09-12 — Phase 3 pilot completion and owner commit (isolated worktree):** Candidate `89f613f94d35c34619d1436ea8556d4fe1412232e6463baca6cefc73897010c1` (tree `5b5f87ff01b16e9d739380e8523eca0698bbfd65`) achieved unanimous PASS across all 7 requirements (SCP-R1 through SCP-R7) and resolved findings SCP-001 through SCP-005. Both Codex builder (`job-0c114c5f...`) and independent Codex verifier (`job-fa5a2cc5...`) issued PASS with zero findings. All 67 offline tests pass, 11 context checks pass, 19 DocTypes linted, and 802-file fresh-copy gate verified in-root. Owner single-use token `owner-commit-grant-phase3-pilot` approved gate `commit-703536a0492e00f385d3f844` and owner commit `72da63dc693e320ea8b73d5bdf7000c4fda57f07` was recorded via `run --record-owner-commit` (`committed=true`, gate null). Zero ERP touch, no unapproved push/merge.

**2026-09-11 — Phase 2 execution:** Against frozen commit `4b77803af418cea8459c4cb7d9a0248674845da3`, the full synthetic suite produced 108 passed / 2 failed. Both failures lose their named class (MALFORMED_RESULT/EVIDENCE_UNAVAILABLE) in Engine._collect; advancement still pauses. Frozen source and checker scripts unchanged. Evidence: `docs/ai/work-items/scope-context-portability/evidence/phase-2-validation.json`. Phase 2 exit blocked; owner amendment required before fixing frozen engine. No project commit, provider run or ERP operation.

**2026-09-11 — Workflow Phases 0–1 (isolated worktree):** Phase 0 passed under the owner consultant directive; all five prompt hashes approved. Phase 1 engine/adapters/operator CLI implemented, with 93 passing tests and native Codex/OpenCode transport proof. Independent review blockers repaired, final bounded review PASS; Phase 1 source freeze recorded. Antigravity uses the explicitly authorized independent Codex substitute. See `docs/ai/work-items/scope-context-portability/IMPLEMENTATION.md`. No project commit or ERP operation; original dirty ERP checkout remains separate.


### Deployment-readiness remediation — Completed (2026-08-20)
- **Result:** All findings from `docs/USER_GUIDE_DEPLOYMENT_REVIEW_2026-08-19.md` remediated; review verdict updated to release-ready.
- **Key fixes:** BOQ Header scope enforcement now honors the feature flag, Administrator bypass, and explicit projects; omitted BOQ Items are hidden from transaction and VO item dropdowns after approved omission; User Guide terminology, VFC labels, cache versions, and test evidence synchronized.
- **Validation:** VO 23/23, Quantity Revisions 30/30, Transaction Validation 13/13, BOQ Link Queries 9/9, BOQ Properties 17/17, Scope Context 17/17, Cost Engine 17/17, Cost DB 10/10, VFC 39/39; `bench build --app construction` passed.

### Current Sprint: rc-1.1 Follow-up (WP1–WP7) — 6/7 Complete
#### Task 1: WP1 — Broader-app Audit → Completed (2026-06-21)
- **Files:** `docs/evidence/broader_app_audit_log.md`
- **Result:** 76 backup files classified into 17 categories; no fragmentation found

#### Task 2: WP2 — Migration Survival Test → Completed (2026-06-21)
- **Files:** `construction/tests/test_migration_survival.py`
- **Result:** 7 formal tests run after every `bench migrate`

#### Task 3: WP3 — Handover Documentation → Completed (2026-06-21)
- **Files:** `docs/handover/INDEX.md` + migrated documents
- **Result:** 7 handover docs consolidated into `docs/handover/`; `AGENTS.md` and `SESSION_MEMORY.md` updated

#### Task 4: WP4 — VFC Debug Flag → Completed (2026-06-21)
- **Files:** `vfc_config.js`, `boot.py`, `hooks.py`
- **Result:** Diagnostic logging gated by `vfc_debug_logging` toggle on Construction Settings

#### Task 5: WP5 — Project-wise Profitability → Pending Client Decision
- **Status:** Deferred per manager direction (2026-06-21). Standard ERPNext report pulls from GL only; would not reflect BOQ-driven costs. Will revisit after BOQ reports are finalized to decide between (a) installing standard report as-is, or (b) building custom Construction Profitability report joining BOQ + GL data.
- **Next action:** None until BOQ reports complete and client confirms requirement

#### Task 6: WP6 — Option B Admin Toggle → Completed (2026-06-21)
- **Files:** `construction_settings.json`, `scope_report.py`
- **Result:** `enable_option_b_report_access_bypass` field + `_user_has_active_scope_context()` gate; default ON for backward compatibility

#### Task 7: WP7 — Audit Logging → Completed (2026-06-21)
- **Files:** `scope_report.py`, `construction/doctype/scope_report_access_log/`, `test_option_a_plus.py`
- **Result:** `_log_report_access()` helper with RuntimeError fix; denial logging; 5 tests; 34 total pass
- **Key fix:** `getattr(frappe.request, "path", "")` → `try/except RuntimeError`

---

## 4. Architecture Decisions Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-04-15 | CSS Variable Token Architecture (3-level) | Complete visual override without core Frappe edits | Active |
| 2026-04-20 | Server-side theme resolution | Prevent FOUC, cross-device sync | Active |
| 2026-04-22 | `frappe.db.set_value()` for theme writes | Avoid TimestampMismatchError on concurrent tab switches | Active |
| 2026-04-25 | Hybrid CSS strategy (static + dynamic) | Fast initial render + runtime customization | Active |
| 2026-05-01 | NestedSet (lft/rgt) for BOQ Structure | Better subtree queries vs adjacency list | Active |
| 2026-05-10 | ERPNext Price List for rate lookups | Avoids custom table duplication | Active |
| 2026-05-20 | BOQ Item uses `cost_item` (Data) not `item_code` (Link) | BOQ items are specification lines, not ERPNext items | Active |
| 2026-05-31 | Repo-local files as source of truth for AI memory | Prevents drift between MCP, skills, and repo state | Active |
| 2026-05-31 | MCP memory treated as cache/index, not authority | Safer fallback if MCP server is offline or stale | Active |

---

## 5. Known Issues & Gotchas

| Issue | Location | Workaround | Priority |
|-------|----------|-----------|----------|
| CSS not loading after adding new file | `hooks.py` `app_include_css` | Register file + bump `?v=` param | P0 |
| Only 6 of 22 CSS files are in `app_include_css` | `hooks.py` | Generated/special-purpose files load conditionally; do not blindly add all 22 | P0 |
| BOQ Item has no `item_code` / `item_name` | `boq_item.json` | Use `cost_item` (Data) + `structure` (Link→BOQ Structure) | P0 |
| JS inline styles conflict with CSS variables | `theme_loader_v24.js` | CSS-only approach enforced | P0 |
| TimestampMismatchError on concurrent theme switches | `theme_api.py` | `frappe.db.set_value(..., update_modified=False)` | P1 |
| v16 DOM selectors need verification | All JS files | Run `verify_v16_selectors.js` after DOM changes | P1 |
| Admin bypasses ALL scope filters | `scope_query.py` | Always test with non-admin user | P1 |
| Python 3.10 quote-nesting compatibility | All `.py` files | Commit `d7b5186` made f-strings safe; keep new code compatible | P1 |

---

## 6. Session Log (Append-Only — Most Recent First)

### Session 2026-09-20 — Integration PR release validation
- Reproduced and repaired a cross-branch Stage 4 provenance mismatch caused by the mutable governed manifest advancing after the historical export.
- Repaired offline-test checkout portability and removed test writes to tracked release artifacts.
- Repaired dashboard test-root configuration so registry ownership/permission checks run against isolated `0700` directories.
- Full affected release suites pass; the integration branch is ready for commit, push, and PR review.

### Session 2026-09-11 — Workflow plan r5 documentation corrections
- Corrected restart reconciliation, PLAN versus operation grants, code/proposal/bundle/payload identities and private storage, Flit/legacy packaging guidance, and canonical definitions.
- Synchronized `CANONICAL_PLAN.md` and `IMPLEMENTATION_HANDOFF.md` numbered bodies; checked references, preserved decisions, and documented consultant sign-off.
- Documentation-only work. No Phase 0, native agent dispatch, ERP suite rerun, data import or Git commit.

### Session 2026-09-11 — Codex Phase 2 synthetic qualification
- Added verification-only tests outside the frozen manifest and executed three recorded runs, ending at 108/110 passing. All 93 frozen regressions still pass.
- Graph proof includes repair/architecture routing, quorum, persistent escalation, candidate drift and real local VACUUM INTO recovery; synthetic test commits only in disposable repositories.
- Found P2-F001: collection discards two required failure classes while correctly pausing. Regressions retained; no production fix applied under the freeze.
- Recorded JSON/XML evidence and bounded correction proposal; Phase 3 remains blocked pending authorized fix and full rerun. All session state kept local.


### Session 2026-09-11 — Codex workflow implementation
- Local SQLite authority, independent native worker sessions, exact candidate binding, owner grants and conditional defect routing implemented in the isolated workflow worktree.
- Permission wrapper protects control/Git writes and peer artifacts; native Codex and OpenCode probes passed. `/run` masking initially broke DNS; preserving only resolver data fixed the regression.
- Independent native code review was launched only after explicit scoped transfer authorization. Four P1 findings repaired and regression-tested: approval scope confusion, prepare/replay crash, pause lock starvation, stale dispatch preconditions.
- Final independent bounded review: PASS; source freeze recorded in phase-1-code-freeze.json. Approval admission also synchronizes pending durable decisions before accepting a token.
- Full regression suite: 93 passed; real process restart and app packaging excluded workflow code/dependencies. Full Phase 2 qualification and real pilot remain pending.
- State/memory remain local per owner directive. No project commit, staging, ERP rerun or import.


**2026-09-11 — Workflow Phases 0–1 (isolated worktree):** Phase 0 passed under the owner consultant directive; all five prompt hashes approved. Phase 1 engine/adapters/operator CLI implemented, with 93 passing tests and native Codex/OpenCode transport proof. Independent review blockers repaired, final bounded review PASS; Phase 1 source freeze recorded. Antigravity uses the explicitly authorized independent Codex substitute. See `docs/ai/work-items/scope-context-portability/IMPLEMENTATION.md`. No project commit or ERP operation; original dirty ERP checkout remains separate.


### Session 2026-08-20 — Deployment-readiness remediation
- **Worked on:** Remediated all F1–F7 findings in the user-guide deployment review.
- **Files changed:** BOQ Header validation, BOQ item link query, transaction and VO dropdown filters, cache-bust hook, user guide, review report, and affected regression fixtures.
- **Validation:** All targeted backend suites passed; Scope Context manual runner repaired to use `_enforce_scope_filters_strict` and passed 17/17; asset build succeeded.

### Session 2026-06-21 — Agent: Cursor (VFC Phase 3 Stabilization)
- **Worked on:** VFC Phase 3 stabilization — WP0 through WP5 complete, plus review findings
- **Decisions:**
  - React runtime removed from hooks.py (components/index.js); all 7 modern_form_api.py endpoints gated to System Manager only (ADR-008)
  - Cache: 60s client-side TTL only, no backend realtime invalidation
  - Recovery: revert-to-default button + full reset (density, hidden fields, preset, layout)
  - Expansion: Project layout seed added; BOQ Item Stage seed verified
  - `hidden_due_to_dependency` guard added to all 4 field-checking locations + `_restoreVisibleFieldWrapper`
  - Non-admin personal layout deletion via new `delete_my_personal_layout(doctype)` endpoint
  - SortableJS CDN replaced with local vendor asset
  - JS cache busters bumped: vfc_layout_engine 1.42→1.44, vite_layout_controls 1.18→1.21
- **Files changed (3 commits: 7aadbdd, d55f6a2, 698ea94):**
  - `ADR.md` — ADR-008 appended
  - `AGENTS.md` — VFC section updated, ADR count 7→8
  - `SESSION_MEMORY.md` — updated
  - `construction/api/modern_form_api.py` — all 7 endpoints gated with `_require_system_manager()`
  - `construction/hooks.py` — patches entry removed; components/index.js include removed; cache busters bumped
  - `construction/install.py` — DEFAULT_PROJECT_LAYOUT added; seed function updated
  - `construction/public/js/vfc_layout_engine.js` — cache TTL, hidden_due_to_dependency guard, observer fixes, retry timer cleanup
  - `construction/public/js/vfc_layout_engine_tests.js` — checkDebounce→checkEngineLoaded
  - `construction/public/js/vite_layout_controls.js` — density fix, revert button, local SortableJS, full reset
  - `construction/public/js/vendor/sortablejs.min.js` — local SortableJS asset
  - `construction/construction/api/layout_api.py` — `delete_my_personal_layout` endpoint added
  - `construction/tests/__init__.py` — `run_vfc_tests()` runner added
  - `construction/tests/test_vfc_backend.py` — 39 backend tests
  - `docs/hook_matrix.md` — stale components/index.js row removed
  - `docs/feature_reviews/evidence/EV-068` through `EV-073` — 6 evidence files
  - `docs/handover/VFC_PHASE_3_PLUS_*` — 3 handover documents
- **Test results:** 39/39 VFC backend tests passing
- **Build:** `bench build --app construction` successful
- **Migration:** `bench --site v16.localhost migrate` successful
- **Next steps:** Final user UI testing
- **Worked on:** VO Quantity Revision model implementation — end-to-end completion
- **Decisions:**
  - `revised_qty` is primary input; `delta_qty` computed from it
  - `rate_change_triggered` uses `change_pct_from_contract` (FIDIC >25% rule)
  - `original_qty` locked at baseline; `current_revised_qty` updated on approval
  - `line_total` intentionally kept as contract value (`quantity * contract_unit_price * factor`)
  - `apply_approved_revision` corrected to NOT overwrite `line_total` with revised value
  - `process_approved_vo_lines` now calls `update_boq_header_totals` for all line types including New Items
  - `item_code` removed from VO Line
  - VO line editing blocked after Engineer Approved (P0-1)
  - Idempotent approval via `created_quantity_revision` check (P0-4)
  - `BOQ Quantity Revision` is non-submittable with custom status field
  - `compute_revision_type` auto-computes 7 revision types (skips "Original Lock" if explicitly set)
  - `create_quantity_revision` uses placeholder "Increase Within 25%" to trigger auto-computation
  - `rate_change_justification` propagated through revision creation and approval
  - Variation items (`is_variation_item = 1`) excluded from `total_contract_value` but included in `total_revised_value`
- **Issues found:**
  - `test_create_lock_baseline_idempotent` had flawed logic comparing `result.get("created")` to DB count
  - Fix: compare DB count before and after the second call
  - `test_variation_item_revision_creates_approved_revision` passed non-existent `variation_order` name
  - Fix: pass `variation_order=None`
  - `test_transition_variation_order_happy_path` and `test_vo_line_revised_qty_synchronization` used old `delta_qty` primary input
  - Fix: update tests to use `revised_qty` as primary input
  - `test_create_material_request_for_vo` had `NameError` (`res` undefined) due to stale test code
  - Fix: remove dead code after `assertRaises`
  - Multiple tests used `revised_qty=1010` but expected results for `110`
  - Fix: change `1010` to `110` in affected tests
  - `apply_approved_revision` was overwriting `line_total` with revised value, breaking `get_revised_boq_rows` and `total_contract_value`
  - Fix: remove `line_total` update from `apply_approved_revision`
  - `process_approved_vo_lines` did not update BOQ Header totals for New Item lines
  - Fix: add `update_boq_header_totals(vo.boq_header)` at end of function
  - `frappe.db.count`/`frappe.db.get_all` do not see uncommitted changes within test transactions
  - Fix: use `frappe.db.sql` for idempotency checks in `create_lock_baseline`
- **Files changed:**
  - `construction/construction/doctype/boq_item/boq_item.json` (new fields)
  - `construction/construction/doctype/boq_header/boq_header.py` (lock hook, total_revised_value calculation)
  - `construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.json` (new DocType)
  - `construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.py` (revision logic)
  - `construction/construction/doctype/vo_line/vo_line.py` (revised_qty primary, FIDIC logic)
  - `construction/construction/doctype/variation_order/variation_order.py` (atomic approval, idempotency)
  - `construction/services/quantity_revisions.py` (core service layer)
  - `construction/services/revised_boq_queries.py` (report queries)
  - `construction/tests/test_quantity_revisions.py` (24 test cases)
  - `construction/tests/test_variation_orders.py` (updated existing tests)
  - `construction/tests/test_boq_link_queries.py` (updated for exclude_zero_revised)
  - `construction/tests/__init__.py` (custom test runner)
  - `docs/feature_reviews/evidence/EV-065-vo-quantity-revision-schema.md` (filled)
  - `docs/feature_reviews/evidence/EV-066-vo-quantity-revision-tests.md` (filled)
  - `docs/feature_reviews/evidence/EV-067-vo-quantity-revision-manual-qa.md` (filled)
  - `SESSION_MEMORY.md` (updated)
- **Test results:** 57/57 tests passing (custom runner via `construction.tests.run_quantity_revision_tests`)
- **Migration:** `bench --site v16.localhost migrate` completed successfully
- **Next steps:** None — feature complete

### Session 2026-05-31 — Agent: Kimi Code (Phase 3)
- **Worked on:** ERPNext read-only MCP server (Phase 3)
- **Decisions:**
  - Created `erpnext-mcp-server/server.py` with 9 read-only tools
  - Tools: get_boq_header, get_boq_structure_tree, get_scope_context, list_construction_themes, get_form_layout_profile, get_doctype_schema, get_document, get_doctype_list, run_safe_select
  - Safety: DocType allowlist (30 DocTypes), SQL injection guard (blocks INSERT/UPDATE/DELETE/DROP/ALTER), audit logging to logs/ai_mcp_audit.log
  - Frappe contextvar isolation solved via dedicated ThreadPoolExecutor (avoids asyncio.to_thread context copy issues)
  - Registered with Kimi, Codex, Antigravity, Windsurf
  - Installed `mcp` package in bench venv (`/home/mohamed/frappe-bench/env`)
- **Issues found:**
  - Frappe's `contextvars.ContextVar` based Local storage incompatible with `asyncio.to_thread()` context copying
  - Fix: use `loop.run_in_executor()` with custom ThreadPoolExecutor that preserves per-thread Frappe state
  - Frappe logger requires site/logs/ directory relative to cwd
  - Fix: `os.chdir(BENCH_PATH)` + `mkdir(parents=True, exist_ok=True)` in init_frappe()
- **Files changed:**
  - `erpnext-mcp-server/server.py` (created)
  - Agent MCP configs updated (Kimi, Codex, Antigravity, Windsurf)
- **Next steps:** Use natural language to query ERPNext data through MCP-enabled agents

### Session 2026-05-31 — Agent: Kimi Code (Phase 2)
- **Worked on:** MCP auto-capture infrastructure (Phase 2)
- **Decisions:**
  - Created `scripts/mcp_store.py` — CLI to store memories via MCP stdio
  - Created `scripts/mcp_recall.py` — CLI to recall memories via MCP stdio
  - Created `scripts/session_end.py` — interactive session summary capture
  - Created `scripts/install_git_hooks.sh` + `.git/hooks/post-commit` — auto-capture on every commit
  - Updated `AGENTS.md` §7 with auto-capture protocol and helper script references
  - Verified `mcp_store.py` and `mcp_recall.py` work end-to-end
  - Verified git post-commit hook stores commit memory automatically
- **Issues found:**
  - Plain `python3` cannot import memorygraph's pydantic due to ABI mismatch
  - Fix: all MCP scripts and hooks use `/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python`
- **Files changed:**
  - `scripts/mcp_store.py` (created)
  - `scripts/mcp_recall.py` (created)
  - `scripts/session_end.py` (created)
  - `scripts/install_git_hooks.sh` (created)
  - `.git/hooks/post-commit` (installed)
  - `AGENTS.md` (updated §7)
- **Next steps:** Use `session_end.py` after every session; commits auto-capture via hook

### Session 2026-05-31 — Agent: Kimi Code (Phase 1)
- **Worked on:** Engineering review + Phase 1A–D implementation
- **Decisions:**
  - Approved revised architecture: repo files authoritative, MCP/skills are adapters
  - Rewrote `AGENTS.md` from Scope Context report to agent context file
  - Created `SESSION_MEMORY.md`
  - Created `docs/ai/` reference folder
  - Created `scripts/ai_context_check.py`
  - Corrected plan: ADR count = 7 (not 4); CSS registration nuance added
- **Issues found:**
  - Original plan over-claimed MCP capability ("no manual updates needed")
  - Original plan included unsafe `run_bench_command` in ERPNext MCP v1
  - AGENTS.md was a 234-line dev report, not an agent onboarding file
- **Files changed:**
  - `AGENTS.md` (rewritten)
  - `SESSION_MEMORY.md` (created)
  - `docs/ai/CONTEXT_INDEX.md` (created)
  - `docs/ai/SCHEMA_FACTS.md` (created)
  - `docs/ai/CODING_PATTERNS.md` (created)
  - `scripts/ai_context_check.py` (created)
- **Next steps:**
  - Run validation script to verify ground truth
  - Seed MCP memory from repo files only (Phase 2)
  - Keep `SESSION_MEMORY.md` updated manually as fallback

### Session 2025-05-30 — Agent: Antigravity
- **Worked on:** Plan revision — `CONSTRUCTION_ERP_AI_MEMORY_PLAN.md` v2.1
- **Decisions:** Updated plan to reflect actual repo state
- **Issues found:** `AGENTS.md` exists but needs content overhaul; BOQ Item schema differs from v1.0 plan
- **Files changed:** `CONSTRUCTION_ERP_AI_MEMORY_PLAN.md`
- **Next steps:** Execute Phase 1 — update AGENTS.md, create SESSION_MEMORY.md

### Session 2026-06-21 — Agent: Cursor (WP1–WP7 rc-1.1 follow-up sprint)
- **Worked on:** 7 post-rc-1.1 follow-up work packages
- **Decisions:**
  - `develop` is the sprint integration branch — all feature branches merged into it, then deleted
  - WP1: Broader-app backup files audited at `docs/evidence/broader_app_audit_log.md`
  - WP2: Formal migration survival test created at `construction/tests/test_migration_survival.py`
  - WP3: Handover docs consolidated into `docs/handover/`; `AGENTS.md` and `SESSION_MEMORY.md` updated
  - WP4: VFC diagnostic logging wired via `vfc_config.js`, `boot.py`, hooks, and settings toggle
  - WP6: Option B admin toggle field on Construction Settings + `_user_has_active_scope_context()` gate
  - WP7: `Scope Report Access Log` DocType + `_log_report_access()` helper with `try/except RuntimeError` for `frappe.request` outside HTTP context; denial logging added for restricted non-scoped users
- **Issues found:**
  - WP7: `getattr(frappe.request, "path", "")` raises `RuntimeError` (not `AttributeError`) outside HTTP context — fixed with `try/except RuntimeError` wrapper
  - WP7: `bench` command requires interactive terminal; replaced with `bench --site v16.localhost console <<PYEOF`
  - WP3: Root-level directories (`01 scope context/`, `02BOQ Integratiom/`, etc.) are outside the construction git repo and cannot be committed
- **Files changed (cumulative):**
  - `construction/overrides/scope_report.py` — WP4 debug logging, WP6 Option B gate, WP7 audit logging + denial logging
  - `construction/construction/doctype/scope_report_access_log/` — WP7 DocType (JSON, py, js)
  - `construction/construction/doctype/construction_settings/construction_settings.json` — WP6 toggle field
  - `construction/boot.py` — WP4 VFC debug flag
  - `construction/hooks.py` — WP4 VFC boot hook
  - `construction/public/js/vfc_config.js` — WP4 VFC debug flag
  - `construction/tests/test_option_a_plus.py` — 5 WP7 audit logging tests + WP6 toggle tests
  - `construction/tests/test_migration_survival.py` — WP2 formal migration survival test
  - `docs/evidence/broader_app_audit_log.md` — WP1 audit log
  - `docs/handover/INDEX.md` — WP3 handover index (created)
  - `docs/handover/BOQ_STRUCTURE_BLOCKER_HANDOFF.md` — WP3 migrated from `docs/`
  - `docs/handover/SCOPE_CONTEXT_STANDARDIZATION_APPROVAL_REPORT.md` — WP3 migrated
  - `docs/handover/SENIOR_ENGINEER_AUDIT_REPORT.md` — WP3 migrated
  - `docs/handover/TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md` — WP3 migrated
  - `docs/handover/VFC_PROJECT_TABS_DEBUG_REPORT.md` — WP3 migrated
  - `docs/handover/CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md` — WP3 migrated
  - `docs/handover/AGENTS_HANDOFF.md` — WP3 migrated
  - `erpnext-mcp-server/server.py` — WP1 audit log directory fix
  - `AGENTS.md` — updated branch, commit count, workstreams
  - `SESSION_MEMORY.md` — updated (this entry)
- **Test results:** 34 tests pass (test_option_a_plus + test_migration_survival)
- **Migration:** `bench --site v16.localhost migrate` completed for WP7 DocType
- **Next steps:** WP5 (Project-wise Profitability) blocked on client confirmation

### Session 2026-09-01 — Agent: OpenCode (Translation Catalog Workbench)
- **Worked on:** Ground-up fix so every ERPNext/Frappe UI string appears in the Translation list and can be filtered/edited.
- **Decisions:**
  - Seed every msgid from `frappe/erpnext/construction` Arabic `.po` files into `tabTranslation` as catalog rows.
  - Catalog rows are excluded from the runtime translation cache via monkey-patch in `construction.__init__`; only existing runtime translations affect the UI, so worker memory stays flat.
  - Editing a catalog row auto-promotes it to a manual override (`override_doctype_class` on `Translation`).
  - New list-view tools: Search Arabic Text, Show Catalog Entries, Show Existing Runtime Translations, Show Empty PO Arabic, Sync Translation Catalog.
  - v8_4 patch fixes tree-view Arabic translations (`Add Child` → `إضافة فرع`, etc.).
  - v8_5 patch creates custom fields and seeds the catalog.
- **Files changed:**
  - `construction/__init__.py` — runtime cache optimization monkey-patch
  - `construction/overrides/translation.py` — `CustomTranslation` controller
  - `construction/setup/translation_catalog_fields.py` — catalog custom fields
  - `construction/api/translation_tools.py` — `sync_translation_catalog`, `reset_catalog_overrides`, `search_arabic_translations`, `get_translation_catalog_stats`
  - `construction/public/js/translation_list_tools.js` — workbench menu actions (v5)
  - `construction/hooks.py` — `override_doctype_class`, bump `translation_list_tools.js?v=5`
  - `construction/patches/v8_4/fix_tree_view_arabic_translations.py` — tree action fixes
  - `construction/patches/v8_5/seed_translation_catalog.py` — catalog seed patch
  - `construction/patches.txt` — registered v8_4 + v8_5
  - `construction/insert_translations.py` — added `Add Child`/`Edit`/`Rename`/`Delete` to `CRITICAL_OVERRIDES`
  - `apps/frappe/frappe/locale/ar.po` — filled `msgstr` for `Add Child`
- **Verification:** All Python/JS modules pass `py_compile` / `node --check`; `.po` scan shows ~15,106 msgids across apps.
- **Next steps:** Run `bench --site v16.localhost migrate` to apply patches; hard-refresh browser to load updated list-view tools.

Workflow session capture: external MemoryGraph write was rejected by automatic approval review; this local record is the fallback. No external retry attempted.

---

## 2026-09-21 — Bilingual program: test-environment closure & HOLD (full session)

**Accomplished:** Stages 0/1A/1B/1C/2/3/4 closed; Stage 2 durable-evidence re-pin (twice contractually); W6-1 governed cycle (69 released / 78 preserved site overrides); W6-0a desk-shell cycle (347 released ver 1.2, 3 real exceptions, 10 deferred-unresolved protected); Stage 7 pilot complete — governed `localized_report` API (P1/P2 hardened), viewer page `/app/bilingual-report-viewer` live-rendering Arabic reports (ar Desk evidence), BOQ ar/en PDF exports via the vendor service (0 vendor edits); `scripts/uat_preflight.py` hardened (stdin-only secret, universal logout, fail-closed missing creds, clean connection-failure records). Site repairs: workspace-sidebar drift row deletion; bench redis 13000/11000 restored.
**Decisions:** evidence re-pin once per catalog event (contract moved 89→91, then payload 450 / PO 810); Site Overrides preserved per §12; production deferred pending owner provides real master/ledger data + backup/restore rehearsal window + explicit authorization; §18 hold state recorded in the end-to-end plan.
**Open issues:** MCP memory runtime broken (`pydantic_core._pydantic_core`) — hold-state stored to `docs/ai/memory_store_fallback/` + this file; vendor `SidebarItem.get_path` benchmark recorded only in the tree-evidence context (site-config drift).
**Next (2026-09-21 snapshot — SUPERSEDED):** HOLD — no W6-0b / Stage 8 work; resume only on owner-provided real data + rehearsal window + production authorization; always run the hardened `uat_preflight.py` before Stage 8 validations.

---

## 2026-09-22 — W6-0b batches 1–7 CLOSED (batch 7 corrected, owner-accepted)

**Accomplished:** W6-0b short-UI cut fully executed on `v16.localhost` only. Exact 1,894-row batch plan (`stage6_w60b_batch_plan_2026-09-22.csv` sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`), batches 01–07 = 271/271/271/271/270/270/270. Batch 7 corrected cycle: scope CSV 270 rows sha256 `1716d01c…` → 241 quorum-confirmed released + 29 EXCEPTION-technical + 0 preserved-site-override; catalog 2,190 all Released; DRY 2190/241/0/1949/0 drift=0; post-DRY idempotent 2190/0/0/2190/0; browser evidence 21/21 PASS; full gate `errors=0` (no skip flag); UAT teardown done (password `ct-w60b-rotated-off`, language `en`).
**Decisions:** Batch 7 **owner-ACCEPTED/closed at `a0f01cb`**; rejected attempt **`8bfc23a`** kept in history only (0 released / empty translations). Proposal commit `dfbced4`. Production Stage 8 still gated on real production data + named production site + rollout window + AI-R on exact release commit. W6-0b short-UI cut **exhausted**.
**Open issues:** Next Stage 6 matrix rows (W6-2 Buying+Selling … W6-7 framework remainder) still unchecked in `stage6_workflow_matrix_proposal_2026-09-21.md`; hold-state JSON + plan §16/§17/§18 updated this session to record batch-7 closure and retire the stale “do not start W6-0b” clause.
**Next:** Propose next bounded Stage 6 workflow-matrix scope (exact row CSV + sha256, ~200–300 rows, PROPOSAL ONLY) → **owner approval** → only then run. No production work authorized. Always run hardened `uat_preflight.py` before Stage 8 validations.

---

## 2026-09-23 — W6-2 batch-01 governed cycle CLOSED (test site)

**Accomplished:** Owner-approved W6-2 Buying+Selling batch-01 fully executed on `v16.localhost` only. Exact 270-row scope CSV sha `b017df4787ff8754be0bf43425151b748ba0aa019348fa29187f660130408fae` → 184 preserved-site-override (incl. Address strip-collision amendment 2276→2275) + 1 already-released + 0 exception + 85 quorum-confirmed payload. Three CSV placeholder/affix fixes + same-version import-gate fix in `translation_service.py`. Catalog **2,275** Released; IMPORT `updated=3`; post-DRY **IDEMPOTENT_OK** 2275/0/0/2275/0 drift=0; decisions 2275 (sha `2d373028…`); freshness critical_pass/has_drift=false; inventory 20692; full gate **errors=0** with evidence; module tests **270/270**; standalone 91 OK; browser evidence **21/21 PASS**; UAT preflight PASS; teardown (password `ct-w60b-rotated-off`, language `en`).
**Decisions:** Batch-01 closed under owner approval of that exact CSV only; all other scopes + production work excluded. Production Stage 8 still gated on real production data + named production site + rollout window + AI-R on exact release commit. Next Stage 6 matrix batch still requires a **new** owner-approved scope proposal before any run.
**Open issues:** Historical build script still asserts 2276 — do not rerun. Owner-approved scope CSV historical trailing-space form intentionally untouched.
**Next:** Propose next bounded Stage 6 workflow-matrix scope (PROPOSAL ONLY) → owner approval → only then run. Always run hardened `uat_preflight.py` before Stage 8 validations. No production work authorized.

---

## 2026-09-23 — W6-2 batch-02 governed cycle CLOSED (test site)

**Accomplished:** Owner-approved W6-2 Buying+Selling batch-02 fully executed on `v16.localhost` only. Exact 48-row scope CSV sha `9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce` → 1 preserved-site-override (`Address`→`العنوان`) + 3 EXCEPTION-technical (`doctype`, `doc_type`, `quotation_item`) + 0 already-released + 44 quorum-confirmed payload. Catalog **2,319** Released; IMPORT `created=44`; post-DRY **IDEMPOTENT_OK** 2319/0/0/2319/0 drift=0; SYNC `created=0 updated=0`; decisions 2319 (sha `1a9475d9…`); freshness critical_pass/packaged=2319/has_drift=false; inventory 20736 (merkle `bb438f9f…`); gate pins 2319; full gate **errors=0** with evidence at base HEAD `90bc65e`; module tests **270/270**; standalone 91 OK; browser evidence **21/21 PASS** (json `4c220726…`); UAT preflight PASS; teardown (password `ct-w60b-rotated-off`, language `en`). Cycle commit **`b3b0681`** (parent `90bc65e`). Evidence HEAD-bound to base per batch-7 pattern.
**Decisions:** Batch-02 closed under owner approval of that exact CSV only; all other scopes + production work excluded. Production Stage 8 still gated on real production data + named production site + rollout window + AI-R on exact release commit. Next Stage 6 matrix batch still requires a **new** owner-approved scope proposal before any run. Raw accounting **337 = 268 + 48 + 21** (never `270+48+20`).
**Open issues:** Untracked `v16.localhost/` at app root left unstaged (owner: can stay as-is). Parallel IMPORT can raise harmless `UniqueValidationError` after rows exist — never run IMPORT twice in parallel.

**Next:** Propose next bounded Stage 6 workflow-matrix scope (PROPOSAL ONLY) → owner approval → only then run. Always run hardened `uat_preflight.py` before Stage 8 validations. No production work authorized.

---

## 2026-09-23 — W6-3 batch-01 governed cycle CLOSED (test site)

**Accomplished:** Owner-approved W6-3 Stock batch-01 fully executed on `v16.localhost` only. Exact 250-row scope CSV sha `5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380`. Seven formula/letter source-equal rows found by the governed gate were reclassified technical; final disposition is 115 preserved-site-override + 17 EXCEPTION-technical + 0 already-released + 118 quorum-confirmed payload. Catalog **2,437** Released; IMPORT `updated=1` for the repaired `%` translation; post-DRY **IDEMPOTENT_OK** `2437/0/0/2437/0` drift=0; SYNC `created=0 updated=0`; decisions 2,437 (sha `14278d8306766aa799c78b8dcd0769cfe48f4faa104dbddc15bfdea9b77a0ef3`); freshness packaged=2437/critical_pass/has_drift=false; inventory 20,854 (merkle `04ba4a368184795aca1113b7239d3c44fff078ba335d5fcd987c539b9138d431`); full gate **errors=0** with evidence; module tests **270/270**; standalone 91 OK; Arabic browser evidence **21/21 PASS**; UAT preflight PASS; teardown (password `ct-w60b-rotated-off`, language `en`). Evidence index is bound to base HEAD `9a3f44f`; cycle commit `0bfc062e12ed1c96da253dadbaa230fa41009a60` (parent/base `9a3f44f`).

**Decisions:** Batch-01 closed under owner approval of that exact CSV only; batches 02/03 remain unapproved and all production work remains excluded. The seven source-equal formula/letter keys are technical exclusions, not Released fallback rows. Next Stage 6 matrix batch requires a new owner-approved scope proposal.

**Open issues:** Untracked `v16.localhost/` at app root remains unstaged per owner directive. Never run governed IMPORT concurrently; use one sequential site mutation at a time.

**Next:** Commit the closure records, then leave production and batches 02/03 gated. Do not run browser evidence after teardown. No production work authorized.

---

## 2026-09-24 — W6-3 batch-02 governed cycle CLOSED (test site)

**Accomplished:** Executed only the exact 250-row scope CSV `stage6_w603_batch02_rows_2026-09-23.csv` (SHA-256 `701ad13e6b4cc530ebd7dbd95705979b70055c46f39da37d4532a26ba60439ef`) on `v16.localhost`. Final disposition: **103 quorum-approved releases + 143 preserved Site Overrides + 2 technical exceptions + 2 deferred source defects**. Independent AI-R readback confirmed all 103 Packaged Releases at v1.6 and all 143 preserved values match; the four withheld rows were not released. Catalog 2,540 (sha `0101fc9d…`); decisions sha `dfdd4633…`; current live DRY `2540/0/0/2540/0`, drift=0; sync 0/0; freshness critical_pass; inventory 20,957 rows / Merkle `7ff7884d…`; full evidence-inclusive gate independently rerun errors=0 at base HEAD `e8d4846`; test envelopes bind 270 module tests and 91 standalone tests; Arabic browser evidence 8/8 with 246/246 translation matches. Administrator/System Settings language restored to `en`; temporary password file absent. AI-R report: `stage6-w603-ai-r-batch02-2026-09-24.md`.

**Evidence caveat:** some same-named `/tmp/opencode/stage2/` files were stale prior-batch captures and excluded. Tracked envelopes/index, fresh live DRY, fresh gate rerun and AI-R SELECT-only live readback were used. Host/DB timestamps are not a synchronized chronology. Evidence index binds pre-commit `e8d4846`; expected HEAD staleness applies after the closure commit until the next approved catalog event/re-pin.

**Decisions:** batch-02 is closed for the test site only. Batch-03 remains unapproved. Stage 8/production remains gated on real production data, a named production site and rollout window, plus explicit production authorization. Leave the pre-existing untracked `v16.localhost/` logs untouched; do not push without explicit request.

**Next:** prepare a bounded batch-03 proposal and present the exact CSV/SHA for separate owner approval. No batch-03 run or production work is authorized.

---

## 2026-09-24 — W6-3 batch-03 governed cycle CLOSED (test site)

**Accomplished:** Owner approved the exact 234-row W6-3 batch-03 scope CSV (sha `a5f0e9f604ea52d89072d2c744864fdcbc733bc8307fd427a5c2658f4855dbc9`) for `v16.localhost` only. Independent AI-A1/A2/A3 and AI-R passed. Exact result: 111 payload releases + 121 preserved Site Overrides + 2 technical exceptions (`UPC`, `UPC-A`). Live import created 111, updated 0, skipped 2540, drift 0; final dry-run **2651/0/0/2651/0**, catalog sync 0/0. Catalog now 2,651 Released; freshness `critical_pass=true`; inventory 21,068 rows / Merkle `57951175001159a0187ef6ea876b06ee67ae9b13f63524fa7cb89f9456f8e70c`.

**Verification:** hardened UAT preflight PASS (Redis 13000/11000, site 200, ar boot 12,953 messages, representative key, logout); browser 8/8 PASS with exact matches for all 232 payload/preserved values and no page errors; 270/270 module suite, 91/91 standalone; lints/scoped/vendor checks PASS; evidence-inclusive gate errors=0 on pre-commit HEAD `fb3e056` after atomic ten-envelope/index re-pin. Evidence index is expected to have the established HEAD mismatch after the closure commit, until next approved catalog event.

**Credential audit:** First console invocation exited before running UAT. During recovery the local test Administrator password was briefly set to literal `test`, immediately replaced with a fresh random credential before UAT, then the UAT credential was rotated again in teardown; final Administrator language is `en`. No production site/credential was involved. See the cycle report for the disclosure.

**Boundaries:** batch 04 and all other unapproved scopes untouched; no Stage 8 or production activity. Production remains held until real production data, named production site, rollout window, and explicit authorization are provided together. Existing untracked `v16.localhost/` logs remain excluded and untouched.
## 2026-09-24 — W6-4 Projects + Subcontracting batch-01 governed cycle CLOSED

Owner approved the exact 147-row CSV (SHA-256
`93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe`) for
`v16.localhost` only. Final partition: **48 Released + 96 preserved Site
Overrides + 3 deferred**. Proposal SHA `a9b9abaf…`; A1/A2/A3 PASS. Final
live DRY **2699/0/0/2699/0**, drift=0; health has no drift/orphans; catalog
2,699. UAT preflight PASS, browser 8/8 / 144/144 matches, standalone 92/92,
module 271/271, evidence-inclusive localization gate errors=0 on pre-commit
HEAD `eaadb014`; inventory 21,116 / Merkle `c62fb539…`.

The first 50-row draft uncovered two runtime-key normalization issues; the
exact two rows created by that draft were removed from the test site, then the
reviewed package was rebuilt at 48 releases. The `% for` formatter case and
two non-bindable edge/dynamic keys remain blank and deferred. UAT Administrator
language restored to `en`, temporary password rotated, secret removed.
Production and Stage 8 remain gated; no other Stage-6 batch was run. The
evidence index binds pre-commit HEAD; the expected HEAD mismatch follows the
closure commit until the next approved catalog-change re-pin.

**Next:** wait for a separate owner-approved Stage-6 scope proposal or for all
original Stage-8/production prerequisites. Do not push this local closure
without explicit request. Leave untracked `v16.localhost/` untouched.

## 2026-09-24 — W6-5 Setup batch governed cycle CLOSED

Owner approved the exact 469-row CSV (SHA-256
`e2d672c4a1b479f9cd52c017f76a3c8a8b1b24dced24ed4b5f5c6d8113900a09`) for
`v16.localhost` only. Final partition: **349 Released + 107 preserved Site
Overrides + 13 technical UOM exceptions**. Proposal SHA `7b0a4215…`; A1/A2/A3/AI-R PASS.
Final live DRY **3048/0/0/3048/0**, drift=0; health has no drift/orphans; catalog
3,048. UAT preflight PASS, browser 8/8 / 456/456 matches, standalone 92/92,
module 271/271, evidence-inclusive localization gate errors=0 on pre-commit
HEAD `51b8b7391704`; inventory 21,465 / Merkle `8d8301d1…`.

13 compound technical UOM/force unit tokens were classified through review as
`EXCEPTION-technical` (vendor rendering retained; empty translations; zero catalog release).
All 107 existing Site Overrides on `v16.localhost` (including FIFO and LIFO) were preserved verbatim.
UAT Administrator language restored to `en`, temporary password rotated, secret removed.
Production and Stage 8 remain gated; no other Stage-6 batch was run. The
evidence index binds pre-commit HEAD; the expected HEAD mismatch follows the
closure commit until the next approved catalog-change re-pin.

**Next:** wait for a separate owner-approved Stage-6 scope proposal or for all
original Stage-8/production prerequisites. Do not push this local closure
without explicit request. Leave untracked `v16.localhost/` untouched.
