# Session Memory — Construction ERP
**LAST UPDATED:** 2026-06-21 (VFC Phase 3 stabilization complete)
**UPDATED BY:** Cursor (WP1–WP7 rc-1.1 follow-up sprint + VFC Phase 3 stabilization)

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
  - Catalog rows are excluded from the runtime translation cache via monkey-patch in `construction.__init__`; only manual overrides affect the UI, so worker memory stays flat.
  - Editing a catalog row auto-promotes it to a manual override (`override_doctype_class` on `Translation`).
  - New list-view tools: Search Arabic Text, Show Catalog Entries, Show Manual Overrides, Show Empty PO Arabic, Sync Translation Catalog.
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
