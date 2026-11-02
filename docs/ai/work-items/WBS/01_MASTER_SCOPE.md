# WBS Master Scope and Architecture — Draft for Local Review

## 1. Outcome
Organize existing item-specific execution portions by reusable buildings/floors/zones, without creating a second quantity source or changing commercial quantity/certification semantics.

## 2. Existing and proposed relationships
Existing: BOQ Header → BOQ Structure → BOQ Item → BOQ Item Stage.
Proposed: Project → Execution Breakdown Node tree; Stage.execution_node → execution leaf.
Many Stages may reference a leaf. BOQ Item location mapping derives through its Stages; no single node on item master. No blanket uniqueness(item,node), because multiple portions can exist at one location.
Names Execution Breakdown Node, execution_node and ebs_code are proposed; verify naming conventions before final schema.

## 3. Included
Project-scoped execution tree; optional Stage link; authorized create/map/relink policies; node/Stage/item navigation; count-based mapping coverage; protected references/tree lifecycle; nullable, repeat-safe upgrade; focused tests and documentation.

## 4. Excluded
Separate Allocation Plan/allocated_qty; Stage generator; new measurement ledger; payment application/certificate; certified_qty reinterpretation; previous-certified calculations; scheduling; subcontract engine; broad VO rewrite; automatic redistribution/repair; direct historical progress attribution.

Future business facts are retained only as compatibility context: sequential multi-item payments; approved-only opening;350submitted/330certified then600→270; external consultant approval recorded internally; partial acceptance and item corrections. They do not authorize billing work.

## 5. Data/behavior invariants
- Preserve commercial wbs_code/tree and all quantity/rate/revision fields.
- Stage, authoritative item/header project, node and parent project must agree.
- New assignment uses eligible leaf; define disabled behavior explicitly.
- Existing records valid with NULL/unmapped link; no name-based backfill.
- Mapping/relink is planning authority, not accidentally measurement authority.
- No historical measured/certified remapping without reviewed explicit policy.
- Protect referenced descendants as well as direct leaf when moving/deleting ancestors.
- No change to quantities/status via report read or mapping operation.
- Node codes unique per project under concurrency; final format/lock/index local design.
- Counts, searches, navigation and export share authorized scope.
- Mapping complete is not quantity-balanced/executed/certified/financially complete.

## 6. Stage-save integration hazard
Historical reviewed controller uses fixed immutable/planning field lists; new execution_node is not automatically protected. Ordinary Stage validation also checks full distribution, potentially blocking mapping-only saves after VO imbalance.
Local architect must compare alternatives: clear rejection of out-of-balance mapping, or explicitly authorized narrow mapping-only route. No generic ignore_validate or setter bypass. Historical mapping policy must be explicit, audited and compatible with actual framework lifecycle. No blanket ledger/VO redesign to solve a mapping problem.

## 7. Coverage view
Required Project; header/Structure subtree/item/mapping state/node subtree/Stage status/search filters.
Node filter plus Unlinked must explain contradiction or clear incompatible filter.
Summary: total Stages, healthy-linked, unlinked, link-issues, count completeness, items without Stages separately. Define disjoint categories and denominator so all counts reconcile.
Rows: mapping status, commercial code, item identity, Stage code/name, existing planned qty+unit, execution code/path, Stage status, navigation.
Item grouping Full/Partial/Unmapped/Needs Review/No Stages, with precise definitions. Invalid links never healthy.
Optional per-item planned quantity context only. No mixed-unit or unrelated-item quantity grand total; no initial capacity comparison or quantity percentage.
Actions navigate/filter/authorized export. No inline qty editing, bulk automatic mapping, splitting or progress changes.

## 8. Increment structure
P0 local reconciliation and plan review; P1 tree; P2 Stage mapping/reference protections; P3 coverage/navigation; P4 integrated acceptance/handover. P4 is final gate, not a substitute for per-package tests. Safe commit boundaries must be validated locally.

## 9. Acceptance boundary
Requires local baseline evidence, allowed/denied ordinary-user routes, Stage mapping across lifecycle states, tree reference safety, code concurrency where claimed, report reconciliation, clean/repeated upgrade and unchanged legacy quantities/history. No production-readiness claim from source reads or agent PASS alone.
