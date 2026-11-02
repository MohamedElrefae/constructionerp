# Construction ERP WBS — Remote Reviewer Final Continuation Handoff

## 0. Identity, purpose and immediate status

Date: 2026-10-27. Reason: remote-session quota exhaustion; continue locally without restarting completed investigation.
Owner: Mohamed Elrefae. Language: English.
Repository: /home/mohamed/frappe-bench/apps/construction
Owner-designated local WBS reference folder: /home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/WBS
Historical and locally reported current baseline: develop / a19bf8efec0b32c2bc71454aaddf42f6583c69e3.

THIS IS A REVIEW/CONTINUATION HANDOFF, NOT AN OWNER PLAN GRANT, SOURCE-WRITE GRANT, ENVIRONMENT APPROVAL, COMMIT AUTHORIZATION OR RELEASE APPROVAL.

Immediate status: local P0 completed according to attributed local evidence; eight scratch planning drafts created; remote review of batches1/2 completed with blocking findings. Batch3 not supplied to remote reviewer. No application implementation, native test, site provisioning, migration, orchestrator dispatch, commit or publication occurred in the reported work. Do not repeat P0 wholesale; reuse still-valid evidence, verify changes since its baseline, and perform missing checks only.

The next local task is to finish the independent document review, especially unseen documents10/30/40/70, consolidate all findings, and return an exact documentation-correction scope for owner authorization. Do not jump to implementing WBS or provisioning a lab.

## 1. Where the work exists

### Repository reference packet
/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/WBS
Reported11files including split planning packet, combined packet and both v3 handovers. Actual filenames must be inventoried locally; remote reviewer did not verify that directory. Previously reported untracked,104K. Do not remove,add,commit or assume governed evidence status.

### Scratch plans (actual reported created files)
/home/mohamed/.opencode/plan/
- wbs-execution-mapping-00-master-scope-and-architecture.md
- wbs-execution-mapping-10-plan-p1-execution-tree.md
- wbs-execution-mapping-20-plan-p2-mapping-audit-reference-safety.md
- wbs-execution-mapping-30-plan-p3-coverage.md
- wbs-execution-mapping-40-verification-matrix.md
- wbs-execution-mapping-50-environment-runbook.md
- wbs-execution-mapping-60-decision-register.md
- wbs-execution-mapping-70-p0-evidence-and-readiness.md
Reported1835lines total. Scratch artifacts are NOT repository evidence or governed state. Importing/revising them in repository scope requires separate owner authority.

### Delivered content
Remote read actual pasted00/60 (batch1) and20/50 (batch2), latter via paste.txt. Remote did NOT read actual10/30/40/70. Prior summaries are not substitutes for content review. Exact reported SHA256s are in supplied manifest CSV. Recompute to detect drift, not as proof of approval or source truth.

## 2. Latest scope overrides earlier billing discussion

IN: separate project execution tree,optional link from existing BOQ Item Stage to eligible leaf,controlled audited mapping,reference protection,permission-aware count-based coverage/navigation/export,preservation upgrade.
OUT: progressive billing,new measurement ledger,certified_qty migration/reinterpretation,standalone Allocation Plan/allocated_qty,Stage generator,broad VO rewrite,automatic redistribution/repair,subcontract/scheduling engine,workspace redesign.
Minimal navigation proposal: one card+one sidebar link total; check optional P2 audit-card proposal doesn't exceed it.

Business quantity example: slab concrete1000m³=10buildings×(GF20+TF1 25+TF2 25+TF3 25+Roof5). Stages are item-specific execution portions,not payment milestones. Reusable execution location may host concrete/rebar/formwork Stages. Item spans locations through Stages; no single execution node on Item master; no blanket item+node uniqueness.

Existing hierarchy Header→commercial Structure(wbs_code)→Item→Stage stays intact. New project execution tree(ebs_code) sits alongside. Proposed names Execution Breakdown Node,parent_execution_node,execution_node,EBN-##### document naming,EBS-#### code. Names not finally owner-approved. Flat codes stable; never auto-renumber.

