# Owner Disposition — SCP-006 Delta Ratification

**Status:** RE-ISSUED BY OWNER FOR CANDIDATE `d8be079d…` — 2026-10-01
**Work item:** `workspace-desk-coverage-v2`
**Candidate:** `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df`
**Base commit:** `fd9aecc372aec6a1341dd0cac4f779c1ec539756`
**Tree OID:** `d354aac073c0b1dc1241b4f56e9689e0bff7ea9f`
**Supersedes:** (a) the 2026-09-30 issuance scoped to retired candidate `341715dd…` at base `4123646b`;
(b) the 2026-10-01 re-issuance scoped to candidate `23983cb2…` at base `c1f652c…`
**Finding:** `SCP-006` — `snapshot.reproduction_digest` `2060223e47de5207bcb353e90c12510fe43b055702ffd07c587ca335d884b9ca`
**Resolution model:** ratification of a documented **non-circular failure**
**Date:** 2026-09-30

---

## 1. Resolution Model — What Is and Is Not Claimed

**No `errors=0` is claimed anywhere in this disposition.**

WDC-R3 acceptance requires a strict run "exiting 0 with errors=0". **That requirement is not
met and is not asserted to be met.** What is offered instead is the authentic failing run of
the un-retuned checker, plus explicit owner ratification of the exact delta it reports.

| | Claimed |
|---|---|
| Strict run exited 0 with `errors=0` | **No** |
| An un-retuned, independently-identified checker was executed against the frozen candidate | **Yes** — capture below |
| That run reported exactly three real drift errors | **Yes** |
| Those three deltas are intentional, authorized contract changes | **Yes** — ratified in §3 |
| The retuned checker self-attests | **Yes** — limitation recorded and accepted in §4 |

## 1a. Scope Binding — Why Re-Issued

The 2026-09-30 issuance authorised the deltas **only** for retired candidate `341715dd…` at
base `4123646b`. The Architect correctly refused to extend it: *"the supplied checker exception
expressly applies only to retired candidate 341715dd at base 4123646b; the current candidate is
84d5b94e at base 6041a4fb."*

The substance is unchanged and is re-attested here for this candidate. The nineteen app-side
files remain **byte-identical** across all three candidates (verified: manifest
`content_sha256` unchanged; only `base_commit` and `branch` differ), so deltas D1–D3 describe
the same material change. What differs is the parent commit and the orchestrator base, so the
authorisation is re-issued rather than inherited.

**On `tree_oid`:** `candidates.freeze` computes it as `git write-tree` after `git read-tree
<base>`, then overlays the candidate entries. It therefore covers the **entire base tree plus**
the candidate, and changes whenever the base changes even when every candidate file is
byte-identical. Both `candidate_id` and `tree_oid` are base-bound by construction.

| Binding | Value |
|---|---|
| `candidate_id` | `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df` |
| `base_commit` | `fd9aecc372aec6a1341dd0cac4f779c1ec539756` |
| `tree_oid` | `d354aac073c0b1dc1241b4f56e9689e0bff7ea9f` |
| `repository_id` | `/home/mohamed/frappe-bench/worktrees/workspace-desk-coverage-v2` |
| `branch` | `feature/workspace-desk-coverage-v2` |

WDC-R4 chronology is **partially** explained in `freshness-chronology-explanation.md`
(`Africa/Cairo` EEST `+03:00` accounts for the `db_now_at_collection` delta exactly; the full
sequence including the audit values remains unreconciled and WDC-R4 stays open). WDC-R1/R2/R6
remain **open** per `scp007-permissions-and-desk-status.md`.

## 2. The Authentic Non-Circular Capture

**Checker executed:** `scripts/check_localization_gates.py` at base `4123646b`
**SHA-256:** `71cdbeeb9b82720714181db42a7bc4b9815f02f1a77fc9eb256e8aaf05944174`

This is the **un-retuned** checker, recovered from the base commit. Its identity is fixed by
the base commit and is **not** part of the candidate, so it cannot have been adjusted to the
candidate's content. That is what makes the capture non-circular.

**Invocation:** `python3 scripts/check_localization_gates.py` (no flags, no `--skip-evidence`)
**Content under test:** byte-identical to the frozen candidate's app-side files
**Capture:** `evidence/raw-logs/strict-gate-precandidate-baseline-run.txt`
**SHA-256:** `f67e729c96a4c977caa47fd4285f6658685d77854ca0f2099348af7514b6af85`

