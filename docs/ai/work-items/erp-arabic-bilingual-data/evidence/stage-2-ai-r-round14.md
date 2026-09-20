# Stage 2 Round 14 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 14 verifier |
| Session | `/root/stage2_ai_r_round14` |
| Verified at | 2026-09-05 (UTC) |
| Candidate | `feature/erp-arabic-bilingual-data`; `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, disposable temporary fixtures, and this report only. No implementation, catalog, payload, database/runtime translation, governed evidence, Git index/history, commit, push, or deployment change. |

The canonical plan v4, handoff, implementation record, Round 13 report,
checker, permanent tests, CI, vendor controls, bootstrap narrative, all ten
envelopes, and the governed index were read.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `d2b0b2132706c4049c857abed08155c6c2135826e8641e645ce978b2a164454a` |
| Round 13 AI-R report | `26aa21c6501c27723aa2270f61ccdeb678d71f3ee79bd71b94d402aa18de46b3` |
| Checker / permanent tests / CI | `581f63b0e962e6ada937474af43a4d3ee455727f179d220923e42cdf674d06b4` / `e165cd8214d8c520b4adebba0549e481cffd5104d082fc87cae72fc3cc667b81` / `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Localization / inventory / freshness | `2f75f8bbe85741a7a8ca743c4267b55848be4c0e2ea46f0518606cf18dae4d2e` / `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` / `09c1d9c614ae830c82db3e8812fbe9f1150f42af95c11e072651468b5023c79c` |
| Vendor coverage / decisions / payload | `b23d31aafb7c341b422dfaf8c72cc36a496afc061b7bf97ca4cbc6d996f7591b` / `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Construction / Frappe / ERPNext PO | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` / `2dfe0a5d07b091d1d34563fa53aac9f4665519aa9672303b4cd6fe3b2d705275` |
| Inventory SQL / governed index | `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` / `cd32c341396470f3d65578ab1afdad074b233fb2ab2bf0929e38ecb29156771a` |

## Fresh healthy results

- Standalone localization adversarial suite: **87/87 passed**.
- Fresh Redis-backed Bench aggregate: **13 + 6 + 5 + 3 + 8 + 87 = 122**, all passed.
- Ordinary full gate exited `0`: catalog `771`; source files `248`; wrapped
  `631`; JSON labels `21`; extraction missing `0`; errors `0`.
- Scoped gate, vendor audit, scope metadata lint, translation-write lint, and
  `git diff --check` all exited `0`.
- Fresh dry-run returned total `34`, created `0`, updated `0`, skipped `34`,
  drift `0`.
- Frappe and ERPNext Arabic POs are Git-clean and have the hashes above.
- A fresh DB query through the canonical serializer reproduced **18,412** rows
  and Merkle `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`.
- The vendor distinct-commit fixture passed in both standalone and Bench runs
  and exercises isolated hashes, output/temp ownership, and live-checkout byte
  identity. Isolated decision-provenance tests also passed.

## Governed ten-envelope hashes

| Envelope | SHA-256 |
|---|---|
| `all-tests.txt` | `d4c33a11f0cca0c3da51f6ffb78997710dd0cb04368e4985501e78f2ded930d0` |
| `final-dryrun.txt` | `bca9acefdd33d1eb611122d9c3afe9059fb26a52a3c0784f15d7cbb9aae5896a` |
| `freshness-envelope.txt` | `f05757f6326b5743598375854f4c6654b06509b4efe0dac39081b613d32dcf5b` |
| `full-gate.txt` | `c3634974b2a3f1c692c68ba70e2923ea4363c080e586c87408fdf1923ffe0e3e` |
| `gate-tests-standalone.txt` | `b6d03f5a5ef2236d19c978a51a5bab5584f1d49b679d13a1daee25da5ea30943` |
| `lints-diffcheck.txt` | `aa31317777e36cc8141d744a8998564ac59b2a48a55a7ebc96ca6085717c0621` |
| `merkle.txt` | `9e0fc31e91b0ab662c27b7ebf7d17fa3d91302b698f71948ec1ac633ed83d2e1` |
| `scoped-gate.txt` | `a0d55a04b71df44bb20ffb671f8379d132acd3b9dae809b848241f17b041378d` |
| `sync.txt` | `50deaa83d92a5f55fef4ec96494250f34f713e1388c9fabbbfa236f9ba8bee99` |
| `vendor-audit.txt` | `f59c8bfb497906ea7684b9769155b2cf0a7b9d92854791b7a4431bdc11df36fe` |

All ten file hashes agree with the ten index hash rows. The candidate-head row
agrees with live HEAD. The governed `full-gate.txt` is an exit-zero
`--skip-evidence` run and CI calls the ordinary checker without that option.

## Round 14 closure assessment