## 3. Future business memory — preserve, DO NOT implement now

Sequential payments: only approved certificate affects next opening; drafts/submitted/rejected/unapproved-cancelled attempts have no certified balance effect.350submitted/330certified then600cumulative→current claim270,NOT250. If next certified580,next opening580.
Payment contains multiple BOQ items. Negative item correction may coexist with positive aggregate payment. Ordinary overall-negative payment not normal;final exception possible,not yet coded prohibition.
Only accepted measurement quantities eligible currently. Consultant reviews Stage supporting sheet; formal payment approval applies to BOQ-item lines/payment header,NOT necessarily Stage metadata. Company engineer records external consultant approval; distinguish approver/recorder; consultant login optional.
Partial acceptance,below-certified reduction with reconciliation,audited distribution changes and revisiting VO accepted as future direction. Do not arbitrarily apportion item certification difference back to Stages. Existing Stage certified_qty historical meaning remains unresolved and must be preserved for WBS.

## 4. Attributed P0 evidence — do not claim remote/local replay

Local architect: OpenCode opencode-go/deepseek-v4.1-flash.
Reported root and SHA as above; no source divergence; upstream local/ref and ls-remote matched;562commits; working tree only untracked WBS packet.
Reported Python3.14.5,Frappe16.51.1(2871914),ERPNext16.50.0(7474d9e),Bench5.29.1.
Reported checks exit0: schema_drift_checker(21owners+1override),ai_context_check11/11,lint_scope_metadata19DocTypes.
SESSION_MEMORY datedOct6 stale (383commits vs562). Refresh only under authorized scope; memory not authority.
Local had read relevant source/vendor; whole item/variation/revision services not re-read locally, some relied on earlier remote source reads. Remote original large tests/schema/standard partially truncated. Preserve explicit full/partial read record in70.
No usable disposable environment: defaultv16.localhost not disposable; v16rehearsal.localhost called UAT from stale memory and needs owner reconfirmation; private old lab sockets missing/bound different worktree; main Redis13000/11000 down; reported14GB/home and3.9GB/root NOT current sufficiency proof.
Orchestrator reportedly no venv/state; documented qualification/pilot gates open. Do not initialize to write prose. One workflow authority required before implementation; T3 and repo engine must not independently modify same candidate.
Credential-bearing Redis URL once surfaced in local output. Value excluded. Owner to assess retained artifacts/access/rotation/sanitization without reprinting. Not proven resolved or externally compromised.

## 5. Governance / authorization record

Read actual AGENTS.md,PROFESSIONAL_ENGINEERING_STANDARD.md,CONTEXT_INDEX.md,root AGENT_WORKFLOW.md,relevant SESSION_MEMORY/ADRs/contracts. Actual checkout/status and mandated checkers before edits; preserve unrelated work. Recheck only evidence invalidated by new baseline.
Source confidentiality instruction exists despite earlier user calling repo public. No publishing/upload/private-source disclosure by implication.
Scratch docs were written with editor tool,not shell. Read-only commands reported ls/find/wc/git status/rev-parse/sha256sum/secret grep. Correct record must distinguish documentation writes from read-only verification.
AUTHORIZATION AMBIGUITY: original authorization was remote reviewer's suggested owner block forwarded to local agent. Local treated it as owner transmission but cannot prove authorship.00Basis/60§3 still unconditionally call it owner authorization; remote required change to:'Documentation writes performed under local agent interpretation of a transmitted authorization block; owner attribution awaiting explicit confirmation.' Retain drafts;do not delete. Latest user asks for handoff,not retrospective business decisions or implementation grant. Ask once for narrowly needed owner authority;avoid circular paperwork.
All Drows were PENDING/NOT VERIFIED. Remote acceptance of recommendation !=owner approval. Audit name Execution Mapping Change approved only for planning use according to reported ambiguous authorization,not schema creation.

## 6. Established source constraints relevant to WBS

