# Stage 3 — Independent AI-R Re-verification, Round 3

## Identity, candidate, and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 3 remediation verifier |
| Session | `/root/stage3_ai_r_round3` |
| Verified at | 2026-09-09 (Africa/Cairo) |
| Candidate | `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted working tree |
| Boundary | Read-only repository/site checks, disposable test fixtures/transactions, current build, and this new report only. No implementation, catalog/payload/evidence rewrite, Git index/history change, commit, push, merge, deployment, runtime Translation mutation, or live Account-name migration. |

This is a fresh review of the current Round-3 candidate, not a reuse of the
Round-2 verdict or its SHA `e56cc83b…`. I read `AGENTS.md`, canonical plan v4,
the handoff, current implementation record through deviation row 37, both
earlier Stage-3 AI-R reports, the complete current builder record, current
diff/code/hooks/patches/tests, governed localization evidence, and all nine
browser artifacts. The Builder did not approve its own work.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before this review | `f95d7006ab7d2372640a9dae02202da29c834eb58f0eed5c1a0896477ce6eced` |
| Original / Round-2 AI-R | `f7e1b8263081ea94e9fcdf945cb67cdd02853600ff073a690bd3ff132f5d642b` / `e56cc83b244f3e11617150639665ddd9b60ef4fe2cbdabc7a9107e2c6aad494b` |
| Current Stage-3 builder record | `2796da9f6d598dc229db72d91198c7648af20b3191632c9a3cbf08ca721e8517` |
| Registry | `9cb10f5a0dd125ebb3b0103f3a6c67b1889a24aab27e145cbd5d5257938f44a4` |
| Pure registry / Frappe service | `691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538` / `be66d2a6fc8d33952fba6f957edc8829ec4f00f2ffdd53270d33e4403eb98290` |
| Account form / tree / browser test | `7c6740056c5e26ab754e2cf9fc64801c556786872867c7493c11bc699257650f` / `9f3f1d62298b845c995f095be398f7576384c1471d1438703c31e6f2b54eabd6` / `5e8ad8472aa3e87400cd75fe3c873f903b20eebf2473017f08d74672174b6d3c` |
| Dropdown search | `f2fa443ccc17262b681f618906ee4e5dc28b5dca5d3a3603c7f5af114fe5f43a` |
| Pure / Bench pilot tests | `060adbb51e0838ab2a5033c6775242dddb164c8c5793247a830828696e52f248` / `5f52e8e49f1138ba843dd6354a743852efb8ec46f984d3588d7a365c5440389e` |
| v9.0 / v9.1 patches | `fbcd2092bd7c99af43cf2b208a9c638d9392e518f9be08833f662483bcd97810` / `2c3a2dfd99f9fffae6d857f8ad809a8272c2ba4a27b8333c4f91d265cd7423ae` |
| Inventory manifest / governed index | `9bc44f3d99ae39ddfd429a12cd5bb84d405fea6b45f1c33b7dff16d17e2aa1fc` / `88ba71e19fc28f19f937818799b42576cd825718b2fb0316fe0aeebd30fd8e15` |

## Prior findings against the current candidate

| Finding | Result | Independent basis |
|---|---|---|
| Insert confinement and Unicode validation | **VERIFIED CLOSED** | `Account.validate` validates every non-null stored value and rejects every Arabic-bearing insert, including `ignore_permissions`; fresh insert test passed. Pure policy rejects all 12 required bidi code points plus C0/C1/DEL. |
| Form/REST/Admin bypass | **VERIFIED CLOSED** | Field is read-only; server hook compares the stored value and refuses direct writer and Administrator saves. This applies to normal document-save/REST paths. |
| Operation-context spoof/leak | **VERIFIED CLOSED within exposed boundary** | Token binds doctype/name/stored-old/intended-new and is cleared in `finally`; mis-aimed token test passed. No client payload can set `frappe.flags`. Residual: an in-process privileged caller can mutate flags, as with any internal trust boundary. |
| Rename transaction ownership | **VERIFIED CLOSED** | Scoped savepoint; no success commit; only rollback-to-savepoint on failure. Fresh tests proved unrelated caller work survives rename failure and remains uncommitted after success, while audit failure restores rename. |
| Reason and standard rename path | **VERIFIED CLOSED** | Nonblank reason plus narrative Unicode policy enforced; standard ERPNext `update_account_number` is delegated to, preserving `_ensure_idle_system`, number, ancestry, descendant, rename, and link validations. Duplicate-number rollback and `from_descendant=True` passed. Busy-ledger cannot execute under the test runner because vendor `_ensure_idle_system` returns while `frappe.in_test`; protected-root was not directly exercised. |
| Registry error propagation | **VERIFIED CLOSED** | Only `ImportError` degrades around registry import. `frappe.ValidationError` from active/schema-installed drift propagates through the dropdown; fresh test passed. Planned mappings alone degrade. |
| Normalized-key invariant and patches | **VERIFIED CLOSED for document saves** | Hook derives the key on insert and every save, overwriting forged/stale/null values; governed update and unchanged-save tests passed. v9.1 backfill is deterministic and v9.0/v9.1 idempotency/reversal tests passed in correct patch order. Direct SQL remains outside document-hook guarantees and is an operational residual. |
| Arabic normalization/search/permission | **VERIFIED CLOSED except global ranking, below** | Alef variants, tatweel and diacritics normalize server-side; bare↔diacritized integration tests passed both directions. Each search path uses one permission-aware `frappe.get_list`; no N+1 and denied-user behavior passed. |
| Visible strings and hooks | **VERIFIED** | Account form visible literals are `__()` wrapped and cataloged. Current gate reports catalog `803`, extraction `257` files / `662` wrapped / `21` JSON / `0` missing. Hook paths resolve. Form values use `.text()`; tree uses `escape_html`, preserves `value`, and does not append internal identity. |
| Browser execution | **VERIFIED with documented limitation** | Exactly nine artifacts exist. JSON sessions ran 2026-09-05 23:17:28–23:17:51Z (ar) and 23:18:06–23:18:29Z (en); server log records live `/app/account/...`, shipped metadata/form endpoint, and governed tree endpoint requests. Four screenshots visually agree; JSON reports 83 tree labels, Arabic probe label only in Arabic, English label only in English, escaping and form section checks green. The tree was instantiated from shipped settings on an Account form because the real tree page hit the documented pre-existing sidebar boot race; therefore this is loaded-code integration evidence, not a full navigation/UAT proof. |

## Reproduced current evidence

- Fresh standalone runs: **89/89** localization gates and **38/38** pure
  registry tests, both green.
- Fresh Bench runs: **13 + 6 + 5 + 3 + 8 + 89 + 38 + 45 = 207**, zero
  failures. The first pilot attempt failed before tests because Redis was not
  running; after starting the normal Bench services the full 45-test module
  passed, fixtures cleaned up, and the temporary services were stopped.
- Fresh ordinary evidence-enabled localization gate: catalog `803`, CSV `34`,
  extraction `257 / 662 + 21 / 0 missing`, raw missing `0`, `errors=0`.
  Vendor audit `errors=0`; scope lint, translation-write lint and
  `git diff --check` passed. The permanent scoped envelope also reports
  `errors=0`.
- Live read-only DB recomputation returned exactly **18,444** Arabic Translation
  rows and Merkle
  `61c0c12cd197a647ba751fd7854c34aab047d09de14e8b0d085bfff4a634d4f9`,
  matching the manifest/envelope.
- Fresh `bench build --app construction` exited zero, produced the same bundle
  `construction.bundle.2XKAHIYO.js`, and compiled the Construction Arabic MO.
  Vendor PO files were not modified.
- Before this report, tracked binary-diff SHA was
  `b500c296cd09b7f9147b39765f16cf10f18cd4d905eb9eefe0b0d0238c40f8cf`;
  staged diff SHA was the empty SHA
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
  No live Account-name migration occurred and HEAD stayed `e7be48855`.

## Material open findings

### P1 — Relevance ranking is applied after pagination, so ranking and pagination are not composable

Both `search_bilingual` and `searchable_link_search` ask the database for only
the requested page ordered by `modified desc`, then compute and sort relevance
in Python. An exact match outside that database slice cannot outrank a prefix
or substring inside it; page boundaries describe modification order, not the
advertised exact → prefix → substring order. The new tests prove only that
offsets are disjoint and that sorting occurs within a fetched page. They do
not prove deterministic relevance-ranked pagination over the full matching
set. This leaves the explicit Round-2 pagination/ranking closure incomplete.

### P1 — The comparative P95 gate is not a meaningful before/after baseline

`test_comparative_p95_against_plain_baseline` labels
`searchable_link_search` as “plain”, but that function is already the current
bilingual registry-union/normalization implementation. It compares `txt="CT"`
against the dropdown with `txt=TEST_AR_BARE` against the second service, while
the fixture is assigned a different Arabic value (`TEST_AR`), so result
cardinality/selectivity and formatting work are not equivalent. It runs only
15 sequential warm samples, has no pre-feature implementation or query-count
baseline, and neither the test nor preserved evidence records the two measured
P95 values despite the builder record saying both are recorded. Passing
`bilingual <= baseline*1.10+15ms` under these different workloads does not
establish the canonical no-more-than-10% regression gate reproducibly.

### P1 — HTTP override and rename audit claims exceed their evidence

The dispatch test invokes `frappe.override_whitelisted_method()` and calls the
resolved Python function directly. It does not issue an HTTP request to the
vendor method path, so request argument coercion and handler dispatch remain
unproved. In addition, the production-path Version assertion covers only
`set_account_name_ar`; the governed rename test verifies its required Comment
but never proves a Version on the post-rename identity. Frappe's rename code
renames pre-existing Version references and adds an Edit Comment; it does not
by itself create the claimed `Version(rename)`. The returned audit string
`Version(rename)+Comment(reason)` is therefore not substantiated by the
current test/evidence. The reason Comment itself and post-rename reference
identity are verified.

## Decision

**BLOCKED — Stage 3 does not close, and Stage 4 must not begin.**

Round 3 genuinely closes both Round-2 P0 defects and the registry,
normalized-key, Unicode, browser-artifact, localization, single-query,
permission, and basic pagination wiring gaps. It does not close globally
relevance-ranked pagination, the canonical comparative performance gate, or
the claimed HTTP/rename-Version evidence. Correct the behavior/evidence and
request a fresh independent verification against new hashes and counts.

Owner authorization remains required for commit, push, merge, deployment,
runtime/catalog mutation, or any live Account-name migration.
