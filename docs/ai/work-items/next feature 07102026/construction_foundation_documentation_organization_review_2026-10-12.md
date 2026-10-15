# F29 — Documentation organization and preservation review

**Date:** 12 October 2026  
**Candidate:** develop c9e6803c5ac63073aeb0b166c779844d29051d8d  
**Status:** Source documentation/index work complete; F29 In progress pending final audience/delivery decisions and linked foundation qualifications.  
**Classification:** Confidential — internal

## 1. Deliverables

- [Central documentation index](../../../DOCUMENTATION_INDEX.md): current foundation entry points; customer-guide candidates; operator/developer references; fixed agent/governance paths; historical and other-workstream evidence.
- [Documentation catalog](construction_foundation_documentation_catalog_2026-10-12.json): 1,552 captured document/evidence paths with sizes/hashes/tracking/audience notes, plus branch/residue preservation inventory. Snapshot captured before navigation edits; hashes describe the captured versions, not a later modified file.
- Scoped navigation notes in root PLAN, STATUS, VERIFICATION, CI_READINESS and PRIVATE_CI identify historical Run 11 scope and point to current foundation status. Original bodies are retained.
- Handover and internal AI-guide navigation distinguish their audiences. Factual AI context index links to the central map; mandatory AGENTS/workflow paths are retained.
- One runbook readiness statement corrected: preflight success means listed checks passed, not approval to deploy the candidate to a site.
- [F28 archive verification](construction_foundation_delivery_artifact_verification_2026-10-12.json): independently verified retained archive hashes, every regular member list/hash and equivalent app contents; identified backend/source qualification gaps below.

No file, branch, patch, backup or evidence was moved/deleted. No app source, artifact contents, site or runtime was modified; no commit, push or publication occurred. The user's isolated F28 build is acknowledged as actual artifact work, distinct from this turn's read-only verification.

## 2. Canonical scope and preserved history

The foundation work register controls current task/issue state for this program; the master plan defines acceptance and the gap ledger reconciles old evidence. Source/runtime/business acceptance are separately identified by each artifact. This does not replace another workstream's governed contract/state.

Root PLAN/STATUS/VERIFICATION/CI_READINESS/PRIVATE_CI describe Run 11/f63d739. The October candidate summary describes 4c236bd. Their bodies and source references remain available; navigation notices prevent their “ready/complete” wording being mistaken for the present c9e6803 runtime qualification. No fresh CI pass was invented.

The two USER_GUIDE files serve different audiences: docs/USER_GUIDE.md is the dated Construction workflow guide; docs/ai/USER_GUIDE.md is internal AI/memory usage. F40 still corrects pricing, role and service-interface instructions. Developer onboarding/runtime/build descriptions remain F25/F41 work. Runbook/troubleshooting are existing theme-oriented guides, not complete current operations acceptance.

## 3. Inventory and privacy boundaries

At capture: 2,134 tracked repo files, 1,450 docs files, 594 tracked docs Markdown files and 610 Markdown files present under docs on disk. Current program untracked files explain the Markdown difference. The catalog also includes other evidence formats and root Markdown, yielding 1,552 captured paths. New index/review files created afterwards are described here and do not retroactively change that snapshot.

Audience classification uses explicit canonical selections and directory/path heuristics. It is not a full reading/security review of every document, nor a declaration that all 1,450 docs files are private or deprecated. There are mixed audiences; internal work-items/data clearly require delivery review. No classified file is authorized for customer/public export by this index. Of the 2,134 tracked files, 519 are under construction/ and **1,615** are outside it; the prior 1,504 non-app count was corrected. “Non-app path” is an inventory category, not proof that every such file is private or unnecessary.

Thirty-three local branches and tracked backup/screenshot/scratch candidates are listed for preservation; names do not establish deletion eligibility. The four tracked backups/stash patches were inventoried by path without exposing their contents. Core instruction/checker paths and hashed evidence references are preserved. A future physical archive must verify references and redirects; it is not required to create a usable index now.

