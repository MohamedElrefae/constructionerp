# Construction ERP — Documentation index

**Audience:** Internal engineering, operators and management  
**Updated:** 12 October 2026  
**Purpose:** Find the right document and understand its scope. This index is not an approved customer-delivery bundle or a release sign-off.

## 1. Current foundation program

| Need | Canonical entry | Standing |
|---|---|---|
| Scope, priority, dependencies and acceptance | [Foundation master plan](<ai/work-items/next feature 07102026/construction_foundation_remediation_master_plan_2026-10-12.md>) | Existing defects/enhancements before new modules |
| Current task/issue state and next queue | [Foundation work register](<ai/work-items/next feature 07102026/construction_foundation_work_register_2026-10-12.md>) | Current status for this program; names/site and qualifications remain open |
| G01–G16 reconciliation | [Gap ledger](<ai/work-items/next feature 07102026/construction_foundation_gap_ledger_2026-10-12.md>) | Dated evidence versus residual candidate-specific work |
| Cost database / repricing design | [F18 draft](<ai/work-items/next feature 07102026/construction_foundation_f18_service_contract_design_2026-10-12.md>) | Current service contracts plus preview/permission/provenance requirements; not implemented |
| Existing reports / integrity design | [F19 draft](<ai/work-items/next feature 07102026/construction_foundation_f19_service_contract_design_2026-10-12.md>) | Five views, bounded authorization/export and literal Administrator audit; not implemented |
| Existing forms, methods and coverage | [F03 route inventory](<ai/work-items/next feature 07102026/construction_foundation_feature_route_inventory_2026-10-12.md>) | Source inventory; installed-site reconciliation pending |
| Framework hooks and compatibility | [F24 register](<ai/work-items/next feature 07102026/construction_foundation_override_compatibility_register_2026-10-12.md>) | Source mapping; runtime matrix pending |
| Runtime, CI, dependencies and assets | [F25 review](<ai/work-items/next feature 07102026/construction_foundation_runtime_asset_consistency_review_2026-10-12.md>) | Five constraint conflicts require F13/F25 resolution |
| Package and delivery contents | [F28 artifact review](<ai/work-items/next feature 07102026/construction_foundation_delivery_artifact_review_2026-10-12.md>) | Flit3.12 compliant artifacts verified; input/delivery decision and install/replay qualification pending |
| Documentation organization and preservation | [F29 review](<ai/work-items/next feature 07102026/construction_foundation_documentation_organization_review_2026-10-12.md>) | Internal classification, navigation notes and remaining guide work |
| Owner test steps | [UI acceptance plan](<ai/work-items/next feature 07102026/existing_features_owner_ui_acceptance_plan_2026-10-12.md>) | Add F03/F18/F19 coverage; existing test groups remain unexecuted unless results show otherwise |
| Actual owner test outcomes | [UI results](<ai/work-items/next feature 07102026/owner_ui_test_results_2026-10-12.md>) | Every pass requires candidate, values and evidence |
| Failed behavior and retests | [UI defect register](<ai/work-items/next feature 07102026/owner_ui_defect_register_2026-10-12.md>) | Source findings are distinguished from deployed failures |

Within this program, use the work register for current state and the linked evidence for its claimed scope. Other governed workstreams retain their own approved state; this index does not supersede them. Historical test counts are not a fresh current-candidate pass.

## 2. Customer-facing documentation candidates

| Entry | Purpose | Qualification before customer delivery |
|---|---|---|
| [Root README](../README.md) | Product/install entry | F39 rewrites template-like claims and supported delivery/version policy |
| [Construction user guide](USER_GUIDE.md) | BOQ, costing, variations and existing UI | Dated August guide; F40 corrects pricing/role expectations and new service interfaces |
| [Arabic UI guidelines](arabic_ui_i18n_guidelines.md) | Terminology/direction conventions | Review for intended user audience and actual supported forms |
| [Troubleshooting](troubleshooting.md) | Problem diagnosis | Legacy theme-oriented guidance; F41 reviews safe operational actions |

These are candidates, not a publishable pack. Select a minimal approved guide set after current UI acceptance. Internal findings, role tooling, credentials, backups and raw evidence stay outside customer exports; refer to the standing [confidentiality policy](ai/OWNER_CONFIDENTIALITY_POLICY.md). No external publication occurs by adding this index.

## 3. Operator and developer references

