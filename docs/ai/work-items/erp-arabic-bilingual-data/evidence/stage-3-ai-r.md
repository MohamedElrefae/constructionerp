# Stage 3 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 3 verifier |
| Session | `/root/stage3_ai_r` |
| Verified at | `2026-09-05T22:30:44Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; `e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, disposable test fixtures, and this report only. No implementation, catalog, payload, governed evidence, Git index/history, commit, push, merge, deployment, or Account-name migration. |

The Builder/proposer did not self-approve. I independently reviewed the
canonical v4 plan, handoff, implementation record, Stage 2 Round 19 approval,
Stage 3 builder record, current diff, registry, services, hooks, form/tree
JavaScript, searchable-dropdown integration, schema/audit patches, tests, and
the regenerated localization evidence.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record before review | `a54b49e5274e6c1c69aee6effe98037200686c09d00ec0016f7a5d373e37cf4e` |
| Stage 2 Round 19 | `3e83a3528fff02a206745df235fcfb5cc212d335129847e3144e0ab68347a880` |
| Stage 3 builder record | `2248a4098dde12ed6c0af4566875d39c525a5e1915d213ff63fbdf3988e7167c` |
| Registry | `a1e5cb207f1a2efa666692656ba690a3f531d948e623d53287c91a7a05279a62` |
| Pure registry / Frappe service | `b15d507a6fa1e63debcb6e807655e0a9e640567b41f92c308bb3f24886f77dfa` / `58c94e8440151cfeb36786e9932a09330e189a81612a2227bda34383f556dbd8` |
| Account form / tree JS | `d20d3e51d5008e189a7769c664f77825528b8f27af98c4e35c456f68fdf07b19` / `9f3f1d62298b845c995f095be398f7576384c1471d1438703c31e6f2b54eabd6` |
| Pure / Bench pilot tests | `d26f64bc19d9fd6181d013dd0bc316ae931e270899a68047e2230852a14663c9` / `08fcc5e2131af3b85a6e810548c0b6cf5c01d9b37a57a45ad4eddece2a819cba` |
| Account track-changes patch | `34842a918fc6129088a31df650c3af0250e7b8c2b9bff1e7ba99f88aaf499c7b` |
| Governed Stage 2/3 index | `2b9fc408a098784a66db7f3eb8f16a07798d7adc726129a2ce4e7231079f303f` |

## Reproduced positive evidence

- All eight modules passed freshly: **169 = 13 + 6 + 5 + 3 + 8 + 89 + 25 + 20**, failed `0`.
- The ordinary evidence-enabled localization checker passed: Construction
  catalog `780`, files `255`, wrapped `640`, JSON labels `21`, missing `0`, raw
  missing `0`, errors `0`. Scope lint, translation-write lint, and
  `git diff --check` also passed.
- A fresh read-only DB serialization reproduced **18,421** rows and Merkle root
  `93ae1f99414db01e5c28d1f682861df5fdbe3604070387ea8800ec2cc1608177`,
  matching the manifest and governed envelope.
- Live metadata confirms the physical Account, Item, Customer, and Supplier
  Arabic fields and `Account.track_changes = 1`.
- `FormMeta("Account")` contains both Construction markers. The resolved files
  are `/home/mohamed/frappe-bench/apps/construction/construction/public/js/bilingual/account_form.js`
  and `account_tree.js`; therefore the new Account paths do load. The unrelated
  legacy `doctype_js` path defect does not prevent these two pilot hooks from
  loading.
- The tree wrapper preserves `value` identity, uses the vendor permission-aware
  children query plus one batched label query, and HTML-escapes the selected
  localized label. No vendor source was edited.
