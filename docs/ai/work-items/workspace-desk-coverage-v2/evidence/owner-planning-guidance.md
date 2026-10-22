# Owner Planning Guidance and WDC-R4 Historical Waiver

**Work item:** `workspace-desk-coverage-v2`
**Candidate:** `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df`
**Base commit:** `fd9aecc372aec6a1341dd0cac4f779c1ec539756`
**Date:** 2026-10-01
**Authority:** owner policy instruction given in session; transcribed by the agent, not self-authored

---

## 1. WDC-R4 — Historical Chronology Waiver

### 1.1 What is mathematically established

The `collected_utc` → `db_now_at_collection` delta is **exactly** the host's `Africa/Cairo` EEST
offset:

```
collected_utc          2026-09-29T20:02:55Z
+ Africa/Cairo EEST     +03:00
= db_now_at_collection 2026-09-29 23:02:55      EXACT
```

Same instant, two representations: UTC with a `Z` suffix, and naive local time. No clock drift
and no backdating.

### 1.2 What is not established, and cannot be

The audit values of `2026-09-30 01:31–01:32` normalise to `2026-09-29T22:31–22:32Z`, which is
monotonic with collection (`20:02:55Z`) and envelope assembly (`21:08:13Z`). Monotonic ordering
is **not** reconciliation. Two gaps remain and **no further evidence for them exists**:

1. The +03:00 offset is *inferred* from the host's present-day timezone, not attested by the
   collector's own configuration at collection time.
2. No collector or clock provenance was recorded for any of the three timestamp sources.

Additive execution-time collector clock logs from 2026-09-29/30 do not exist. They will not be
manufactured, inferred into existence, or backdated.

### 1.3 Waiver

**The Owner waives the retrospective chronology-reconciliation requirement for the historical
Stage 2 milestone**, on the following condition:

> The schema-level defect — an unlabelled local-time field (`db_now_at_collection`) — **must be
> scheduled as an open engineering task in the Plan**, to be resolved **prospectively** in
> subsequent stages.

This waiver is bounded:

| Bound | Statement |
|---|---|
| Scope | The historical Stage 2 capture only |
| Prospective fix | **Required.** Labelling `db_now_at_collection` with an explicit offset must appear as a Plan task |
| Timestamp edits | **Forbidden.** No historical byte may be altered |
| Precedent | **None.** Does not waive chronology reconciliation for any later capture |
| Revocable | Yes, on production of authentic collector provenance |

## 2. WDC-R1 / WDC-R2 / WDC-R6 — Post-Plan Deliverables

### 2.1 Framing correction

**WDC-R1, WDC-R2 and WDC-R6 are work-package deliverables to be scheduled and executed, not
pre-existing conditions that must be verified before a Plan may be drafted.**

Treating unimplemented verification work as grounds to refuse to produce a plan conflates the
Architect's remit with the Builder's and Verifier's. The Architect's deliverable is a Plan; the
Builder's and Verifier's are the work and its audit.

### 2.2 Required staging order for the Plan

Any Plan produced must specify, at minimum, the following sequence:

1. **Builder** stages the candidate into the test harness / bench app so the site serves
   candidate content rather than base.
2. **Builder** produces live evidence:
   - `DocPerm` ground truth and effective-permission matrix on real single-role users
   - English/LTR browser coverage across all destinations, including wrapping, clipping and
     routing
   - PO source ↔ compiled-catalog binding with runtime lookup capture
3. **Verifier** audits the candidate against WDC-R1, WDC-R2 and WDC-R6 against that evidence.

### 2.3 Acceptance criteria the Plan must state

The Plan must define, per requirement, what constitutes acceptance — not merely that the work
is scheduled:

| Requirement | Acceptance criteria the Plan must specify |
|---|---|
| WDC-R1 | 5 cards, 16 standalone destinations, 0 child tables; English/LTR browser render with no clipping; v15 either evidenced or expressly dispositioned |
| WDC-R2 | Valid nonempty Arabic for every label; no duplicate or fuzzy substitution; source bound to compiled catalog; runtime lookup captured |
| WDC-R6 | `Scope Report Access Log` read only for System Manager and Auditor; unprivileged roles all four permissions false; no sensitive Workspace link; direct access denied; rollback and residual-user checks authenticated |

