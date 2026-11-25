# WBS P4 — Integrated Acceptance & Handover Record

## 1. Identity

| Field | Value |
|---|---|
| **Work item** | WBS First Increment (Execution Breakdown Tree, Stage Mapping & Reference Safety, Execution Coverage & Authorized Export) |
| **Package** | **P4 — Integrated Acceptance Gate & Handover** |
| **Actual root / branch / HEAD** | `/home/mohamed/frappe-bench/apps/construction` · `develop` · `98ef4f66fe5051e06bc309fae6e4d4c41a8a69fd` (`98ef4f6`) |
| **Base / upstream** | `origin/develop` at `98ef4f6` (synced; green CI run `45603791415`) |
| **Working-tree changes** | Documentation-only addition of this P4 record (`docs/ai/work-items/WBS/P4_INTEGRATED_ACCEPTANCE_AND_HANDOVER_2026-11-25.md`); zero code, schema, hook, or localization modifications |
| **Live acceptance site** | `v16.localhost` (`/home/mohamed/frappe-bench/sites`, `http://v16.localhost:8000`) — explicitly directed by the owner in this thread; all synthetic fixtures cleaned up with cryptographic baseline restoration proven |
| **Observed local runtime** | Ubuntu 24.04 (`x86_64`), MariaDB `10.11.14`, Bench venv Python `3.14.5` (system `python3 3.12.3`), Node `v24.15.0`, Frappe `16.51.1` (`2871914`), ERPNext `16.50.0` (`7474d9e`) |
| **Observed CI runtime** | GitHub Actions `ubuntu-24.04`, MariaDB `10.11`, Redis `alpine`, Python `3.14`, Node `24`, Frappe `16.51.1` (`2871914b` + reviewed private divergence `af440917`), ERPNext `16.50.0` |
| **Prior closed packages** | **P1** (`5e6fe93`, `47bad26`), **P2** (`98fd5a3`, `5b7ac58`, `43e84b2`, `cf42516`, `559b763`), **P3** (`b76abbf`, `98ef4f6`) — all pushed to `origin/develop` with green CI |

---

## 2. Package Commit Lineage (`develop`)

| Package | Commit(s) | Scope | CI Status |
|---|---|---|---|
| **P1** | `5e6fe93`, `47bad26` | Execution Breakdown Node tree foundation, project/company derivation, `ebs_code` concurrency counter, scope-aware tree API/UI, M1C contract | Closed · Green |
| **P2 Slice 1** | `98fd5a3`, `5b7ac58` | Optional `execution_node` / `planned_execution_node`, inheritance, `Execution Mapping Audit`, referenced leaf & ancestor protections, M1D contract | Closed · Green |
| **P2 Slice 2** | `43e84b2`, `cf42516` | Stage execution mapping API (`set_stage_execution_node`), historical/measured/out-of-balance mapping policy, execution-lock guards, M1E contract | Closed · Green |
| **P2 Slice 3** | `559b763` | Bilingual EN/AR form UX on `BOQ Item` and `BOQ Item Stage`, dirty-form & stale-async guards, 10 UI regression tests, M1F contract | Closed · Green |
| **P3 Slice 1** | `b76abbf` | Execution Coverage rules/service/API (`get_execution_coverage`, `export_execution_coverage`), streaming CSV/XLSX, BOQ Structure cutoff guard, M1G contract | Closed · Green (`45589844520`) |
| **P3 Slice 2** | `98ef4f6` | Bilingual EN/AR `execution-coverage` Frappe Page, selectable `BOQ Structure` subtree filter, P1 `View Coverage` drilldown, 7 coverage UI tests, P3-only M1H contract | Closed · Green (`45603791415`) |

---

## 3. Executed Verification & Evidence (on `HEAD = 98ef4f6`)

All checks below were executed on the exact committed candidate `98ef4f66fe5051e06bc309fae6e4d4c41a8a69fd`. Offline, native database, native upgrade, native Chrome browser, and CI layers are kept strictly separate.

### 3.1 CI Verification (`HEAD = 98ef4f6`)

