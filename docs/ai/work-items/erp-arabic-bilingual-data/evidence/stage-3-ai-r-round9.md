# Stage 3 — Independent AI-R Round 9 Verification

**Verdict: BLOCKED. Stage 4 must not begin.**

I reviewed the current candidate (not prior reports), including `AGENTS.md`,
the current service/dropdown code and permanent tests, the Round-8 report and
Round-9 pilot/tracker material, governed Stage-2/localization evidence, HTTP
and browser evidence, and the preserved performance artifact. No
implementation, catalog, payload, business-data, runtime Translation, Git
index/history, or existing evidence file was changed. The only file written
is this report. The live pilot test was run read-only and passed **52/52**.

## Round-8 closure checks

The two public paths now lower/upper clamp integer-like inputs before ORM
pagination or Python slicing:

`min(max(int(page_length or 1), 1), MAX_PAGE_LENGTH)` and
`max(int(start or 0), 0)`, with `MAX_PAGE_LENGTH = 200`. The permanent test
`test_negative_zero_and_oversized_pagination_inputs_are_lower_bounded` drives
negative, zero, and oversized combinations through service and dropdown calls
on real fixture matches; it passed. The probe/refusal/meta contract remains
present, including the genuine 5,000/5,001 test, and the pilot run showed no
regression.

### Blocking findings

**P1 — non-integer input handling is not consistent or permanently tested.**
The required “non-integer inputs consistently” behavior is not established.
The service calls `int(...)` without a local normalization/error contract and
therefore raises `ValueError` for inputs such as `"abc"`; the dropdown wraps
that path in its broad exception handler and returns `[]` (and logs), rather
than exposing the same documented result/error. No permanent test exercises
non-integer `page_length` or `start` on either path. Define one fail-closed,
bounded behavior and test it on both paths, including text and blank queries.

**P1 — min-of-rounds performance provenance is insufficient.** The preserved
`p95-measurement.json` contains one selected 50-sample result per side and
labels its statistic “nearest-rank P95 over the best round (min-of-rounds)”.
It does not preserve all five round results, the round-selection rule inputs,
or per-round P95s, so an independent reviewer cannot establish that the
reported +1.47% selection is not cherry-picked. The artifact is otherwise
internally coherent: current code hashes are service
`d1cab050ed006b3233ed4330368c2cdb1360d1d4c541bef56b8be0018d514279`, registry
`691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538`, and
dropdown `ac84a57fe5bdb877f55d1dc3c4f1610249a9b56db66f9602af5e978893989497`;
the stored selected P95 is baseline **2.173 ms** versus bilingual **2.205 ms**
(1.47%), with 50 samples, equal 12-row match sets, alternating order, GC
paused, and one SQL call per call. Those facts do not cure the missing
five-round provenance.

## Other results

The current pilot suite passed **52/52**. Existing evidence reports standalone
89/89, pure 38/38, aggregate 214 (`13+6+5+3+8+89+38+52`), catalog 804,
extraction `663 + 21` with zero missing, inventory 18,445 with Merkle
`6fcffc90…`, evidence gate `errors=0`, and clean lints/diff-check. These
reported gates were not regenerated or modified during this review. Existing
handler/HTTP cleanup, permissions, ranking, overflow, rename/audit,
registry/normalization/UI/browser, and governed Stage-2 controls remain
represented by the passed suite and supplied evidence.

## Next gate

Add permanent cross-path tests and a documented normalization contract for
non-integer pagination inputs. Re-record the P95 with all five rounds and
preserve every round’s raw samples/results, selection calculation, balanced
ordering, environment/code/DB/user/cardinality identity, and per-call SQL
counts; the canonical gate remains `bilingual_p95 <= baseline_p95 * 1.10`
with no floor. Then request a fresh independent AI-R review. No commit, push,
merge, deploy, or live Account-name migration is authorized by this report.
