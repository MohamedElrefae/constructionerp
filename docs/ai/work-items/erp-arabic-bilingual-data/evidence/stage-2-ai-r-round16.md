# Stage 2 Round 16 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 16 verifier |
| Session | `/root/stage2_ai_r_round16` |
| Verified at | 2026-09-05T19:19:17Z |
| Candidate | `feature/erp-arabic-bilingual-data`; `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, automatically deleted temporary fixtures, and this report only. No implementation, catalog, payload, database/runtime translation, governed evidence, Git index/history, commit, push, or deployment change. |

The repository `AGENTS.md`, canonical plan v4, build handoff,
`IMPLEMENTATION.md`, Round 15 report, Round 16 remediation record, checker,
permanent tests, CI workflow, bootstrap description, all ten governed envelopes,
the governed index, and every referenced candidate artifact were read.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `5793607aa52eb5e1b57a75021d83812435ab39bce37c644b912ccfc063bad796` |
| Round 15 AI-R report | `e3cf4886382163e9289f224b402580df76e4298ea69c30327df7817926d39be3` |
| Round 16 remediation record | `58a9be75cb422edfba64312050e6f7ab878e235b280ba1c31a487f75ab160cef` |
| Checker / permanent tests / CI | `374fda237f074561cc1980b77f5ae0532d298d606d0d09230784afd920d8bf95` / `81cb6045561ace42741d893a1fdc25a7cf4cbf905f7619bf0ae365247140779d` / `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Construction PO / payload | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Localization manifest / vendor baseline / decisions | `2f75f8bbe85741a7a8ca743c4267b55848be4c0e2ea46f0518606cf18dae4d2e` / `4e8a7152eb5af053b3d654796d1c8792d95fd96161ce9b6bc696320928773b2a` / `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` |
| Inventory manifest / freshness / inventory SQL | `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` / `09c1d9c614ae830c82db3e8812fbe9f1150f42af95c11e072651468b5023c79c` / `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` |
| Scope lint / translation-write lint | `8436fed02c0dc5bc0c9f1f3abcf716cdbcbad68e28eb0db575535ad3e0e068c9` / `bcf1d242fcb7417a391f42f4ecd3a8edbc7b96c81c760704b8071e7b19b1b738` |
| Frappe / ERPNext Arabic PO | `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` / `2dfe0a5d07b091d1d34563fa53aac9f4665519aa9672303b4cd6fe3b2d705275` |
| Governed index | `1e06539a982009c9c630f58db690721358f4cfae559c957c3dfe688dac5d2c21` |

## Fresh health results

- Standalone localization suite: **87/87 passed**. It emitted one existing
  `ResourceWarning` for an unclosed fixture index handle; this did not fail the
  suite.
- Fresh Redis-backed Bench aggregate: **13 + 6 + 5 + 3 + 8 + 87 = 122**, all
  passed.
- Ordinary full gate exited `0`: catalog `771`; source files `248`; wrapped
  `631`; JSON labels `21`; extraction missing `0`; raw missing `0`; errors `0`.
- Scoped gate and vendor audit exited `0`; scope metadata lint,
  translation-write lint, and `git diff --check` passed.
- The governed dry-run records total `34`, created `0`, updated `0`, skipped
  `34`, drift `0`. It was not rerun because this review forbids runtime writes;
  all fresh read-only gates agree with its candidate hashes.
- Frappe and ERPNext Arabic POs are Git-clean and have the hashes above.
- A fresh read-only DB query passed through
  `construction.localization_inventory.merkle_root` reproduced **18,412** rows
  and `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`.

## Governed ten-envelope hashes

