# F37 — Workload qualification evidence (lab fresh site, 2026-10-15)

Candidate HEAD `fa38022` · lab site `f31fresh-clean.localhost` (isolated lab
`/tmp/construction-foundation-lab-20261014`) · D1 profile (Egypt-SME reference
baseline, test-only — **not a capacity promise**).

## 1. Workload assumptions (explicit, engineering-only)

- Actors: 2–4 threads on lab hardware; personas are the ordinary acceptance accounts
  (`f31-pm`, `acc-eng`, `acc-owner`, `Administrator` used only where a persona cannot
  legally act, and then recorded).
- Timings below are **observations, not SLAs**. No customer-capacity, no scale claim;
  D1 profile bounds every statement.
- Setup that mirrors documented configuration (not product defects): wizard completion,
  standard masters, `enable_variation_orders` switch, reviewed Custom DocPerm Company
  read-only grant applied via the reviewed process (replicate standard rows, then narrow
  rows — never a bare first write; verified PM read=True, write=False).

## 2. Dataset (D1 profile achieved)

| Dimension | Target | Achieved | Evidence |
|---|---|---|---|
| Projects | 2 | ACC-001 + PROJ-0002 | dataset script |
| BOQ items | ~200 | 200 items + structures (seeded 116.4s) | prior F37 record |
| Analyses | ~50 | 50 approved analyses (3.4s) | `f37_dataset.py` |
| Purchase history | 6 months | 6 backdated Resource Price History rows 2026-04..2026-09 | `f37_dataset.py` |
| Variation orders | 5 | 5 VOs in Draft / Submitted / Approved by Engineer / Approved by Client ×2 on locked header BOQ-2026-0218 | `f37_vos.py` |
| Header total integrity | — | BOQ-2026-0008 total 268,310.00 matches recompute | prior F37 record |

Setup finding during VOs: `create_variation_order` correctly refuses while
`enable_variation_orders=0` (“disabled by Construction Settings”) — the safety gate,
mirroring rehearsal. Line validation enforced rate-change justification rules; the
dataset was corrected to satisfy them (52 vs 50 qty change, revised price, justification).

Partial-run fixture: an earlier failed VO attempt left header BOQ-2026-0209 whose
Approved quantity revisions are **permanent by design** (deletion refused:
“Approved or previously approved revisions cannot be deleted”). The header was therefore
kept as documented fixture state rather than force-cleaned — recorded, not hidden.

## 3. Concurrency — reconciliation of existing evidence (not repeated)

| Already proven | Where | Scenario |
|---|---|---|
| VO client approval | `test_concurrent_variation_order_client_approval` (test_security_audit_remediation.py:572) | Barrier-synchronized 2 transitions on same VO → exactly 1 revision, serialized |
| Stage over-allocation | `run_stage_concurrent_distribution_smoke` (test_boq_item_stage.py:210) | ThreadPoolExecutor 2 inserts on same item → 1 success + 1 refused (“exceeds BOQ Item quantity”), total planned 6 |
| Atomicity | F08/customer Release guard suites (savepoint rollback) | No partial writes on refusal |
| Same-item approval single-winner + reports | F37 turn-1 batch `f37_conc.py` | 1 submit + 1 refusal on same item; parallel reports 150 rows ~0.57–0.58s; stage autoname race single winner (retry succeeds) |

## 4. Concurrency — gaps executed this turn (`f37_conc2.py`)

| Scenario | Threads | Result |
|---|---|---|
| Same-VO concurrent engineer transition | 2× `acc-eng` on BOQ-2026-0218-VO-002 | Both calls returned success; final status `Approved by Engineer`; single approver recorded; **0 duplicate revisions**; no double side effects |
| Parallel approvals on different items | 2× `f31-pm` | Both submitted (0.02–0.03s each, wall 0.12s) — independent progression, no false contention |
| Concurrent measurement on same stage | 2× `acc-eng` on BOQ-STG-00004 | One refused `TimestampMismatchError` (stale-read refused, optimistic concurrency), one committed; final 7.0 consistent — last-writer-wins, no corruption |

Honest limits recorded:

- The same-VO race used the **same user on both threads**, so a same-user overwrite
  cannot be distinguished from an idempotent second transition. The cross-user
  serialization case is already proven by the barrier test in §3 (exactly one revision).
  Both callers here were engineers; the SoD boundary (engineer ≠ client approver) is
  proven separately in F06/F36 evidence.
- The lab site has no independent second owner-class account beyond `acc-owner`; VO client
  approvals in the dataset therefore used the permitted owner persona.

## 5. Residue management

Concurrency fixtures removed after capture: 5 analyses (`ACC conc*`, `ACC conc par*`)
cancelled then deleted, 3 stages deleted — residue check 0/0. Dataset headers ACC-*: 7
intentionally retained as the acceptance fixture (BOQ-2026-0001 reserved for owner UI).

## 6. Status

Dataset + read + write concurrency coverage complete at D1 scale on the lab.
**Out of scope (by decision):** business volumes at production scale, customer capacity
statements, shared-DBA provisioning. F37 engineering row: lab measurement complete;
owner limits commentary remains with the F44 block.
