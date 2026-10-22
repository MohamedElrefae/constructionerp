# Stage 2 Round 13 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 13 verifier |
| Session | `/root/stage2_ai_r_round13` |
| Verified at | 2026-09-05 (UTC) |
| Candidate | `feature/erp-arabic-bilingual-data`; uncommitted worktree |
| Boundary | Read-only repository/site checks, disposable isolated fixtures, and this report only. No implementation, catalog, payload, governed evidence, Git index/history, or runtime translation value changed. No commit/push/deploy. |

The canonical v4 plan, handoff, implementation record, Round 12 report,
checker, adversarial tests, CI workflow, vendor-delta tool, manifests, bootstrap
documentation, all ten governed envelopes, and the governed index were read.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record (before this report) | `b194c21c43525f8086e5a6b712900bcf4ab6b55078f7ddb29d6d82531c5caf85` |
| Round 12 AI-R report | `aa1a698f3497d93eb6b00afbec59f7e11b4a276283610f0e914e6af7c0c2c909` |
| Checker / adversarial tests | `a22e3efa8e4661b4ce57420647656e287f88b5236ba634e496e16857d169f905` / `62413ccc5fcfbba75d810b2a870d6db76cd1ca22310809e425acab7fec3ec218` |
| Vendor delta / baseline | `ec089e8c51e66c6439e5d811f14554f3f6c12e1786669aed0d9c575386ac21bc` / `4e8a7152eb5af053b3d654796d1c8792d95fd96161ce9b6bc696320928773b2a` |
| Localization / inventory manifests | `2f75f8bbe85741a7a8ca743c4267b55848be4c0e2ea46f0518606cf18dae4d2e` / `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` |
| Freshness / release decisions | `09c1d9c614ae830c82db3e8812fbe9f1150f42af95c11e072651468b5023c79c` / `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` |
| Retired lifecycle / released payload | `cad850c823a169ff338b2b8e78cf17d20626d36efd0e27dbd38e214c2d162706` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Construction / Frappe / ERPNext PO | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` / `2dfe0a5d07b091d1d34563fa53aac9f4665519aa9672303b4cd6fe3b2d705275` |
| Inventory SQL / CI | `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` / `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Governed evidence index | `61861901468a172730d21960630ba02c4d2f3fe9d39959d5b2d2502ec0862607` |

## Independently reproduced healthy results

- Standalone adversarial suite: **79/79 passed**.
- Fresh Redis-backed Bench aggregate: **13 + 6 + 5 + 3 + 8 + 79 = 114**, all passed.
- Fresh full gate exited `0`: catalog `771`; source files `248`; wrapped `631`;
  JSON labels `21`; extraction missing `0`; raw-text missing `0`; errors `0`.
- Positive scoped gate, vendor audit, scope metadata lint, translation-write lint,
  and `git diff --check` exited `0`.
- Governed dry-run evidence records total `34`, created `0`, updated `0`, skipped
  `34`, drift `0`, payload `037e79c…`, runtime digest `ce8e729f…`.
- Frappe and ERPNext Arabic POs are Git-clean and match the hashes above.
- The inventory manifest and governed envelope record `18,412` rows and Merkle
  `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`.
- The permanent vendor fixture now uses distinct commits and asserts delta sets,
  isolated old/new PO hashes, root-owned output/temp behavior, and no live-checkout
  output. Isolated release-decision provenance tests remain fail-closed.

## Ten-envelope recomputation

The current ten files match the ten governed rows exactly:

| Envelope | SHA-256 |
|---|---|
| `all-tests.txt` | `c935455e855c5193d71e64509ac2e698ce643eee24f21b5c03058afc73939ee6` |
| `final-dryrun.txt` | `a44a5152c1b3f131bca95caf4ff62743e4bf41abac9efc3f128dc671757b7be9` |
| `freshness-envelope.txt` | `56ffde8be9674e66a85c2325075d794a6adb168b60c0d408d3119888f7d7830c` |
| `full-gate.txt` | `a2288aeb6fabc4667545da1e6bc3816ab1bc5748bb6f01bb6fa92131c084c9fe` |
| `gate-tests-standalone.txt` | `9adcf45cdd7a752ec87ee3ed3dc2dd4d6f513eb4e08ce0d8fd46ac689a9786be` |
| `lints-diffcheck.txt` | `24bae562cb0d3de587ad2304ad4e59b463ab90c0e20ca892cb15ab74644ea1b9` |
| `merkle.txt` | `5756245df6dc1e9323282cbf62ea7867f11d3226488a5acf22979005e06d5666` |
| `scoped-gate.txt` | `fc67f19be8ea7116612d717ce63f9886fd35259f5c9c9b01d0cf1aaaded49ad7` |
| `sync.txt` | `4f721b2015a14133038c10fc810c15e21be4aabb45809e0165d1f35d9fb3a540` |
| `vendor-audit.txt` | `95f90a0e70afa3a485156f2ed8e17df293cb48a31780bcd528dc29c18f1ed37d` |