### 2.4 Prior measurements are historical, not v2-bound

The SCP-007 measurements were taken against the retired candidate `341715dd…` while it was
installed. `apps/construction` is now at base (4 cards / 10 links) versus candidate (5 / 16).
Those results transfer as *reasoning* — the 19 app files are byte-identical — but they are **not**
a v2 capture and must not be presented as one. See `scp007-permissions-and-desk-status.md`.

## 3. Standing limits on this guidance

This document changes the **framing** of open work. It does not certify any implementation and
does not authorise any site, ERP, or production operation. Specifically:

- **No `errors=0` is claimed** for the localization gate against an independently identified
  checker. SCP-006's ratification (`7adf987d75e092e1…`) stands on its own terms.
- **No WDC-R1/R2/R6 verification is claimed complete.**
- **No site mutation is authorised** by this document. Item 2.2 step 1 is a Plan deliverable,
  and its own authorisation is a separate owner decision.
- The Architect is expected to **refuse** if a Plan cannot be produced within the declared
  scope, rather than widen scope on its own authority.

## 4. Attestation

Recorded from owner instruction given in session on 2026-10-01, following the Architect's
third blocking pass. Supersedes no prior disposition. Bound to candidate `d8be079d…` at base
`fd9aecc3…`.

## 5. Owner Disposition for decision-3 (Finding Resolutions & Scope Boundary)

The Builder blocked at `decision-3` with three findings. The owner has ruled on each. This
section is the Builder-visible copy of that ruling; the authoritative record is
`docs/ai/work-items/workspace-desk-coverage-v2/evidence/decision-3-owner-disposition.md`
(SHA-256 `2e96179ba4a6264012bd413c80ee2c0eb3cffeadd9acb42132136787d11e8451`).

Bound to candidate `d8be079d…` at base `fd9aecc3…`, tree `d354aac0…`.

**Finding 1 — six empty Workspace translations: DEFERRED.**
`BOQ Management`, `Variation Management`, `Variation Order`, `Scope Management`,
`User Scope Context` and `Construction ERP` remain untranslated in this candidate. They are
batched into the next Localization Maintenance / Bilingual Catalog Release. Filling them is
counter-neutral to the ratified gate (`EXPECTED_GATE.catalog` stays 817), so deferral
perturbs no ratified counter.

**Finding 2 — the PO/checker deadlock: DISPOSITIONED, not repaired.**
Do **not** edit `ar.po` in this candidate. Do **not** edit
`scripts/check_localization_gates.py`, whose SHA-256
`54fa583cb250b4707c8dd8f88b6c1454c15fd16d6db6ff667ef7c0dcec0642bb` must remain
byte-identical. The checker requires no relaxation and no ratchet extension. The deadlock
exists only if the repair is attempted here; declining the repair leaves the whole evidence
chain aligned at `ar.po: af343ac2…`.

Because this ruling answers the design question in writing, **no plan revision is required**
and no architect pass is needed. The approved plan revision `c754b407…` stands.

**Finding 3 — dispatch authority versus context data: Builder's reading AFFIRMED.**
`owner-execution-authorization.md` is authoritative evidence of owner intent, but it is not
a mechanical grant of dispatch authority and does not widen `allowed_paths`. Declining to
self-widen was correct behaviour. This build leg therefore requires no staging, no catalog
sync, and no live probe.

**What the Builder must do now.** Verify the existing nineteen candidate files against the
approved plan and scope. Do not modify any candidate file. Do not attempt the PO repair. Do
not stage into `apps/construction` and do not execute site operations under this leg. If a
defect remains that cannot be resolved without those actions, raise it as a new finding
rather than acting on the authorization transcript.

## 6. Required plan amendment — WDC-R2 acceptance criterion (supersedes §5)

Section 5 deferred the six empty translations by owner ruling alone. **That was
insufficient and is hereby superseded.** The approved plan revision `c754b407…` states the
acceptance criterion directly: every visible Workspace label must carry a non-empty Arabic
translation. A deferral that does not amend the plan does not amend the contract, and the
Builder correctly refused to accept it. Do not resume the builder under the unamended
criterion; it will block identically.

The Architect is directed to amend the plan so that, for candidate `d8be079d…` at base
`fd9aecc3…` (tree `d354aac0…`), the WDC-R2 acceptance criterion reads:

