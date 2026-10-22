# F38 — Candidate freeze + authorization request (2026-10-15)

**One package, three explicit authorizations requested. Nothing here has been executed.
No commit, push, publication or deployment has occurred. Delivery approval is NOT
requested here (see §6).**

## 0. Candidate identity (freeze)

| Fact | Value |
|---|---|
| Base HEAD | `fa380226d641f32f749c7ae003f82eeb6404ba2c` (fix(migrate): reconcile translation review status options) |
| Candidate content | HEAD + tracked worktree diff + untracked files listed in snapshot manifest |
| Tracked diff sha256 | `e5704e5fd0b794a9…` (frozen at end of the F25-sweep + D4-rebuild turn; register/matrix/evidence docs are untracked and do not enter the diff — regenerate `git diff HEAD | sha256sum` at commit time and compare) |
| Uncommitted entries | 159 total / 107 untracked entries · 174 hashed untracked files (105 entries at F37 start → +F37 evidence, F43 pack, F37 logs/scripts, F38 package) |
| Vendor trees | frappe `2871914` clean · erpnext `7474d9e` clean (F38-D001 reversion verified) |
| Staged distribution | `verify_staged_distribution.py` → **STAGED VERIFICATION PASSED** (`docs/DISTRIBUTION.md` set, never-ship absent) |
| Startup checks | `ai_context_check.py` → ALL CHECKS PASSED · `schema_drift_checker.py` → match (21 schema-owning DocTypes) |

Candidate under test = this exact content. Any change after approval voids the request.

## 1. Authorization A — commit the F38 batch (local only)

Proposed batch structure (single commit preferred; order preserved if split):

1. Product: `boq_permissions.py`, `file_permissions.py`, `file_download.py`,
   `cost_database_service.py`, `boq_report_service.py`, `construction_reports.py`,
   `scope_context_api.py`, `boq_header.js`, `boq_import_service.py`,
   `boq_cost_analysis_detail/*.json`, `variation_order.py`, `boq_item_stage.py`,
   `vite_layout_controls.js` + `vite_form_override.css`, sidebar json,
   `workspace_sidebar_items.json`, hooks (`?v=` bumps + download override registration +
   **F25-D003 hygiene: `web_include_css` `modern_theme.css` `2.5.8`→`2.5.9`, aligning both
   registrations — same bytes served, cache-buster consistency only**),
   `construction_report_viewer`/`cost_database_workbench` pages,
   `erpnext-mcp-server/server.py`, `pyproject.toml`
2. Tests: the 7 regression suites listed in F38 evidence §"Tests"
3. Scripts: permission reconciliation + grant scripts + staging verifiers
4. Docs (customer set marked): README packaging note, `docs/CUSTOMER_ONBOARDING.md`,
   `docs/MAINTENANCE.md`, `docs/DISTRIBUTION.md`, runbook §0.3–0.6, F39–F41 guides
5. Translations: `approved_ar_overrides.csv` (F31-D001 controlled edit)
6. Program evidence (internal, `docs/ai/`): register, closure matrix, decision sheet,
   F10 reassessment, F28/F31/F36/F37/F38/F43 evidence, SESSION_MEMORY
7. Deletions: `setup.py`, Sidebar `.bak`s

**Excluded from the batch (needs separate decision):**

- `orchestrator/engine.py` (+ opencode binary paths) — environment tooling predating the
  program; stash or separate commit, never inside F38.
- Living docs with program-adjacent edits: `CI_READINESS.md`, `PLAN.md`, `PRIVATE_CI.md`,
  `STATUS.md`, `VERIFICATION.md`, `CONTEXT_INDEX.md`, `SCHEMA_FACTS.md`, `USER_GUIDE.md`,
  `docs/handover/INDEX.md` — owner to confirm scope at commit time.
- Never-ship: `maps/*.map`, 12 relocated test PNGs stay in evidence paths (already out of
  staged set).

**Requested action:** approve batch composition (or amend §1/§3 exclusions), then
engineering commits locally. Push is a separate, later decision — not requested.

## 2. Authorization B — private CI execution on the exact committed candidate

- Repo/branch: `MohamedElrefae/constructionerp-private` (observed Private before/after),
  working branch per Run-11 convention (e.g. `codex/foundation-ci-20261015`).
- Candidate: the commit from Authorization A (SHA recorded in this file at run time).
- Pins: frappe/erpnext at the qualified versions (frappe `2871914` = 16.51.1,
  erpnext `7474d9e` = 16.50.0). The CI pin mapping (prepared) reconciles the workflow lock
  against these qualified hashes — **run with the mapping applied and record which pins
  executed**; do not silently substitute.
- Gates to pass: install/setup · Python business regression (19 modules, 260 tests —
  matching the local single-pass of 2026-10-15) · JS property tests · linters.
- Evidence: run URL, logs and SHA archived under `isolated-qualification-evidence-2026-10-15/`
  and referenced from F35/F38 rows.
- Scope: private CI only. No public visibility change, no customer deployment.

## 3. Authorization C — final installation route (committed candidate)

Per the isolated-qualification plan, on the isolated lab sites (shared-DBA provisioning
remains out of scope):

1. `bench get-app` the committed candidate into a **fresh** lab bench; record SHA.
2. Fresh install + migrate (twice, second exit=0 clean) — extends existing
   `fresh-clean-migrate-1/2.log` evidence onto the committed candidate.
3. Upgrade route on a copy: restore baseline copy → replace app with committed candidate
   → migrate → verify counts unchanged vs baseline (36/94/162/12/235/45 on rehearsal
   fixtures or the lab equivalent).
4. Re-confirm F32 recovery restore on the final candidate (timed restore log exists;
   re-run only if the candidate changed recovery behavior).

Outcome recorded in F31/F32 rows; F31 stays INCOMPLETE until this passes.

## 4. What this package does NOT request

- No push to `origin/develop` (separate later decision).
- No delivery/publication to any customer channel; no `bench get-app` from a public URL.
- No production activation, site overwrite, credential reset or privilege change.
- No F44 execution (owner) and no F45 decision — both stay with the owner after the gates.

## 5. Remaining engineering obligations at freeze (disclosed, not hidden)

- F25 full-asset sweep **completed 2026-10-15**: all 38 registered assets byte-identical
  source↔served (0 missing, 0 unsynced, 0 mismatch); F25-D003 hygiene finding —
  `modern_theme.css` version split (desk `2.5.9` vs web `2.5.8`, same bytes served).
  One-line `web_include_css` alignment added to this batch (§1) with a standing rule to
  bump both registrations together.
- F27 bridge per-user authorization — operators-only posture stands; NO customer path.
- F10 historical inconsistencies: preserved and disclosed; acceptance uses clean fixtures.
- The BOQ-2026-0209 lab fixture (Approved revisions are permanent by design; kept as
  documented fixture state, recorded in F37 evidence §2).
- F12/F11 access-policy findings stay open for owner acceptance.
- Delivery scratch repo `/tmp/opencode/customer-repo`: **rebuilt and re-verified
  2026-10-15** after the `/tmp` cleanup wiped the earlier one (1,252 files, 1 commit
  `1f575b2b…`, 0 remotes, 0 never-ship paths, byte-identical — still unpublished). Because
  it lives in volatile `/tmp`, **re-run the rebuild+verify at delivery time from the
  committed candidate**; method and script preserved in the program repo.

## 6. Delivery approval (kept separate, per D4)

Curated set prepared and verified offline; separate clean repository verified (1 commit,
0 remotes, no never-ship paths). **Publication requires its own explicit approval** —
requested only after Authorization A–C complete and the owner chooses to authorize
delivery.
