# Stage 2 Round 11 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 11 verifier |
| Session | `/root/stage2_ai_r_round11` |
| Verified at | 2026-09-05 (UTC) |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, disposable isolated fixtures, and this report only. No implementation, catalog, payload, governed evidence, Git index/history, or runtime translation value was changed. No commit/push/deploy. |

The canonical v4 plan, handoff, implementation record, Round 10 report, current
checker/tests/CI, vendor-delta producer and consumer, freshness/provenance
controls, manifests, all ten evidence envelopes, and governed index were read.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `22e88e9eb6d034b6aed0d9a34eef36fe5c3ceda988c97fdcc27fc02c2d2252b0` |
| Round 10 AI-R report | `f4a90afda2f72a268e50e18d31177a667b5a9c7f749d890b6bb77c015ded6b85` |
| Checker / adversarial tests | `8d7b98d984b58610916256e311f37402cd9c5443eb7e54c53ef0cd711a999a43` / `9ab0dfcb343ebf3d7ba093ed87f77636b3432735098f8b94025206d05db0ddd2` |
| Vendor delta / vendor baseline | `9249674ae2a0ab67a924fa08b5f9bc983bb5f4e1220e35c28d7fe3dd1c50f8be` / `4e8a7152eb5af053b3d654796d1c8792d95fd96161ce9b6bc696320928773b2a` |
| Localization manifest / inventory manifest | `2f75f8bbe85741a7a8ca743c4267b55848be4c0e2ea46f0518606cf18dae4d2e` / `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` |
| Freshness collector / evidence | `6bf96dbdc1664496bf6a4bb6c6f96260598914fb978115962a0d160eb5fbd34d` / `09c1d9c614ae830c82db3e8812fbe9f1150f42af95c11e072651468b5023c79c` |
| Release decisions / retired lifecycle | `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` / `cad850c823a169ff338b2b8e78cf17d20626d36efd0e27dbd38e214c2d162706` |
| Construction PO / released payload | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Frappe / ERPNext vendor PO | `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` / `2dfe0a5d07b091d1d34563fa53aac9f4665519aa9672303b4cd6fe3b2d705275` |
| Inventory SQL / CI workflow | `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` / `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Governed evidence index | `00c932cae1b51ab47e8c662fef9498f020be2e3cc69547c7804842aa0ff82bcb` |

## Independent results

- Standalone adversarial suite: **71/71 passed**.
- Bench paths with Redis available: `13 + 6 + 5 + 3 + 8 + 71 = 106`, all
  passed. The requested/saved label of **105** is arithmetically inconsistent
  with the six recorded module counts; `all-tests.txt` itself says
  `AGGREGATE total=106 failed=0`.
- Full gate: catalog `771`; `248` files; `631` wrapped literals; `21` JSON
  labels; missing `0`; raw-template missing `0`; errors `0`.
- Positive scoped gate, vendor audit, scope metadata lint, translation-write
  lint, and `git diff --check`: all exit `0`.
- Released-payload dry run: total `34`, created `0`, updated `0`, skipped `34`,
  drift `0`.
- Vendor Frappe and ERPNext PO paths are Git-clean and their live hashes match
  the recorded manifest values above.
- Fresh DB query plus the committed serializer reproduced exactly `18,412`
  rows and Merkle
  `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`.

## Ten-envelope recomputation

All current file hashes agree with the governed index:

| Envelope | SHA-256 |
|---|---|
| `all-tests.txt` | `ece0a73883d9a6d56e16938b08e6f06f4766c5168260d87f1876e7b23a953839` |
| `final-dryrun.txt` | `845c44a9871243e52914a83c3dcf2641464be9dda1933593c6174ef1d03593a4` |
| `freshness-envelope.txt` | `56ffde8be9674e66a85c2325075d794a6adb168b60c0d408d3119888f7d7830c` |
| `full-gate.txt` | `f151b562d73530650addaf123719d5ff603a908ba44d99d406f9cb3d52345722` |
| `gate-tests-standalone.txt` | `a2e40c1c3033be2715cb67bcc37cc8ac7624d05da988e4e8c14f861b7eba7d36` |
| `lints-diffcheck.txt` | `32d3f57e0d0c362057ad56bb31c35d23154d33a594953cddaffe904e93bb367c` |
| `merkle.txt` | `9fc1695372c0e6a5c32971441a12d1fb6c60fa45a434b33774662a866afab798` |
| `scoped-gate.txt` | `22d12277e404d5a7f4438bab24b261e76a4affc74b55965032cc75a00f1de7ea` |
| `sync.txt` | `53f5dd361823c743087b474492b78f3e081c881b727f37a504b98e9d42cd2294` |
| `vendor-audit.txt` | `5100a2932937cd910f6b34095074c2affcd5338e2c69a8641fe041159bb6f75f` |

Hash agreement does not make the set valid: the indexed `full-gate.txt`
explicitly records `FAIL evidence-index-missing` and `EXIT_CODE: 1`.

## Round 11 closure assessment

| Requirement | Result | Evidence |
|---|---|---|
| Explicit-root vendor blobs/Git/hashes/output | **PARTIAL** | A true conflicting isolated Git fixture produced one isolated add and remove; both PO hashes matched isolated commit bytes; `--write` stayed under isolated root; protected checkout files were byte-identical. However, both parse files were created as `/tmp/vendor-frappe-...po`, outside the supplied root. |
| Evidence exact set and hash agreement | **PARTIAL** | Missing, extra, duplicate-content, and traversal fixtures were rejected; all ten current hashes agree with the index. |
| Complete/fail-closed evidence envelopes | **NOT CLOSED (P0)** | Isolated fixtures were accepted after: changing `EXIT_CODE: 0` to `1` and refreshing its index hash; replacing an envelope with only five marker/hash lines; appending a duplicate index line; and altering recorded command output while refreshing the index hash. The validator tests presence, not successful exit, unique/exact envelope fields, substantive completeness, unique index entries, or result semantics. The current governed full-gate envelope is direct proof: it failed but validates. No permanent evidence-validator adversarial tests exist in the 71-test file. |
| Provenance remains fail-closed | **NOT CLOSED (P0)** | `check_manifest(root=...)` calls `decisions_sha()` and `decision_root()` without passing `root`. A disposable candidate containing no `release_decisions.json` returned zero errors because the validator silently read the live checkout's decisions. Thus an isolated candidate can borrow live provenance. Vendor-delta forged provenance/set fixtures themselves remain green and fail closed. |
| Fresh standalone/Bench suites | **PASS with count correction** | 71 standalone and 71 Bench adversarial tests passed; the complete six-module Bench aggregate is 106, not 105. |
| Live gates, zero drift, vendor cleanliness, Merkle | **PASS** | Results and exact hashes are recorded above. |

## Integrity boundary

Before verification, the tracked unstaged binary diff SHA-256 was
`8c8c3b8170276c1238ea75854c21d81d2fb0b88316bb8461979c86d47e75632f`;
the staged diff was empty
(`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
After all checks and before adding this report, those values were unchanged.
The checker, tests, vendor tool, manifests, catalogs, payload, decisions,
freshness evidence, inventory, and all pre-existing evidence retained the exact
hashes listed above. Disposable fixtures were confined to system temporary
directories and removed automatically. This report is the only repository file
created by this verifier.