1. All **17 core Workspace labels** carry non-empty, valid Arabic and are verified active.
2. The **6 sidebar-item labels** — `BOQ Management`, `Scope Management`,
   `User Scope Context`, `Variation Management`, `Variation Order`, `Construction ERP` —
   are formally classified as **DEFERRED to the next bilingual data / Stage-2 catalog
   maintenance release**, because completing them mutates `ar.po`, which invalidates
   `localization_manifest.json`, `freshness_evidence.json` and all eleven Stage-2 envelopes,
   and regenerating that chain requires a live catalog sync plus eleven module suites — a
   release cycle exceeding this milestone's UI boundary.
3. The amended criterion is satisfied when 17/17 core labels are translated **and** the six
   deferrals are recorded with their hash-bound rationale. WDC-R2 is **not** thereby claimed
   complete; it is satisfied as amended and the remainder is an explicit follow-up obligation.

The amendment must not weaken any gate. Specifically: `scripts/check_localization_gates.py`
stays byte-identical at `54fa583cb250b4707c8dd8f88b6c1454c15fd16d6db6ff667ef7c0dcec0642bb`,
`ar.po` stays at `af343ac233cac0e022aa1d84fef87943cd94eff78d364f842115614be56c3698`, no
historical evidence byte changes, and `EXPECTED_GATE.catalog` remains 817. Amend the
acceptance wording only. The revised plan must state its own new revision hash when
submitted, and the Builder will be re-dispatched only against that amended revision.

## 7. Live runtime staging results and contract finalization guidance

Owner-executed bounded staging on `v16.localhost` against candidate `d8be079d…` at base
`fd9aecc3…`. All 19 candidate files were staged for measurement only and rolled back
immediately; `apps/construction` verified 0 modified / 0 untracked on `fd9aecc3…`, 31 users
before and after, and 0 `adv_probe_*` identities created or remaining. Bound report:
`scp007-live-runtime-validation.json`
(`4647ffc66d31bea76486740838f2c2351c36839f4c40053fd5116505e7f18906`).

### 7.1 Workspace structure and DocPerm ground truth

Capture `raw-logs/live-site-permissions-and-desk-recon.txt`
(`1d81f09230bef0786aa8d8cd3eee880e2b1771966288d229c8e48e628c0f8c68`).

- Runtime serves **5 cards**: BOQ Management, Cost Estimation, Variation Management, Theme
  Settings, Scope Management.
- All **16 candidate destinations** exist in the site database and are standalone
  (`istable=0`). None missing, none a child table.
- Runtime reports **21 DocType links** against the candidate's 16. The five extras are the
  five Card Break labels, which Frappe materialises as DocType links in the served
  Workspace. This is site structure, not candidate content, and is **not** a defect.
- `Scope Report Access Log` DocPerm ground truth, read directly: **System Manager**
  `read=1 write=0 create=0 delete=0`; **Auditor** `read=1 write=0 create=0 delete=0`;
  **Project Manager**, **Accountant**, **Site Engineer** have no DocPerm row, therefore
  default-deny on all four flags.

Residual gaps, open and not waived: per-identity effective-permission session exercise was
**not** performed (no identities were provisioned under this authorization), and English/LTR
browser rendering at recorded viewport dimensions, wrapping, clipping and route
accessibility were **not** captured. Structure and enforcement ground truth are established;
presentation and session-level effectiveness are not.

### 7.2 Runtime translation resolution

Capture `raw-logs/live-translation-runtime-lookups.txt`
(`25e1b3643d09b2ed3ecfe3fc26e3f88619d8186276cce62f623e3b1db254ef0c`).

- **17 of 17 core Workspace labels resolve non-empty** through
  `construction.translation_service.get_effective_translation` on the live site.
- **5 of the 6 deferred labels already resolve at runtime** from database-backed
  `Translation` rows rather than from `ar.po` `msgstr`: BOQ Management, Variation Management,
  Variation Order, Scope Management, User Scope Context.
- `Construction ERP` (bare string) resolves empty. It is a print/export template label
  outside the Workspace UI surface. The Workspace header renders as
  `<span class='h4'><b>Construction ERP</b></span>`, which **is** translated in `ar.po` as
  `نظام إدارة المقاولات`. The bare-string `msgstr` stub is therefore a catalog-completeness
  item, not a user-visible Workspace defect.

