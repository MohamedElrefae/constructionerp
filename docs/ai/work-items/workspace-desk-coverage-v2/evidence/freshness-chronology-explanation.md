# WDC-R4 Freshness Chronology — Explanation

**Work item:** `workspace-desk-coverage-v2`
**Finding addressed:** Architect finding 3 (`design_defect`) — WDC-R4 chronology partially explained, partially unreconciled
**Date:** 2026-10-01 · **Revised after Architect attempt 2 (seq 5)**

---

## 1. The discrepancy

| Field | Value | Source |
|---|---|---|
| `collected_utc` | `2026-09-29T20:02:55Z` | `construction/data/localization/freshness_evidence.json` |
| `db_now_at_collection` | `2026-09-29 23:02:55` (unlabelled) | same |
| Envelope `STARTED_UTC` | `2026-09-29T21:08:13Z` | `stage2/freshness-envelope.txt` |
| Audit values | `2026-09-30` ≈ `01:31–01:32` | Stage-2 audit records |

The `db_now_at_collection` value is exactly **3 hours** ahead of `collected_utc`, and carries
no timezone designator.

## 2. What IS explained: the `db_now_at_collection` delta

Exactly one pair is accounted for, and the arithmetic is exact.

The host runs in **`Africa/Cairo`**, which on 2026-09-29 was on **EEST (UTC+03:00)** — Egypt
observes daylight saving, which ends in late October, so late September is +03:00, not +02:00.

Verified on this host:

```
$ date -u      -> Wed Sep 30 10:34:23 PM UTC 2026
$ date         -> Thu Oct  1 01:34:23 AM EEST 2026
$ python3 astimezone() -> 2026-10-01T01:34:23.685882+03:00
/etc/timezone  -> Africa/Cairo
```

Arithmetic, to the second:

```
collected_utc          2026-09-29T20:02:55Z
+ Africa/Cairo offset  +03:00
= local wall clock     2026-09-29 23:02:55
= db_now_at_collection 2026-09-29 23:02:55   EXACT MATCH
```

`collected_utc` and `db_now_at_collection` record **the same instant**: UTC with a `Z`
suffix, and naive local time. The collector wrote local time into an unlabelled field. That
is a labelling defect, not clock drift and not backdating.

**This is the only pair the timezone offset explains.**

## 3. What is NOT reconciled: the audit-value spread

An earlier revision of this document claimed the full sequence was consistent. **That claim
was wrong and is withdrawn.** The Architect's second attempt correctly rejected it:

> *"A hypothetical +03:00 offset does not explain audit values occurring after collection and
> envelope assembly."*

Normalising the unlabelled `2026-09-30 01:31–01:32` audit values by the same +03:00 offset
gives `2026-09-29T22:31–22:32Z`. That instant is:

| Event | UTC | Ordering |
|---|---|---|
| `collected_utc` | `2026-09-29T20:02:55Z` | — |
| envelope `STARTED_UTC` | `2026-09-29T21:08:13Z` | +1h05m after collection |
| audit values (normalised) | `2026-09-29T22:31–22:32Z` | +1h23m after envelope start |

The ordering is monotonic, so nothing implies backdating. But **monotonic ordering is not
reconciliation.** Two things remain genuinely unexplained:

1. **The +3h offset is inferred, not attested.** It is derived from the host's *current*
   timezone. No collector record states the timezone in force at collection time, so the
   inference rests on the assumption that the host did not change offset between collection
   and now. That assumption is unverified.
2. **No collector or clock provenance was supplied.** There is no record of which clock wrote
   `db_now_at_collection`, nor of the collector's own timezone configuration. The architect
   plan requires exactly this: *"Require collector provenance and explicit timezone/clock
   interpretation. Do not infer validity from unlabeled timestamps."* Interpretation from the
   host's present-day offset is inference, and is therefore insufficient on the plan's own
   terms.

## 4. Correction required, and its limit

The honest fix is to **label the field**, not to change its value:

- `db_now_at_collection` should carry an explicit offset or `Z` designator.
- **No historical timestamp has been edited, and none should be.** `freshness_evidence.json`
  is a frozen candidate file; WDC-R4 requires the frozen envelopes be preserved as historical
  evidence, and the architect plan forbids inferring validity from unlabelled timestamps *or*
  editing historical timestamps to remove a discrepancy.

**This document does NOT supply the collector provenance the plan requires.** It supplies a
timezone *interpretation* derived from the host's current offset, which the plan explicitly
disallows as a basis for validity. It does not retro-correct the artefact, and it does not
satisfy WDC-R4.

## 5. Residual

| Item | Status |
|---|---|
| Is the `collected_utc` → `db_now_at_collection` delta explained? | **Yes**, exactly, by `Africa/Cairo` EEST +03:00 |
| Is the **full** sequence reconciled, including the audit values? | **No.** Offset is inferred from the host's present-day timezone; no collector or clock provenance was supplied |
| Was any timestamp altered? | **No** |
| Is `db_now_at_collection` now labelled? | **No** — schema defect persists in the candidate |
| Does this close WDC-R4? | **No.** WDC-R4 requires additive authenticated collector/clock reconciliation covering the complete sequence. That evidence does not exist and has not been manufactured here. |

## 6. What would actually close it

Additive, without rewriting any historical byte:

1. A collector record stating the timezone in force at collection time, obtained from the
   collector's own configuration rather than inferred from the host now.
2. An explicit offset designator on `db_now_at_collection`, applied prospectively.
3. A clock-provenance statement covering the envelope and audit writers, so each timestamp's
   clock and zone are attested rather than assumed.

Until those exist, WDC-R4 remains open and the Architect is entitled to block on it.
