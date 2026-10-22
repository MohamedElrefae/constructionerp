# Stage 2 Round 15 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 15 verifier |
| Session | `/root/stage2_ai_r_round15` |
| Verified at | 2026-09-05 (UTC) |
| Candidate | `feature/erp-arabic-bilingual-data`; `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, disposable temporary fixtures, and this report only. No implementation, catalog, payload, database/runtime translation, governed evidence, Git index/history, commit, push, or deployment change. |

The canonical plan v4, handoff, implementation record, Round 14 report,
checker, permanent tests, CI, bootstrap documentation, all ten governed
envelopes, index, and referenced candidate artifacts were read.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `55d16d2e17f030203d3dccce8113a8ea98bb0b71dd072d23ed162a87792730fb` |
| Round 14 AI-R report | `80bd0f9ac5037606ccf46139e1695d9153362ff1112bfabde965cca301c54467` |
| Checker / permanent tests / CI | `894e811ae54afc165fc1d1f91741be8aefdc664d9cc5212f80b570f13b91402a` / `daf572cace6798e9c5332126e3a0e1f216dc28881c87e1c634932ecfaf505c44` / `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Construction PO / payload | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Localization manifest / vendor baseline / decisions | `2f75f8bbe85741a7a8ca743c4267b55848be4c0e2ea46f0518606cf18dae4d2e` / `4e8a7152eb5af053b3d654796d1c8792d95fd96161ce9b6bc696320928773b2a` / `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` |
| Inventory manifest / freshness / inventory SQL | `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` / `09c1d9c614ae830c82db3e8812fbe9f1150f42af95c11e072651468b5023c79c` / `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` |
| Frappe / ERPNext Arabic PO | `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` / `2dfe0a5d07b091d1d34563fa53aac9f4665519aa9672303b4cd6fe3b2d705275` |
| Governed index | `d202f094bdd2ab46a0aef646b1f41e45278a8b93d98f0c25e739f25e6f53578d` |

## Fresh healthy results

- Standalone localization suite: **87/87 passed**.
- Fresh Redis-backed Bench aggregate: **13 + 6 + 5 + 3 + 8 + 87 = 122**, all passed.
- Ordinary full gate exited `0`: catalog `771`; source files `248`; wrapped
  `631`; JSON labels `21`; extraction missing `0`; raw missing `0`; errors `0`.
- Scoped gate, vendor audit, scope metadata lint, translation-write lint, and
  `git diff --check` all exited `0`.
- Fresh dry-run returned total `34`, created `0`, updated `0`, skipped `34`,
  drift `0`.
- Frappe and ERPNext Arabic POs are Git-clean and have the hashes above.
- A fresh DB query through `construction.localization_inventory.merkle_root`
  reproduced **18,412** rows and
  `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`.

## Governed ten-envelope hashes

| Envelope | SHA-256 |
|---|---|
| `all-tests.txt` | `7e0a2e6d4546a2d3194715288bdf888a0f1741e3870ea7cdb461e87b2b44ed03` |
| `final-dryrun.txt` | `bca9acefdd33d1eb611122d9c3afe9059fb26a52a3c0784f15d7cbb9aae5896a` |
| `freshness-envelope.txt` | `f05757f6326b5743598375854f4c6654b06509b4efe0dac39081b613d32dcf5b` |
| `full-gate.txt` | `5537eee7aef9817d117f63d0b0498eef3399a42eceac644be20fd808a294d4a7` |
| `gate-tests-standalone.txt` | `b6d03f5a5ef2236d19c978a51a5bab5584f1d49b679d13a1daee25da5ea30943` |
| `lints-diffcheck.txt` | `aa31317777e36cc8141d744a8998564ac59b2a48a55a7ebc96ca6085717c0621` |
| `merkle.txt` | `2e175307b5eeb03363dddb6a60cf3134bb7b461c120273d1aa36f0bfb502fecd` |
| `scoped-gate.txt` | `a0d55a04b71df44bb20ffb671f8379d132acd3b9dae809b848241f17b041378d` |
| `sync.txt` | `50deaa83d92a5f55fef4ec96494250f34f713e1388c9fabbbfa236f9ba8bee99` |
| `vendor-audit.txt` | `f59c8bfb497906ea7684b9769155b2cf0a7b9d92854791b7a4431bdc11df36fe` |

All ten byte hashes agree with the ten index hash rows. That agreement is not
sufficient: the ordinary gate accepts the semantic and candidate-binding
failures below.

## Round 15 closure assessment