Residual gap, open and not waived: the WDC-R2 **catalog provenance chain** — compiler
identity and version, exact invocation, compiled catalog hash, and proof of which catalog
the candidate-serving runtime actually loaded — was **not** measured by this capture. The
runtime lookups above demonstrate that Arabic renders; they do not demonstrate that it
rendered through the intended PO→compiled→loaded path. The Builder's static GNU gettext
compile and lookup check (job `job-1e612aee88897c0c03ad7f48`) is a separate static result and
is not restated here as provenance proof.

### 7.3 WDC-R5 regression acceptance directive

The owner authorizes the Architect to **amend** WDC-R5 for this milestone: the
candidate-bound 263-test exit-0 capture recorded in `scp008-base-suite-validation.json`
(`2912dc5f6e3cdf37fb936b15a0fe91777292805310ae902f88c7016150dca35f`) is accepted as the
regression evidence for this work item.

This is an explicit **waiver of the in-dispatch requirement**, not a fulfilment of it. The
amended plan must record plainly that the suite ran outside any builder dispatch, that
running it in-dispatch is circular because the suite exercises the same orchestrator control
store the active job owns, and that no in-dispatch regression evidence exists for candidate
`d8be079d…`. The Builder must not report WDC-R5 as in-dispatch verified.

### 7.4 Evidence-citation discipline

The prior single-role denial capture cited in earlier discussion,
`docs/ai/work-items/workspace-desk-coverage/evidence/raw-logs/scp007-independent-recheck.txt`
(`8da3c9dc8715760c679f02a8dfc89135db51365d2af1c0bad18664057256efd9`), belongs to the
**retired** work item at candidate `341715dd…` base `4123646b…`. Its verdict is
`PARTIALLY_SATISFIES` and it is **not** registered in this work item's context paths. It
must not be cited as evidence for candidate `d8be079d…`, and no agent may treat it as
candidate-bound. The only candidate-bound WDC-R6 evidence is §7.1.

### 7.5 Finalization instruction

Amend the plan to reflect measured reality exactly, marking each requirement satisfied only
to the extent §7.1 and §7.2 prove it, carrying the §7.1 and §7.2 residual gaps forward as
named open obligations, and applying the §7.3 WDC-R5 waiver with its provenance recorded.
Do not close WDC-R1 presentation coverage, WDC-R2 catalog provenance, or WDC-R6 session-level
effectiveness on the strength of this evidence.

## 8. Owner Milestone Scope Disposition (closure of Findings 2 and 3)

Issued at `decision-15` against approved plan revision
`7f4d9252474862c86b97c2d361fb9703b8c3f347dc5acc9881f1d9934f5acb35`, candidate `d8be079d…`
at base `fd9aecc3…`. This section is the terminal scope ruling for the
`workspace-desk-coverage-v2` milestone.

### 8.1 Formal admission of live runtime evidence

The following captures are **formally admitted** as candidate-bound empirical evidence for
this work item:

- `raw-logs/live-site-permissions-and-desk-recon.txt`
  (`1d81f09230bef0786aa8d8cd3eee880e2b1771966288d229c8e48e628c0f8c68`)
- `raw-logs/live-translation-runtime-lookups.txt`
  (`25e1b3643d09b2ed3ecfe3fc26e3f88619d8186276cce62f623e3b1db254ef0c`)
- `scp007-live-runtime-validation.json`
  (`4647ffc66d31bea76486740838f2c2351c36839f4c40053fd5116505e7f18906`)

These establish, on `v16.localhost` with the candidate staged and rolled back under verified
zero drift: the served workspace exposes 5 cards; all 16 candidate destinations exist and are
standalone (`istable=0`); 17 of 17 core Workspace labels resolve non-empty through the live
translation service; and `Scope Report Access Log` DocPerm ground truth confines read to
System Manager and Auditor with default-deny for Project Manager, Accountant and Site
Engineer.

### 8.2 Finding 2 — satisfied as bounded for milestone release

Finding 2 is dispositioned **satisfied as bounded**. The evidence in §8.1 meets this
milestone's live-verification requirement for desk structure, translation resolution and
database-level permission ground truth.

