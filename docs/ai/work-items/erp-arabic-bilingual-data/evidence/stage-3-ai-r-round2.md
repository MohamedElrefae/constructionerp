# Stage 3 — Independent AI-R Re-verification, Round 2

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 3 remediation verifier |
| Session | `/root/stage3_ai_r_round2` |
| Verified at | 2026-09-06 (Africa/Cairo) |
| Candidate | `feature/erp-arabic-bilingual-data`; `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, disposable transactional tests, and this report only. No implementation, catalog, payload, governed evidence, Git index/history, commit, push, merge, deployment, or Account-name migration. |

The Builder did not self-approve. I independently reviewed the repository
instructions, canonical v4 plan, build handoff, implementation record through
deviation row 35, the original Stage 3 AI-R report, the Round 2 builder record,
the current diff, registry, services, hooks, patches, form/tree/search code,
tests, and the governed localization evidence.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `70c68528a2db791179c6c291fc06a418f794c1f4c62b0073d6f16d0e8442bafe` |
| Original Stage 3 AI-R | `f7e1b8263081ea94e9fcdf945cb67cdd02853600ff073a690bd3ff132f5d642b` |
| Round 2 builder record | `52fe40a0a6625cd4e7f07bdfcb6141caa3879137c6168855523c4fb1c2ec2ee8` |
| Registry | `9cb10f5a0dd125ebb3b0103f3a6c67b1889a24aab27e145cbd5d5257938f44a4` |
| Pure registry / Frappe service | `ab7abc431c899a3c271d184e8391cb269638b243f669531d7d536ecdeb6153e1` / `cd09d74aad7069bbc22a2cc4efe0052cc326fc809375964b1f61edc697231c5f` |
| Account form / tree / manual browser script | `7c6740056c5e26ab754e2cf9fc64801c556786872867c7493c11bc699257650f` / `9f3f1d62298b845c995f095be398f7576384c1471d1438703c31e6f2b54eabd6` / `574a0c4dca942a925160d7d5146a9948e957352b183bcb70a92adf585ac99c5d` |
| Pure / Bench pilot tests | `c65485552a01f844a1fba36d8b02ed82fb783a6f48f96aea7cf90e3d668b5459` / `8f96466058af4f615345d45269eb4212987a6ba79248835d8eafdccf8fe600f3` |
| v9.0 / v9.1 patches | `fbcd2092bd7c99af43cf2b208a9c638d9392e518f9be08833f662483bcd97810` / `2c3a2dfd99f9fffae6d857f8ad809a8272c2ba4a27b8333c4f91d265cd7423ae` |
| Governed Stage 2/3 index | `59173a6255e2b5444000b51989cbee41febd924dc621a5ecf91f98317092f561` |

## Reproduced positive evidence

- Fresh standalone suites passed: **89/89** localization-gate tests and
  **34/34** pure bilingual tests.
- Fresh Bench runs passed all six site modules: **13 + 6 + 5 + 3 + 8 + 33**.
  Together with the two standalone suites this independently reproduces the
  advertised **191 = 13 + 6 + 5 + 3 + 8 + 89 + 34 + 33**, failed `0`.
- The ordinary evidence-enabled checker passed and reported catalog `802`,
  files `257`, wrapped `661`, JSON labels `21`, missing `0`, raw missing `0`,
  errors `0`. Scope lint, translation-write lint, and `git diff --check`
  passed.
- The governed evidence set is internally bound and reports 18,443 inventory
  rows with Merkle root
  `d495093e50f1453e14a951e24502e33409e6ea5d4ee5704edd3a8dbc17a0d1d4`.
  The live database count is independently 18,443 with app totals
  `<untagged>=2678`, `construction=824`, `erpnext=9014`, `frappe=5927`.
- The pure identity policy rejects all twelve locked bidi code points. The
  separate narrative policy accepts only LRM/RLM/ALM among those controls and
  rejects C0/C1/DEL and embedding/override/isolate controls.
- Existing-document direct saves are rejected for the ordinary writer and
  Administrator, `account_name_ar` is read-only, the two Account hooks resolve,
  the tree renderer escapes labels and does not append the internal identity,
  and the governed happy-path rename resolves and comments on the post-rename
  identity. Native Version emission through the governed Arabic service path
  is exercised with test suppression disabled.
- Before review, tracked binary diff SHA-256 was
  `422beb1ed16244684cb4a7c580679cf52d64fbecd3f88a6442688e20fb73825c`;
  staged diff was empty
  (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
  Test fixtures were removed. No live Account-name migration was performed.

## Blocking findings

### P0 — New Account insertion bypasses both confinement and canonical Unicode validation

`enforce_account_arabic_policy` returns immediately for every new Account
after optionally deriving `account_name_ar_norm` (`bilingual_service.py:185-188`).
It neither refuses a client/form/REST-supplied `account_name_ar` nor calls the
canonical identity validator. Therefore a user permitted to create Account can
insert an Arabic value outside the governed API, including any of the twelve
forbidden bidi controls. The tests cover updates to existing records only
(`test_bilingual_account_pilot.py:302-321`). This leaves the prior P0
server-side confinement and stored-value Unicode requirements open.

The request-global `frappe.flags.ct_governed_arabic_edit` is not directly
forgeable through a document payload, so I did not reproduce the specific
client flag-spoof concern. That does not close the insertion bypass. The flag
also grants the whole save/hook chain a broad bypass rather than binding the
authorization to the exact document, expected old value, and intended new
value.

### P0 — The rename endpoint owns the caller's whole transaction

`governed_rename_account` unconditionally commits on success and rolls back the
entire connection transaction on failure (`bilingual_service.py:314-321`). A
whitelisted Frappe request already has framework-managed transaction
boundaries. If this function is called after any other in-transaction work, a
successful rename makes that unrelated work irrevocable; a Comment failure
rolls unrelated work back. A caller cannot compose the service atomically with
larger governed operations. The rollback test explicitly commits all prior
work to accommodate this behavior (`test_bilingual_account_pilot.py:414-438`),
so it proves rename rollback in isolation but does not prove safe transaction
ownership. Atomicity must use the request transaction or a scoped savepoint,
without committing/rolling back unrelated caller work.

## Other material findings

### P1 — Fail-closed registry behavior is discarded by the dropdown path

The core `get_mapping` now raises for active/schema-installed schema drift, but
`searchable_link_search` catches every exception from it and silently sets
`mapping = None` (`search.py:102-107`). Thus an active mapping mismatch still
degrades silently in one shipped search path, precisely the fail-open behavior
the remediation says was removed. Its later generic exception handler also
logs and returns `[]` (`search.py:160-164`). No regression test covers this
path.

### P1 — The normalized key is not invariant on all document write paths

For existing records, the validate hook recomputes `account_name_ar_norm` only
under the broad governed flag or when the key is `None`
(`bilingual_service.py:197-201`). A submitted non-null stale or forged derived
key is retained when the Arabic value is unchanged. New records likewise keep
any caller-supplied non-null normalized key. Consequently the server does not
enforce `account_name_ar_norm == normalize_arabic(account_name_ar)` on every
document save, and search correctness can be suppressed or poisoned. The v9.1
backfill corrects existing rows once, but it does not establish the ongoing
invariant.

### P1 — Claimed browser, rename-failure, pagination/ranking, and performance closure is incomplete

- There is a manual browser script but no execution record, screenshot, DOM
  capture, browser/session identity, or result artifact for either language.
  Moreover its `check` helper coerces a documented skip (`null`) to `false`, so
  skips are counted as failures (`account_bilingual_browser_tests.js:23-33,
  76-126`). This is not a completed browser regression.
- Permanent tests do not exercise duplicate-number, protected-root, or
  busy-ledger failures requested by the canonical Account pilot plan and prior
  AI-R gate. The hook-map assertion proves registration, not an HTTP dispatch
  through the overridden vendor method, reason enforcement at that route, or
  signature compatibility with vendor's `from_descendant` argument.
- The searchable-dropdown query accepts `start` but never passes
  `limit_start=start` (`search.py:135-143`), and neither search implementation
  has relevance ranking; ordering is only `modified desc`. Pagination/ranking
  parity is therefore not established.
- The performance test compares twenty calls only to a self-described
  “generous” absolute 250 ms ceiling (`test_bilingual_account_pilot.py:632-644`).
  It has no approved pre-feature baseline and cannot prove the canonical P95
  requirement of no more than 10% regression.

## Decision

**BLOCKED — Stage 3 remains open. Stage 4 must not begin.**

Round 2 closes the pure Unicode-policy defect, existing-record direct-save
bypass, reason-required one-call UI flow, post-rename identity resolution,
happy-path Comment/Version audit, core registry validation, basic Arabic
normalization matching, visible-string wrapping, and the advertised green test
and localization evidence. It does not close the two P0 defects or the material
P1 behavior/evidence gaps above.

## Exact next gate

Reject or govern `account_name_ar` on Account insertion and validate every
stored Arabic value server-side; bind any bypass to the exact server operation
rather than a broad mutable request flag. Remove service-level full
commit/rollback ownership and prove scoped atomicity without affecting caller
work. Propagate registry schema failures through every shipped search path,
enforce the normalized-key invariant on every document save, and add permanent
tests for the insertion path, forged/stale normalized keys, real overridden
endpoint dispatch, vendor failure classes, pagination/ranking, and an approved
before/after P95 baseline. Execute and preserve genuine Arabic and English
browser evidence for the loaded form/tree behavior. Regenerate governed
evidence and request another fresh independent AI-R verification.

Owner authorization remains mandatory for commit, push, merge, deployment,
runtime mutation, or Account-name migration.
