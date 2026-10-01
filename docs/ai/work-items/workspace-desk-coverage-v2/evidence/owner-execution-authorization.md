# Owner Bounded Execution Authorization

**Work item:** `workspace-desk-coverage-v2`
**Candidate:** `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df`
**Base commit:** `fd9aecc372aec6a1341dd0cac4f779c1ec539756`
**Tree OID:** `d354aac073c0b1dc1241b4f56e9689e0bff7ea9f`
**Date:** 2026-10-01
**Authority:** owner instruction given in session; transcribed by the agent

Issued in response to the Builder's Finding 1 at `decision-3`: the approved contract required
separately authorised execution-time validation, and the packet specified no boundary.

---

## 1. Target and boundary

| Item | Value |
|---|---|
| Site | Local test bench, `http://127.0.0.1:8000` |
| Site name | `v16.localhost` |
| App path | `/home/mohamed/frappe-bench/apps/construction` |
| Environment | **Local test bench only.** Not production. Not any remote site |
| Candidate source | This worktree, `/home/mohamed/frappe-bench/worktrees/workspace-desk-coverage-v2` |

## 2. Authorised actions

1. **Staging.** Copy the 19 candidate files from this worktree into `apps/construction` for
   execution-time measurement only. No other file may be written to `apps/construction`.
2. **Probe identities.** Create isolated temporary users matching `adv_probe_*@test.local`,
   each carrying exactly one target role, solely to exercise effective-permission paths.
3. **Measurement.** Run the permission/Desk probe and any English/LTR browser coverage,
   capturing evidence.
4. **Rollback — mandatory.** Restore `apps/construction` to committed base `fd9aecc3…`
   immediately on completion, in the same working session, whether measurement succeeded or
   failed. **Guaranteed net drift: zero.**
5. **Identity cleanup — mandatory.** Delete every `adv_probe_*` identity. **Guaranteed user
   count returns to exactly 31.**
6. **Evidence destination.** Write evidence artefacts **exclusively** to
   `docs/ai/work-items/workspace-desk-coverage-v2/evidence/`.

## 3. Explicit prohibitions

| Prohibited | Reason |
|---|---|
| Any production, staging-remote, or non-`v16.localhost` operation | Out of scope; test bench only |
| Writing evidence outside `<work-item>/evidence/` | Keeps evidence out of the candidate payload |
| Retaining any `adv_probe_*` identity | Cleanup is part of the authorisation, not optional |
| Leaving `apps/construction` modified after the session | Zero-drift guarantee is a condition |
| Editing historical Stage-2 envelopes or timestamps | WDC-R4 waiver forbids retroactive edits |
| Any commit to `develop`, or any remote push | Separate owner authorisation required |

## 4. Reversibility

Every authorised action is reversible and the reversal is specified in advance:

| Action | Reversal | Verification |
|---|---|---|
| Staging 19 files | `git -C apps/construction checkout -- <19 paths>` | `git status --porcelain` empty |
| Probe identities | `DELETE` each `adv_probe_*` | `frappe.db.count("User") == 31` |
| Evidence artefacts | Additive; `evidence/` is `generated`-excluded | `candidate recheck` PASS |

The pre-authorisation state is recoverable: the 19 candidate files are byte-identical in this
worktree and pinned by the candidate manifest, so `apps/construction` can always be restored
from `fd9aecc3…`.

## 5. What this authorisation does NOT do

- It does **not** certify WDC-R1/R2/R6. It authorises the *measurement* that would.
- It does **not** waive the WDC-R3 strict-gate requirement, which remains governed by
  `scp006-delta-ratification-disposition.md`.
- It does **not** authorise an in-dispatch orchestrator test run. The isolated-harness
  requirement for a *builder-dispatched* regression capture remains separately unmet; the
  SCP-008 report is an out-of-dispatch executed capture under this authorisation.
- It confers **no precedent**. Every future measurement requires its own authorisation.

## 6. Revocation

Authorised by the owner in session on 2026-10-01, bounded to candidate `d8be079d…` at base
`fd9aecc3…`. Revocable at any time; if revoked mid-session, actions already taken must still be
rolled back per §2.4 and §2.5.