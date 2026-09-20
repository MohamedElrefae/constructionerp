# Stage 3 — Independent AI-R Re-verification, Round 4

## Identity, candidate, and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 3 remediation verifier |
| Session | `/root/stage3_ai_r_round4` |
| Verified at | 2026-09-09 (Africa/Cairo) |
| Candidate | `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted working tree |
| Boundary | Read-only repository/site inspection, disposable test fixtures, a safe local build, and this new report only. No implementation, catalog/payload, existing-evidence, Git index/history, runtime Translation, or live Account-name mutation. |

This is a fresh review of the current Round-4 candidate, not a reuse of the
Round-3 verdict. I read `AGENTS.md`, canonical plan v4, the build handoff,
`IMPLEMENTATION.md` through row 39, the Round-3 AI-R report, the complete
Round-4 builder record, current services/search/hooks/patches/UI/tests, all
Stage-3 browser artifacts, the P95 and HTTP artifacts, and the governed Stage-2
localization evidence. The Builder did not approve its own work.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `0d5265318011fdd52c94a334d61265fa20a6131325024665877349d163eaad02` |
| Stage-3 builder record | `44a95bba385ce942302f065e038cbc318ba9d5c35a96706f12ead418ec4147bc` |
| Round-3 AI-R | `2a3df61b3329afcee46881a65fb68a6c37a7bf431e742787391951076e272957` |
| Registry | `9cb10f5a0dd125ebb3b0103f3a6c67b1889a24aab27e145cbd5d5257938f44a4` |
| Pure registry / Frappe service | `691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538` / `d3b5349e661e5923168e5de04d666f8e935004c5e7a01b613b7dbf0303607204` |
| Dropdown search | `8aaed801e79bc681e631c5a4e1c7ad3efec12493845b877f9bc7cd81a331daf8` |
| Pure / Bench pilot tests | `060adbb51e0838ab2a5033c6775242dddb164c8c5793247a830828696e52f248` / `f258f8d92cd4f90f0bc49b1c3612f8accdcafd34c89df841efd22ebbd9c99633` |
| Hooks | `d32eebf50788aabe3dc29d060d4b6789c1a4d9140fa303a0498c4d1114716e66` |
| P95 / HTTP transcript | `389b52f3b00db6397f915a9e525125a9d014260a1b18aaceda25fe22314001a2` / `20cd653323e0ef22de0e2ad5afcd5041e9739fe5603f41169d3aa77649ef570c` |

## Round-3 P1 closure results

### 1. Global relevance-ranked pagination — **BLOCKED (P1)**

Both paths now rank before their Python page slice, use the advertised rank
classes, and use `value` as a deterministic tie-break. Permission-aware
`frappe.get_list` remains the single query. Those improvements are real, but
the candidate does **not** obtain the complete matching candidate set:

- `search_bilingual` requests only `RANK_CANDIDATE_LIMIT = 1000` rows ordered
  by `modified desc`; the dropdown independently hard-codes the same limit.
  Any exact/prefix match at database position 1001 or later is absent before
  ranking. It cannot outrank an in-window substring, and offsets reaching
  beyond the window silently return incomplete/empty pages. Thus ordering is
  global only within an arbitrary modification-ordered sample, not over all
  matching permitted rows. No overflow signal or continuation strategy exists.
- The claimed permanent regression is not meaningful. Its 12 alleged
  “substring-only” fillers are named `CT-RANK-FILLER-*`, while the query is
  `CT-RANK-TARGET`; they do not match the query at all. The exact row is
  therefore the only matching fixture and would pass under the old
  slice-then-sort implementation. The test exercises only `search_bilingual`,
  not the dropdown path, and has no 1000/1001 boundary, cap-overflow,
  cross-page, or duplicate assertion tied to a genuinely competing set.

For more than 1,000 matches, the current result is incorrect relative to the
advertised exact → prefix → substring total order. A bounded design may be
acceptable only if its semantics are explicit and safe (for example a
database-computed rank ordered before database pagination, or an explicit
truncation/continuation contract); silently taking the newest 1,000 is not a
complete bounded matching set.

### 2. Equivalent pre-feature P95 — **BLOCKED (P1)**

The preserved numbers are internally arithmetically consistent with the
implemented threshold (`2.706 * 1.10 + 15 = 17.977`; `3.991 <= 17.977`) and
the calls are interleaved for 25 iterations on the same text. They do not
establish the claimed equivalent before/after workload:

- The baseline conditionally filters `company = Elrefae`; the bilingual call
  passes no company filter. This changes scope, permission work, and possible
  cardinality.
- The baseline fetches 20 rows and two fields, ordered by modified date. The
  bilingual path fetches up to 1,000 rows and four identity fields, adds the
  Arabic normalized predicate, formats every fetched row, globally sorts it,
  and only then returns 20. Result/query workload is therefore deliberately
  different, contrary to the function and evidence claim.
- There is no warm-up phase. Baseline always runs first in each pair, so order
  effects are not balanced. For 25 samples the statistic selects index 22
  (the 23rd value, approximately P92), not nearest-rank P95 (the 24th value).
- The artifact preserves only rounded summary values, not raw samples,
  environment/fixture counts, filters, query counts, or a code hash. It cannot
  independently authenticate the stated measurement. The permanent test calls
  the same helper and checks its self-computed permissive result; it does not
  consume or validate the preserved artifact and cannot detect these workload
  substitutions. The fixed +15 ms floor also makes a 47% regression pass on
  this very small baseline, so it is not by itself the canonical “no more than
  10%” performance proof.

The recorded values are a useful smoke measurement, but not a trustworthy
equivalent Stage-1A comparative P95 gate.

### 3. HTTP override dispatch — **CONDITIONALLY VERIFIED; evidence gap remains P1**

The permanent test genuinely invokes `frappe.handler.execute_cmd` at the
vendor method name with a POST-shaped request and string `form_dict` values.
That exercises override resolution, whitelist/HTTP-method checking, argument
dispatch, reason-free rejection, reasoned success, and same-value
`from_descendant` compatibility. The hook maps the vendor endpoint to the
governed wrapper.

The claimed live-socket transcript is not independently auditable enough to
close the evidence claim. It records only five result lines: no request URLs
or response bodies, no fixture creation/identity precondition, no cleanup
result, no server PID/build/hash, and no corresponding server log. The
archived `serve.log` is dated 2026-09-06, predates the 2026-09-09 HTTP run, and
contains no matching request. The transcript names a command under
`/tmp/opencode/stage3/http_dispatch.py`, whereas the preserved script is under
the evidence directory; that script assumes a pre-created fixed Account and
does not create or clean it. A fresh read-only check found zero `CT-HTTP-%`
Accounts, Comments, or Versions, which is clean current state but does not
prove how the prior fixture was restored. The hermetic dispatcher test closes
the code-path point; a fully reproducible socket-level artifact remains due if
the live-HTTP claim is retained.

### 4. Native post-rename Version and reason Comment — **VERIFIED CLOSED**

The wrapper delegates to ERPNext's standard Account rename service inside its
scoped savepoint, re-resolves the new identity server-side, then inserts both
the reason Comment and a real `Version` DocType row attached to the post-rename
Account. Its native `data.changed` contains the old/new account number (and
other changed identity fields), and the fresh end-to-end test asserted the
exact old/new pair. Audit insertion is inside the same savepoint: audit failure
rolls back the rename, duplicate-number failure creates neither record, caller
transaction composition remains intact, and permission/reason/narrative
validation precedes mutation. Fresh fixtures left zero `CT-T3-%`,
`CT-RANK-%`, or `CT-HTTP-%` Account/audit residue.

Residual: manually constructing a native Version is application-authored audit
rather than a Version automatically emitted by `Document.save`; this is
acceptable for the documented native-audit decision because the row is a real
Version, contains independently derived before/after data, is transactionally
bound to the standard rename, and is attached to the server-resolved identity.

## Prior closure regression check

The current code and fresh tests continue to close the earlier P0s and prior
P1s: insertion refuses client-supplied Arabic; every stored Arabic value is
canonically validated; direct writer/Administrator saves are confined; the
operation token is document/old/new-bound and cleared; scoped savepoint
composition works both directions; active/schema-installed registry drift
propagates; normalized keys are server-derived on every save; the patches are
idempotent/reversible; permission-safe one-query search and normalization work;
all 12 forbidden bidi code points are rejected; visible strings are wrapped;
Account hooks resolve; stable tree identity/escaping and the earlier Arabic
and English browser evidence remain intact. The nine browser artifacts retain
the hashes reviewed in Round 3 (including AR/EN JSON
`991e56f8…`/`8103b36e…` and script `5e8ad847…`).

## Fresh reproduced evidence

- Fresh tests: `13 + 6 + 5 + 3 + 8 + 89 + 38 + 47 = 209`, all green.
  Standalone localization `89/89` and pure registry `38/38` also passed.
- Fresh ordinary localization gate: catalog `803`, CSV `34`, extraction
  `257` files / `662` wrapped + `21` JSON / `0` missing, raw missing `0`,
  `errors=0`. Scope lint, Translation-write lint, vendor PO cleanliness, and
  `git diff --check` passed.
- Fresh read-only DB serialization returned exactly **18,444** Arabic
  Translation rows and Merkle
  `61c0c12cd197a647ba751fd7854c34aab047d09de14e8b0d085bfff4a634d4f9`,
  matching both manifests.
- Fresh `bench build --app construction` exited zero, retained
  `construction.bundle.2XKAHIYO.js`, and reported the Arabic MO up to date.
- Before report creation, worktree-status SHA was
  `3b249fdcc9c68ba125d4d5b63c4ed94f823e0d5626b6cf447f047bf4308233d5`,
  tracked binary-diff SHA was
  `8424761611889a822004fd11a721a3503aa11369acac0dde315abe945ea959ee`,
  and staged diff was empty SHA
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
  HEAD remained `e7be48855`; no live Account names were migrated.

## Decision and next gate

**BLOCKED — Stage 3 does not close, and Stage 4 must not begin.**

Round 4 closes the real rename-Version gap and materially improves in-window
ranking and handler-dispatch coverage. It does not close globally correct
pagination or the equivalent comparative P95 gate, and the socket-level HTTP
artifact is not independently reproducible as preserved.

The next candidate must rank the complete permitted match set before page
slicing (including correct >1000 semantics), add meaningful competing-row and
1000/1001 tests for both paths, and produce an actually equivalent,
statistically correct, independently auditable P95 comparison. If retaining
the live-HTTP claim, preserve fixture setup, exact request/response, matching
server log/build identity, and cleanup proof. Then request a fresh independent
AI-R verification against new hashes and results.

Owner authorization remains required for commit, push, merge, deployment,
runtime/catalog mutation, or any live Account-name migration.