| Requirement | Result | Independent evidence |
|---|---|---|
| Exact versioned index grammar, cardinality, and order | **BLOCKED (P0)** | The parser does not define or enforce a version row or an exact ordered 25-line grammar. It merely harvests ten hash rows, ignores any recognized metadata-shaped rows, and skips every `CANDIDATE_HEAD` while parsing. The permanent synthetic “valid set” contains only ten hashes plus HEAD and passes. A coherently reindexed fixture with two HEAD rows also passed. |
| Candidate identity and candidate-root binding | **BLOCKED (P0)** | Live HEAD equality is checked and an unresolvable Git HEAD fails closed, but exactly-one HEAD is not enforced. No candidate-root marker exists in the index or validator, so wrong/missing root evidence cannot be rejected as a grammar or value error. The last duplicate HEAD wins. |
| Artifact recomputation everywhere and cross-envelope agreement | **BLOCKED (P0)** | Artifact rows in `index.txt` are never parsed as authoritative bindings; recomputation scans envelopes only and silently accepts a required marker that is absent. Temporary coherent fixtures accepted byte changes to the localization manifest, tests, payload when its recognized marker was absent, and vendor baseline, and accepted removal of the checker marker. Decisions, freshness artifact, inventory SQL, vendor POs, and lint scripts have no enforced candidate binding. The real `gate-tests-standalone.txt` records stale `TESTFILE_SHA256=e165cd82…` while the live test file is `daf572ca…`; the ordinary gate exits 0 because the validator looks only for `TESTS_SHA256`. |
| Manifest-marker collision fix | **CONDITIONALLY VERIFIED** | Anchored matching now distinguishes `MANIFEST_SHA256` from `INVENTORY_MANIFEST_SHA256`; changing the inventory manifest was rejected against the latter. However, `MANIFEST_SHA256` appears only in the ignored index metadata and not in an envelope, and absence is accepted. A localization-manifest byte change therefore passed. The collision is fixed syntactically but the intended artifact binding is still absent. |
| Exact successful semantic schemas and arithmetic for all ten envelopes | **BLOCKED (P0)** | Exact module identities/arithmetic, headline full-gate counts, and dry-run totals receive partial checks. There is no success schema for standalone tests, scoped gate, vendor audit, lint/diff, or freshness. Sync checks only the substring `'created': 0`; updated/dry-run/apps are unvalidated. Merkle rows are not compared with the manifest and SQL is unbound. A coherent fixture containing arbitrary false results in scoped/vendor/lint/freshness envelopes passed. Extra decoy result text is generally allowed. |
| Failure-text rejection | **BLOCKED (P0)** | Rejection is a five-spelling prefix/sub-string heuristic, not a parsed success contract. A coherently rehashed envelope containing lowercase `error: forged hidden` passed. Many noncanonical error/failure spellings and false result fields remain invisible. |
| UTC, embedded times, recency, and generation order | **BLOCKED (P0)** | Per-envelope syntax, local start-before-finish, future, and older-than-30-days checks exist. There is no exact global envelope/bootstrap/index order and no embedded-time validation. The governed freshness envelope finishes at `10:11:10Z` but embeds `collected_utc=10:29:03Z`; that impossible sequence is accepted. Database audit times later than the envelope are also accepted. |
| Bootstrap/ordinary order and CI bypass resistance | **CONDITIONALLY VERIFIED** | The documented two-phase narrative and current timestamps place the skip-evidence bootstrap before the governed index, and CI calls the ordinary checker without `--skip-evidence`. The validator does not enforce that order, and `--skip-evidence` remains an unrestricted public CLI bypass. More importantly, the ordinary CI command currently accepts the real stale test hash and incomplete contract. |
| Permanent adversarial coverage | **BLOCKED (P0)** | The suite is still 87 tests and its evidence section has the Round-13-era cases only. It lacks rejection coverage for exact/versioned index shape and order, duplicate HEAD, candidate root, marker absence, the real `TESTFILE`/`TESTS` mismatch, each governed candidate artifact, all missing semantic schemas, embedded/global time order, lowercase/general failures, and Merkle rows/SQL. Its minimal synthetic “valid set” positively codifies several omissions. |
| Implementation/runtime health and vendor isolation | **VERIFIED** | Fresh standalone and Bench tests, full/scoped/vendor/lints/diff, zero-drift dry-run, clean vendor POs, and independently reproduced Merkle are green. The distinct-root vendor and isolated decision fixtures pass within the 87-test suite. |

## Integrity boundary

Before creating this report, the tracked unstaged binary-diff SHA-256 was
`8c8c3b8170276c1238ea75854c21d81d2fb0b88316bb8461979c86d47e75632f`;
the staged diff was empty
(`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
All adversarial mutations were confined to automatically deleted temporary
directories. This report is the only repository file created by this verifier.

## Decision

**BLOCKED — Stage 2 Round 15 is not independently verified. Stage 3 remains closed.**

The implementation/runtime gates remain healthy, and the narrow
manifest-marker collision is corrected. The asserted exact evidence contract
is not implemented: a real stale test artifact hash passes today, candidate
root and unique identity are not bound, multiple candidate artifacts are
unbound, five envelopes have no successful semantic schema, and impossible
embedded timing is accepted.

## Exact next gate and residual risks

1. Replace the permissive index scanner with one exact versioned line schema,
   including a canonical candidate-root identity, exactly one 40-hex HEAD,
   exact metadata cardinality/order, and all required artifact rows. Reject
   missing or duplicate rows and fail closed on root/Git resolution.
2. Recompute every required candidate artifact from that root, require every
   marker exactly once under one canonical name, and compare it wherever it
   appears. Include checker, tests, Construction/vendor POs, payload,
   localization and inventory manifests, vendor baseline, decisions, freshness,
   inventory SQL, and both lint scripts.
3. Implement exact ordered successful schemas for all ten envelopes, including
   standalone/scoped/vendor/lint/freshness/sync, Merkle rows/root/SQL, and reject
   any extra or duplicate result/failure material rather than using a spelling
   blacklist.
4. Enforce candidate-root/HEAD scope, per-envelope and embedded UTC consistency,
   global generation order, bootstrap-before-index, and an ordinary validated
   run after index generation.
5. Add permanent isolated tests for every Round-14 residual and every bypass
   above; regenerate the ten envelopes/index; demonstrate the real standalone
   test hash equals the candidate; run the ordinary CI-equivalent gate; then
   request a fresh AI-R rerun. Owner authorization remains separately required
   for commit, push, merge, deployment, or production mutation.
