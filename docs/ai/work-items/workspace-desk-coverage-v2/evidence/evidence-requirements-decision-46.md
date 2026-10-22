# Evidence Requirements for `decision-46` (SCP-006 / SCP-007 / SCP-008)

**Date:** 2026-09-30
**Work item:** `workspace-desk-coverage`
**Gate:** `decision-46` (`PAUSED`, `OWNER_DECISION`)
**Builder result:** `job-567d102eadebb723396424a4` — `BLOCKED`, seq 47
**Purpose:** concrete, checkable requirements for closing the three blocking findings, derived
from the builder's own findings and the authoritative plan it cited.

---

## 0. Source of Truth for This Document

The builder cited `plan.md` lines 90, 108, 120–140, 156, 158, 166–168. That plan resolves to:

```
docs/ai/work-items/workspace-desk-coverage/runs/job-3c717b1ed18a9fe10142bf7d/results/plan.md
```

(219 lines; the architect plan referenced in all three findings' `evidence_refs` as
`job-3c717b1ed18a9fe10142bf7d-plan`). It is **not** `owner-plan-source.md` (39 lines) nor
`owner-original-implementation-plan-2026-09-29.md` (210 lines, whose lines 118–140 are JSON diff
fragments). The architect plan is the contract.

## 1. The Structural Blocker — Read This First

The builder **cannot produce any of this evidence itself**, and is not authorized to try.
Plan line 158:

> "Any new test run needs a separately permitted isolated harness and temporary-write
> footprint. **No engine mutation, approval command, live workflow exercise, or routing repair
> is authorized here.** `orchestrator/roles.json` remains excluded."

And the builder's own explanation: *"the packet supplies empty `builder_evidence` and
`candidate_validation_reports` lists."*

Therefore every requirement below must be satisfied by an **owner-controlled evidence package**,
delivered through the one channel the engine actually binds into the job packet:

```python
# engine.py:974-1006
evidence_roots = {work / "evidence",
                  <repo>/docs/ai/roles/... -> docs/ai/work-items/<work_item>/evidence}
for source in evidence_root.glob("*validation.json"):
    binding = report.get("candidate")
    if not isinstance(binding, dict) or not isinstance(report.get("commands"), list): continue
    if (binding["candidate_id"] != v["candidate"]["candidate_id"]
        or binding["manifest"]     != v["candidate"]["manifest"]
        or binding["tree_oid"]     != v["candidate"]["tree_oid"]
        or digest(binding["manifest"]) != binding["candidate_id"]): continue
    # -> copied read-only into job runtime, added to read_artifacts
```

**Binding contract — non-negotiable:**

| Field | Required value |
|---|---|
| `candidate.candidate_id` | `341715dde1ab8ab7abbefb66faba89c4b3590062177dcb82865f8a46a3570cad` |
| `candidate.manifest` | Byte-equal to the frozen manifest object |
| `candidate.tree_oid` | Frozen `tree_oid` |
| `digest(candidate.manifest)` | Must equal `candidate_id` |
| `commands` | A list (per-command detail) |

File location: `docs/ai/work-items/workspace-desk-coverage/evidence/*validation.json`
(in `generated`, so it does not perturb the candidate). Symlinks are rejected
(`engine.py:980-981`).

**This binding is what makes the evidence candidate-bound rather than self-asserted** — the
report cannot be reused against any other candidate.

## 2. SCP-006 — Authenticated Strict-Gate Provenance

