# Construction ERP — Business Workflow and Owner Decisions Handover

## Document control
- Revision: v3 — consolidated WBS scope reset and coverage-view proposal
- Date: 2026-10-27
- Prepared for: Mohamed Elrefae, civil-engineering management, QS/planning and manager coordinating AI agents
- Language: English
- Status: End-to-end session reference. Not an implementation PLAN, release approval or deployment/publication authorization.
- Supersedes: Earlier business handovers in this conversation wherever inconsistent, particularly payment opening basis, Stage approval metadata and immediate feature scope.
- Companion: Developer / AI Coding Agent Technical Handover v3.

## 1. Management summary

The current feature is a new execution breakdown tree linked to existing BOQ Item Stages. The existing commercial BOQ Structure remains unchanged. This is not the progressive-billing implementation.

The session initially considered a separate Execution Allocation Plan with its own allocation quantities. The owner's site example showed that Stages already represent item-specific execution portions. The preferred first increment therefore links Stages to reusable execution locations without introducing another quantity owner.

Later discussion clarified owner payments, partial acceptance and VO corrections. Those decisions remain valuable future requirements, but payment certificates, new measurement ledgers and broad VO redesign are explicitly outside the immediate WBS increment.

Enough business information exists to draft the bounded WBS plan. Local startup checks, native verification and precise mapping-lifecycle decisions remain necessary before editing and acceptance. No repository source changes, native Frappe/MariaDB tests, migrations, commits or deployment occurred in the reviewed session.

## 2. What the owner means by Stage

A Stage is a measurable execution portion of a BOQ item. It is not a payment milestone or another activity reusing the same whole quantity.

Example: slab concrete item, 1,000 m³ for ten buildings.

| Portion per building | Quantity |
|---|---:|
| Ground-floor slab | 20 m³ |
| First typical-floor slab | 25 m³ |
| Second typical-floor slab | 25 m³ |
| Third typical-floor slab | 25 m³ |
| Roof slab | 5 m³ |
| One building | 100 m³ |
| Ten buildings | 1,000 m³ |

Five ground-floor slabs plus ten first-floor slabs give `5×20 + 10×25 = 350 m³` in a supporting quantity sheet.

The consultant reviews detailed supporting quantities separately. Formal payment certification is against BOQ-item lines in a multi-item payment, not necessarily separately against every Stage.

## 3. Two hierarchies, different purposes

### Existing commercial hierarchy — preserve

```text
BOQ Header
  → BOQ Structure (commercial WBS code)
    → BOQ Item
      → BOQ Item Stage
```

### New execution hierarchy — proposed

```text
Project
  → Execution Breakdown Node
    → Building
      → Floor / Zone / Work Package
        ← linked BOQ Item Stages
```

A node can be reused by Stages for concrete, reinforcement, formwork and other items at the same location. Each Stage retains its BOQ Item and existing quantity/history.

For an item spanning many locations, one node field on the BOQ Item is insufficient. The first-increment relationship is derived through its Stages. Items without Stages remain visible as having no staged execution mapping; do not invent Stages just to make coverage look complete.

The execution tree is not a new financial cost-centre hierarchy or a replacement for BOQ Structure. Proposed labels: Execution Breakdown Node and ebs_code, to distinguish the existing commercial wbs_code.

## 4. Current scope — authoritative reset

### Include in the first increment
- Project-scoped execution tree.
- Optional execution-node link on existing Stage model.
- Controlled creation/mapping with server-side permission and project checks.
- Navigation among nodes, Stages and BOQ Items.
- Mapping/coverage report for linked and unlinked Stages.
- Preservation of existing quantities, revisions, measurement and certification behavior.
- Protection against deleting or moving referenced nodes in a way that changes historical location meaning.

### Explicitly exclude
- Owner applications, payment certificates and certified carry-forward implementation.
- A new measurement/certification ledger or migration of certified_qty meaning.
- Financial credits, receipts and accounting redesign.
- Broad VO rewrite.
- Automatic distribution changes after VO approval.
- Separate Allocation Plan with independently editable allocation quantities.
- Scheduling engine, subcontract management and automatic inferred progress.

### Follow-up recommendation, not first-increment commitment
- Previewed, atomic, retry-safe repetitive Stage generation.
- Distribution-revision implementation, once quantity-change lifecycle is separately agreed.

The generator is useful but interacts with exact distribution checks. Defer it rather than quietly expanding the first release.

## 5. Owner decision register and proposal status