- **Workflow Run:** `https://github.com/MohamedElrefae/constructionerp/actions/runs/45603791415` — **Status: `completed` / `success`**
  - **Stage-2 evidence protocol (round trip + CLI matrix):** `success` (pinned Frappe/ERPNext catalogs, protocol round trip, negative CLI matrix, frozen contract/live source agreement, standalone localization gate suite — `M1H`: `catalog=1298`, `files=351`, `wrapped=1094`, `json_labels=80`, `missing=0`).
  - **Server:** `success` (10 no-site migration regressions, clean Frappe/ERPNext/Construction install, translation transaction ownership, full site-backed Python business regression suites including `test_boq_structure_conversion` and `test_boq_structure_delete_safety`, quality linters, `ai_context_check` 12/12, JS property tests).

### 3.2 Native Repeated Upgrade & Legacy Preservation on `v16.localhost` (`W11`, `W18`)

Executed two consecutive `bench --site v16.localhost migrate` runs with SHA-256 snapshots of all commercial and Stage records (`BOQ Header`, `BOQ Item`, `BOQ Item Stage`) before Migrate #1, after Migrate #1, and after Migrate #2:

| Checkpoint | Exit | `BOQ Header` SHA-256 (23 rows) | `BOQ Item` SHA-256 (34 rows) | `BOQ Item Stage` SHA-256 (2 rows: 1 mapped, 1 unmapped `NULL`) |
|---|---|---|---|---|
| **Before Migrate #1** | `0` | `197ecb3ac72360724f48aaf8ef84a908ee3e47002053ab6b562021bd37ee9e5b` | `56650d17378b8955f3e04c3565c18dbd9973a02b5ed4fea2973e1d2b344f1865` | `5ad5963ed6119a4274d7f7b33d6d80ce82322c4a22306c8e8a84d7416d182790` |
| **After Migrate #1** | `0` | `197ecb3ac72360724f48aaf8ef84a908ee3e47002053ab6b562021bd37ee9e5b` | `56650d17378b8955f3e04c3565c18dbd9973a02b5ed4fea2973e1d2b344f1865` | `5ad5963ed6119a4274d7f7b33d6d80ce82322c4a22306c8e8a84d7416d182790` |
| **After Migrate #2** | `0` | `197ecb3ac72360724f48aaf8ef84a908ee3e47002053ab6b562021bd37ee9e5b` | `56650d17378b8955f3e04c3565c18dbd9973a02b5ed4fea2973e1d2b344f1865` | `5ad5963ed6119a4274d7f7b33d6d80ce82322c4a22306c8e8a84d7416d182790` |

- **Result:** **PASS** — both migrations exited `0`; 100% of commercial fields, quantities, statuses, and unmapped `NULL` legacy links remained byte-for-byte identical.

### 3.3 Native Integrated Backend & Real Multi-Connection DB Concurrency Suite on `v16.localhost` (`W01`–`W15`)

Executed `verify_p4_integrated.py` directly against `v16.localhost` (`exit 0`, `"status": "ALL_PASS"`):

- **`W01_W02` (Tree & Company Derivation):** Created `Execution Breakdown Node` group + leaves (`EBS-0001`..`EBS-0003`) as ordinary `Project Manager` (`planner_a`), verified derived company, verified cross-project parent rejected, verified `BOQ Item` count unchanged.
- **`W03` (Real Database Concurrency):** Spawned 6 concurrent threads with 6 independent MariaDB connections inserting sibling nodes under the same Project; all 6 committed with 6 strictly unique codes (`EBS-0005`..`EBS-0010`), zero duplicates, zero corrupted state.
- **`W04` (Pre-Stage Ordinary-User Auth):** Before any Stage links existed, `planner_a` read/searched Project A (`10` nodes) and was denied Project B; `planner_b` was denied Project A.
- **`W05`–`W09` (Mapping Lifecycle, Auth, Historical/Out-of-Balance VO, Quantity Preservation):**
  - `Accountant` and `Site Engineer` (measurement-only) denied `set_stage_execution_node` with `PermissionError`.
  - Group node, foreign-project node, and disabled node assignments rejected.
  - Locked + measured (`50`) + certified (`30`) + out-of-balance VO Stage (`120` planned vs `200` item qty) rejected without reason, succeeded with explicit reason via dedicated route, wrote `Execution Mapping Audit` (`is_historical_assignment=1`), and kept cryptographic commercial hash (`BOQ Item` + `BOQ Item Stage` quantities/rates/statuses) 100% unchanged.
