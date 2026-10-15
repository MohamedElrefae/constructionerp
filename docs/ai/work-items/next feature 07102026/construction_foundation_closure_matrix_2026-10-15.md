# F01–F45 closure matrix (2026-10-15)

Candidate: `fa38022` + worktree snapshot (diff `66082350`, 92 untracked files hashed).
Evidence binds this tree on stated sites unless noted. Owner acceptance (F44) and F45 open
throughout; "Engineering verified" never means owner-accepted.

| Task | Status 2026-10-15 | Evidence / candidate | Remaining action → dependency | Done-when |
|---|---|---|---|---|
| F01 kickoff/gaps | Engineering verified | gap ledger + K-01 reproductions | none | closed |
| F02 env + recovery baseline | In progress | UAT manifest; backups 20261014_* verified; lab now exists | isolated-site battery → lab available | restore+recovery on lab |
| F03 inventory | Engineering verified | source/site reconciliation D001–003 | none | closed |
| F04 fixtures/roles | In progress | 7 sessions, persona matrix; credentials rotated 2026-10-15 (see isolated qual) | revalidate logins post-rotation → none | owner confirms access |
| F05 totals/factors | Engineering verified | 13/13 | none | closed |
| F06 VO/history | Engineering verified | 25/25 + D001 chain | none | closed |
| F07 projection/cancel | Engineering verified | 18/18 | none | closed |
| F08 concurrency | Engineering verified | 4/4 | none | closed |
| F09 stages | Engineering verified | 15/15 | none | closed |
| F10 legacy/integrity | Preserved per owner direction; acceptance dataset separate | [Reassessment](construction_foundation_f10_reassessment_2026-10-15.md): D001 6 headers with exact amounts; D002 197 orphans; D003 8 items; D004 4 structs; D005 11 VOs; D006 9 items; 54 missing paths classified (all BOQ-2026-0002 print/export residue, none signed) with embedded ID list. No repairs applied | steward/business approvals per item |
| F11 authorization | In progress | matrix + scope boundary + 10/10 fail-before | residual denials → none | owner acceptance |
| F12 scope/reports | In progress | disposition closed (finance-only) | 15-report disposition + ON/OFF evidence → lab | ledgers stay finance-only |
| F13 deps/security | Engineering verified | runtime manifest | CI-pin vs bench mapping → F35 run | closed |
| F14 bounds/exports | Engineering verified | 27/27 | none | closed |
| F15 secrets/audit | Engineering verified | controls + suites; no secrets in repo | owner acceptance | — |
| F16 import repair | Engineering verified | 8/8 + K-01 two-step | F36-D003 fixed + verified | owner retest |
| F17 import review | Engineering verified | 17/17 | none | closed |
| F18 cost DB UI | Engineering verified | workbench 8/8 + narrowings | owner retest | — |
| F19 reports | Engineering verified | 10/10 + adapters | owner retest | ledgers excluded |
| F20 handoffs | Engineering verified | 26/26 personas | owner retest | — |
| F21 workspaces | Engineering verified | 7/7 reach + Sidebar fixture | owner UI | — |
| F22 Arabic UI | Engineering verified | 19/19 + 8/8 + coverage 5/5 | reviewer pass + D007 closed | — |
| F23 VFC/theme | Engineering verified | 18/18 + D002 10/10 | owner acceptance | — |
| F24 overrides | Engineering verified | 6 signatures + wrapper health | vendor-bump re-check rule | — |
| F25 runtime/assets | Engineering verified (full sweep 2026-10-15) | [F25 evidence](construction_foundation_f25_evidence_2026-10-14.md): 38/38 registered assets byte-identical source↔served, 0 missing/unsynced/mismatch; F25-D003 version-split finding dispositioned into F38 batch | none |
| F26 scaffolds | Engineering verified (classified) | CostItem/React/dead-code classification | F30 removals done; tables preserved | — |
| F27 bridge | Retrieval fixed; operators-only (D3) | 3/3 rows; posture recorded | per-user auth open; NO customer path | — |
| F28 delivery | Packaging implemented; route prep verified | 1,239-member rebuild; 1,244-file scratch repo verified | delivery approval open | — |
| F29 docs | Prerequisite met; guides delivered | README + 4 guides + index | audience sign-off | — |
| F30 refactoring | Completed in scope | .bak removed; switch_theme retained (test-pinned) | none | closed |
| F31 install/upgrade | Rehearsal verified; INCOMPLETE (fresh/isolated) | migrate + replay clean; lab fresh/upgrade per isolated qual | DBA/lab-gated final route + committed candidate | — |
| F32 recovery | Lab-executed per isolated qual; rehearsal prep done | 138.907s restore; rehearsal backup sets verified | re-confirm on final candidate | — |
| F33 monitoring | Preparation complete | runbook + probes; lab execution per plan §4 | lab failure drills → lab ready | owner walkthrough |
| F34 assisted setup | Explicit dependency: qualified fresh site | guides + rehearsal import proof | lab fresh-site run → lab ready | Finance sign-off |
| F35 CI/coverage | Local 19/19 (260 tests); CI run open | single-pass 2026-10-15; pins prepared | matching CI execution | — |
| F36 browser | Engineering verified (38/38) | lifecycle + import + first-round | owner acceptance | — |
| F37 workload | Engineering verified at D1 scale (lab) | [F37 evidence](construction_foundation_f37_evidence_2026-10-15.md): dataset complete (2 projects, 200 items, 50 analyses, 5 VOs mixed states, 6-mo history); reads (150 rows ~0.57s) + writes (single-winner approvals, same-VO race no dup revisions, parallel approvals independent, stage measure last-writer-wins via TimestampMismatch refusal); residue 0/0 | owner limits commentary | lab measurement complete; production business volumes out of scope by decision (not a capacity promise) |
| F38 defects | Candidate review complete; authorization package prepared | reconciled table; F38-D001 reverted; UOM fix; D001 test fix; F37 evidence + F43 pack completed | commit + private-CI authorization (package prepared) | F44/F45 |
| F39 README | Engineering verified | packaging note + pointers | owner acceptance | — |
| F40 task guides | Engineering verified | 5 tasks EN/AR + troubleshooting | reviewer pass | — |
| F41 handover | Walkthrough scheduled (D2) | guides + inventory delivered | post-F31/F32 walkthrough | owner sign-off |
| F42 baseline | Approved (D1) | Egypt-SME profile | concurrency/volumes before F37 | — |
| F43 UAT prep | Pack complete (step text + session plan) | [F43 pack](construction_foundation_f43_pack_2026-10-15.md): UI-01–69 + F18/F19-U + COV/F21-U/defect retests mapped; 8 sessions + reserve (~14 h); preflight + evidence rules | engineering gates in F38 package | Mohamed executes |
| F44 acceptance | Proposed (consolidated block) | — | F43 + engineering complete | Mohamed executes |
| F45 decision | Open | — | all gates + acceptance | recorded owner decision |

## Stale-reference reconciliation (this turn)

- F33/F34/F37 "DBA-blocked" wording is stale: the isolated lab removes the shared-DBA dependency for engineering execution. Rows now point at lab execution; DBA provisioning remains relevant only for shared-bench fresh sites.
- F31-D001/D002 closed with corrected evidence language (quorum precision; privilege-dependent visibility).
- Count baseline: 19 modules / 260 tests, verified per-module live 2026-10-15 (all OK):
  boq_properties 17, quantity_revisions 31, variation_orders 27, cost_analysis_engine 38,
  cost_database_api 26, customer_release_financial_guards 12, boq_transactions 12,
  boq_wbs_generation 2, boq_structure_conversion 1, boq_structure_delete_safety 1,
  boq_excel_parser 4, boq_rollup_audit 5, bilingual_install_schema 6,
  boq_legacy_cost_conversion 8, boq_parent_permissions 6, bilingual_desk_link_dispatch 17,
  stage7_bilingual_reports 34 (24+10 split batches; static method count confirms 34),
  packaged_translation_adoption 6, report_export_authorization 7. Prior 236 understated stage7.
- Vendor trees: frappe clean at 2871914; erpnext reverted to clean at 7474d9e (F38-D001).
