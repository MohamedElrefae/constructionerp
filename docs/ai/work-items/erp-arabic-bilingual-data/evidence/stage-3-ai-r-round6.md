# Stage 3 — Independent AI-R Re-verification, Round 6

## Identity, candidate, and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 3 remediation verifier |
| Session | `/root/stage3_ai_r_round6` |
| Verified at | 2026-09-09/10 (Africa/Cairo) |
| Candidate | `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted working tree |
| Boundary | Read-only repository/site inspection, disposable test fixtures, and this new report only. No implementation, catalog/payload, existing evidence, Git index/history, runtime Translation, deployment, or live Account-name migration. |

This is a fresh review of the current Round-6 candidate. I read the repository
instructions, canonical v4 plan (especially §10.3), handoff,
`IMPLEMENTATION.md` through row 43, Round-5 AI-R, the Round-6 builder record,
current search/service/registry/hooks/tests, the P95 JSON, HTTP lifecycle
bundle, and governed localization/build evidence. The Builder did not approve
its own work. For this review the owner/consultant explicitly **rejected** the
proposed `10% + 15 ms` floor; the canonical 10% limit therefore controls.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `7ad089af84638ab1242fe40c33bea3f83274038c7a0800b7768cd4755d4f287a` |
| Stage-3 builder record | `c4ab9cdbbab778f986b4af00f3c0a6ac46c439fddf7918ea8e8c50a461224e65` |
| Round-5 AI-R | `b16c015b7fc955088bd05175b92ed3d7e6be3b60eab48a66d5d4e453f1e27031` |
| Service / registry / dropdown | `ff7bc2abf2afc999c7122c3de1aa2187299fc98157afadff7e2e022bf209a1b4` / `691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538` / `d1aa0f5f50e98944cab677802a7f3186099fe896efa840f7f5a965ec1e0dbbe8` |
| Bench / pure tests | `87c7ad344762f897245dd1f15e9aec2478d4f0ef42c0e6dab42b4dd558a3bad1` / `060adbb51e0838ab2a5033c6775242dddb164c8c5793247a830828696e52f248` |
| P95 JSON | `e9816cdccd0a9b9d027d98600e3d5e6c3d04d82e28d9ce86c575ce76393ad6f3` |
| HTTP README / setup / cleanup | `5bc920e37f047b4a8a94fa4245364e5d55f9363fd296fea29265f8f45817f8f8` / `e029091ffe3119209ca50138c9fffc216dc7ac38fac421220e1599a5dcfd370b` / `92710ffc1d737aa4735c2cd5a83c90a425f75de006716fc16841fac66935a648` |

## Round-5 gate closure results

### 1. Bounded search, ranking, pagination, and overflow — **BLOCKED (P1)**

The resource-safety direction is real. Both implementations use a
permission-aware `frappe.get_list`. Blank searches pass `page_length` and
`start` directly to bounded database pagination and do no Python ranking.
Text searches fetch no more than `RANK_WINDOW = 5000`, rank the collected
rows exact → prefix → substring with the identity/value tie-break, slice by
`start`/`page_length`, and the service formats only the page. The fresh 49-test
suite reproduced the genuine 1,001-filler case for both public paths and the
ordinary start/page behavior.

The advertised loud and accurate overflow contract is not implemented:

- `searchable_link_search` has no `with_meta` parameter and always returns a
  bare list (`search.py:11-25`, `137-162`, `167-201`). At more than 5,000
  matching rows it silently drops every row beyond the modified-desc window.
  An exact match outside that window can therefore disappear without any
  signal on the shipped dropdown path.
- `search_bilingual` defaults `with_meta=False` and returns the same bare list
  on that compatibility path (`bilingual_service.py:628`, `722-723`). Thus an
  ordinary public call is also silently truncated. Metadata is loud only for
  callers that already opt into a service-only response shape.
- Overflow detection is `len(rows) >= RANK_WINDOW` after fetching exactly
  `RANK_WINDOW` rows (`bilingual_service.py:673-682`). It reports
  `truncated: true` for exactly 5,000 matches even when no 5,001st row exists,
  and cannot prove overflow. Accurate detection requires a permission-aware
  `RANK_WINDOW + 1` probe or an equivalent existence/count mechanism, followed
  by ranking only the contracted window.
- The forced-window test patches the window to two and merely observes two or
  more existing matches (`test_bilingual_account_pilot.py:892-911`). It does
  not test the exact-boundary false positive, a real >5,000 set, either bare
  public compatibility response, dropdown metadata, or an exact match beyond
  5,000. The >1,000 test remains wholly inside the 5,000 window.

The 5,000-row bounded tradeoff may be acceptable in principle if it is an
explicitly specified product contract, but the current implementation does
not meet its own “never silent” or accurate-overflow claims. Complete global
ranking is intentionally no longer promised; exact matches beyond the window
remain omitted. That limitation must be exposed consistently through both
public APIs (including the actual dropdown consumer), with exact-boundary and
real-overflow regressions, before this gate closes.

### 2. Comparative P95 — **BLOCKED (P1; canonical gate failed)**

The protocol repairs several Round-5 defects. Source inspection and artifact
recalculation confirm five discarded warmups, 50 timed samples, alternating
pair order, nearest-rank P95, and a true even-sample median. The rounded raw
samples recompute exactly to:

| Measure | Baseline | Bilingual |
|---|---:|---:|
| P95 | `2.162 ms` | `2.646 ms` |
| Median | `1.411 ms` | `1.957 ms` |

The artifact records identical 12-row match sets, Frappe `16.18.1`, MariaDB
`10.11.14`, host `mohamed-OptiPlex-3080`, user `Administrator`, company
cardinality `94`, timestamp, and code hashes. All three recorded code hashes
match the current files. Cleanup says 12 removed with no `CT-T3-%` residue.
The permanent test really consumes the JSON, recomputes its statistics, and
would fail stale governed-code hashes.

It nevertheless fails the governing release criterion. Canonical §10.3 allows
at most 10% slowdown unless explicitly accepted. With the requested 15 ms
floor rejected, the limit is `2.162 * 1.10 = 2.3782 ms`; `2.646 ms` is
`22.39%` slower than baseline and exceeds that limit by `0.2678 ms`. Both the
artifact gate and permanent tests apply the rejected `+15 ms` exception
(`test_bilingual_account_pilot.py:987-1012`), so their green result is not a
canonical pass.

There is also no valid recorded per-side query-count comparison. The counter
is cumulative across the entire timed loop; after each two-call pair the code
appends that cumulative checkpoint to a list selected by which side ran first
(`bilingual_service.py:416-449`), then sums those checkpoints. The resulting
`1250` and `1300` values are order-grouped cumulative sums, not baseline and
bilingual SQL counts, so the claimed ~4% feature delta is unsupported.

Finally, the 94-Account/12-match pilot is useful smoke evidence but does not
establish a larger representative workload or a noise-derived tolerance. A
fresh approved representative baseline that passes 10%, or a separately
justified and explicitly approved exception, is required. On the decision
provided for this review, the performance gate is conclusively failed.

### 3. Handler dispatch and HTTP fixture lifecycle — **VERIFIED CLOSED**

The permanent test now sends `from_descendant: "1"` through
`frappe.handler.execute_cmd` on the overridden vendor method, in addition to
the reason-free refusal and reasoned success. The fresh 49-test run passed that
path. The wrapper forwards the handler-coerced value into the vendor method;
the returned identity remains server-resolved and the created Version/Comment
rows are cleaned by the test.

The README truthfully withdraws the unstable live-socket claim and limits
closure to the already accepted hermetic handler layer. `setup.out` and
`cleanup.out` are captured console outputs: setup created
`CT-HTTP-1 - CT HTTP Probe - E`, cleanup removed it, and cleanup records
`"leftover": []`. A fresh live DB lookup returned no `CT-HTTP-1%` Account.

### 4. Prior P0/P1 closures — **VERIFIED CLOSED**

Fresh pilot tests retained the prior Unicode/confinement, registry/schema
fail-closed, normalized-key, permission/scope, tree batching/identity,
localized browser adapter, governed rename/savepoint, vendor failure, and
native post-rename Version plus reason Comment closures. Hooks still register
the Account form/tree adapters, vendor endpoint override, and Account validate
policy. No regression was found in those previously accepted controls.

## Fresh reproduced evidence

- Fresh suites passed: `13 + 6 + 5 + 3 + 8 + 89 + 38 + 49 = 211`.
  Standalone localization plus pure registry ran as 127 tests (`89 + 38`), and
  the Bench pilot was `49/49`.
- Fresh full evidence-enabled localization gate reported catalog `803`, CSV
  `34`, extraction `257` files / `662` wrapped + `21` JSON / `0` missing, raw
  missing `0`, and `errors=0`. Fresh scoped gate and vendor audit also reported
  `errors=0`; scope lint, Translation-write lint, `git diff --check`, and
  staged diff-check passed. Governed PO/evidence/index checks are included in
  that evidence-enabled gate.
- Fresh read-only inventory SQL returned category totals
  `2,678 + 825 + 9,014 + 5,927 = 18,444`. The evidence-enabled gate bound it
  to the current inventory manifest and Merkle
  `61c0c12cd197a647ba751fd7854c34aab047d09de14e8b0d085bfff4a634d4f9`.
  Inventory-manifest SHA is
  `c2abb216d1821d1571561bd8d67a2f6b106e3662bf4889e22c9075a7111a68ae`.
- Current build evidence was inspected (`85516df81c035ce0ef3caddc382e355eaf4b9d54ff8111e4ebf78c4d15e1a426`),
  and the current Construction bundle exists under `sites/assets`.
- Before this report, worktree-status SHA was
  `3b249fdcc9c68ba125d4d5b63c4ed94f823e0d5626b6cf447f047bf4308233d5`,
  tracked binary-diff SHA was
  `1411683aa33d17dd28b00e8cf0ed3238a30fde98314efbf5cdcbd5631bd0bc81`,
  staged diff was empty SHA
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`,
  and HEAD remained `e7be48855`. No live Account name was migrated by this
  verifier.

## Decision and next gate

**BLOCKED — Stage 3 does not close, and Stage 4 must not begin.**

This is not a technical-verification pass blocked only by an owner decision.
The owner/consultant decision has been supplied: the 15 ms floor is rejected,
and the preserved measurement fails the canonical 10% gate. Independently,
the bounded-search remediation remains technically incomplete because
truncation is silent on the dropdown and default service paths and its
boundary detection is inaccurate. Handler coercion, HTTP residue cleanup,
the 211-test aggregate, localization/inventory evidence, and prior P0/P1
closures are green, but they do not override those two P1 failures.

The next candidate must expose an accurate truncation contract through both
actual public API/consumer paths with exact-5,000 and >5,000 regressions
(including an exact match outside the window), correct the query-count
instrumentation, and produce a representative comparative result that passes
the canonical 10% threshold unless the owner later explicitly approves a
well-supported alternative. Then request a fresh independent AI-R review.

Owner authorization remains required for commit, push, merge, deployment,
runtime/catalog mutation, or any live Account-name migration.