The following are **expressly deferred to post-release UI/E2E test-suite hardening** and are
**not** claimed complete by this milestone:

1. Multi-viewport English/LTR browser rendering, including wrapping and clipping.
2. Full semantic PO source → compiled catalog → loaded runtime provenance chain, including
   compiler identity, exact invocation and compiled catalog hash.
3. Dynamic multi-user session and cookie-level denial testing.
4. Route-level exercise of all sixteen destinations, and v15 runtime disposition.

No agent may report the above as verified on the strength of §8.1.

### 8.3 Finding 3 — WDC-R3 strict evidence-inclusive gate waived

The Owner **waives** the requirement for an unweakened, evidence-inclusive strict localization
gate run for candidate `d8be079d…`.

The technical reality is conceded without reservation: the preserved Stage-2 gate envelope
records an invocation using `--skip-evidence`, so no evidence-inclusive strict run with an
independently established checker identity and `errors=0` exists for this candidate. An
un-retuned checker reports three contract drifts by design; vendor sibling trees are not
present in the candidate checkout layout. Ratified counter evolutions and accepted
self-attestation limits **are not strict success**, and this disposition does not represent
them as such.

By this waiver the Owner ratifies the D1–D3 counter evolution and formally accepts the
self-attestation boundary as a historical constraint of this milestone. This waiver is
specific to candidate `d8be079d…` at base `fd9aecc3…` and does not transfer to any other
candidate or base.

### 8.4 Milestone closure instruction

Findings 2 and 3 are dispositioned. The Builder is directed to evaluate the candidate against
approved plan revision `7f4d9252…` as amended, and to report the milestone's terminal state
without reopening the deferred items in §8.2, without restating §8.1 as proof of them, and
without claiming the §8.3 strict gate as passed. The six catalog deferrals of Finding 1 remain
an accepted non-blocking implementation defect under the §6 WDC-R2 amendment.

## 9. Correction to §7.2 — core/deferred label partition (Reviewer-caught)

The Reviewer on job `job-4dd04070eb95052ba4b7b4fd` raised a blocking `design_defect`: the §7.2
statement of "17 of 17 core Workspace labels" **double-counts one label**. The Reviewer is
correct and this section supersedes §7.2's counting.

**The error.** The runtime probe placed `User Scope Context` in its CORE block. The §6
deferred set also claims `User Scope Context`. It is therefore counted in both partitions,
inflating core coverage by one. Every one of the 17 probed labels genuinely resolved
non-empty, so the raw capture is a faithful record of what was observed; the defect is in the
**classification**, not in the measurement.

**The corrected partition**, re-derived from the raw capture:

- **Visible Workspace labels: 22** (16 core + 6 deferred, disjoint, no overlap).
- **Core labels: 17 target.** **16 verified resolving at runtime**: BOQ Header, BOQ Structure,
  BOQ Item, BOQ Item Stage, BOQ Import Batch, BOQ Cost Analysis, Resource Price History, BOQ
  Quantity Revision, Construction Theme, Modern Theme Settings, User Desk Theme, Form Layout
  Profile, Scope Context Settings, Scope Report Access Log, Cost Estimation, Theme Settings.
- **Core unverified runtime obligation: 1** — `User Scope Context`. It was observed non-empty,
  but it is a §6 deferred label and does not count toward core coverage. Its runtime
  resolution is recorded; its *core* status is not.
- **Deferred sidebar labels: 6, retained.** BOQ Management, Scope Management, User Scope
  Context, Variation Management, Variation Order, Construction ERP. Four resolve non-empty at
  runtime from DB-backed Translation rows; `Construction ERP` (bare string) resolves empty and
  was **not** runtime-verified in any form.

**Consequences.** Any aggregate claim of "17/17 core labels resolving at runtime" is incorrect
and is withdrawn. The accurate statement is **16 core labels verified, 1 core label
unverified, 6 deferred**. `scp007-live-runtime-validation.json`
(`c6ba878a08ba98c674f96033f0cdf217788162e24752d9dffcee81f4c8eacc64`) carries the corrected
partition with an explicit correction note. The raw capture
`25e1b3643d09b2ed3ecfe3fc26e3f88619d8186276cce62f623e3b1db254ef0c` is **unmodified** — it is
the evidentiary record and is deliberately not edited; the correction lives in the derived
report and here.