| Envelope | SHA-256 |
|---|---|
| `all-tests.txt` | `b1e82bd2603fc61de60fb1158ea97d061ee3901520bfd7166673931ca7502406` |
| `final-dryrun.txt` | `231b4b58b664c15c90540483468af8b0d21ee4e1068cc1cb6aa2674643ef30ba` |
| `freshness-envelope.txt` | `7019b63524b4e9c5d804668dc1cb155cd98375fd3090e2545e495d07d7c21366` |
| `full-gate.txt` | `7c9147dfbad4a29af0788f4b3667fcb5fffc82d13a51da0e307afc6cbc86af64` |
| `gate-tests-standalone.txt` | `587f0c4e278adbbfe08043c4219ba853dd2b8f63762df21bd8de28dbcf38a96f` |
| `lints-diffcheck.txt` | `4556cd44aaabf6833774cff0a50648c4c30040e2a0c6e82f92f252d49a37ce0b` |
| `merkle.txt` | `26c53fa6750be423c56febbb8e640ae35c0e20fce742c0dac6d66db65ca110a2` |
| `scoped-gate.txt` | `facfd804ca37fa15e57f6ad1cb2be9d6ae0651f1dc870a23f2aa74c26867b121` |
| `sync.txt` | `ee03bcdf9466e862fa47ca8745cf470faa7462fbfacd35bc8fde1c60c5c3a3c5` |
| `vendor-audit.txt` | `2f0f633deedb93d016c97413f15d9d219e8f47e35c58c02c060f5609422049e0` |

All ten byte hashes agree with their index hash rows. All 14 artifact values in
the live index happen to agree with the candidate. Those agreements do not make
the evidence contract fail closed.

## Round 16 closure assessment

| Requirement | Result | Independent evidence |
|---|---|---|
| Exact versioned index grammar/cardinality/order | **BLOCKED (P0)** | Version line and ten filename rows receive partial checks, but there is no exact full-line sequence. Recognized metadata and artifact rows may be omitted, reordered, duplicated, or added arbitrarily. `COMMAND` is read but never compared, index `ENVELOPE_LINES` is never validated, and the governed index itself has **32 nonempty lines while declaring 31**; the ordinary gate accepts it. The permanent positive fixture intentionally omits the governed artifact section and index length marker yet passes. |
| Canonical candidate root and HEAD | **BLOCKED (P0)** | Exactly one full HEAD is required, resolved at the supplied invocation root, and the governed HEAD is correct. Wrong/missing/duplicate HEAD values reject. But no `CANDIDATE_ROOT` is required, parsed, compared, or resolved. The governed index contains no root. A coherent fixture without a root passed, and adding `CANDIDATE_ROOT: /forged/apps/construction` also passed. Invocation-path suffix checking is not evidence binding. |
| Fourteen artifact markers, collision safety, and consistency everywhere | **BLOCKED (P0)** | Anchored marker names avoid the manifest collision, and each canonical marker must occur at least once across envelopes with the candidate byte hash. However, index artifact values are wholly ignored; an arbitrary forged `CHECKER_SHA256` index row passed. Exact-once is not enforced: a duplicate envelope artifact marker passed. The standalone envelope still uses the noncanonical unchecked alias `TESTFILE_SHA256`, while the canonical `TESTS_SHA256` binding is borrowed from the aggregate envelope. Therefore “everywhere they appear,” canonical naming, cardinality, and index agreement are false. |
| Exact successful schemas for all ten envelopes | **BLOCKED (P0)** | Checks are substring/first-match predicates, not exact ordered schemas. Fully rehashed/reindexed fixtures passed added false result records in scoped, vendor, lint, freshness, and standalone envelopes; a forged sync application/dry-run result; and duplicate false Merkle root/row records. Existing good substrings act as decoys. Marker uniqueness and result exclusivity are not enforced. |
| General failure rejection | **BLOCKED (P0)** | The spelling blacklist is not a semantic success grammar. A rehashed/reindexed `fatal: forged hidden failure` passed, as did `RESULT success=false`. Many lowercase/general failure forms remain accepted. |
| UTC, embedded time, global order, and recency | **BLOCKED (P0)** | Envelope boundary timestamps receive strict parse, local order, future, and 30-day checks. Embedded times are not validated. The governed freshness envelope says it finished at `10:11:10Z`, but its embedded artifact says `collected_utc=10:29:03Z`; embedded audit values are later still (`14:55:42` and `15:59:03`). This impossible evidence is accepted. A fixture with embedded year 2099 passed. Global order enforces only “within one day” plus index-after-latest-envelope, not an exact generation/bootstrap/ordinary-validation sequence. |
| Bootstrap determinism and CI bypass resistance | **CONDITIONALLY VERIFIED** | Documentation describes a two-phase `--skip-evidence` bootstrap, the governed bootstrap envelope precedes the index, and CI invokes the ordinary checker without the flag. The checker does not authenticate the index command, does not require the root, does not enforce a final governed ordinary-validation record, and accepts the defects above. The permanent “valid” fixture is materially weaker than the claimed governed grammar. |
| Permanent adversarial coverage | **BLOCKED (P0)** | The count remains 87. The added Round 16 behavior is not backed by new tests for root identity, exact index layout/order/cardinality, index artifact agreement, exact-once artifact/result markers, canonical alias rejection, each envelope's exact schema, embedded/global time sequence, or general failure forms. Existing mutations are generally not coherently reindexed; the positive fixture codifies omitted root/artifact/index-length fields. |
| Implementation/runtime health and vendor isolation | **VERIFIED** | Fresh standalone/Bench tests, full/scoped/vendor/lint/diff gates, clean vendor POs, and independent Merkle reproduction are green. No implementation regression was found. |

