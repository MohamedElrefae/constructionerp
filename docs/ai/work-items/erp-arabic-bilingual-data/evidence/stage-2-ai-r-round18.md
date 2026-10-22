# Stage 2 Round 18 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 18 verifier |
| Session | `/root/stage2_ai_r_round18` |
| Verified at | 2026-09-05T22:02:00Z |
| Candidate | `feature/erp-arabic-bilingual-data`; `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, automatically deleted temporary candidates, and this report only. No implementation, catalog, payload, runtime translation, governed evidence, Git index/history, commit, push, or deployment change. |

The repository instructions, canonical v4 plan, build handoff, implementation
record through deviation row 26, Round 17 remediation record, Round 16 AI-R
report, checker, permanent tests, CI workflow, bootstrap/update-baseline paths,
all ten regenerated envelopes, governed index, and all referenced candidate
artifacts were reviewed.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `b96b586faeff64ab2903d43f8fbada1beba2dc704fd7c597eee4b919083ec196` |
| Round 17 remediation record | `14816f2c9464e6951a7789473e38f1d8f6ca100c42896abef57a137c79e0021b` |
| Round 16 AI-R report | `07fb328b6369b68494fb77e9d34f12a5596faa8af467dc1acc910bdf55d68c22` |
| Checker / permanent tests / CI | `495515f287b21b5e03c8125e3d2449e50f33e1f9ae3e6411fc558a46bbfc096b` / `63a7e1be2d47d94a365f6f89134ea8e34a68d7ccb4b0554e9d20d5a619a75b0a` / `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Construction PO / payload | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Localization manifest / vendor baseline / decisions | `434321b5d4048b50e488ab53e10cdaf6f6f9dcc13c943218349bf0b2878bfa16` / `1da208b5a4a2d2ffeba3c24aac7248d3eac7318b24d335c2c449ca18830404d7` / `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` |
| Inventory manifest / freshness / inventory SQL | `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` / `9206c2273bf9791fc79ba9827d8209b7e2d48448238553a418bc222a1fde9789` / `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` |
| Scope lint / translation-write lint | `8436fed02c0dc5bc0c9f1f3abcf716cdbcbad68e28eb0db575535ad3e0e068c9` / `bcf1d242fcb7417a391f42f4ecd3a8edbc7b96c81c760704b8071e7b19b1b738` |
| Frappe / ERPNext Arabic PO | `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` / `2dfe0a5d07b091d1d34563fa53aac9f4665519aa9672303b4cd6fe3b2d705275` |
| Governed index | `36d424692f2fb0844840d7552eda918d046395ec1d48f919c665ffd22dae449c` |

## Governed envelope hashes

| Envelope | SHA-256 |
|---|---|
| `all-tests.txt` | `bb3829deae669a6fcceaafc14022f1a9462ac5b7f2a0b59ff1474fac314f1785` |
| `final-dryrun.txt` | `17461d85f49bc0ece7986e9fdfcd896938bbf75037465a893f5c1ed7954cc5e6` |
| `freshness-envelope.txt` | `137b9413d2b538a9a768dd9f5d7ab733ccbd9267bbe571d7dd9cb97ed7db47ac` |
| `full-gate.txt` | `3b139f405abbc44b7dfe09e61de966b6b1b096d2b55c3141d53a49afd74fbed0` |
| `gate-tests-standalone.txt` | `f153ec96db79a648d593dc3c892909afea9b3e5c7ce21b27901128d61f1cb6e3` |
| `lints-diffcheck.txt` | `4cc4141909e889e89edbcf547c128bee33998726042603194244ba9c4eacb69f` |
| `merkle.txt` | `f0a2a1d2bbedec5a87711440e4e070e05cce5172ccd0d9309599f88d42440974` |
| `scoped-gate.txt` | `4fc5ba24d4b1486caa51fc2bd8dbcf35b95b7a687b0e920905294df56546b0a3` |
| `sync.txt` | `f9482ea85abf55e55a528fdbb0d55c9c003a943efc7dd83703cb1bca2c6cb261` |
| `vendor-audit.txt` | `8a00f43e1f30e4b75613228252916fd3583db82c137c7811acd76300c506bb21` |

All ten byte hashes agree with the index. Each supplied envelope and the index
has a truthful `ENVELOPE_LINES` value (13, 9, 49, 11, 8, 10, 11, 8, 7, 9,
and 33 respectively). The supplied index has one correct candidate root, one
correct HEAD, and fourteen correctly ordered artifact rows whose values match
the candidate. The supplied semantic records, arithmetic, UTC bounds, embedded
freshness JSON, and generation/index order pass the current checker.

