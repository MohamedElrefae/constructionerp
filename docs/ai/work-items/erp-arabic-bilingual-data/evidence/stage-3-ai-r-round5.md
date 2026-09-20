# Stage 3 — Independent AI-R Re-verification, Round 5

## Identity, candidate, and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 3 remediation verifier |
| Session | `/root/stage3_ai_r_round5` |
| Verified at | 2026-09-09 (Africa/Cairo) |
| Candidate | `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted working tree |
| Boundary | Read-only repository/site inspection, disposable test fixtures, and this new report only. No implementation, catalog/payload, existing-evidence, Git index/history, runtime Translation, deployment, or live Account-name migration. |

This is a fresh review of the current Round-5 candidate. I read the repository
instructions, canonical v4 plan, handoff, `IMPLEMENTATION.md` through row 41,
the Round-4 AI-R report, Round-5 builder record, current registry/search/service/
hooks/tests, the full P95 JSON/session, the full withdrawn HTTP bundle, and the
governed localization evidence. The Builder did not approve its own work.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `2c89a65d8802890c054f5571717a470d335c1412a5329bf80f193f58fd46ace7` |
| Stage-3 builder record | `86225052888b1b6353b6ce7a4903819188ff71b90ea009bbefdeaf576bb00066` |
| Round-4 AI-R | `fdf0c951bdae90ffd2646c59c4dff68c3fc402ab3feb1184e50ed579d5c0955a` |
| Frappe service / dropdown search | `082c39e1f95fc6923831c9f9c869ae65837559ea258b78336aea1c8036bc334d` / `f6db85fe9d9c5a7d85d9013e69f4773a1e0257f102486da823c880222c03b55f` |
| Bench / pure tests | `29ba8e704f0af1c0491efbb7bbf1ae1a2fd0222948608caa47c4cabb5bc546d5` / `060adbb51e0838ab2a5033c6775242dddb164c8c5793247a830828696e52f248` |
| P95 JSON | `e91b3bf745302cba1c85c307630a2ff0dc8bf77607f14a31f2c1e658437e8fa9` |
| HTTP README / serve log | `a77055fe8f9dbbb8bd2f9ba7ffbb0fabe264cb13e6045f3e70f964f254ee795b` / `ba045fec9712ae87438e2a774e6876b8b9149f6e122dc4f036c3b54adf05e956` |

## Round-4 P1 closure results

### 1. Complete ranking and pagination — **BLOCKED (P1)**

The old 1,000-row cap is genuinely removed from both paths. Each uses one
permission-aware `frappe.get_list`, ranks exact → prefix → substring with a
stable `value` tie-break, and slices only afterward. The 12 fillers now really
match `CT-RANK-TARGET`; fresh tests proved the backdated exact result first in
both paths and disjoint cross-page behavior. The 1,001-filler test also passed
and proves the service path returns the old-window-excluded exact row from a
served set of at least 1,002.

The replacement is not release-safe large-tenant behavior, however:

- Both whitelisted paths use `limit_page_length=0`, materialize every permitted
  match, format every row, and Python-sort it for every page request. With an
  empty `txt`, the OR predicate is absent, so an ordinary blank Link search
  reads the entire permitted DocType even to return 20 rows. User-controlled
  broad text likewise creates unbounded database transfer, memory, and sort
  work. This is a resource-exhaustion/denial-of-service surface and violates
  the canonical no-material-query-cost and acceptable large-search-response
  gates.
- The comment saying a database-computed rank “becomes the scaling path” is
  only a future intention. No database rank expression, bounded continuation,
  minimum-query contract, timeout, or other scaling control exists in the
  candidate, and no owner acceptance of this performance exception exists.
- The >1,000 boundary test exercises only `search_bilingual`, not the dropdown
  path. The smaller test covers both paths, but it cannot detect reintroduction
  of a dropdown-only cap above 1,000.

Global correctness is improved, but replacing silent truncation with
unbounded request work does not close the performance/safety gate. Ranking
must be performed permission-safely in the database before bounded database
pagination (or an equivalently bounded, explicitly accepted design), with a
>1,000 regression for both public paths.

### 2. Comparative P95 — **BLOCKED (P1)**

The preserved arithmetic is reproducible. Independently applying nearest-rank
P95 to the 50 raw values gives exactly baseline `2.121 ms` and bilingual
`2.885 ms`; the implemented formula gives `17.3331 ms`. Both identity lists
contain the same 12 fixture Accounts, five warmups are declared, and cleanup
reports no `CT-T3-%` residue.

The artifact and permanent gate still do not prove the required comparison:

- Sampling is interleaved but not balanced: every one of the 50 pairs runs the
  baseline first and bilingual second. There is no alternation or randomized
  order, contrary to the Round-5 claim.
- The timed baseline is a page-limited `get_list` (at most 20 rows), while the
  timed bilingual path fetches and sorts the complete match set. They happen
  to return all 12 rows in this tiny fixture, but the benchmark does not cover
  the newly introduced >1,000 behavior or a representative large tenant.
- The JSON has no code/artifact hashes, query counts, database version/config,
  host/runtime identity, Account cardinality, or permission/user identity.
  `frappe_version` plus a timestamp is not the claimed environment record.
- The reported even-sample “median” selects element 26 rather than averaging
  elements 25 and 26. Independent medians are baseline `1.447 ms` and
  bilingual `1.851 ms`, not the recorded `1.451` / `1.852`.
- The permanent test never reads or authenticates `p95-measurement.json`. It
  calls the same helper under test, then checks that helper's self-produced
  statistic and permissive result. Artifact deletion, tampering, stale code,
  missing hashes/query counts, or an order bias would not fail it.
- Canonical plan §10.3 permits no more than 10% slowdown unless explicitly
  accepted. The measured bilingual P95 is about 36% slower. The added 15 ms
  floor is documented by the Builder but is not an explicit owner acceptance
  of the canonical exception; it makes this 36% regression pass.

The raw values are a useful pilot smoke result, not an independently bound,
balanced, canonical P95 release gate.

### 3. HTTP dispatch and withdrawn socket claim — **BLOCKED (P1 evidence/residue)**

The authoritative Round-5 builder record, tracker row 41, and HTTP README do
explicitly withdraw the live-socket claim. The preserved 417/403 transcripts
and access log are therefore treated only as an environment finding, not as
release evidence. The permanent `frappe.handler.execute_cmd` test remains a
real handler-level override test: it supplies POST-shaped string form data,
resolves the vendor method override, rejects a reason-free request, and
accepts a reasoned request.

Two narrower claims are not substantiated:

- Handler-level `from_descendant` coercion is not tested. The execute_cmd call
  omits it; compatibility is tested separately by a direct Python service
  call. Thus the Round-5 README's statement that the handler test covers
  `from_descendant` is inaccurate.
- `setup.session` and `cleanup.session` are scripts, not captured setup/cleanup
  outputs. A fresh read-only database check found the live test fixture
  `CT-HTTP-1 - CT HTTP Probe - E` still present, while the builder claims no
  residue. There were zero `CT-T3-%`, `CT-RANK-%`, and `CT-BULK-%` Accounts,
  but the HTTP fixture was not cleaned. I did not delete this pre-existing
  state because this evidence-only review did not create it.

Withdrawal is acceptable in principle because Round 4 already accepted the
hermetic code-path point, but the authoritative evidence must stop overstating
handler coverage and must truthfully prove cleanup/no residue.

### 4. Rename Version + Comment and prior closures — **VERIFIED CLOSED**

The governed rename still runs through the vendor method inside a scoped
savepoint, re-resolves the post-rename identity, and transactionally inserts a
native Version containing old/new identity fields plus the required reason
Comment. Fresh tests retained permission refusal, reason enforcement, duplicate
rollback, audit-failure rollback, both transaction-composition directions,
server-resolved identity, and the prior Unicode/confinement/normalization/
registry failures. No regression was found in the prior P0 closures.

## Fresh reproduced evidence

- Fresh suites passed: `13 + 6 + 5 + 3 + 8 + 89 + 38 + 47 = 209`.
  Standalone localization was `89/89`, pure registry `38/38`, and the Bench
  pilot `47/47`. (An initial system-Python pure-test invocation lacked Frappe;
  rerunning with Bench's `env/bin/python` passed all 38.)
- Fresh full localization gate reported catalog `803`, CSV `34`, extraction
  `257` files / `662` wrapped + `21` JSON / `0` missing, raw missing `0`, and
  `errors=0`. Vendor audit, scope lint, Translation-write lint, and
  `git diff --check` passed.
- Fresh read-only DB serialization returned exactly `18,444` Arabic
  Translation rows and Merkle
  `61c0c12cd197a647ba751fd7854c34aab047d09de14e8b0d085bfff4a634d4f9`,
  matching the current manifest. The manifest SHA is
  `c2abb216d1821d1571561bd8d67a2f6b106e3662bf4889e22c9075a7111a68ae`.
- Current build evidence was inspected; no rebuild was needed to decide the
  open server-side safety/evidence gates.
- Before this report, worktree-status SHA was
  `3b249fdcc9c68ba125d4d5b63c4ed94f823e0d5626b6cf447f047bf4308233d5`,
  tracked binary-diff SHA was
  `2a08943c5a3394728dc74e672f0db9c38d58eeed2f43b249cb2acc9edf7dfa62`,
  staged diff was empty SHA
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`,
  and HEAD remained `e7be48855`. No live Account name was migrated by this
  verifier.

## Decision and next gate

**BLOCKED — Stage 3 does not close, and Stage 4 must not begin.**

Round 5 closes the silent 1,000-row truncation and repairs the small competing
fixtures, but it substitutes unbounded request work and does not provide a
large-tenant-safe implementation. The P95 artifact remains order-biased,
non-canonical, incompletely bound, and unvalidated by the permanent test. The
withdrawn HTTP claim is correctly demoted, but its documentation overstates
handler coverage and a claimed-clean fixture remains live.

The next candidate must implement bounded permission-safe database ranking
before database pagination (and test >1,000 on both paths), produce a balanced
and artifact-bound P95 comparison against an explicitly approved baseline/gate
with correct statistics and sufficient environment/query/code identity, and
clean/prove the HTTP fixture residue while correcting the handler coverage
claim. Then request a fresh independent AI-R rerun.

Owner authorization remains required for commit, push, merge, deployment,
runtime/catalog mutation, or any live Account-name migration.