| Entry | Use / scope |
|---|---|
| [Operating profile](ai/work-items/customer-release-gap-fixes/RELEASE_OPERATING_PROFILE.md) | Isolation, candidate rollout, backups and support; confirm named target/runtime before executing |
| [Operations runbook](runbook.md) | Existing theme/deployment procedures; preflight checks alone do not approve a deployment |
| [Developer onboarding](onboarding.md) | Existing setup guide; F25/F41 reconcile runtime/build descriptions |
| [Hook matrix](hook_matrix.md) | Existing hook reference; read alongside current F24 source register |
| [Token reference](token_reference.md) | Theme design reference; source/default values must be checked |
| [ADRs](../ADR.md) | Accepted architecture decisions, including manual cache policy and native/VFC primary path |
| [Accounting dimension ADR](ADR-001-accounting-dimension.md) | BOQ accounting/source integration context |
| [Confirmed financial rules](ai/work-items/customer-release-gap-fixes/FINANCIAL_RULES.md) | Owner-approved arithmetic/provenance; preserve unless owner revises the domain rule |

## 4. Agent instructions and internal guides

| Entry | Authority / audience |
|---|---|
| [AGENTS](../AGENTS.md) | Mandatory startup entry; path retained |
| [Professional Engineering Standard](ai/PROFESSIONAL_ENGINEERING_STANDARD.md) | Owner engineering instructions |
| [Governed workflow](../AGENT_WORKFLOW.md) | Apply relevant contract/state; path retained |
| [Session memory](../SESSION_MEMORY.md) | Factual handover with dated/corrected claims; not release approval |
| [AI context index](ai/CONTEXT_INDEX.md) | Startup navigation and context references |
| [Schema facts](ai/SCHEMA_FACTS.md) | Checker-generated source schemas; not live database verification |
| [Internal AI/memory user guide](ai/USER_GUIDE.md) | Developer/agent usage; different audience from Construction user guide |

Preserve mandatory instruction and checker paths. A root file named USER_GUIDE under docs/ai is not a second customer product guide. Use exact audience and candidate scope when reading it.

## 5. Historical snapshots and other workstreams

| Entry / family | Treatment |
|---|---|
| [Root PLAN](../PLAN.md), [STATUS](../STATUS.md), [VERIFICATION](../VERIFICATION.md) | Historical Run 11 release/CI snapshots; retained with current-program navigation notes |
| [CI_READINESS](../CI_READINESS.md), [PRIVATE_CI](../PRIVATE_CI.md) | Historical harness/private CI handoff; do not infer a new upload authority or current pass |
| [Candidate summary](ai/CUSTOMER_RELEASE_CANDIDATE_SUMMARY.md) | 6 October candidate summary; current G01–G16 reconciliation is in the foundation ledger |
| [Correction ledger](ai/work-items/customer-release-gap-fixes/STATUS.md) | Preserve fix/test history and original candidates; reconcile mixed closure notes with F01 |
| [Handover index](handover/INDEX.md) | Dated handover map; other workstream scopes remain intact |
| docs/ai/work-items/* | Other tasks/fixtures/plans; not globally archived or declared inactive by this program |
| docs/feature_reviews/* | Feature reviews and dated evidence |
| docs/evidence/* and docs/translation/* | Internal logs, data and review artifacts; not customer guides |

Historical notes are retained where they are. Navigation headers qualify selected overlapping status claims; no file, branch, backup, patch or evidence is deleted. Do not move hashed evidence merely to make the tree look simpler. A future physical archive needs a reference-impact check and preserved redirects.

## 6. Inventory and maintenance

The [documentation catalog](<ai/work-items/next feature 07102026/construction_foundation_documentation_catalog_2026-10-12.json>) records the captured paths, sizes, hashes, tracking state and audience classifications. At initial capture the repository contained 2,134 tracked files, including 1,450 docs files and 594 tracked Markdown files under docs; disk contained 610 docs Markdown files including current untracked program documents. These are snapshot counts, not permanent targets. Classification is an explicit selection or directory/audience heuristic, not a content/security audit of every document.

Thirty-three local branches and the listed backup/screenshot/scratch paths are inventoried for preservation. No branch retention decision is inferred from its name. For new documents: link from the applicable index, name audience/owner/date/candidate, state whether the artifact is source, runtime, business acceptance or historical evidence, and update the work register when it changes a task result.

F39/F40/F41 still owe the complete customer README, bilingual task-guide corrections and operator/developer handover updates. F29's navigation work does not close those packages or authorize customer delivery.