- Before this report, tracked binary diff SHA-256 was
  `30bb62102e00ce2a84a2d3dcdce84811bc87fef48aa576d9678701f4fd05cba4`;
  staged diff was empty (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
  Test execution left repository status unchanged. Build/MO compilation was
  not repeated because those commands write generated files; their governed
  successful captures were inspected instead.

## Blocking findings

### P0 — Unicode safety contradicts the locked canonical policy

Canonical C1 requires rejection of U+202A–U+202E, U+2066–U+2069, U+200E,
U+200F, and U+061C in stored Arabic values. The implementation deliberately
allows U+200E/U+200F/U+061C and, because its regular expression only covers
C0/C1/DEL, also accepts every tested embedding/override/isolate character
U+202A, U+202E, U+2066, and U+2069. Fresh direct calls returned `True` for all
seven tested code points. The permanent tests assert the opposite policy for
three of them. This permits invisible direction-control content in stored
identity data and must be corrected to the canonical rule (or the canonical
plan must be explicitly revised and re-approved).

### P0 — Arabic edits are not confined to the controlled server API

`account_name_ar` remains an ordinary visible, writable permlevel-0 field, and
the Account form override does not make it read-only. Any user with ordinary
Account write permission can therefore save the field through the standard
form/REST document path, bypassing `set_account_name_ar`, its Unicode policy,
and its intended controlled workflow. The implementation uses the broad
existing `Accounts User` role rather than the canonical narrow bilingual-data
permission/permlevel design. Tests exercise only the helper API and do not test
the direct form-save/REST bypass. This fails canonical E3's explicit
server-enforcement requirement.

### P0 — Required rename reason is neither enforced nor atomic

The UI first invokes ERPNext's independently whitelisted
`update_account_number`, then makes a second call to record a Comment. The
standard endpoint remains callable without any reason, and failure of the
second call leaves a completed rename without required rationale. In the
actual client code the second call uses the pre-rename `frm.doc.name`; ERPNext
can rename the Account, and the test itself has to re-resolve the new name
before adding the Comment. Consequently the shipped UI can rename successfully
and then fail to attach the reason. The test proves only a manually sequenced
happy path, not the shipped flow. Provide one permission-checked Construction
endpoint that requires the reason, delegates to the standard ERPNext function,
resolves the resulting identity, records the audit evidence, and fails/rolls
back as one transaction while preserving ERPNext validations.

### P1 — Active registry mappings fail open on schema mismatch

Canonical C1 requires live-schema validation and an error for an `active`
mapping mismatch, while only `planned` entries may degrade safely. A fresh
mocked live-meta check removed `Item.item_name_ar`; `get_mapping("Item")`
returned the active mapping with `arabic_field: None` instead of raising or
reporting unhealthy. `schema_installed` is treated the same way. This can
silently remove bilingual search/display after schema drift and is not covered
by the six structural JSON-negative tests.

### P1 — Required Arabic search normalization is absent

Both bilingual search paths send the trimmed user text directly to SQL `LIKE`.
There is no server-side Alef-variant, Tatweel, or optional-diacritic
normalization/derived search key, despite canonical C3 and the automated test
plan explicitly requiring it. Current tests cover only exact Arabic text.

### P1 — New visible form strings bypass localization governance

The form injects many raw visible English literals (`English`, `Arabic`,
`Edit Arabic`, `Preview`, `Completeness`, prompt labels/titles, and success
messages) without `__()`. The builder statement that no raw user-facing sinks
were introduced is factually incorrect. The current extractor/gate reports
zero missing because it does not recognize these HTML-array and widget-option
sinks. Canonical F1 requires every new visible source string to be wrapped and
extracted before the feature is localization-complete; postponing these pilot
strings to later waves is not an approved exception in v4.

### P1 — The claimed test envelope is incomplete for the pilot gate

The 45 tests are green but do not execute the form/tree JavaScript in a browser
or assert the shipped rename sequence, DOM escaping/XSS, RTL rendering, no
internal-name append, direct-save/REST permission bypass, concurrent stale
Arabic edits, active-schema failure, normalized Arabic search, duplicate/root/
busy-ledger rename failures, or measured P95 versus an approved baseline. The
Version test separately performs a direct save with `frappe.in_test = False`;
it does not prove that the service call itself emitted the claimed Version.
The v9.0 patch is exercised in state but has no dedicated idempotency/reversal
test, and no reversible implementation accompanies the documented manual DB
instruction.

## Decision

**BLOCKED — Stage 3 is not independently verified and does not close. Stage 4
must not begin.**

The positive runtime and localization evidence is truthful, and the Account
hook path concern is resolved in favor of the builder. It does not outweigh
the three P0 contract failures and four P1 coverage/behavior failures above.

## Exact next gate

Correct the locked Unicode policy, enforce Arabic-field writes server-side,
replace the two-call rename flow with an atomic reason-required wrapper, make
active/schema-installed registry validation fail closed as specified, implement
server-authoritative Arabic normalization, wrap and inventory all new visible
strings, and add meaningful regression/browser/security tests for these paths.
Regenerate all governed evidence from the corrected candidate, then request a
fresh independent AI-R Stage 3 verification. No live Account-name migration is
authorized. Owner authorization remains mandatory for commit, push, merge,
deployment, credentials, or any production/runtime mutation.