## 4. F28 verification corrections and qualification gaps

The retained wheel and tar.gz exist in /tmp/opencode/f28-artifacts. Their SHA-256 values match the F28 evidence JSON. Each has 1,229 regular files. All recorded member names match the archives; this follow-up adds per-member bytes and SHA-256 without extracting files. Their **1,225 app members are identical in paths and bytes**. Metadata/source-root additions differ, so describing app files as a strict subset of app files was imprecise.

### F28-D005 — diagnostic backend mismatch; backend action subsequently closed

Installed temporary-tool metadata confirms flit_core 4.1.0; pyproject.toml requires flit_core >=3.4,<4. The initially inspected artifacts used an out-of-range backend. **Subsequent follow-through:** compliant artifacts built with flit_core3.12.0 were independently archive/member-hash verified; member sets and all app bytes are identical. Wheel METADATA/RECORD/WHEEL and sdist PKG-INFO are the only changed member bytes. The backend action is closed; package contents, input binding and install/replay qualification remain open.

The earlier assertion that root-level exclusions “never excluded anything” cannot be generalized from this out-of-range build. They do not remove the observed residue inside the package. The compliant3.12 rebuild produced the same observed member sets; this verifies the observed contents under an allowed backend, without proving a counterfactual build with exclusions removed. Setuptools find_packages does not govern this Flit build. No packaging rule was changed.

### F28-D006 — artifact contents extend beyond tracked source

The archives include every tracked Construction app file plus **706 app files absent from Git tracking**: 704 theme CSS outputs and two dist outputs (bundle and map). HEAD alone cannot bind those delivered bytes. Capture a reviewed input/build manifest or rebuild deterministically from the selected source in isolation, then inspect the output again.

The 710-member theme_* pattern also includes six tracked files, including Construction Light/Dark, Light/Dark and theme_current. The theme controller generates/uses such CSS paths. A blanket theme_* exclusion or deletion can remove legitimate runtime theme assets; distinguish intended runtime output from test residue before filtering. No theme file was deleted, renamed or excluded here.

### Secret-scan wording

The F28 report records a pattern scan finding no matching secret/config/dump/backup classes. The evidence is not a blanket proof that no sensitive value exists in any file. This follow-up verified archive/member hashes and filenames; it did not repeat a content-oriented secret scan. Preserve the reported scan's method/limits and use positive contents/allowlist review before customer delivery.

## 5. Remaining document work and ownership

| Work | Package | Completion evidence |
|---|---|---|
| Select supported delivery route and approved customer contents; compliant package rebuild and install/replay | F28/F13/F31 | Exact backend/runtime/input manifest, artifact inventory and lifecycle evidence |
| Rewrite template customer README with actual scope/versions/support | F39 | Accurate supported user/install guide accepted for intended delivery |
| Correct bilingual user tasks, roles, pricing and service UI instructions | F40/F43 | Mohamed follows actual UI, correct arithmetic and added test cases |
| Refresh developer/operator guide; review legacy troubleshooting advice to disable failing hooks | F41/F24/F33 | Safe failure/recovery steps preserve fail-closed enforcement; tested named ownership |
| Finalize audience labels/customer selection and any later physical archive | F29/F28 | Owner delivery decision, preserved references and source/current status links |

The preflight readiness overstatement was corrected now. Broader guide and operator-policy changes remain their named packages; a documentation index does not grant site/deployment or external-disclosure authority.

## 6. Verification and sources

Read current standards/context/workflow/session and master/register F28/F29 scope; F28 review/evidence and temporary backend METADATA; pyproject; documentation entry guides/indexes; root Run 11 snapshot headings; theme CSS controller references. Git tracked/file/branch inventory was read without moving branches/worktrees. Archive/member verification is independently recorded in JSON. Both startup checks passed (schema21+1, context11/0), with HEAD unchanged. Markdown targets, table shapes, task rows and non-destructive navigation edits were checked. No package install/build, site, suite, migration or network action occurred in this turn.