## Fresh independent health checks

- Ordinary evidence-enabled full gate exited `0`: catalog `771`; source files
  `248`; wrapped `631`; JSON labels `21`; missing `0`; errors `0`.
- Standalone localization-gate suite passed **87/87**. Fresh Bench modules
  passed **13 + 6 + 5 + 3 + 8 + 87 = 122** tests. An initial parallel Bench
  launch caused a `System Settings` timestamp race in the eight-test module;
  its immediate isolated rerun passed 8/8, so this is recorded as test-runner
  concurrency noise rather than a product failure.
- Fresh scoped gate and vendor audit returned `errors=0`. Both lints and
  `git diff --check` passed. Both vendor PO files are clean in their own Git
  worktrees and match the governed hashes.
- The governed dry-run records `34/0/0/34/0`; sync records zero creates and
  updates; freshness records `critical_pass: true`. These mutation-adjacent
  operations were not repeated by AI-R; the ordinary read-only gates bind their
  artifacts.
- A fresh read-only DB query through the canonical serializer reproduced
  **18,412** rows and Merkle root
  `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`,
  matching the committed inventory manifest.
- `--skip-evidence` without `STAGE2_EVIDENCE_BOOTSTRAP=1` exited nonzero. CI
  invokes the ordinary checker and does not pass that flag. The Round 17
  freshness-before-rebinding behavior and existing update-baseline refusal
  tests demonstrate the intended fail-closed ordering, but the final evidence
  authorization still has the defects below.

## Round 16 coherent-forgery rerun

Automatically deleted `.../bench/apps/construction` candidates were built from
the permanent live-contract fixture. Modified envelopes had their declared
length and SHA index row coherently refreshed. The residual cases were rerun:

- Missing, forged, or duplicate candidate root and missing/duplicate/wrong
  HEAD: rejected.
- Duplicate artifact row and noncanonical `TESTFILE_SHA256` alias: rejected.
- False scoped, vendor, lint, freshness, standalone, sync, and Merkle results;
  lowercase hidden `fatal`; duplicate/decoy results; and impossible embedded
  time material: rejected.
- **False index `ENVELOPE_LINES: 999`: accepted with no error.**
- **Arbitrary index `CHECKER_SHA256` value of 64 zeroes: accepted with no
  error.**

The last two results reproduce Round 16 P0 authorization bypasses. Inspection
confirms why: `check_evidence_index()` classifies the final index length row but
never compares its numeric value to the nonempty-line count, and it checks the
ordered artifact marker names but never parses/compares the index artifact
values to the candidate. Envelope artifact occurrences are checked separately,
so a good envelope value can act as a decoy for a forged governed-index value.

Permanent coverage is also incomplete. The 87-test suite has no coherent test
for a wrong governed-index line count or arbitrary governed-index artifact
value. Its existing length-marker test removes an envelope marker, and its
artifact-related duplicate test does not assert index-value recomputation.

## Integrity boundary

Before this report, the unstaged binary diff SHA-256 was
`8c8c3b8170276c1238ea75854c21d81d2fb0b88316bb8461979c86d47e75632f`;
the staged diff was empty
(`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
All adversarial candidates were automatically deleted. This report is the only
repository file created by AI-R.

## Decision

**BLOCKED — Stage 2 Round 18 is not independently verified. Stage 2 remains
open and Stage 3 must not begin.**

The regenerated evidence happens to be internally correct and all live health
checks are green, but the governed index still authorizes a false length and a
false artifact SHA. Therefore the claimed exact fail-closed evidence contract
is not implemented and cannot support a Stage 2 closure decision.

## Exact next gate and residual risks

1. Parse the single index `ENVELOPE_LINES` value and require it to equal the
   actual nonempty index line count.
2. Parse every one of the fourteen ordered index artifact rows, require each
   exactly once, recompute each from `CANDIDATE_ROOT`, and compare index values,
   every prescribed envelope occurrence, and candidate bytes.
3. Add permanent coherent-rehash/reindex adversarial tests for both reproduced
   bypasses (plus missing/wrong/unresolvable/duplicate root and HEAD, artifact
   aliases/duplicates, all semantic false-result/decoy/failure cases, and
   embedded-time ordering), then rerun standalone and Bench suites.
4. Regenerate all ten envelopes and the governed index from the fixed candidate,
   run the ordinary CI-equivalent checker with evidence validation enabled, and
   request a fresh independent AI-R verification.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