- **`W10` (Referenced Leaf & Ancestor Protection):** Blocked `delete_node` on referenced leaf, blocked `delete_node` on referenced ancestor, blocked `is_group=1` conversion on referenced leaf, blocked `move_node` reparenting on referenced leaf; allowed `set_disabled=1` (historical preservation) and rejected new assignment to disabled leaf.
- **`W12`–`W15` (Coverage, Subtree Filter, Mixed UOM, Read-No-Writes, Scope & Export Parity):**
  - Reconciled `total_stages=4 == healthy_linked(2) + unlinked(1) + link_issues(1)` (`disabled_links=1`, `integrity_issues=0`, `coverage_pct=50.0%`), `items_without_stages=1` separate, zero mixed-UOM grand total.
  - `BOQ Structure` group filter narrowed strictly to `2` descendant Stages (`50.0%`) with exact CSV/XLSX row-order parity.
  - Contradictory `execution_node + unlinked` returned `filter_conflict.code = "node_with_unlinked"`, `total_stages=0`, `coverage_pct_display="N/A"`.
  - `planner_b` denied both `get_execution_coverage` and `export_execution_coverage` for Project A.
  - DB counts and commercial hash proven identical before/after reads & exports (`read_no_writes_verified: true`).
- **Cleanup Proof:** `cleanup_verified: true`, `legacy_hash_unchanged: true` across all 10 tracked DocTypes on `v16.localhost`.

### 3.4 Native Chrome Browser End-to-End Acceptance on `http://v16.localhost:8000` (`W16`)

Executed via live Chrome Desk session (`p4_desk_e2e@example.com` scoped to temporary fixture `PROJ-0112`, verified against DB and cleaned up after):

1. **Create Tree in Desk** (`/desk/construction-home/execution-breakdown`): Created root group `P4 Tower Main` (`EBN-10034` / `EBS-0001`), leaf `P4 Floor 1` (`EBN-10035` / `EBS-0002`), leaf `P4 Floor 2` (`EBN-10036` / `EBS-0003`) via Desk UI dialogs.
2. **Map Stage & Hard-Reload** (`/desk/boq-item-stage/BOQ-STG-10031`): Mapped `STG-01 — P4 Pour Stage 1` to `EBS-0002 — P4 Tower Main / P4 Floor 1` (`EMA-0000025`); after `page.reload()`, `P4 Floor 1` remained persisted and `planned_qty` stayed `60.00`.
3. **View Coverage Drilldown:** Clicked **View Coverage** on `1.1 P4 Floor 1` → opened `/desk/construction-home/execution-coverage?project=PROJ-0112&execution_node=EBN-10035&view_mode=stages` showing `1` Matching Stage (`100.0%`).
4. **Full Coverage, BOQ Structure Subtree Filter, Tabs, Conflict Banner & Exports:**
   - Unfiltered `PROJ-0112`: `3` Matching Stages (`1` Healthy Linked, `2` Unmapped, `0` Needs Review, `33.3%`), `1` No Stages item.
   - `#ct-cov-boq-structure` = `01 — P4 Civil Superstructure [Group]` (`mlpf71ilk6`): narrowed strictly to `2` rows (`P4 Pour Stage 1`, `P4 Pour Stage 2`, `50.0%`), excluding `P4 Mobilization Stage`.
   - **Download CSV** (`execution_coverage_PROJ-0112_stages.csv`) & **Download Excel** (`execution_coverage_PROJ-0112_stages.xlsx`) triggered cleanly with `boq_structure=mlpf71ilk6`.
   - **No Stages** tab displayed `01.002 — P4 Closeout Dossier`.
   - Contradictory filter (`EBS-0002` + `Unmapped`) displayed the `role="alert"` explanation banner, `0` Matching Stages, `N/A` completeness, and `No Stages: 1 (Zero Matching Stages: 2)`.