The governed `full-gate.txt` is now a real exit-0 `--skip-evidence` bootstrap
run and a subsequent ordinary full gate validates it. This resolves the literal
hash circularity deterministically, but the validator remains semantically
fail-open, so the bootstrap cannot yet be release evidence.

## Round 13 closure assessment

| Requirement | Result | Evidence |
|---|---|---|
| Exact set/hash/basic envelope rejection | **CONDITIONALLY VERIFIED** | Exact ten filenames, duplicate content, missing/extra `.txt`, traversal rows, nonzero exit, duplicate/missing primary markers, UTC parse/order, hash agreement, basic aggregate arithmetic, and Merkle marker presence are covered and pass their permanent tests. |
| Strict semantic evidence validator | **BLOCKED (P0)** | Independent disposable copies were coherently rehashed and reindexed. The validator accepted: `79/114` changed coherently to `999/1034`; full-gate catalog/extraction totals changed to `999/888/77`; dry-run total/skipped changed to `999/1`; a hidden `FAIL forged` line; arbitrary command content; and an unparsed junk index line. No length marker is parsed or required. Expected command identity, expected module counts/total, full-gate result object/counts, dry-run arithmetic, freshness/vendor/lint/scoped result semantics, embedded artifact hashes against live artifacts, exact index grammar, marker ordering, or evidence freshness/cross-envelope agreement is enforced. |
| Permanent adversarial evidence contract | **BLOCKED (P0)** | Seven new tests cover a subset of Round 12 paths, but their synthetic baseline itself uses the prior `71/106` totals and generic envelopes. There are no permanent rejection tests for coherent-but-wrong totals, altered full-gate output, dry-run arithmetic, hidden failure output, arbitrary commands, junk index lines, missing length markers, artifact-hash mismatch, or cross-envelope disagreement. |
| Two-phase bootstrap | **CONDITIONALLY VERIFIED** | The documented sequence produces a real exit-0 bootstrap envelope and the normal verifier passes it; CI does not use `--skip-evidence`. Because `--skip-evidence` is an unrestricted public CLI option and semantic/index/freshness bindings are incomplete, the process does not yet prove that a regenerated set is current, successful, or truthful. |
| Vendor root isolation / isolated decision provenance | **VERIFIED** | Fresh 79-test runs exercised the extended distinct-commit CLI fixture and isolated manifest provenance failures; implementation inspection confirms explicit root flow. |
| Fresh implementation/runtime gates | **VERIFIED** | Fresh standalone 79, complete Redis-backed 114, full/scoped/vendor/lints/diff, live `771 / 631 + 21 / 0`, clean vendor POs, and the governed zero-drift/Merkle results are consistent. |

## Integrity boundary

Before review, the tracked unstaged binary-diff SHA-256 was
`8c8c3b8170276c1238ea75854c21d81d2fb0b88316bb8461979c86d47e75632f`;
the staged diff was empty
(`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
All adversarial mutations were confined to temporary directories. This report
is the only repository file created by this verifier.

## Decision

**BLOCKED — Stage 2 Round 13 is not independently verified. Stage 3 remains closed.**

Round 12's failed governed envelope is fixed, vendor isolation is durably tested,
and the implementation/runtime state is healthy. The remaining release blocker
is that coherent rehashing/reindexing still authorizes materially false evidence.

## Exact next gate and residual risks

1. Parse every line of `index.txt` with an exact grammar; reject any unparsed line.
   Require exact nonempty expected command identity and exact ordered command/start/
   result/hash/length/exit/finish markers for each envelope.
2. Bind semantic expectations: exact six module identities and `13+6+5+3+8+79=114`;
   exact full-gate `771`, `248`, `631`, `21`, missing `0`, errors `0`; dry-run
   `34=0+0+34` and drift `0`; and exact scoped/vendor/lint/freshness/sync/Merkle
   schemas. Reject any failure/error text inconsistent with success.
3. Recompute and compare every embedded artifact SHA/length to the actual candidate;
   enforce cross-envelope equality, evidence recency/order, candidate commit/root,
   inventory rows/root/manifest, payload/runtime digest, and checker/test hashes.
4. Add permanent isolated adversarial tests for every reproduced coherent forgery,
   using the current `79/114` contract, then regenerate all ten envelopes/index via
   the documented bootstrap and rerun an ordinary full gate.
5. Request a fresh independent AI-R rerun. Owner authorization remains separately
   required for commit, push, merge, deployment, or production mutation.