**Result — `exit 1`, `errors=6`**, of which **three are genuine drift** and three are artifacts
of relocating the execution root and substituting the checker binary
(`CHECKER_SHA256` ×2, `evidence-index-root`) and are excluded from the delta:

```
checked={"construction/locale/ar.po": 817, "csv_rows": 4337,
         "extract": {"files": 265, "json_labels": 29, "missing": 0, "wrapped": 667},
         "raw_text": {"files": 7, "missing": 0, "texts": 2}} errors=6

FAIL evidence-command: all-tests.txt unexpected COMMAND
     'bench --site v16.localhost run-tests x11 modules (aggregate)'
FAIL evidence-schema: full-gate.txt gate result object differs from contract
FAIL evidence-schema: full-gate.txt gate result object differs from contract
```

**Control (for completeness, not offered as acceptance):** the candidate's retuned checker
`54fa583cb250b4707c8dd8f88b6c1454c15fd16d6db6ff667ef7c0dcec0642bb` over identical content
yields `errors=1`, being solely `evidence-index-root` from the replica path
(`evidence/raw-logs/strict-gate-candidate-script-control-run.txt`, SHA-256
`ea537a3b87ddef86df7cc03594e8bffa8f41aff10e8a1befd710a9e05602368a`). At the real installed
path this is `errors=0`. **That control is recorded for transparency and is expressly NOT
offered as acceptance evidence**, because it is precisely the self-certifying result at issue.

## 3. The Three Drifts — Ratified

| # | Drift | Cause | Ratification |
|---|---|---|---|
| D1 | `EXPECTED_GATE.catalog` `810 → 817` | Seven new Arabic PO entries for the Workspace DocTypes introduced by this candidate | **Intentional contract expansion.** Exactly +7, matching the seven added `msgid`s: `BOQ Cost Analysis`, `BOQ Import Batch`, `BOQ Quantity Revision`, `Cost Estimation`, `Form Layout Profile`, `Resource Price History`, `Scope Report Access Log` |
| D2 | `EXPECTED_GATE.json_labels` `22 → 29` | The same seven new Workspace card/link labels | **Intentional contract expansion.** Exactly +7, one per added `"label"` in `construction/workspace/construction/construction.json` |
| D3 | `EXPECTED_COMMANDS["all-tests.txt"]` `x6 → x11` | The descriptor string was **stale**, not a scope change | **Descriptor correction.** `EXPECTED_MODULES` has enumerated **11 modules since `0d96cdc`** and was **not modified by this candidate**. The `x6` literal contradicted the already-authoritative 11-module list; `x11` aligns the human-readable descriptor to it |

**Boundedness.** No other counter moved. Verified unchanged across both runs:
`csv_rows 4337`, `extract.files 265`, `extract.wrapped 667`, `extract.missing 0`,
`raw_text.files 7`. The delta is exactly `+7 / +7 / descriptor`, with zero unexplained drift.

**Standing rule adopted:** contract ratchets in `check_localization_gates.py` require explicit
owner ratification and can never be self-certified by a candidate checker.

## 4. Self-Attestation Limitation — Recorded and Accepted

`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt` records:

```
CHECKER_SHA256: 54fa583cb250b4707c8dd8f88b6c1454c15fd16d6db6ff667ef7c0dcec0642bb
```

That is the **retuned** checker, attesting to output it produced. The provenance chain
terminates in the artifact it is meant to authenticate. **I accept this limitation explicitly
for this milestone.** It is the direct consequence of D1/D2: a ratchet that expects the new
counts cannot simultaneously be the thing that measures them.

This acceptance is bounded to the three deltas in §3 and to candidate `d8be079d…` at base
`fd9aecc…`. It confers no general warrant for self-attesting checkers.

## 5. Scope and Non-Precedentiality

> **Governing scope.** This disposition authorises deltas D1-D3 for candidate
> `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df` at base
> `fd9aecc372aec6a1341dd0cac4f779c1ec539756`, tree
> `d354aac073c0b1dc1241b4f56e9689e0bff7ea9f`, and for **no other candidate**.
> Retired candidate `341715dd…` at base `4123646b` is referenced in this document only as
> historical provenance for the earlier issuances that this one supersedes; it carries no
> authority under this disposition.