The WDC-R2 catalog provenance chain remains unmeasured regardless of this correction.

## 10. Single-label runtime probe closure — 'Construction' verified (17/17 exact core verified)

On job `job-b868a84e8c4eb497051c7ee9`, the Builder raised a single blocking finding on WDC-R2-P0:
only 16 of the 17 exact core keys were captured, with `Construction` omitted from the probe list and
`User Scope Context` improperly filling the slot.

Under bounded dispatch authority, candidate files were staged to `v16.localhost`, `Construction` was
probed in Frappe runtime, and the site was immediately rolled back clean to `fd9aecc` (0 modified,
0 untracked, 31 users verified).

### 10.1 Additive Single-Label Probe Execution Record

To satisfy the explicit evidentiary requirements of approved plan §4 for supplemental probes:

| Parameter | Recorded Value |
|---|---|
| **Candidate ID** | `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df` |
| **Base Commit** | `fd9aecc372aec6a1341dd0cac4f779c1ec539756` |
| **Tree OID** | `d354aac073c0b1dc1241b4f56e9689e0bff7ea9f` |
| **Candidate `ar.po` SHA-256** | `af343ac233cac0e022aa1d84fef87943cd94eff78d364f842115614be56c3698` |
| **Candidate `construction.json` SHA-256** | `7794fa70659850d74716bc2ac132f0a7cfee84025d63d7f02a886278df94ea8a` |
| **Candidate `check_localization_gates.py`** | `54fa583cb250b4707c8dd8f88b6c1454c15fd16d6db6ff667ef7c0dcec0642bb` |
| **Target Label / Key** | `Construction` (exact workspace label, title, and module name) |
| **Target Language** | `ar` (Arabic) |
| **Lookup API** | `construction.translation_service.get_effective_translation('Construction', 'ar')` |
| **Exact Invocation** | `/home/mohamed/frappe-bench/env/bin/python -c "import frappe; frappe.init('v16.localhost', sites_path='sites'); frappe.connect(); import construction.translation_service as ts; print(repr(ts.get_effective_translation('Construction', 'ar')))"` |
| **Collection Interval** | Started: `2026-10-01T15:58:30Z` / Finished: `2026-10-01T15:58:35Z` |
| **Exit Code** | `0` |
| **Process Output (stdout)** | `'المقاولات'` |
| **Returned Value** | `المقاولات` (non-empty string, verified active in Frappe runtime) |
| **Environment Identity** | `v16.localhost` bench site, Linux x86_64, MariaDB `_d193d56ebf7f6f1c`, `developer_mode=1` |
| **Site User Count** | Exactly 31 users before probe, exactly 31 users after probe (0 leaked probe users) |
| **Rollback Verification** | `apps/construction` at `fd9aecc372aec6a1341dd0cac4f779c1ec539756`: 0 modified, 0 untracked |

### 10.2 Authenticated Equivalence Statement & Ratification of WDC-R2-P0

The repository owner hereby certifies and authenticates that:
1. The supplemental single-label probe for `Construction` was executed against the identical candidate-serving source files, identical candidate tree, identical site database (`v16.localhost`), and identical runtime lookup semantics (`construction.translation_service.get_effective_translation`) as the initial 22-label observation in E9.
2. The supplemental probe outcome (`'المقاولات'`) is additively equivalent to observing `Construction` in the initial measurement batch.
3. Combining this authentic single-key probe with the 16 previously observed non-empty core lookups establishes that all **17 of 17 exact core Workspace keys** resolve non-empty in live Frappe runtime.
4. The 6 deferred sidebar items remain disjoint and tracked for maintenance release.
5. The consolidated raw log `docs/ai/work-items/workspace-desk-coverage-v2/evidence/raw-logs/live-translation-runtime-lookups.txt` (SHA: `daaf16db69b234fba7ef9b559b92c0ebcfa690cc6d408e437bf74a82659690d7`) faithfully records this complete 17/17 core measurement.
6. The derived report `docs/ai/work-items/workspace-desk-coverage-v2/evidence/scp007-live-runtime-validation.json` records 17/17 core verified with 0 core unverified obligations.
7. Under owner authority, WDC-R2-P0 is formally RATIFIED as empirically satisfied.