## Coherent forgery results

Each accepted case below was constructed under an automatically deleted
`.../bench/apps/construction` Git candidate, then the changed envelope's SHA,
declared length, and index row were regenerated before validation where
applicable:

- no candidate-root row: **accepted**;
- forged candidate-root row: **accepted**;
- arbitrary forged index artifact row: **accepted**;
- duplicate canonical artifact marker: **accepted**;
- false scoped, vendor, lint, freshness, standalone-test, and sync result
  material with good decoy markers retained: **accepted**;
- lowercase hidden `fatal` failure: **accepted**;
- duplicate false Merkle root and row-count result: **accepted**;
- impossible embedded future collection time: **accepted**.

These are coherent variants of the Round 15 residuals, not mere byte tampering.
The existing validator did reject its narrow covered cases such as an incorrect
or duplicate HEAD, missing all occurrences of a canonical artifact marker, and
direct changes to the first expected numeric result.

## Integrity boundary

Before this report, the tracked unstaged binary-diff SHA-256 was
`8c8c3b8170276c1238ea75854c21d81d2fb0b88316bb8461979c86d47e75632f`;
the staged diff was empty
(`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
All adversarial candidates were confined to automatically deleted temporary
directories. This report is the only repository file created by this verifier.

## Decision

**BLOCKED — Stage 2 Round 16 is not independently verified. Stage 3 remains closed.**

The implementation/runtime gates are healthy, but the claimed Round 16
evidence contract is not present. The current governed index itself proves the
gap: it omits candidate root, misstates its length, and nevertheless validates.
Coherent false evidence and duplicate results continue to authorize the
candidate.

## Exact next gate and residual risks

1. Define one literal ordered index schema and enforce every row and value:
   version, authenticated command, times, ten ordered envelope hashes, exit,
   exactly one canonical resolved candidate root, exactly one HEAD, artifact
   section with exactly 14 ordered unique markers, and correct index length.
2. Resolve Git and every artifact from the canonical root recorded in the
   index. Recompute and compare all 14 index values and every envelope
   occurrence; require a prescribed exact-once occurrence map and reject aliases
   such as `TESTFILE_SHA256`.
3. Replace substring/blacklist validation with exact ordered parsers for each
   of the ten successful outputs. Require unique result records and reject all
   extra/duplicate/decoy/failure material. Fully validate sync apps/dry-run,
   scoped counts, vendor cleanliness, lint results, freshness JSON, standalone
   result, and Merkle/SQL/result uniqueness.
4. Parse embedded UTC/DB timestamps, enforce their relationship to envelope
   bounds, and enforce the explicit global generation, bootstrap, index, and
   ordinary-validation sequence. Regenerate the currently impossible freshness
   envelope and the malformed-length index.
5. Add permanent coherent-rehash/reindex tests for every accepted case above,
   including missing/wrong/unresolvable/duplicate root and HEAD combinations;
   regenerate all ten envelopes and index; run the ordinary CI-equivalent gate;
   then request a fresh AI-R rerun. Owner authorization remains separately
   required for commit, push, merge, deployment, or production mutation.