| Topic | Status |
|---|---|
| English discussion and reports | Owner requested |
| Stage = measurable item execution portion | Owner confirmed |
| Owner claim substantiation first, subcontract later | Accepted future direction |
| Partial acceptance across claims | Accepted future requirement |
| Cumulative application input | Accepted future requirement |
| Previous basis = last approved certified cumulative quantity | Explicit owner correction |
| Sequential payments; drafts contribute nothing to balances | Owner confirmed |
| Only accepted measurements included in owner application | Owner confirmed current policy |
| Company engineer records external consultant approval | Owner confirmed current operating model |
| Consultant app login | Optional future capability, not required |
| Negative item movements within overall positive payment | Owner confirmed normal possibility |
| Ordinary whole-payment negative outcome | Not normal; final payment may differ; not yet a strict coded prohibition |
| Reductions below certification with reconciliation | Accepted future direction |
| Audited distribution revisions | Accepted direction; not included automatically in initial WBS delivery |
| Revisit/redesign VO if needed | Owner accepts investigation/proposals; no blanket rewrite grant |
| Keep current work WBS-only | Latest explicit owner scope instruction |
| Stage-link Option A | Preferred architecture for the plan; exact schema/actions need approval |
| Coverage-view layout | Outlined by assistant; not yet independently approved as final specification |
| Detailed roles, migration and exceptional reversal rules | Not finalized |

## 6. Supporting quantities versus formal approval

Stages and supporting sheets collect details that sum to a BOQ-item quantity. Formal approval evidence belongs in payment/certificate context associated with item lines, not necessarily on every Stage.

Future payment header candidates: consultant approval date/reference, signed attachment, period, external decision maker and internal recorder. Future item-line history: previous certified cumulative, current cumulative submitted and current cumulative approved quantities.

Do not repeatedly replace period-specific values on the permanent BOQ Item master. Do not conclude that missing certificate metadata on a Stage is a defect.

If a supporting sheet totals350 but the consultant certifies330 at item level, do not proportionally reduce Stages or assign20 to a random Stage. Record the decision where it was made unless a specific supporting measurement correction exists.

Existing Stage certified_qty remains historically ambiguous until real records are inspected. Preserve it unchanged for WBS.

## 7. Future payment contract — retained, not being implemented now

Payment is sequential. Work the current payment until approval; an unapproved attempt may be cancelled/reworked/replaced. Only approved results advance balances. Drafts and pending/rejected attempts have no certified financial effect, though review history may remain.

| Event | Correct figures |
|---|---|
| Payment1 | Submitted cumulative350m³, approved330m³ |
| Payment2 | Current cumulative600m³; previous330m³; movement270m³ |
| If Certificate2 approves580m³ | Certificate movement580−330=250m³ |
| Payment3 opening | 580m³, not600m³ |

Never use600−350=250 as Payment2 operative claim movement. Preserve submitted350 separately.

All application quantities require measurement acceptance under the current owner policy. Company engineer prepares/records external consultant decisions. Distinguish external approver from internal recorder; consultant need not use the app.

Payments contain many BOQ items. Example with unchanged illustrative rates:

| Item | Movement | Rate | Value movement |
|---|---:|---:|---:|
| Concrete | +270m³ | 100 | +27,000 |
| Plaster | −50m² | 20 | −1,000 |
| Tiling | +100m² | 30 | +3,000 |
| Whole work-value movement | Do not sum mixed units | — | +29,000 |

A negative item correction does not invalidate an overall positive payment. Final net amount can include other deductions; valuation and final-payment exceptions remain future design topics.

## 8. WBS mapping policy — recommendations for the first plan

- New Stages can select a valid same-project execution leaf.
- Existing Stages can remain unlinked after upgrade.
- Existing mapping/relinking requires planning-level authorization, not accidental measurement-user access.
- No automatic historical mapping from Stage names.
- No automatic remapping of measured/certified records.
- A reviewed historical mapping operation may be needed; define it explicitly and audit changes.
- No single execution-node field on the BOQ Item master.
- Do not impose uniqueness of item+node without evidence; multiple Stages at a location may be legitimate.
- Disabled-node and tree-change policy must distinguish preserving references from allowing new assignments.

An important remaining check: ordinary Stage save also validates quantity distribution. Linking an otherwise unchanged Stage may fail if a prior VO left it out of balance. Plan must either reject clearly or provide a narrowly reviewed mapping-only path; no silent blanket bypass.

## 9. Coverage view — detailed outline for manager review

### Purpose
Which existing Stages have execution-node assignments, and which still need mapping? Not payment, progress, commercial completeness or quantity allocation.

### Filters
Required Project; optional BOQ Header, commercial Structure subtree, BOQ Item, mapping status, execution node/subtree, existing Stage status and search.

Execution-node filter plus Unlinked is contradictory. Explain or clear the node filter; do not silently return unexplained emptiness.

### Counts
Total Stages; Linked; Unlinked; Stage mapping completeness by record count; BOQ Items without Stages separately. Example50/40/10 gives80% of Stage records mapped, not80% of quantity or progress. Zero Stages means Not applicable, not100%.

### One row per Stage
Mapping status; Commercial WBS Code; BOQ item reference/title; Stage code/name; planned quantity; unit; Execution Code; execution path; existing Stage status; navigation actions.

Example:

| State | Item | Stage | Qty/unit | Execution path |
|---|---|---|---|---|
| Linked | Slab concrete | B01 GF slab | 20m³ | Building01 → Ground Floor |
| Unlinked | Slab concrete | B02 GF slab | 20m³ | — |
| Linked | Reinforcement | B01 GF reinforcement | 3t | Building01 → Ground Floor |

### Item grouping
Fully mapped = all existing Stages assigned. Partially mapped = some. Unmapped = none. No Stages = separate state. Fully mapped does not establish that total planned quantities match commercial capacity.

### Quantity context
Optional per-item linked/unlinked planned totals with unit, e.g.1,000 total/800 linked/200 unlinked m³. No mixed-unit grand total. Initial recommendation: omit quantity-based coverage percentages and revised-capacity comparisons.

### Integrity warnings
Keep warnings separate from Linked/Unlinked: invalid/missing node, different project, disabled node, non-leaf where prohibited. Populated invalid links must not count as healthy mapping; final count/warning presentation must reconcile transparently.

### Actions
Open Stage, Item and node; filter; permission-respecting export. No inline quantity editing, automatic splitting, measurement/certification editing or unrestricted bulk relinking. Counts/exports/navigation use the same authorized scope.

### Acceptance
Counts reconcile; unlinked records remain valid; node descendant filtering works; no cross-project leak; no quantity/history changes; no confusion between mapping and completion.

## 10. Business risks with bounded treatment

| Risk and example | Current classification | WBS response |
|---|---|---|
| New field bypasses old permission lists: measurement-only user relinks location | Specific integration risk | Explicit server checks for new field |
| Stage linking triggers exact-distribution check after VO1000→1100 | Candidate blocked mapping path | Reproduce; define narrow handling |
| Move Building01 subtree after its Stages are mapped | Proposed lifecycle risk | Protect history-changing moves/deletion |
| Wrong project node linked | Relationship risk | Validate server-side across save/REST/import |
| Auto-map ambiguous legacy name | Data integrity risk | Leave unmapped; reviewed mapping only |
| 80% mapping read as80% executed | Reporting interpretation risk | Explicit count-based label |
| Hidden item progress vs Stage/report totals | Existing consumer concern | Do not reinterpret; show existing planned data only |
| Duplicate VO lines/value mismatch | Separate commercial candidate defect | Track separately; not blanket prerequisite for tree |
| Stage positive certification freezes future progress | Existing policy conflicts with future requirement | Preserve now; redesign in later scoped work |
| Measured uncertified Stage deletion may be allowed | Candidate preservation gap | Investigate when mapping/history path affected; no delete-as-rebalance |
| Omitted item blocks new correction attribution | Future billing integration concern | Defer; do not weaken generic omission rule for WBS |

No candidate defect was reproduced in a running site during this session.

## 11. Competitor context — retained without expanding scope

- Oracle Textura: controlled billing/application approvals and tracking. Relevant later, not a WBS dependency.
- Procore: application line review/rejection/resubmission; approved changes connected to applications. Does not prove our exact schema or330-based formula.
- SAP: service acceptance distinct from invoice processing and controlled revocation/correction. Procurement analogy, not identical owner IPC workflow.
- Earlier claims of P6 destructive restructuring, SAP absolute rigidity and Procore user-discipline-only controls were not established and must not be repeated.

References used earlier:
- https://www.oracle.com/construction-engineering/textura-construction-payment-management/
- https://v2.support.procore.com/product-manuals/invoicing-project/tutorials/revise-and-resubmit-a-subcontractor-invoice-as-an-invoice-contact
- https://en-gb.support.procore.com/products/online/user-guide/project-level/commitments/tutorials/revise-and-resubmit-an-invoice-as-an-invoice-contact
- https://help.sap.com/docs/SUPPORT_CONTENT/spmm/3362167764.html

## 12. Verification before implementation

1. Actual local branch/HEAD/uncommitted work and governance startup checks.
2. Stage/item/header/node project relationship.
3. New link authority for creation, existing mapping and relinking.
4. Mapping saves in Draft/Locked/certified/out-of-balance conditions.
5. Referenced tree node deletion/move/disabled behavior.
6. Count-based report, filters and permissions.
7. Clean/repeated upgrade preserves all existing quantities/history and leaves records unmapped.

A named disposable Frappe site and execution channel remain unavailable in this conversation. Do not claim remote source review verifies the local site.

## 13. Next step and restart instruction

Next deliverable: bounded first WBS implementation plan, exact file scope, permission/mapping rules and verification gates. Not progressive billing design.

> Continue from both v3 handovers. Keep scope to project execution tree, optional existing Stage link, controlled mapping and mapping coverage. Preserve current BOQ Structure, quantities and history. No Allocation Plan, new ledger, certification migration or billing implementation. Retain future payment facts, especially600−330=270, but do not make billing a prerequisite. Verify checkout/governance and named disposable environment before edits/tests. Reproduce mapping-specific risks, draft bounded PLAN and obtain required approval. Do not publish/deploy by implication.