Stage controller explicit planning/certified field sets; new link unprotected unless deliberately covered. Measurement-only policy returns on new Stage;parent-read exception admits create/write;create-with-node needs Header-write planning authority plus native Stage create,node read,scope/eligibility.
Stage.validate always calls quantity validation;Frozen/Locked exact planned distribution±0.001;Draft/Pricing≤without same tolerance branch. Link-only ordinary save can fail after prior VO imbalance. New operation may skip only distribution check if verified;no generic ignore_validate/db_set.
Existing certified state=statusCertified OR certified_qty>0 freezes defined business fields;no Stage payment metadata requirement. Stage deletion explicitly blocks certified/reference evidence,not measured-only alone. Do not call every reduction permanent deadlock.
NestedSet generic lifecycle insufficient for application Stage refs;protect referenced descendant when ancestor changes. Wildcard scope hooks reported,not replacement for native DocPerm/explicit project access tests.
Correct transaction service path construction/services/boq_transaction_validation.py (transaction_validation.py absent). is_progress_billing has attribution/client consumers,not unused or full billing engine.
Quantity revision updates current projection via direct setter,doesn't redistribute Stages. Existing code helper divergences,duplicate VO targets and added-item percentage bases remain separate backlog unless WBS exercises/worsens path. No broad fix prerequisite.

## 7. Recommended design status before corrections

D02 proposal: noncertified(including measured) map/relink/clear by planning authority with audit;certified unmapped NULL→node dedicated historical initial(reason);certified mapped no ordinary relink/clear. Location mapping does not assert consultant approval. Incorrect historical mapping escalation documented outside increment.
D03 target dedicated scalar endpoint,server loads Stage,current authority,row control before expected_modified check,state/node validation,normal guarded save,audit same transaction,context cleanup. Plain rejection fallback requires explicit changed-rule approval,not silent flag feature.
Existing ordinary saves cannot change execution_node. Creation-with-link other route,audited and planning-authorized. Reference guards atomic with mapping availability.
D09 total=healthy+unlinked+issues;healthy/total,zeroN/A;40healthy/0unlinked/10issues=80%. Secondary rate optional clearly labelled.
Dedicated audit store preferred,application-level immutability not DBA-proof. Must retain reason,old/new identities,actor,time,action/mode. Final design has defects in§9 below.
P1 tree-only can land safely without Stage link/endpoint/misleading UI;P2 adds all guards before mapping reachable;P3 Page+RPC acceptable in app conventions. No claim Frappe cannot use Query Reports.

## 8. Batch1 review — open corrections (00/60)

B1-01 authorization attribution as§5.
B1-02 I14 'byte-identical apart from no changes at all' unclear. Replace with exact pre-existing business-field/relationship preservation;schema additions separately tested;no inferred mapping;specify recordsets/fields.
B1-03 D07 split header eligibility(no new type/status gate) from D02-D04 lifecycle and D03 dedicated distribution exception.
B1-04 D08 manual codes unapproved expansion. Default auto-only;manual pending option needs syntax/normalization/reserved namespace/collisions/sequence policy.
B1-05 EBN-##### vs EBN-#### mismatch;standardize proposed five placeholders,still unapproved.
B1-06 source greenfield grep not proof installed-site custom-field/column/PropertySetter/ref absence. Retain preactivation collision/reference scan.
B1-07 ebs_code immutable after insert regardless refs;separate structural rules. Title edits allowed means displayed historic path TEXT changes;state limitation,not frozen historical presentation claim.
B1-08 clear has no target. Require Stagewrite+Headerwrite+scope+reason,state policy;source broken/disabled/crossproject link must not prevent authorized cleanup. Relink validates target only. Certified mapped rule still prevents ordinary clear/relink. Don't leak forbidden source-node data.
Local architect acknowledged all as deferred,not applied.

## 9. Batch2 review — P2 blockers and corrections (20)