5. **Forbidden Delete on Referenced Node:** Clicked **Delete** on `1.1 P4 Floor 1` → confirmed **Yes** → server returned HTTP `417` and Desk displayed `"Cannot delete this execution location or branch because it is referenced by a BOQ Item Stage."`. After reload, all 3 nodes (`P4 Tower Main`, `P4 Floor 1`, `P4 Floor 2`) remained intact.
6. **Post-Journey DB & Cleanup Proof:** `fixture_commercial_unchanged: true`, `stage_1_mapped_node_persisted: "EBN-10035"`, `mapping_audits_recorded: ["EMA-0000025"]`, `cleanup_verified: true`, `legacy_hash_unchanged: true` on `v16.localhost`.

### 3.5 Offline & Static Consistency Gates (`W17`)

- `pytest tests_offline -q`: **357 passed, 85 subtests passed**
- `python3 -m unittest discover -s construction/tests/tools -p 'test_stage2_contract_source_agreement.py'`: **8/8 OK**
- `python3 -m unittest discover -s construction/tests/tools -p 'test_stage2_evidence_shallow_vendor.py'`: **6/6 OK**
- `python3 scripts/schema_drift_checker.py`: **PASS** (24 schema-owning DocTypes, 1 override-only)
- `python3 scripts/ai_context_check.py`: **12/12 PASS** (including `9` JS test files, `200 passed, 0 failed`)
- `pre-commit` (`ruff`, `ruff-format`, `prettier`, `eslint`, metadata lint) & `git diff --check`: **PASS**

---

## 4. Verification Matrix (`W01`–`W18`)

| ID | Requirement | Package | Evidence Layer | Status |
|---|---|---|---|---|
| **W01** | Separate execution tree; no auto BOQ Item creation | P1 | Native `v16.localhost` + CI (`test_execution_tree`) | **PASS** |
| **W02** | Same-project hierarchy and derived company | P1 | Native `v16.localhost` + CI | **PASS** |
| **W03** | Stable unique execution code per project under concurrency | P1 | Real 6-connection MariaDB concurrency on `v16.localhost` | **PASS** |
| **W04** | Node permissions before any Stage links | P1 | Ordinary-user native API on `v16.localhost` + CI | **PASS** |
| **W05** | Optional Stage mapping preserves quantities/history | P2 | SHA-256 before/after snapshots on `v16.localhost` | **PASS** |
| **W06** | Explicit create/map/relink/clear authority (deny measurement-only) | P2 | Native ordinary-user denial (`Accountant`, `Site Engineer`) + offline tests | **PASS** |
| **W07** | Valid same-project eligible leaf (reject group/foreign/disabled) | P2 | Native `v16.localhost` + offline tests | **PASS** |
| **W08** | Historical lifecycle handling (Draft/Locked/measured/certified) | P2 | Native `v16.localhost` with mandatory reason + `Execution Mapping Audit` | **PASS** |
| **W09** | Out-of-balance mapping handling without hidden qty mutation | P2 | Native VO out-of-balance fixture on `v16.localhost` | **PASS** |
| **W10** | Referenced subtree identity safety (leaf + ancestor) | P2 | Native API (`v16.localhost`) + Live Desk (`W16`) | **PASS** |
| **W11** | No auto historical mapping across repeated upgrades | P2 | 2× consecutive `bench migrate` + SHA-256 proof on `v16.localhost` | **PASS** |
| **W12** | Coverage count reconciliation (`0/0 -> N/A`, `No Stages` separate) | P3 | Native `v16.localhost` + offline tests + Desk UI | **PASS** |
| **W13** | Filters (BOQ Structure subtree, node+unlinked) & non-financial disclaimer | P3 | Native `v16.localhost` + Live Desk (`W16`) + 7 JS tests | **PASS** |
| **W14** | No mixed-UOM totals; reads/exports perform zero DB writes | P3 | Mixed `m3`/`m2`/`LS` fixture + DB count/hash proof on `v16.localhost` | **PASS** |
| **W15** | No scope leak in counts, navigation, or CSV/XLSX exports | P3 | Cross-project denial + CSV/XLSX parity on `v16.localhost` | **PASS** |
| **W16** | End-to-end native acceptance (create→map→reload→coverage→forbidden delete) | P4 | Live Chrome Desk on `http://v16.localhost:8000` + DB verification | **PASS** |
| **W17** | Documentation, schema, localization (`M1H`), and regression consistency | Each | `ai_context_check` 12/12, `schema_drift_checker`, Stage-2 14/14, CI `45603791415` | **PASS** |
| **W18** | Supported runtime & upgrade claims bounded | P4 | Repeated migrate on `v16.localhost` + CI `ubuntu-24.04` (see Section 6) | **PASS (Bounded)** |