## Decision

**BLOCKED — Stage 2 Round 11 is not independently verified.**

The live localization behavior, inventories, vendor hash sourcing, dry run,
Redis-backed tests, and Merkle are healthy. Release remains blocked because the
governed evidence validator accepts a known failing envelope and several forms
of coherent truncation/tamper, isolated manifest validation can borrow live
decision provenance, and vendor parse temp files remain outside the explicit
root contract.

## Exact next gate and residual risks

1. Thread `root` into `decisions_sha(root=...)` and `decision_root(root=...)`
   inside `check_manifest`; add isolated missing/tampered-decision fixtures that
   cannot see the live checkout.
2. Make the evidence validator require exactly one normalized command, start,
   finish, and `EXIT_CODE: 0` field per envelope; validate time order, exact
   one-to-one index membership, unique index rows, required per-envelope result
   schema, and the aggregate arithmetic. Add permanent isolated tests for
   truncated, altered, missing, extra, duplicate-content, duplicate-index,
   traversal, nonzero-exit, and coherent file+index tamper cases.
3. Regenerate the ten envelopes atomically only after the index exists or use a
   two-phase/self-consistent procedure; the replacement `full-gate.txt` must be
   a real exit-0 run. Record the aggregate as 106 while the suite contains 71
   localization tests (or explicitly explain a deliberately excluded test).
4. Create delta parser temporary files beneath an isolated root-owned temp
   directory and extend the cross-root test to assert actual delta JSON hashes,
   sets, output location, every temp path, and checkout byte identity.
5. Rerun the complete aggregate, all live gates, dry run, inventory/Merkle, ten
   hashes, and governed index, then request a fresh independent AI-R review.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