P2-B1 AUDIT INSERT LIFECYCLE: 'deny on_update outright' can also block first insertion. Inspect pinned lifecycle,permit trusted first insert,deny later mutation/delete;explicit server-only creation guard plus tests. DocPerm alone not enough when internal ignore_permissions used.
P2-B2 PRESERVATION:1e-6 float tolerance contradicts no business-value change. Compare normalized actual persisted representation;don't allow real tiny mutation. Description must stay unchanged;reason belongs audit.
P2-B3 FULL DIFF: enumerate all persisted fields incl installed custom/future fields,explicit framework exclusions,child table policy if present,hook-induced changes after check;final invariant check before success. Not static known-field blacklist alone.
P2-B4 LOCK PROTOCOL OPEN: current candidates plain-node-read/stage-lock or version/unique alone not race proof. Need selected reviewed protocol BEFOREimplementation. Cover map/create vs node delete/reparent/convert/disable,Stage delete,ordinary save/precontroller locks,current-read/snapshot behavior. State actual VO invariant,don't demand blanket no-interleaving. Separate bounded investigation may close artifact;don't leave choice to builder.
P2-B5 RETRY/ROLLBACK:recommend no automatic retry initially;contention rollback+clear error,fresh reload/version before caller retry. Specify operation boundary for internal callers catching exceptions. Current 'one retry but never after audit' not coherent. Full atomic link/audit required.
P2-B6 AUDIT LINK RETENTION:old_node/new_node Links may prevent deletion even after Stage clear/relink;current definition onlyStage refs incomplete. Choose retaining audit-linked nodes or durable identity snapshots+reviewed deletion policy. Also define Stage rename/delete effects on immutable audit refs. No generic ignore_links shortcut.
P2-C1 NEW STAGE UI read-only but creation route allows node:choose editable-on-new authorization or create-unmapped then action. Unsaved Stage cannot use existing-record endpoint.
P2-C2 explicit Stagewrite in operation. Derive historical mode from stored state;client label cannot weaken rules. Define same-node request no-op/reject without false audit.
P2-C3 REAL TRANSPORT tests: get_doc(dict).save not DataImport transport evidence;client.save not entire standardREST. Bound route completeness claims to inspected/tested paths.
P2-C4 FALLBACK:don't introduce unplanned guarded-mode flag merely for fallback test;select approved rule/test accordingly.
Local deferred notes: clear/relink access correction;creation audit hook unspecified(propose after_insert with true lifecycle);creation planning check placement missing. Resolve with vendor source and tests,not assertion.
Scope issue to check:optional extra audit navigation card may exceed onecard+onelink total.

## 10. Batch2 review — environment blockers (50)

ENV-B1 COMMAND SEQUENCE incomplete:explicit new-site steps missing before appinstall/freshmigrate;M1 baselinebackup transfer/restore into candidate missing. Need exact model-specific sequence,cwd,actors,write effects/prereqs;not 'confirm flags later' executable approval.
ENV-B2 BINDING:symlink+HEAD not enough. Verify Pythoninstalled/import path,dependencies,assets,restarts/cache. Uncommitted candidate requires candidate manifest/hash,not HEAD alone. Baseline→candidate proof incl each package candidate.
ENV-B3 SAFETY exact approved site/root/database/socket/cwd allowlists;wbs-prefix insufficient. No default/mainbench inference.
ENV-B4 SNAPSHOTS canonical order,null,escaping,numeric representation,exact fields. Baseline lacks execution_node:logicalNULL projection not nonexistent-column query. Separate upgrade-before-tests preservation from expected behavior-test changes and cleanup/recovery comparisons.
ENV-C1 UAT designation stale,reconfirm. Avoid inspecting UAT contents for sizing if synthetic/env estimates suffice.
ENV-C2 resources include RAM,process/ports,temp,model duplication;disk limits proposals not established sufficiency. No unrelated cleanup.
ENV-C3 select reviewed provisioning procedure,not unresolved freshbench/skeletoncopy. Define pinnedframework/dependencies,app install,ownercredentialentry,isolation.
ENV-C4 restore/capacity separately gated;not mandatory add-on. Replace backup-every-structural-test with proportionate suite/fixture recovery.
ENV-C5 broadruff can find preexisting issues;capture baseline/touched-scope acceptance,no opportunistic cleanup.
Reported models:M1 two benches baseline→backuprestorecandidate;M2 onebench stopped/exclusivephase rebind. Allsites share appbinding. M2fresh/fixture created only candidatephase. Neither model selected/approved.
No provisioning approved. Browser,ordinaryusers,controlled concurrency,v15 evidence/workload remain separate evidence gaps. Do not claim lab alone satisfiesW01–W18.