| Requirement | Result | Independent evidence |
|---|---|---|
| Exact envelope command, marker, exit, basic length, per-file hash, test arithmetic, and full-gate headline counts | **CONDITIONALLY VERIFIED** | Permanent tests and fresh probes reject the covered wrong command, nonzero exit, missing marker, wrong length, wrong module totals, and changed full-gate headline counts. Ten index file hashes agree. |
| Exact index grammar and unique metadata | **BLOCKED (P0)** | The parser explicitly accepts arbitrary `COMMAND`, UTC, exit, length, `ARTIFACTS`, and any `*_SHA256` metadata lines without validating their exact identity, cardinality, order, or value. A coherently reindexed fixture with a second `CANDIDATE_HEAD` was accepted. The parser takes the last head and does not require exactly one. There is no candidate-root binding at all, and failure to resolve Git HEAD causes head validation to be skipped. |
| Artifact and cross-envelope bindings | **BLOCKED (P0)** | Coherently rehashed/reindexed fixtures were accepted after replacing the payload hash in dry-run and freshness with zeros; replacing all governed index checker/test artifact hashes; and replacing Merkle rows/root/manifest. Most index artifact rows are never parsed or compared with live files. `full-gate.txt` currently records `CHECKER_SHA256=35b9c294...`, while the live checker and governed index record `581f63b0...`; the ordinary gate still passes this real inconsistency. |
| Per-envelope semantic schemas | **BLOCKED (P0)** | Coherently rehashed fixtures were accepted with scoped `missing=999/errors=999`, vendor `errors=999`, all lint/diff success text replaced by “not run”, sync `updated=999`, freshness `packaged_rows=999` and a false site, and an added `ERROR: forged failure`. Only a subset of four envelopes has partial semantics. Failure rejection covers four narrow spellings, not general error/failure results. |
| UTC, ordering, freshness, and scope | **BLOCKED (P0)** | Per-envelope timestamp syntax and start-before-finish are checked, but evidence age, cross-envelope order, embedded-result time, and candidate scope are not. Moving every envelope timestamp coherently to 2020 was accepted. The governed freshness envelope itself finishes at `10:11:10Z` while its embedded artifact says `collected_utc=10:29:03Z`; this impossible ordering passes. |
| Permanent regression coverage | **BLOCKED (P0)** | The 87-test suite covers Round 13's headline examples only. It has no rejection tests for live artifact hash mismatch, cross-envelope mismatch, false freshness/scoped/vendor/lint/sync semantics, wrong Merkle values/rows, stale/cross-envelope UTC, duplicate candidate metadata, missing Git identity, or candidate-root binding. Its “valid set” uses synthetic arbitrary artifact hashes and a non-repository root, codifying the absence of these bindings. |
| Two-phase bootstrap and CI | **CONDITIONALLY VERIFIED** | The documented sequence resolves the literal self-reference and CI does not pass `--skip-evidence`. However, `--skip-evidence` remains an unrestricted CLI option and the subsequent ordinary run validates a semantically fail-open index/envelope set, so the process is deterministic only at the byte-hash layer and is not release-proof. |
| Implementation/runtime health and vendor isolation | **VERIFIED** | Fresh 87 standalone, complete 122 Bench aggregate, full/scoped/vendor/lints/diff, zero-drift dry-run, clean vendor POs, isolated vendor tests, and independently reproduced Merkle are green. |

## Integrity boundary

Before review, the tracked unstaged binary-diff SHA-256 was
`8c8c3b8170276c1238ea75854c21d81d2fb0b88316bb8461979c86d47e75632f`;
the staged diff was empty
(`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
All mutations were confined to automatically deleted temporary directories.
After all checks and report creation, both diff hashes remained exactly the
same; `git diff --check` remained clean. This report is the only repository file
created by this verifier.

## Decision

**BLOCKED — Stage 2 Round 14 is not independently verified. Stage 3 remains closed.**

The implementation/runtime gates are healthy, but the claimed strict evidence
contract is not implemented. Coherent false evidence remains accepted, and the
current governed full-gate checker hash already disagrees with the actual
candidate while the ordinary gate reports success.

## Exact next gate and residual risks

1. Give `index.txt` one exact, versioned grammar and validate every line,
   cardinality, order, value, candidate root, and exactly one full 40-hex HEAD;
   fail closed when Git identity cannot be resolved.
2. Recompute every index/envelope artifact SHA and length from the candidate,
   including checker, tests, PO, payload, manifests, baseline, decisions, SQL,
   vendor POs, lint scripts, and freshness artifact. Require agreement wherever
   the same artifact appears across envelopes.
3. Define and parse exact successful schemas for all ten envelopes: scoped,
   vendor, both lints and diff, freshness, sync, Merkle rows/root/manifest,
   dry-run payload/runtime, tests, and full gate. Reject general error/failure
   results and decoy/duplicate result markers.
4. Enforce evidence recency, global generation order, embedded collection time
   inside its envelope, candidate revision/root scope, and bootstrap-to-ordinary
   validation ordering.
5. Add permanent isolated tests for every accepted forgery above, regenerate
   all ten envelopes/index through the two-phase procedure, run an ordinary
   full gate, and request a fresh independent AI-R rerun. Owner authorization
   remains separately required for commit, push, merge, deployment, or any
   production mutation.