---

## 5. Decisions Register (`D01`–`D10`)

| ID | Selected Rule | Governance / Spec Reference |
|---|---|---|
| **D01** | Legacy Stages remain unmapped (`NULL`) by default; explicit authorized mapping only | `P2_EXECUTION_MAPPING_SPEC_2026-11-24.md` |
| **D02** | Historical/measured/certified mapping requires explicit reason & records `Execution Mapping Audit` | `P2_EXECUTION_MAPPING_SPEC_2026-11-24.md` |
| **D03** | Narrow invariant-preserving mapping-only API (`set_stage_execution_node`) succeeds on out-of-balance VO without mutating quantities/statuses | `P2_EXECUTION_MAPPING_SPEC_2026-11-24.md` |
| **D04** | Planning-level roles (`Project Manager`, `Construction Owner`, `System Manager`) required; `Site Engineer` & `Accountant` denied writes | `execution_tree_rules.py`, `execution_mapping.py` |
| **D05** | New assignments restricted to enabled leaves; existing disabled links preserved and surfaced under `Needs Review -> Disabled Links` | `P2_EXECUTION_MAPPING_SPEC_2026-11-24.md`, `P3_EXECUTION_COVERAGE_SPEC_2026-11-25.md` |
| **D06** | Structural changes (delete, reparent, leaf/group conversion, project change) blocked on referenced leaves and ancestors; disabling/renaming allowed | `execution_tree.py`, `execution_mapping.py` |
| **D07** | Contract and Tender Headers across Draft, Pricing, Frozen, and Locked included; Header type & status displayed visibly | `P3_EXECUTION_COVERAGE_SPEC_2026-11-25.md` |
| **D08** | Stable project-scoped `ebs_code` (`EBS-0001`...) via `Execution Code Counter` lock; no historical renumbering | `execution_tree.py` |
| **D09** | `coverage_pct = healthy_linked / total_stages`; `0/0 -> N/A`; `Needs Review` split into `Disabled Links` + `Integrity Issues`; `No Stages` separate | `P3_EXECUTION_COVERAGE_SPEC_2026-11-25.md` |
| **D10** | Reuses audited `User Scope Context` + tree browse roles + native BOQ read permissions identically across UI, API, and CSV/XLSX exports | `execution_tree_access.py`, `execution_coverage.py` |

---

## 6. Bounded Supported-Runtime Matrix (`W18`)

Verification claims are strictly bounded to the tested combinations below:

| Combination | Tested? | Evidence |
|---|---|---|
| Ubuntu 24.04 · MariaDB 10.11.14 · Python 3.14.5 · Node 24.15 · Frappe 16.51.1 (`2871914`) · ERPNext 16.50.0 (`7474d9e`) | **YES (Native + Repeated Migrate + Browser)** | `v16.localhost` P4 suite + 2× `bench migrate` + Chrome W16 |
| GitHub Actions Ubuntu 24.04 · MariaDB 10.11 · Redis Alpine · Python 3.14 · Node 24 · Frappe 16.51.1 (`af440917` private pin) · ERPNext 16.50.0 | **YES (Clean Install + Full CI)** | Run `45603791415` (`success`) |
| Frappe v15 / v14, PostgreSQL, non-Ubuntu OS, older Python (<3.14) or older Node (<24) | **NOT TESTED** | Explicitly excluded from support claims |