**Finding:** *"`stage2/full-gate.txt` line 1 records `COMMAND: python3
scripts/check_localization_gates.py --skip-evidence`; `freshness_evidence.json`
`collected_utc` 2026-09-29T20:02:55Z vs `db_now_at_collection` 2026-09-29 23:02:55 (+3h)
remains unreconciled. The authenticated strict-run package … is absent. Comparator exit 0
proves present equality only."*

Plan L120–140 (WDC-R3/R4) requires an **owner-controlled evidence package** of five parts:

| # | Requirement | Detail |
|---|---|---|
| 1 | **Original strict-gate capture** | Exact command, working directory, start/end UTC, exit status, complete relevant output, digest. Must be a *native* execution of `python3 scripts/check_localization_gates.py` with **no weakened flags** (i.e. **not** `--skip-evidence`), exit 0, `errors=0` |
| 2 | **Execution-time linkage manifest** | Link the tested 19 app-side files to the frozen candidate **at execution time**. Must include: tested base commit, relevant additional changes *or positive evidence of their absence*, checker inputs, framework/vendor revisions, catalog hashes, interpreter/dependency context. Plan is explicit: *"A shared base commit and the 19 changed files alone do not rule out unrelated installed modifications."* |
| 3 | **Native comparison result** | From the declared command, with **candidate identity rechecked before relying on it**. *"A mismatch blocks acceptance rather than authorizing copying or synchronization."* |
| 4 | **Independent assessability** | *"Provenance sufficient for an independent verifier to assess the capture without relying on another reviewer's verdict."* |
| 5 | **Chronology reconciliation** | Collector provenance for freshness; explicit timezone/clock interpretation for `collected_utc 20:02:55Z` vs `db_now_at_collection 23:02:55` vs envelope start `21:08:13Z` vs audit `2026-09-30 01:31–01:32`. Plan forbids editing historical timestamps: *"Do not infer validity from unlabeled timestamps or edit historical timestamps to remove the discrepancy."* |

### 2.1 The circularity problem this must break

Independently confirmed by adversarial re-check
(`independent-adversarial-recheck-2026-09-30.md`):

- `stage2/index.txt` records `CHECKER_SHA256: 54fa583c…` — **the retuned checker attesting to
  its own output.** The provenance chain terminates in the artifact it authenticates.
- Running the **pre-candidate** checker against byte-identical content yields **3 real drift
  failures** that the retuned thresholds suppress.

Requirement 2 is therefore the crux: the manifest must prove the *checker itself* was the
independently-fixed version at execution time. A capture produced by the retuned checker
reproduces the circularity regardless of how well it is documented.

### 2.2 Practical route

- Run the strict gate with a checker whose `EXPECTED_GATE` is **not** part of the evidence
  chain, or record the checker's own hash from a trusted source independent of the candidate.
- Regenerate `stage2/` envelopes is **prohibited** for WDC-R4: *"Preserve the frozen envelopes
  as historical evidence"* and *"Excluded release files must not be rewritten to satisfy
  checks."* The new capture must be **additive**, in a new `*validation.json`.

## 3. SCP-007 — Runtime Acceptance (WDC-R1/R2/R6)

**Finding:** *"the report describes Arabic Administrator navigation and English dictionary
fallback, not English/LTR browser coverage including wrapping/clipping. Compilation and lookup
claims lack the required source/compiled-catalog binding; effective-permission, Workspace
filtering, direct-access and rollback claims lack the required authenticated
candidate/framework-bound captures."*

Plan requirements:

| Requirement | Source | Status against work already done |
|---|---|---|
| **English/LTR browser run** demonstrating all 16 destinations incl. wrapping, clipping, routing | L90 | **NOT MET.** The adversarial re-check measured label lengths (max card 20, max label 23) and RTL/bidi absence **statically**. Plan: *"The report's Arabic Administrator navigation and English dictionary fallback do not establish an English browser run."* Static checks are explicitly insufficient |
| **PO parsing/compilation evidence** bound to source **and** compiled catalog | L108 | **NOT MET.** No source↔compiled-catalog binding exists |
| **Runtime lookup evidence** bound to source and compiled catalog | L108 | **NOT MET** |
| **Effective permissions** for SRAL: System Manager/Auditor `read=true`, `create/write/delete=false`; unprivileged Site Engineer/Project Manager/Accountant all four `false` | L166-168 | **PARTIALLY MET.** `DocPerm` ground truth confirmed; real single-role probe users confirmed. But plan: *"Static DocPerm records and Administrator navigation cannot substitute for these checks"* |
| **Workspace filtering** + no sensitive link for unprivileged roles | L166-168 | **PARTIALLY MET.** Measured 14/16, 11/16, 12/16, 6/16 visibility from real users |
| **Denied direct list/data access** | L166-168 | **MET.** `frappe.get_list` raised `PermissionError`; each identity confirmed to retain normal `User`-doctype access, so denial is targeted not blanket |
| **Authenticated rollback + residual-user checks** | L168 | **MET.** 31 → 31, drift 0, no probe identities remain |
| **v15 compatibility** | L90 | **NOT ADDRESSED.** Plan: *"do not claim v15 runtime verification without evidence or an explicit reviewed disposition"* |

**Why the builder still blocked it despite the measurements being real:** the re-check ran as
an *out-of-band* operator action and produced `FINDINGS: 0` in
`raw-logs/scp007-independent-recheck.txt` — but that file is **not a `*validation.json`**, so
the engine never bound it into the job packet. The builder saw no candidate-bound evidence at
all. This is a **packaging failure, not a measurement failure**: the work satisfies several
requirements but is invisible to the evaluator.

**Genuinely still missing regardless of packaging:** English/LTR **browser** coverage with
wrapping/clipping, and PO source↔compiled-catalog binding.

## 4. SCP-008 — Regression Capture (WDC-R5)

**Finding:** *"The 236/236 result exists only as prose … no exact suite command, collected
count, exit, environment or source-hash capture … source assertions are not executed
regression evidence. No suite run attempted: plan line 158 requires a separately permitted
isolated harness."*

Plan L156 requires:

1. **Captured regression evidence** for: builder and verifier metadata, missing/mismatched
   grants, continued builder refusal, preapproval behavior, absence of consumable fields.
2. **Exact suite command**, collected count, exit, source hashes, environment.
3. *"Do not equate a `test_engine.py`-only run with a full orchestrator suite without evidence
   of its collected count."*

**Position against work already done:** the required evidence **exists** at
`raw-logs/orchestrator-regression-236.txt` —

```
$ ./orchestrator/.venv/bin/pytest orchestrator/tests -v
236 passed in 82.24s
EXIT_CODE=0
```

with source hashes recorded (`engine.py 42161cee…`, `test_engine.py 2fb47b5b…`, base
`4123646b`). The adversarial re-check additionally ran the base suite against the candidate
`engine.py` unmodified (22/22, and 234/236 full suite with 2 environmental failures).

**Again a packaging failure:** `orchestrator-regression-236.txt` is not a `*validation.json`,
so it was never bound into the packet and the builder correctly refused prose claims.
All four named cases (builder/verifier metadata, missing/mismatched grants, builder refusal,
preapproval absence) are already asserted by `test_engine.py` and were executed.

## 5. Consolidated Delivery Checklist

Create candidate-bound reports under `docs/ai/work-items/workspace-desk-coverage/evidence/`:

| File | Contents | Closes |
|---|---|---|
| `strict-gate-authenticated-validation.json` | Requirements 1–5 of §2, incl. execution-time linkage manifest and chronology reconciliation | SCP-006 |
| `runtime-acceptance-validation.json` | PO source↔compiled-catalog binding, runtime lookup, effective-permission/filtering/direct-access/rollback captures, **plus the English/LTR browser run** | SCP-007 |
| `regression-capture-validation.json` | Exact suite command, collected count, exit, environment, source hashes, and the four required case outcomes | SCP-008 |

Each must satisfy the §1 binding contract or it will be silently skipped by `engine.py:989-998`.

## 6. Honest Assessment

- **SCP-008 is essentially complete** and needs repackaging into the bound channel.
- **SCP-007 is partially complete.** Permission/filtering/denial/rollback work is done and
  valid; English/LTR **browser** evidence and PO source↔compiled-catalog binding are genuinely
  absent. v15 remains unaddressed.
- **SCP-006 is the hard one.** It requires a strict-gate capture that is not self-referential.
  Since the candidate's own checker is the retuned one, the capture must come from a checker
  whose identity is established independently — otherwise the circularity the builder and the
  adversarial re-check both identified is reproduced no matter how well documented.

## 7. Escalation Warning

Current budget: `unsuccessful_cycles = 2` (threshold ≥3), `unchanged_rounds = 1` (threshold
≥2), `attempt = 18` (**uncapped** — not a budget). The next blocked result fold sets
`unchanged_rounds = 2` and triggers `pause(state, "ESCALATED")` (`routing.py:187-188`).
Recovery then requires `owner_decision("resume", …, reset_budget=True)`.

Producing the evidence package takes at least one cycle. **The budget reset should be an
explicit, deliberate owner decision made before the next dispatch**, not a reaction to
escalation.