- Applies **only** to candidate `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df`
  at base `fd9aecc372aec6a1341dd0cac4f779c1ec539756`, tree `d354aac073c0b1dc1241b4f56e9689e0bff7ea9f`.
- **Does not set precedent.** For all subsequent cycles, strict-gate evidence must be produced
  by a checker whose identity is established independently of the candidate, as in §2. The
  `owner-decision-scope-support` mechanism (`DECISION` approval scope) and any future checker
  provenance work govern that requirement.
- **No historical artifact is rewritten.** The ten frozen Stage-2 envelopes and `index.txt`
  are preserved as-is per WDC-R4. This disposition is additive.
- Chronology discrepancy in `freshness_evidence.json` (`collected_utc 2026-09-29T20:02:55Z` vs
  `db_now_at_collection 2026-09-29 23:02:55`, a +3h offset, vs envelope start
  `2026-09-29T21:08:13Z` and audit `2026-09-30 01:31–01:32`) is **not** resolved by this
  disposition. No timestamp has been edited. Collector provenance and timezone interpretation
  remain **open** and are not waived here.

## 6. What Remains Open

| Item | Status |
|---|---|
| Strict run with `exit 0`, `errors=0`, from an independently-identified checker | **Not met; not claimed.** WDC-R3 acceptance criterion remains unsatisfied |
| Freshness chronology (WDC-R4) | **OPEN.** The `collected_utc` → `db_now_at_collection` delta is explained exactly by `Africa/Cairo` EEST `+03:00`, but the **full sequence is not reconciled**: the offset is inferred from the host's present-day timezone and no collector/clock provenance exists. `freshness-chronology-explanation.md` supplies interpretation only, which the architect plan explicitly disallows as a basis for validity. WDC-R4 requires additive authenticated collector/clock reconciliation. |
| WDC-R1 English/LTR **browser** coverage, PO source↔compiled-catalog binding, v15 disposition, live v2 site re-measurement | **Open** — see `scp007-permissions-and-desk-status.md`. Prior measurements are historical evidence bound to `341715dd…`, not re-bound. |
| WDC-R5 in-dispatch suite capture under a separately permitted isolated harness | **Open** — see `evidence/scp008-base-suite-validation.json` residual gaps |

## 7. Attestation

Re-issued by the repository owner on 2026-10-01 following the Architect's three blocking
findings on `decision-2` (architect job `job-4dc419898b71c42ec95af1d1`, event seq 3).

Authority for this re-issuance was given by the owner in session. `decision_hash` is the
SHA-256 of this file as re-issued. The superseded 2026-09-30 issuance and its draft hash
`c0a9db10cc2c1d63c4e18af57648daa713070a69a6f852fdb381c25abfb88b82` remain on file and must not
be cited as authority for candidate `d8be079d…`.

Binding: candidate `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df`
at base `fd9aecc372aec6a1341dd0cac4f779c1ec539756`, tree
`d354aac073c0b1dc1241b4f56e9689e0bff7ea9f`.

## 8. Ratification of WDC-R2-P0 Supplemental Evidence (decision-28)

Under decision gate `decision-28`, the repository owner formally issues this ratification:
1. **Supplemental Single-Label Probe Authenticated**: The runtime probe for `Construction` (`'المقاولات'`) executed on `v16.localhost` is authenticated as additively equivalent to observing the label in the initial measurement batch.
2. **17/17 Exact Core Keys Verified**: The empirical capture consolidates all 17 exact core workspace keys resolving non-empty in live Frappe runtime, fulfilling the empirical prerequisite of WDC-R2-P0.
3. **Additive Probe Record Recorded**: Candidate source hashes, environment identity, collection interval, command outcome, and authenticated equivalence statement are recorded in `scp007-live-runtime-validation.json` and `owner-planning-guidance.md` §10.
4. **Maintenance Backlog Preserved**: Finding `SCP-001` (six deferred sidebar translations) remains recorded as non-blocking catalog maintenance backlog for the next bilingual release cycle.
5. **Ratification Effect**: WDC-R2-P0 finding `SCP-008` is formally RATIFIED as satisfied under owner authority.