## 11. Still-unreviewed documents / proposals

Read10,30,40,70 in full locally using independent reviewer session;use review order10→30→40→70 after understanding above. Examine cross-document consistency with00/20/50/60.
Known summaries mention proposedPMdelete(withheld default),depth12,headerthreshold5000,exportcap2000,EBSoverflow9999,optional capacitysite. Each requires rationale/failurebehavior/proportionate tests,not an accidental business requirement. Just 'proposed' doesn't make restrictive design safe. Avoid needless caps/secondarymetrics/auditJS polish if no need.
Verification matrix allNOTRUN must remain so until actual evidence. Distinguish offline/native/browser/concurrency;no fake historical log reconstruction.

## 12. Coverage contract to preserve

Project-required;optionalheader,commercialStructure subtree,item,mappingstatus,node subtree,Stagestatus,search. Node+Unlinked contradiction explicit. Authorizeddataset beforeaggregation/count/export with identical boundary.
Rows mappingstate,commercialcode,item,Stagecode/name,existingplannedqty/UOM,executioncode/path,Stagestatus,navigation. ItemFull/Partial/Unmapped/Issues/NoStages precisely defined. Full meansall existingStage links healthy,not scopebalanced/executed/certified.
Optional peritemqtycontext,no mixedunit grandtotal/noqtycoveragepercentage/capacitycomparison initially. ZeroStageN/A. No reportwrites/inlinequantityedit/unrestrictedbulkmap. Disabledexistingrefs retained but issues;new assignments eligibleleaf/enabled.

## 13. Continue locally without starting over

1. Readthishandoff+WBSrepo packet+scratchdocs,check actual state/hash changes and existing active jobs. Don'trerunallP0unless evidence invalidated.
2. Record current task as review-only unless owner explicitly grants docs corrections. Clarify documentation-write attribution once;don't confuse with design approval.
3. Review unseenbatch3 in independent session;combine with findingsCSV. Priorauthor doesn't silentlyself-clearfindings.
4. Produce consolidated review(dispositionP1/P2/P3/environment separately),requirements/findings table and exact doc correctionfile scope. No changesyetwithoutgrant.
5. Owner resolvesD02/D03/D04/D09/naming/limits/authority/environment decisions;may authorize documentation correction only. Do not demand all futurebillinganswers.
6. Underexactgrant,correctdocs,recordhashes/diff,secondreview. Close lock-protocol investigation beforeP2implementation;record any additional boundedread/experiment authorization.
7. Review runbook separately;owner environmentprovisioning grant separate. Testtargetexact/synthetic,credentialsenteredlocally,neverprompted/logged.
8. Resolve one implementationworkflowauthority/readiness. Repogovernedenginepreferred onlyif qualified;supervisedlocalfallbackrequiresownerexplicitpolicy. Noorchestratorrebuildforsmallfeature.
9. ReviewedPLAN+ownergrant→P1buildertests→separateverifier→exactcommitgrant/ownercommitreconciliation;thenP2,P3 andintegratedgate. Safeintermediate constraints respected.
10. Updated handover actualbaselines/diffs/testlimits;release/publication/deployment separate.

## 14. Important review posture

Review finitefeature,not endless redesign. Keep blockers tiedto data integrity/security/execution correctness. Respect truly necessary corrections but avoid expanding infrastructure/auditbusinessworkflowbeyond mapping.
The remote assistant cannot attest localmachine facts,grant ownerauthority,or claim unseenplansapproved. Remotequota exhaustion changes reviewer location,not approval standards.

## 15. External reference

Frappe Document API:https://docs.frappe.io/framework/user/en/api/document
Frappe Database API:https://docs.frappe.io/framework/user/en/api/database
Exact vendor behavior must be inspected locally at installedversion. Noexternalcompetitorcomparison required for this WBS review.
