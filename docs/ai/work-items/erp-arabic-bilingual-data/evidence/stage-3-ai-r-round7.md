# Stage 3 — Independent AI-R Re-verification, Round 7

## Identity, candidate, and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 3 remediation verifier |
| Session | `/root/stage3_ai_r_round7` |
| Verified at | 2026-09-09 (Africa/Cairo) |
| Candidate | `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted working tree |
| Boundary | Read-only repository/site inspection, disposable test fixtures, and this new report only. No implementation, catalog/payload, existing evidence, Git index/history, runtime Translation, deployment, or live Account-name migration. |

This is a fresh review of the current Round-7 candidate. I read the repository
instructions, canonical v4 plan §10.3, handoff, `IMPLEMENTATION.md` through row
45, Round-6 AI-R, the Round-7 builder record, current search/service/registry,
hooks/tests, P95 artifact, HTTP evidence, and governed localization evidence.
The Builder did not approve its own work. The owner's rejection of the 15 ms
floor is controlling: the comparative gate is the bare 10% rule.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `3096cd4b447d18bbbdc8806e7932d4fb1e0497541927213f1777b0b823cda475` |
| Stage-3 builder record | `7268956f39f2a0e97ad149d20bdbee202f8de4f6fcc8e938849193eb4ebc810e` |
| Round-6 AI-R | `26b2f6918e40c4847a7454e6285bf7c743187b6ed2dcb76b7835191838ec75b7` |
| Service / registry / dropdown | `e32d8dd7d8467a6c8eb9a250faf596904c9bae3c086ebac80d3a3abec50f2df6` / `691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538` / `baa082c6facbf69766145d8118484d0332b87db8172bf61dce94e354e01aaf82` |
| Bench / pure tests | `5c9392210e86d26b3ec22be2fd2dd8c8f66151475e600518f1ed43aac451d39a` / `060adbb51e0838ab2a5033c6775242dddb164c8c5793247a830828696e52f248` |
| P95 JSON | `cab3c0207411ef5a6a3e51ffe7ac6f0f07ee5972f3e28f3aeea106e0b3f47367` |
| Inventory manifest | `27897e2ce523a3a5dcdc141753d01b84ddfcd8b88a6c54de0f7dd65d67c8187d` |
| Build evidence | `85516df81c035ce0ef3caddc382e355eaf4b9d54ff8111e4ebf78c4d15e1a426` |

## Round-6 gate closure results

### 1. Ranking-window probe, overflow API contract, and resource bounds — **BLOCKED (P1)**

Both text paths do issue one permission-aware `frappe.get_list` with
`limit_page_length=RANK_WINDOW + 1`, `limit_start=0`, and the expected fields.
Both distinguish exact-window from overflow using `len(rows) > RANK_WINDOW`.
The plain service response and dropdown response both raise the cataloged,
wrapped `ValidationError` on detected overflow. Blank requests use database
pagination, and ordinary ranking remains exact → prefix → substring with the
identity/value tie-break.

The claimed probe semantics and tests are incomplete:

- `search_bilingual` detects the probe at lines 717–726 but never removes it.
  With `with_meta=True`, all `RANK_WINDOW + 1` rows proceed into sorting and
  slicing (lines 735–756). Thus the probe row is part of the ranked/served set,
  contrary to the explicit contract that it is dropped before ranking. A
  caller using a sufficiently large page or offset can receive the probe row
  while metadata says the ranking window is 5,000.
- The permanent boundary test does not create 5,000 or 5,001 rows. It patches
  the service constant to 2 and 1 over two ordinary fixtures. The dropdown has
  only the patched real-overflow refusal assertion. There is no exactly-full
  dropdown boundary assertion, no `>5000` fixture on either public path, and
  no proof involving an exact match outside the real 5,000-row window. The
  separate bulk test creates only 1,001 fillers (about 1,002 matches), wholly
  inside the current 5,000 window.
- The dropdown offers no structured metadata route at all. Refusal is a valid
  loud default, but the requested both-public-path metadata/refusal matrix is
  not implemented or tested; only the service has `with_meta`.
- Blank request work is not actually capped by the service. Both public APIs
  pass the client-controlled `page_length` straight to the ORM. A caller can
  request an arbitrarily large blank page, defeating the stated large-tenant
  bounded-work guarantee. Negative/oversized pagination inputs are likewise
  not normalized to a server maximum.

Fetching 5,001 projected rows in one permission-aware query is a finite and
reasonable transitional bound for text searches, but it does not cure the
uncapped blank path or the incorrect probe handling. The required first-
principles real boundary reproduction cannot be credited because the
permanent fixtures do not exercise it.

### 2. ASCII optimization and request memoization — **CONDITIONALLY VERIFIED (P2 residuals)**

For the service path, the optimization is match-set sound for the implemented
normalizer: `_normalize_arabic` changes only Arabic-block diacritics/tatweel
and Alef variants, `_has_arabic` includes that block, mixed ASCII/Arabic input
therefore retains the normalized predicate, and ASCII/digits/punctuation are
already searched in raw English/Arabic/code/identity fields. This creates no
identified false negative. The dropdown does not use this optimization and
still adds its normalized predicate for every query, so its correctness is
unchanged but its optimized shape is not equivalent to the measured service.

The registry and mapping caches live on `frappe.local`, so they are request/
site/user scoped by Frappe request lifetime rather than process-global. Parse
and active-schema failures raise and are not memoized into permissive state;
new requests revalidate. Imports load without a circular/startup failure in
the fresh suites.

Residual: `get_mapping` returns a cached mapping before consulting the
registry signature. A registry edit during the same request can therefore
leave mapping resolution stale even though `get_registry` documents edit
invalidation. Tests manually clear the mapping memo to exercise schema drift,
and there are no dedicated equivalence tests covering ASCII, mixed script,
Unicode digits/punctuation, and case/collation. These are not the primary
Stage-3 blocker, but the invalidation contract and regression matrix should be
made explicit.

### 3. Comparative P95 — **BLOCKED (P1 test-gate defect; artifact itself passes)**

The artifact is authentic against all three governed code hashes. Independent
recalculation of its 50 raw samples confirms five discarded warmups,
alternating pair order, nearest-rank P95 and true medians:

| Measure | Baseline | Bilingual |
|---|---:|---:|
| P95 | `2.272 ms` | `2.442 ms` |
| Median | `1.424 ms` | `1.607 ms` |

The bare limit is `2.4992 ms`; the recorded bilingual result is 7.4824% slower
and passes. The recorded identity sets are equal (12 each). Environment is
bound to Frappe `16.18.1`, MariaDB `10.11.14`, host
`mohamed-OptiPlex-3080`, `Administrator`, company cardinality 93, and the same
text/company/page shape. The 50-entry `baseline_counts` and
`bilingual_counts` arrays are genuine per-call deltas and every entry is 1;
both means are 1.0. The artifact-authentication test recomputes statistics,
checks hashes and identity equivalence, and applies the bare 10% threshold.

However, the advertised permanent *live* canonical gate is not present at
runtime. `TestBilingualAccountPilot` defines
`test_comparative_p95_live_measurement_is_balanced_and_bound` twice, at lines
1016 and 1035. Python silently replaces the first bare-10% method with the
second method, whose limit is still `baseline * 1.10 + 15.0` and whose failure
message still describes the rejected floor. The fresh 49-test output lists
only one method of that name, proving the override. Consequently live
re-derivation can regress above 10% while the suite remains green, and the
reported 49 count hides the missing test. The preserved artifact gate is
useful evidence, but it does not satisfy the claim that the live permanent
gate also enforces the owner's decision.

The pilot workload is small (93 Accounts, 12 matching identities), but it is
the approved same-input pilot baseline and the artifact result itself is
inside the canonical rule. No floor exception is needed. Closure requires
removing the duplicate/old-floor test and demonstrating that the actually
collected live test applies `<= baseline * 1.10`.

### 4. Handler, HTTP cleanup, and prior controls — **VERIFIED CLOSED**

The handler test still reaches `frappe.handler.execute_cmd`, covers string
`from_descendant: "1"`, requires the rename reason, and cleans Version/Comment
state. Fresh DB checks found zero `CT-HTTP-1%`, zero general `CT-%` Account
fixtures, and zero non-empty live `account_name_ar` values. Previously accepted
permission, Unicode, normalized-key invariant, tree batching/identity,
browser adapter, savepoint, vendor-failure, Version+Comment, and hook closures
remain green. The unstable live-socket claim remains withdrawn, as previously
accepted.

## Fresh reproduced evidence

- Fresh suites passed: `13 + 6 + 5 + 3 + 8 + 89 + 38 + 49 = 211`, failed 0.
  The green count does not cure the duplicate-method omission described
  above. Standalone localization was 89/89 and pure registry 38/38.
- Fresh evidence-enabled full gate reported catalog `804`, CSV `34`,
  extraction `257` files / `663` wrapped + `21` JSON / `0` missing, raw
  missing `0`, and `errors=0`. Scoped and vendor gates reported `errors=0`;
  scope lint, Translation-write lint, and tracked/staged diff checks passed.
- The current inventory manifest records `2,678 + 826 + 9,014 + 5,927 =
  18,445` rows and exact Merkle
  `6fcffc90dc59027256f63d46c4243da470243f504391a03bdaa734ee3d43fc60`.
  The evidence-enabled gate live-matched it. Steady-state evidence records
  sync `0/0`; governed PO/evidence/index checks are included in that gate.
- Before this report, worktree-status SHA was
  `3b249fdcc9c68ba125d4d5b63c4ed94f823e0d5626b6cf447f047bf4308233d5`,
  working diff SHA was
  `4718d9ea3f3577fb145326285e93c4c14fe5d6427ed8823abacfdfdedac27bd6`,
  and staged diff was empty SHA
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
  HEAD remained `e7be48855`. This verifier left no disposable Account residue
  and migrated no live Account names.

## Decision and next gate

**BLOCKED — Stage 3 does not close, and Stage 4 must not begin.**

Round 7 produces an authentic P95 artifact that passes the bare 10% rule and
closes the per-call SQL-count defect. It does not close the full gate because
the service ranks/serves its probe row, the claimed real 5,000/5,001 both-path
boundary coverage does not exist, blank public pagination remains
client-unbounded, and Python overrides the new live bare-10% test with the old
rejected-floor test.

The next candidate must: drop the probe before any ranking/slicing; cap and
validate blank-page work; add genuine exact-5,000 and >5,000 tests for both
public paths (including beyond-window exact-match and loud refusal/structured
metadata behavior appropriate to each API); and retain exactly one live P95
test whose executed threshold is the bare 10%. Then request a fresh independent
AI-R review. Commit, push, merge, deploy, runtime/name migration, and other
operational actions continue to require explicit owner authorization.