---

## 7. Findings & Deferred Items (Non-Blocking Transparency Log)

| ID | Classification | Observation | Impact & Disposition |
|---|---|---|---|
| **F-P4-01** | Minor P1 UI UX defect (runtime-reproduced during W16) | In `construction/construction/page/execution_breakdown/execution_breakdown.js:592-597` (and `move_node` at `:539-544`), the `.catch()` block clears the rendered tree and prints `"Not permitted."` after any failed mutation — including a `417 ValidationError` (such as blocked deletion of a referenced leaf), even though Frappe already displayed the accurate validation dialog. Reloading immediately restores the intact tree. | **Zero data loss, zero security defect.** Server properly blocks the delete (`HTTP 417`) and preserves all nodes/links. Tracked as a small optional follow-up UX polish item outside frozen P1–P3 scope. |
| **F-P4-02** | Pre-existing unrelated scope/auth interaction (observed during W16) | When an invalid password is submitted to `POST /api/method/login` while Scope Enforcement is enabled, Frappe's `add_authentication_log` triggers `"Scope enforcement is active: Guest sessions cannot modify scoped documents."` alongside `"Invalid login credentials"`. Valid sign-ins succeed cleanly. | Unrelated to WBS P1–P4; logged for future scope-enforcement hardening if desired. |
| **D-A1** | Pending separate owner decision (explicitly split out of P3) | Optional future restriction preventing planners from setting or changing a `BOQ Item`'s `planned_execution_node` default once any `BOQ Item Stage` exists on that Item. | **Not included in P3/P4.** Approved P2 Choice B behavior (default may still be updated for future Stages) remains intact unless the owner explicitly approves A1 as a separate change. |

---

## 8. Owner Completion Checklist (`07_OWNER_REVIEW_CHECKLIST.md`) & Scope Exclusions

- [x] **End-to-end mapping journey works:** Verified natively in Chrome Desk + MariaDB on `v16.localhost` (create tree → map Stage → reload → View Coverage → BOQ Structure subtree filter & CSV/XLSX export → blocked delete on referenced node).
- [x] **Coverage does not misrepresent mapping as progress:** Non-financial disclaimer shown in UI and exports; count-based completeness only; zero mixed-UOM grand totals.
- [x] **Unmapped legacy records remain valid:** Verified across 2× consecutive `bench migrate` runs with byte-identical SHA-256 hashes.
- [x] **Final verified baseline and known limits documented:** Recorded in Sections 1, 6, and 7 above.
- [x] **Scope exclusions confirmed:** Zero duplicate quantity owner, zero Allocation Plan / `allocated_qty`, zero Stage generator, zero measurement/payment certificate ledger, zero `certified_qty` reinterpretation, zero broad VO redesign, zero `construction/hooks.py` mutation in P2–P4.
- [x] **No release/deployment inference:** Production rollout/deployment remains a separate owner-governed decision.

---

## 9. Handover Summary

- **Completed:** WBS P1, P2, P3, and **P4 Integrated Acceptance Gate** (`W01`–`W18`) verified on `HEAD = 98ef4f66fe5051e06bc309fae6e4d4c41a8a69fd` (`develop`, green CI `45603791415`).
- **Not executed:** Unsupported runtime matrix combinations (Section 6) and production deployment (out of scope).
- **Blocked:** None.
- **Next exact action:** Owner review of this P4 handover record and explicit authorization to commit & push `P4_INTEGRATED_ACCEPTANCE_AND_HANDOVER_2026-11-25.md` to close the WBS First Increment (and optional separate decision on **F-P4-01** UX polish and **D-A1**).
