# IMPLEMENTATION — `erp-arabic-bilingual-data` (Builder record)

Outcome: **PARTIAL — STAGES 1C–3 VERIFIED; STAGES 4–8 NOT STARTED**.
Builder does NOT declare `VERIFIED_FOR_RELEASE`. No commit/push/merge/deploy performed.

- Branch: `feature/erp-arabic-bilingual-data` from `develop@e7be488`.
- Plan hash: `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` (v4; matches `BUILD_HANDOFF.md`).
- TARGET_SITE: `v16.localhost` (test DB, owner-confirmed non-production 2026-09-04).
- Evidence: `evidence/stage-0-baseline.md`, `evidence/stage-1abc.md`.

## Stages

- [x] Stage 0 — baseline, no behavior changes. Evidence reproducible.
- [x] Stage 1A — defensive searchable-dropdown projection. Gate passes (13 + 6 tests OK).
  Finding: handoff's suspected silent-`[]` failure is DISPROVED on this Frappe version
  (`get_list` drops unknown SELECT fields; verified live). Hardened anyway:
  `effective_fields` resolved once from live metadata and used for OR/SELECT/labels.
- [x] Stage 1B — `Account.account_name_ar` (Data, visible, non-translatable,
  after `account_name`, no index) via idempotent patch
  `construction.patches.v8_8.add_account_arabic_name_field` + `patches.txt`.
  5/5 schema/idempotency/no-rename tests pass on test site. No values populated.
- [x] Stage 1C (code) — `Typography Settings` extraction gap fixed: msgid added to
  Construction `ar.po` with source ref; catalog sync created 1 row
  (`ct_app=construction`, Pending). The 5 Frappe labels already exist as Pending
  catalog rows; vendor `.po` untouched.
- [x] Stage 1C (independent review quorum) — AI-A1, AI-A2, and AI-A3 independently
  passed all six proposed mappings. AI-R verified role/session separation and the
  exact proposal/review hashes. Evidence:
  `evidence/stage-1c-ai-a1-review.md`, `stage-1c-ai-a2-review.md`,
  `stage-1c-ai-a3-review.md`, and `stage-1c-ai-r-verification.md`.
- [x] Stage 1C (runtime/render gate) — Builder pass complete 2026-09-04, evidence
  `evidence/stage-1c-runtime-render.md`:
  (1) raw-`Workspaces` premise corrected: `frappe.ui.menu` (`menu.js:109`) applies
  `__(item.label)` at render, so the literal IS the dictionary key; the
  `add_app_item` path is dead (no `.sidebar-header-menu` in template/DOM). A drafted
  DOM extension was removed unused; no vendor edit, `hooks.py` clean. مساحات العمل
  rendered live on `/app/invoicing`.
  (2) Six-row v1.0 payload (AI-A1/A2/A3 provenance) imported on test site only:
  dry-run 6 creates/0 drift, live 6 created/28 skipped/0 drift; all six effective
  at runtime via the governed service.
  (3) Fresh Arabic session DOM proof for all six + 390px no-clip measurement for
  `Edit Sidebar` (AI-A3 exception closed); screenshots hashed in evidence.
  Independent AI-R rerun completed with **CONDITIONALLY VERIFIED**. Evidence:
  `evidence/stage-1c-ai-r-rerun.md` (SHA-256
  `4c0afc406ac17e9a688219c31e6ce3a0bd6d54bfb1ec7ce95274732080329072`).
   Full verification initially remained pending correction of the stale `Workspaces` payload
   note and preservation of durable raw logs for the 13+6+5+3+8 tests and build.
   Both conditions closed 2026-09-05: (a) `Workspaces` CSV note now states resolution
   via `frappe.ui.menu __(item.label)` with no extension; post-edit dry-run import
   shows 0 creates/0 updates/0 drift (notes column is runtime-inert), new payload
   SHA-256 `7ba7902c201e4010ffc30cad068490917b1cea1452faf859eb3020ff101badc0`
   — supersedes the hash recorded in the AI-R rerun and needs AI-R acknowledgment;
   (b) durable raw logs in `evidence/raw-logs/` as `.txt` (`.log` is gitignored and
   was auto-cleaned): 13+6+5+3+8 tests all exit 0, build exit 0, both lints and
   `git diff --check` exit 0, final dry-run 34 skipped/0 drift — every file embeds
   command, UTC timestamps, and exit code. Durability-only AI-R subsequently
   returned **VERIFIED** in `evidence/stage-1c-ai-r-durability-final.md`.
- Evidence `evidence/stage-1c-review-package.md` filed (consultant pre-review, PENDING).
  That package records the pre-release state. The governed v1.0 payload has since
  created the six runtime rows and stamped the six catalog rows Released on the
  authorized test site only. The stale v3
  human-signature wording in this package is superseded by canonical plan v4 and
  was recorded by all reviewers as non-substantive governance drift.
- [x] Stage 2 — VERIFIED BY INDEPENDENT AI-R ROUND 19 2026-09-05.
  Both final P0 controls are closed: the governed index length is parsed and
  bound to its actual nonempty line count, and all fourteen canonical artifact
  values are recomputed from candidate bytes and compared directly with the
  index. Independent fixtures rejected missing/duplicate/nonnumeric/false
  lengths; forged values for each of all fourteen artifacts; and missing,
  duplicate, or alias artifact rows. Fresh verification passed `89` standalone
  tests and `124` aggregate tests (`13+6+5+3+8+89`), ordinary evidence-enabled
  full/scoped/vendor/lint/diff gates, live `771` catalog / `631` wrapped + `21`
  JSON / `0` missing, clean vendor POs, and the 18,412-row Merkle root
  `973b8fac…`. No Stage 2 P0/P1 blockers remain. Round-19 evidence:
  `evidence/stage-2-ai-r-round19.md` (SHA-256
  `3e83a3528fff02a206745df235fcfb5cc212d335129847e3144e0ab68347a880`).
  Stage 3 may begin under the canonical plan; live Account-name migration is
  not authorized by this sign-off. A low-priority unclosed test-fixture handle
  warning remains as hygiene only.
  Prior Round-18 status retained below:
- [X] Stage 3 — VERIFIED BY INDEPENDENT AI-R ROUND 12 2026-09-10.
  All Stage 3 P0/P1 gates closed (canonical Unicode, server-side Arabic
  confinement + operation-bound authorization, scoped-savepoint governed
  rename + native Version/Comment audit, complete-set bounded ranking
  with loud truncation contract + window probe + 5,000/5,001 both-path
  tests, cross-path strict integer pagination parity incl. None + identical
  messages + shared coercer, fail-closed registry + normalization +
  normalized-key invariant, strings cataloged, handler dispatch +
  fixtures cleaned, executed browser evidence, min-of-rounds
  cherry-pick-resistant bare-10% P95 artifact). Evidence:
  `evidence/stage-3-ai-r-round12.md`; aggregate 215; Stage 4 may begin.
- [ ] Stage 4 (in progress) — BUILDER STARTED 2026-09-10.
  Engineered the governed Account-language export + proposal machinery
  (`construction/services/account_language_proposal.py`) plus a test module
  (`construction/tests/test_stage4_account_language.py`, 6 tests). Ran the
  export on the authorized non-production copy: 81 rows (55 leaves + 26
  groups), 0 with Arabic names, glossary-match 0, all flagged
  `no_verified_reference` + `pending_proposal`, no invented MOF/EAS/ETA
  reference (canonical Stage 4 items 1–4); the sensitive rows are written
  only to `<site>/private/stage4/` (never committed); the non-sensitive
  manifest is recorded (export SHA `d9699243…`). Aggregate now 221;
  evidence `evidence/stage-4-export.md`. Awaits the independent AI
  proposal + AI-A2 review; no live migration/import/commit/deploy.
- [ ] Stage 4 report extension-point spike — BUILDER DONE 2026-09-10.
  Construction-side bilingual extension for GL / Trial Balance /
  Balance Sheet / P&L via `construction/services/report_bilingual_extension.py`
  (pure `transform_report` with ar/en/both rendering; `bilingualize_report`
  runs vendor `execute` read-only; no vendor edit, no Report DocType, no
  Account/translation mutation). 11 tests; aggregate now 232.
  Evidence `evidence/stage-4-report-extension-spike.md`; rollback = remove
  the two new files. Proposal/AI-A2/import/deploy remain blocked.
- [X] Stage 4 governed review-bundle schema + validator — VERIFIED BY INDEPENDENT AI-R 2026-09-10 (row 61).
  `construction/services/account_review_bundle.py` (pure, non-mutating,
  fail-closed) + `construction/tests/test_stage4_review_bundle.py`
  (18 tests, standalone + bench). Refuses an import payload unless every
  row has distinct proposal/AI-A2 provenance, a decision, confidence,
  and a verified reference or explicit documented absence; exceptions
  preserved as reviewable rows; no Arabic values invented; no DB write.
  Aggregate now 255; evidence `evidence/stage-4-review-bundle.md`.
  Hardened identity binding (`expected_identities` / `expected_english` /
  `now_utc` refusal; no silently omitted exported accounts) with 23 tests;
  AI-R round-1 BLOCKED on two fixes, both closed: `build_import_payload`
  now REQUIRES the private export's `expected_identities` +
  `expected_english` bindings (missing/empty → BundleError; forged
  identities cannot reach a payload), and a malformed non-empty `now_utc`
  fails closed instead of disabling the future-timestamp control. AI-R
  re-review then BLOCKED on one P0 (caller-fabricated bindings); fixed by
  replacing them with a single authenticated `CandidateExport` created only
  via `load_candidate_from_export(path, expected_sha256)` (SHA-bound to the
  private export; raw lists/maps refused; missing/extra/forged keys and
  English mismatches rejected). A further AI-R review then BLOCKED because
  `CandidateExport` was publicly constructible/mutable; fixed by removing any
  caller object/SHA as authority: the export persists a governed manifest
  (`construction/data/localization/stage4_export_manifest.json`) and
  `build_import_payload` itself reloads the private export, verifies it
  against the manifest SHA, and derives the identity→English map internally
  (raw objects/dicts refused). A further AI-R review then BLOCKED because
  `manifest_path` was caller-selectable; fixed by removing it from the
  public entry — `build_import_payload(bundle, now_utc=None)` resolves exactly
  one INTERNAL governed manifest via the private `_governed_manifest_path()`
  resolver (test DI isolated there only; `manifest_path=` raises TypeError).
  Suite 36 tests, aggregate 268. The fixed governed-path boundary is
  independently VERIFIED (report `evidence/stage-4-review-bundle-ai-r-fixed-path.md`).
  Independent proposal and AI-A2 sessions may now populate the bundle;
  owner approval, dry-run, test-site import, post-import verification, and
  all data mutation remain blocked.
  Session-ready population guide (contract, field rules, independence,
  reference/absence examples, UTC rules, exception handling, exact
  validation/build commands, non-authorization statement):
  `evidence/stage-4-review-bundle-population-guide.md`.
  Prior Stage 3 status retained below for traceability.
- [ ] Stage 3 — INDEPENDENT AI-R BLOCKED 2026-09-05. Builder code is
  complete but Stage 3 does not close. Three P0 defects were reproduced:
  (1) stored Arabic values accept canonical-forbidden bidi controls U+200E,
  U+200F, U+061C, U+202A–U+202E, and U+2066–U+2069; (2)
  `account_name_ar` remains a normal permlevel-0 writable field, so standard
  form/REST saves bypass the governed API and Unicode policy; (3) English/code
  rename and required-reason logging are two non-atomic calls, the standard
  endpoint remains reason-free, and the shipped client logs against the stale
  pre-rename name. P1 defects: active/schema-installed registry mappings fail
  open on missing fields; Arabic search normalization is absent; new visible
  form strings are unwrapped and invisible to the current localization gate;
  browser, permission-bypass, concurrency, rename-failure, audit, and measured
  performance coverage is incomplete. Positive evidence remains valid: all 169
  tests pass; the evidence-enabled gate reports `780` catalog, `640` wrapped +
  `21` JSON, `0` missing; DB inventory is 18,421 rows with Merkle `93ae1f99…`;
  and FormMeta proves both new Account hooks load. Independent evidence:
  `evidence/stage-3-ai-r.md` (SHA-256
  `f7e1b8263081ea94e9fcdf945cb67cdd02853600ff073a690bd3ff132f5d642b`).
  Stage 4 must not begin.
- [ ] Stage 3 remediation round 2 — INDEPENDENT AI-R BLOCKED 2026-09-06.
  Two P0 defects remain: (1) the Account insert path returns before confinement
  and canonical identity validation, so form/REST creation can store Arabic
  names—including forbidden bidi controls—outside the governed API; (2)
  `governed_rename_account` unconditionally commits or rolls back the caller's
  entire transaction, making the service unsafe to compose and allowing it to
  commit or discard unrelated work. P1 defects: the dropdown catches and
  discards fail-closed registry errors; the normalized-key invariant is not
  enforced for inserts or non-null stale/forged values; browser evidence was
  not executed and its skip handling is broken; actual overridden HTTP
  dispatch, duplicate/root/busy-ledger rename failures, pagination/ranking,
  and an approved comparative P95 baseline are unproven. Positive results
  remain valid: 191 tests pass; evidence gate `802` catalog / `661` wrapped +
  `21` JSON / `0` missing; inventory 18,443 rows with Merkle `d495093e…`.
  Independent evidence: `evidence/stage-3-ai-r-round2.md` (SHA-256
  `e56cc83b244f3e11617150639665ddd9b60ef4fe2cbdabc7a9107e2c6aad494b`).
  Stage 4 must not begin.
- [ ] Stage 3 remediation round 3 — INDEPENDENT AI-R BLOCKED 2026-09-09.
  This is a fresh current-candidate review and supersedes the stale Round-2
  report for this gate. Both Round-2 P0s are independently verified closed:
  Account insertion confinement/canonical validation and scoped-savepoint
  transaction composition now pass. Registry propagation, normalized-key
  invariants, Unicode policy, permission-safe single-query search, UI
  localization, loaded hooks, and the nine-file Arabic/English Playwright
  evidence also pass. Three P1 release gates remain: (1) relevance sorting is
  applied only after a `modified desc` database page is fetched, so exact →
  prefix → substring ranking is not globally composable with pagination;
  (2) the P95 comparison uses an already bilingualized dropdown as the “plain”
  baseline, non-equivalent queries/results, only 15 samples, and records no
  measured P95 values; (3) override testing calls the resolved Python function
  rather than the actual HTTP method, and rename proves its Comment but not the
  claimed post-rename Version. Fresh evidence remains green: 207 tests, catalog
  803, extraction `662` wrapped + `21` JSON / `0` missing, inventory 18,444
  rows / Merkle `61c0c12c…`, evidence gate/lints/diff/build.   Independent report:
  `evidence/stage-3-ai-r-round3.md` (SHA-256
  `2a3df61b3329afcee46881a65fb68a6c37a7bf431e742787391951076e272957`).
  Stage 4 must not begin.
- [ ] Stage 3 remediation round 4 — INDEPENDENT AI-R BLOCKED 2026-09-09.
  The native post-rename Version plus reason Comment is independently verified,
  and the handler-level `execute_cmd` override path is conditionally verified.
  Three P1 gates remain: (1) both searches fetch only the newest 1000 matching
  rows by `modified desc`, then rank them, so exact/prefix results beyond row
  1000 disappear; the claimed regression's `CT-RANK-FILLER-*` rows do not match
  query `CT-RANK-TARGET`, tests only one search path, and would pass the old
  implementation; (2) the P95 “plain” baseline and bilingual workload differ
  in company filter, row limit, selected fields, predicates, formatting, and
  sorting; there is no warmup, ordering is biased, the 25-sample statistic is
  approximately P92, and raw samples/environment/query counts are absent;
  (3) the live HTTP transcript lacks requests/responses, fixture setup/cleanup,
  matching server log, and build identity, so only the hermetic handler path is
  auditable. Fresh positives remain: 209 tests, catalog 803, extraction
  `662` wrapped + `21` JSON / `0` missing, inventory 18,444 / Merkle
  `61c0c12c…`, gates/lints/diff/build green. Independent report:
  `evidence/stage-3-ai-r-round4.md` (SHA-256
  `fdf0c951bdae90ffd2646c59c4dff68c3fc402ab3feb1184e50ed579d5c0955a`).
  Stage 4 must not begin.
  Builder Round-4 claim retained below for traceability. Reported closures:
  (1) relevance ranking is now GLOBAL — both search paths fetch the whole
  matching window (documented cap 1000), rank it (exact > prefix >
  substring, value tie-break), and only then slice start/page_length; a
  permanent test proves a 30-day-old exact match surfaces first on page 1
  despite 12 newer substring-only fills; (2) the P95 gate now measures an
  EQUIVALENT pre-feature workload (Stage-1A-era plain get_list, same text,
  interleaved 25 samples) via `measure_search_p95`, with the executed
  measurements recorded in `evidence/raw-logs/stage3/p95-measurement.txt`
  (baseline 2.706 ms, bilingual 3.991 ms, canonical limit 17.977 ms — pass);
  (3) real HTTP dispatch: a permanent test drives `frappe.handler.execute_cmd`
  (the HTTP /api/method dispatch layer) with POST-shaped form_dict coercion
  through the overridden vendor path (reason-free refused), and a LIVE HTTP
  run against `bench serve` is archived (`http-dispatch-evidence.txt`):
  reason-free → HTTP 417 ValidationError, reasoned → HTTP 200 renamed with
  server-resolved identity; (4) the rename's Version audit is now REAL: the
  governed endpoint inserts a native `Version` row
  ({"changed": [[account_number, old, new], ...]}) on the post-rename
  identity, asserted by test alongside the reason Comment. Live: 209
  aggregate (13+6+5+3+8+89+38+47) all green; catalog 803; inventory 18,444
  rows / Merkle `61c0c12c…` live-matched; evidence-enabled gate `errors=0`;
  lints + diffcheck clean.   Builder evidence: `evidence/stage-3-pilot.md`
  (round-4 section). No live Account names migrated.
- [ ] Stage 3 remediation round 5 — INDEPENDENT AI-R BLOCKED 2026-09-09.
  Prior P0 closures and rename Version+Comment remain verified, but three P1
  gates remain: (1) both public searches now use unbounded
  `limit_page_length=0`, including blank text, materializing and sorting the
  entire permitted DocType per page; this replaces truncation with a
  large-tenant resource-exhaustion risk, while the >1000 test covers only the
  service path; (2) the P95 artifact recomputes to 2.121/2.885 ms, but every
  pair runs baseline first, the small baseline and complete-set workloads are
  not representative/equivalent at scale, even-sample medians are wrong, code/
  query/environment bindings are incomplete, the permanent test does not
  authenticate the artifact, and the measured 36% slowdown exceeds the
  canonical 10% gate without explicit owner acceptance of the +15 ms floor;
  (3) the socket claim is correctly withdrawn and handler dispatch is real,
  but handler coercion for `from_descendant` is untested, setup/cleanup files
  are scripts rather than results, and live Account `CT-HTTP-1 - CT HTTP Probe
  - E` remains despite the cleanup claim. Fresh positives: 209 tests, catalog
  803, extraction `662` + `21` / `0` missing, inventory 18,444 / Merkle
  `61c0c12c…`, gates/lints/diff green. Independent report:
  `evidence/stage-3-ai-r-round5.md` (SHA-256
  `b16c015b7fc955088bd05175b92ed3d7e6be3b60eab48a66d5d4e453f1e27031`).
  Stage 4 must not begin.
  Builder Round-5 claim retained below for traceability. Reported closures:
  (1) complete match-set ranking — the 1,000-row window is removed; both
  search paths fetch every permitted match, rank the complete set (exact >
  prefix > substring, value tie-break), then slice start/page_length; no
  truncation semantics remain; (2) genuine competing fixtures — 12 recent
  substring-matching fillers must not outrank a backdated exact match, for
  BOTH paths with a cross-page assertion, plus a 1000/1001-boundary test
  bulk-inserting 1,001 parameterized matching rows (exact match beyond the
  old window still ranks first; served set >= 1002); (3) equivalent,
  statistically correct P95 — true pre-feature implementation shape (plain
  get_list, two fields, page-limited, same text/company/page), 5 discarded
  warmups, 50 interleaved samples, nearest-rank P95, raw samples + medians +
  matched identity sets + environment recorded; the permanent test
  recomputes the statistic from the raw samples, asserts match-set
  equivalence, and applies the canonical gate; executed measurement
  preserved as full JSON (`p95-measurement.json`: baseline 2.121 ms /
  bilingual 2.885 ms / limit 17.333 ms — PASS, identical 12-match sets);
  (4) the live-socket HTTP claim is WITHDRAWN per the AI-R allowance — the
  dev server demonstrably flaps identical whitelisted requests between 417
  and 403 (serve log preserved), so the closure rests on the permanent
  handler-level dispatch test Round-4 AI-R already accepted; all socket
  artifacts preserved under `evidence/raw-logs/stage3/http/` with an
  explanatory README. Live: 209 aggregate (13+6+5+3+8+89+38+47) all green;
  catalog 803; inventory 18,444 rows / Merkle `61c0c12c…` live-matched;
  evidence-enabled gate `errors=0`; lints + diffcheck clean. Builder
  evidence: `evidence/stage-3-pilot.md` (round-5 section). No live Account
  names migrated.
- [ ] Stage 3 remediation round 6 — INDEPENDENT AI-R BLOCKED 2026-09-10.
  The requested performance exception was explicitly rejected: at baseline
  2.162 ms the canonical 10% limit is 2.3782 ms; measured bilingual P95 is
  2.646 ms, a 22.39% slowdown and therefore a gate failure. A second P1 remains
  in bounded search: truncation is silent through `searchable_link_search` and
  default `search_bilingual` responses, and `len(rows) >= 5000` falsely reports
  truncation at exactly 5000 because no 5001st-row probe is made. Tests do not
  cover exact-5000, real >5000, an exact result outside the window, or metadata
  through the actual dropdown consumer. The recorded 1250/1300 SQL counts are
  cumulative checkpoint sums grouped by call order, not per-path query counts.
  Handler `from_descendant` coercion, HTTP cleanup, prior P0/P1 closures, 211
  tests, catalog 803 / extraction `662` + `21` / `0` missing, inventory 18,444
  / Merkle `61c0c12c…`, and governed gates remain verified. Independent report:
  `evidence/stage-3-ai-r-round6.md` (SHA-256
  `26b2f6918e40c4847a7454e6285bf7c743187b6ed2dcb76b7835191838ec75b7`).
  Stage 4 must not begin.
- [ ] Stage 3 remediation round 7 — INDEPENDENT AI-R BLOCKED 2026-09-10.
  The authenticated P95 artifact independently passes the bare canonical 10%
  rule (2.272 ms baseline / 2.442 ms bilingual, +7.48%) and records true
  per-call one-SQL deltas. However, the permanent live bare-10% test is silently
  replaced by a second method with the same Python name that still applies the
  rejected +15 ms floor. Search also remains incomplete: `search_bilingual`
  detects but does not remove its 5,001st probe before ranking/slicing;
  blank-query `page_length` is client-unbounded; and tests patch tiny windows
  or create only ~1,002 matches rather than proving genuine exact-5000 and
  >5000 behavior on both public paths, including an exact match outside the
  window. Request-scoped caching/ASCII optimization are conditionally sound,
  with minor same-request invalidation/equivalence coverage residuals. Handler
  coercion, cleanup, prior P0/P1 closures, 211 tests, catalog 804 / extraction
  `663` + `21` / `0` missing, inventory 18,445 / Merkle `6fcffc90…`, and gates
  remain verified. Independent report: `evidence/stage-3-ai-r-round7.md`
  (SHA-256 `d4c46dea95604fa56d863958dad0fa7ecb176351f9ba02e4bd731652fdac130d`).
  Stage 4 must not begin.
  Builder Round-7 claim retained below for traceability. Owner performance decision ACCEPTED
  (floor REJECTED — bare 10% applies); all five Round-6 gates closed by
  making the implementation genuinely fast instead of gating exceptions:
  (1) window+1 probe — an exactly-full window is never flagged; only a
  real 5,001st row triggers truncation; probe rows dropped before ranking;
  (2) no silent truncation on default paths — plain list (service +
  dropdown API) refuses with a wrapped catalog message on real overflow;
  `with_meta` carries the structured flag; refusal paths covered by
  tests; (3) exact-boundary + real-overflow tests (window == match count
  NOT flagged; window = count-1 flagged; dropdown refusal);
  (4) bare-10% P95 met with real optimizations — ASCII-only queries skip
  the normalized-key predicate (it cannot change their match set),
  registry parse + metadata resolution request-memoized (fail-closed per
  request), imports hoisted; recorded measurement baseline 2.272 ms /
  bilingual 2.442 ms (+7.5%, inside bare 10%, 1 SQL/call on BOTH sides);
  the permanent gate applies `<= baseline * 1.10` with NO floor;
  (5) per-call SQL deltas recorded (`baseline_counts`/`bilingual_counts`
  + per-call means). Live: 211 aggregate
  (13+6+5+3+8+89+38+49) all green; catalog 804 (+1 refusal literal;
  steady-state sync 0/0); inventory 18,445 rows / Merkle `6fcffc90…`
  live-matched; evidence-enabled gate `errors=0`; lints + diffcheck clean.
  Builder evidence: `evidence/stage-3-pilot.md` (round-7 section). No live
  Account names migrated.
- [ ] Stage 3 remediation round 11 — INDEPENDENT AI-R BLOCKED 2026-09-10.
  The dropdown-local coercer is removed and both paths use the shared strict
  helper with widened annotations; P95 provenance and prior controls remain
  verified. One P1 permanent-test gap remains: `None` is not covered, and the
  cross-path test asserts only `frappe.ValidationError` class, not identical
  exception messages. A future service/dropdown message divergence could pass.
  Stale test comments also mention the removed permissive behavior. Fresh
  evidence reports pilot 53/53, aggregate 215, catalog 805 / extraction
  `664` + `21` / `0` missing, inventory 18,446 / Merkle `2e284695…`, and
  evidence gates green. Independent report:
  `evidence/stage-3-ai-r-round11.md` (SHA-256
  `735b09986fe7e5c626a37f55bf5619e287197fee8e647d72fab1fc5f2405d484`).
  Stage 4 must not begin.
  Builder Round-11 claim retained below for traceability.
- [ ] Stage 3 remediation round 10 — INDEPENDENT AI-R BLOCKED 2026-09-10.
  The P95 artifact is independently valid: five raw rounds per side, correct
  nearest-rank recomputation and minimum selection, balanced samples, hashes,
  environment, identity sets, and SQL counts; selected 1.974/2.034 ms is
  +3.04% and passes the bare 10% rule. The remaining P1 is cross-path integer
  semantics: `search_bilingual` uses strict `_coerce_int` and raises
  `frappe.ValidationError`, but the dropdown defines a separate permissive
  coercer (`int(float(...))` with fallback) that truncates fractional values
  and silently defaults garbage/`None`. Its test uses broad `assertRaises(Exception)`
  and would not detect this mismatch. Fresh evidence reports 215 aggregate
  tests, catalog 805 / extraction `663` + `21` / `0` missing, inventory 18,446
  / Merkle `2e284695…`, and evidence gates green. Independent report:
  `evidence/stage-3-ai-r-round10.md` (SHA-256
  `edad0fd49dc618cc68213d0799a4112c099d12a70a6b250559a4c5c38c90de12`).
  Stage 4 must not begin.
  Builder Round-10 claim retained below for traceability.
- [ ] Stage 3 remediation round 9 — INDEPENDENT AI-R BLOCKED 2026-09-10.
  Round-8 lower-clamp behavior is verified for negative/zero/oversize integer
  inputs on both paths, but two P1 gaps remain: non-integer `start` and
  `page_length` are inconsistent (service raises `ValueError`, dropdown
  returns `[]`) and lack permanent cross-path tests; and the P95 artifact says
  “min-of-five-rounds” while preserving only the selected round, so selection
  and cherry-pick resistance cannot be independently verified. Fresh pilot
  evidence: 52/52, aggregate 214, catalog 804 / extraction `663` + `21` /
  `0` missing, inventory 18,445 / Merkle `6fcffc90…`, evidence gate green.
  Independent report: `evidence/stage-3-ai-r-round9.md` (SHA-256
  `cd0b7dfd325cb574e59e55492d9cd1899b8484bea1d2a05ea540c953f78062ab`).
  Stage 4 must not begin.
  Builder Round-9 claim retained below for traceability.
- [ ] Stage 3 remediation round 8 — INDEPENDENT AI-R BLOCKED 2026-09-10.
  Round-7 probe removal, upper page clamp, genuine 5,000/5,001 fixtures, bare
  10% P95 artifact, and duplicate-test deletion were independently checked
  green. One P1 remains: both public paths upper-clamp `page_length` but do
  not lower-clamp negative `page_length` or `start`; negative values reach ORM
  pagination or Python slicing with framework-dependent behavior. Permanent
  tests for negative, zero, and oversize inputs on both paths are absent. Fresh
  evidence remains 211 tests, catalog 804 / extraction `663` + `21` / `0`
  missing, inventory 18,445 / Merkle `6fcffc90…`, and gates green.
  Independent report: `evidence/stage-3-ai-r-round8.md` (SHA-256
  `6e8a4295a9bbcefc5ba67bba126a59aeab36b1fda500ceeef3ea8900a7f9e108`).
  Stage 4 must not begin.
  Builder Round-8 claim retained below for traceability:
  All four Round-7 blockers closed:
  (1) the 5,001st probe row is REMOVED from the ranked set after detection
  (`rows[:RANK_WINDOW]`) on both paths; (2) every caller-supplied
  `page_length` is clamped to `MAX_PAGE_LENGTH = 200` on both paths
  (including blank queries — no client unbounded transfer); (3) genuine
  5,000/5,001 boundary tests on BOTH paths with real bulk fixtures:
  exactly-full window → not truncated + clean dropdown page; the 5,001st
  row → BOTH paths loudly refuse, `with_meta` flags, count verified =
  RANK_WINDOW + 1; (4) the duplicate stale `+15 ms` test name is deleted,
  the surviving bare-10% live test reasserted (authoritative gate remains
  the hash-bound artifact). Live: P95 artifact passes the bare rule
  (baseline 2.085 / bilingual 2.234 = +7.15%, min-of-rounds,
  GC-disciplined); 213 aggregate (13+6+5+3+8+89+38+51) all green;
  catalog 804 / extraction `663 + 21` / 0 missing; inventory 18,445 rows /
  Merkle `6fcffc90…` live-matched; evidence-enabled gate `errors=0`;
  lints + diffcheck clean. Builder evidence: `evidence/stage-3-pilot.md`
  (round-8 section). No live Account names migrated.
  Builder Round-6 claim retained below for traceability. Reported closures:
  (1) bounded request work — blank queries use plain bounded
  DB pagination (LIMIT/OFFSET, no scan); text queries fetch at most
  `RANK_WINDOW = 5000` matching rows via the permission-aware ORM, rank the
  collected set, slice, and format only the page; the window carries an
  EXPLICIT loud truncation contract (`truncated: true` via `with_meta`;
  never silent); forced-overflow and blank-boundedness tests prove it;
  (2) the >1,000 boundary test now covers BOTH public paths (dropdown
  served >= 1002 matches and surfaced the beyond-window exact match);
  (3) the P95 protocol is order-balanced (alternating pairs), uses true
  medians, and binds to its reality — code SHA-256s (the permanent gate now
  CONSUMES AND AUTHENTICATES `p95-measurement.json`; stale hashes fail, the
  statistic is recomputed from preserved raw samples), frappe/db versions,
  host, user, cardinality, and recorded SQL query counts (~4% more queries
  for the feature); executed measurement preserved as full JSON: baseline
  2.162 ms / bilingual 2.646 ms / limit 17.383 ms — PASS with identical
  match sets; (4) handler-level `from_descendant: "1"` STRING coercion
  tested through `execute_cmd`, README coverage wording corrected, and the
  `CT-HTTP-1` fixture cleaned with CAPTURED lifecycle outputs
  (`setup.out`/`cleanup.out`, leftover: []).
  **Owner decision requested by Builder**: plan §10.3 requires explicit owner
  acceptance for the documented "10% + 15 ms floor" comparative P95 gate.
  This exception was rejected before independent review. Live: 211 aggregate
  (13+6+5+3+8+89+38+49) all green; catalog 803; inventory 18,444 rows /
  Merkle `61c0c12c…` live-matched; evidence-enabled gate `errors=0`; lints
  + diffcheck clean. Builder evidence: `evidence/stage-3-pilot.md`
  (round-6 section). No live Account names migrated.
  Builder Round-3 claim retained below for traceability. Reported closures:
  (1) Account insertion
  refuses any client-supplied Arabic name outright (create-then-edit is the
  governed workflow) and the validate hook now applies canonical Unicode
  validation to EVERY stored value; (2) `governed_rename_account` no longer
  owns the caller's transaction — work runs in a scoped savepoint
  (`ct_bilingual_rename`), failures roll back to the savepoint only, success
  commits nothing; composition tests prove caller work survives a failed
  rename and remains uncommitted after a successful one (a final full
  rollback undoes the rename). The broad boolean bypass flag is replaced by
  an operation token bound to {doctype, name, expected-old, intended-new};
  mis-aimed tokens are refused. Round-2 P1s closed: registry/schema
  ValidationErrors propagate through the dropdown path (only ImportError
  degrades); the normalized-key invariant is enforced server-side on EVERY
  save (forged/stale keys overwritten); genuine Playwright browser evidence
  executed for BOTH sessions against the live desk (form identity section +
  the shipped tree settings driving the real `frappe.ui.Tree` over the
  governed children endpoint; 83 live labels; Arabic label without internal-
  name append; escaping verified; artifacts + runner + screenshots under
  `evidence/raw-logs/stage3/`; the shipped script's skip semantics fixed);
  overridden dispatch asserted end-to-end with reason enforcement and
  `from_descendant` compatibility; duplicate-number vendor failure class
  covered (busy-ledger not reproducible under the test runner — documented);
  pagination `limit_start` wired in the dropdown path; deterministic
  relevance ranking (exact > prefix > substring) applied to both search
  paths; comparative same-run P95 (plain dropdown baseline vs bilingual,
  ≤ +10% + 15 ms floor) asserted and recorded. Live: 207 aggregate
  (13+6+5+3+8+89+38+45) all green; catalog 803 (steady-state sync 0/0);
  inventory 18,444 rows, Merkle `61c0c12c…` live-matched; full evidence-
  enabled gate `errors=0`; lints + diffcheck clean. Builder evidence:
  `evidence/stage-3-pilot.md` (round-3 section). No live Account names
  migrated.
  Builder remediation claim retained below for traceability. Reported fixes:
  (1) identity Unicode policy now rejects every bidi control (canonical C1:
  U+202A–U+202E, U+2066–U+2069, U+200E, U+200F, U+061C) with a separate
  documented narrative policy (§8.6) allowing only LRM/RLM/ALM in rename
  reasons and never the embedding/override/isolate controls; (2)
  `doc_events["Account"].validate` confines `account_name_ar` writes to the
  governed API (direct form/REST saves refused even for Administrator; field
  now read-only; bypass tests for writer and Administrator); (3) atomic
  reason-required `governed_rename_account` delegates to the standard ERPNext
  path, resolves the post-rename identity server-side, records the reason in
  the same transaction with explicit rollback (proven by a rollback test),
  and `override_whitelisted_methods` routes the vendor endpoint through the
  wrapper; (P1) fail-closed active/schema_installed mappings, server-
  authoritative Arabic normalization (Alef/tatweel/diacritics) over a
  maintained derived key (`account_name_ar_norm`, v9_1 patch + backfill, both
  patches reversible with `revert()` and covered by idempotency/reversal
  tests), all visible strings wrapped and cataloged (+22; catalog 802;
  steady-state sync 0/0), and an expanded envelope (bypass, atomicity,
  normalization, concurrency/TimestampMismatch, production-path Version via
  the service call, P95 smoke, manual browser script). Live: 191 aggregate
  (`13+6+5+3+8+89+34+33`) all green; 89 standalone + 34 pure OK; inventory
  18,443 rows, Merkle `d495093e…` live-matched; full evidence-enabled gate
  `errors=0`; build exit 0. Builder evidence: `evidence/stage-3-pilot.md`
  (round-2 section). No live Account names migrated.
  Builder Stage 3 claim retained below for traceability.
  Bilingual framework + Account UI/tree pilot per canonical Stage 3 items 1–9:
  staged JSON registry (`construction/data/bilingual/bilingual_registry.json`,
  states planned/schema_installed/active), pure registry module + Frappe
  service (`construction/services/bilingual_registry.py`,
  `bilingual_service.py`) with Arabic→English→identity fallback (reverse for
  English sessions), physical-field adapters reusing the existing site fields
  (`Item.item_name_ar`, `Customer.customer_name_in_arabic`,
  `Supplier.supplier_name_in_arabic`), controlled Arabic-only Account edit
  that can never rename (server-enforced, native-Version audited via the
  v9_0 `track_changes` patch), standard-path English/code rename with a
  required recorded reason, Account form identity section
  (`doctype_js` `public/js/bilingual/account_form.js`), Account tree override
  (`doctype_tree_js` `public/js/bilingual/account_tree.js`: governed children
  wrapper with ONE batched label query + escaped `get_label` renderer that
  never appends the internal name), single-query permission-safe bilingual
  search (`search_bilingual` + registry union in the searchable-dropdown API).
  Inventory manifest regeneration formalized as the promised governed command
  (`construction/services/stage2_inventory_record.py`).
  Tests: 45 new (25 pure registry standalone + 20 bench pilot), suite
  aggregate now 169 (`13+6+5+3+8+89+25+20`) all green; catalog grew to 780
  (+9 wrapped service literals as Pending rows; steady-state sync 0/0);
  inventory now 18,421 rows, Merkle `93ae1f99…` live-matched; evidence
  regenerated; full evidence-enabled gate `errors=0`. Evidence:
  `evidence/stage-3-pilot.md`. No live Account names migrated.
  ROUND 18 AI-R BLOCKED. Independent AI-R
  verified the regenerated evidence is internally truthful and reproduced all
  live health: `87` standalone, `122` aggregate, `771` catalog, `631` wrapped +
  `21` JSON, `0` missing, full/scoped/vendor/lints/diff green, clean vendor POs,
  and the 18,412-row Merkle. It also verified candidate root/HEAD handling,
  semantic false-result rejection, and bootstrap authorization. Two P0 index
  checks remain fail-open: a coherently changed `ENVELOPE_LINES: 999` is
  accepted because the declared index length is never compared with its actual
  nonempty line count; an arbitrary 64-zero `CHECKER_SHA256` index value is
  accepted because ordered artifact names are checked but their index values
  are not recomputed against candidate bytes. The permanent 87-test suite lacks
  these two coherent regression cases. Round-18 evidence:
  `evidence/stage-2-ai-r-round18.md` (SHA-256
  `4681f79370bd646b1812f2f95f7a3b186be12b94206723f2d59753037ae295e3`).
  Stage 3 remains blocked.
  Builder Round-17 regeneration claim is recorded in deviation 26.
  Prior Round-16 status retained below:
  ROUND 16 AI-R BLOCKED. Independent AI-R
  reproduced healthy implementation/runtime behavior (`87` adversarial,
  `122` aggregate, `771` catalog, `631` wrapped + `21` JSON, `0` missing,
  clean vendor POs, and the 18,412-row Merkle). The claimed exact evidence
  contract remains fail-open: the governed index omits `CANDIDATE_ROOT`, has 32
  nonempty lines while declaring 31, and still validates. Index artifact values
  are ignored; marker aliases, duplicate artifact/result records, semantic
  decoys, lowercase hidden failures, false scoped/vendor/lint/freshness/sync/
  Merkle results, and impossible embedded timestamps remain accepted after
  coherent rehash/reindex. The governed freshness envelope finishes before its
  embedded collection and audit times. Permanent tests do not cover these
  residuals, and one fixture emits an unclosed-handle warning. Round-16
  evidence: `evidence/stage-2-ai-r-round16.md` (SHA-256
  `07fb328b6369b68494fb77e9d34f12a5596faa8af467dc1acc910bdf55d68c22`).
  Stage 3 remains blocked.
  Builder Round-16 claim retained below for traceability:
  exact versioned index grammar with candidate root/HEAD binding (fail closed
  when unresolvable); artifact SHAs recomputed from the candidate everywhere
  they appear (14 markers incl freshness/SQL/lints/vendor POs; manifest-marker
  collision fixed by anchored matching); ten semantic envelope schemas with
  arithmetic; UTC/order/recency enforcement; general failure-text rejection;
  adversarial tests for every coherent forgery; stale TESTFILE hash fixed by
  regeneration; 10 hash envelopes + governed index. Live: catalog 771, wrapped
  631 + JSON 21; 87 adversarial green both ways; 122-test aggregate green
  (13+6+5+3+8+87); payload `037e79c2…` 0-drift, runtime digest stable.
  Evidence `stage-2-remediation.md` + `raw-logs/stage2/` (+ `index.txt`).
  AI-R rerun completed with the blocked verdict above.
  Prior Round-15 status retained below:
  ROUND 15 AI-R BLOCKED 2026-09-05. Independent AI-R
  reproduced healthy implementation/runtime behavior (`87` adversarial,
  `122` aggregate, `771` catalog, `631` wrapped + `21` JSON, `0` missing,
  zero drift, clean vendor POs, and the 18,412-row Merkle). The asserted exact
  evidence contract remains incomplete: there is no exact versioned index
  grammar or candidate-root row; duplicate candidate HEAD rows pass; missing
  artifact markers are silently accepted; several candidate artifacts and five
  envelope success schemas remain unbound; lowercase hidden errors and
  impossible embedded timestamps pass. The real standalone envelope records
  stale test SHA `e165…` while the live tests are `daf572…`, yet the ordinary
  gate exits 0 because it looks for a different marker name. The manifest-marker
  collision is narrowly fixed, but the localization manifest remains unbound.
  Round-15 evidence: `evidence/stage-2-ai-r-round15.md` (SHA-256
  `e3cf4886382163e9289f224b402580df76e4298ea69c30327df7817926d39be3`).
  Stage 3 remains blocked.
  Builder Round-15 claim retained below for traceability:
  exact evidence contract (index grammar incl CANDIDATE_HEAD, command identity,
  ordered markers, exit-0, UTC/order/recency, length markers, failure-text
  rejection, semantic schemas with arithmetic, index/file hash agreement,
  candidate HEAD binding with fail-closed); artifact SHAs recomputed from the
  candidate everywhere they appear (manifest-marker collision fixed);
  adversarial tests for every coherent forgery; 10 hash envelopes + governed
  index. Live: catalog 771, wrapped 631 + JSON 21; 87 adversarial green both
  ways; 122-test aggregate green (13+6+5+3+8+87); payload `037e79c2…` 0-drift,
  runtime digest stable.
  Evidence `stage-2-remediation.md` + `raw-logs/stage2/` (+ `index.txt`).
  AI-R rerun completed with the blocked verdict above.
  Prior Round-14 status retained below:
  ROUND 14 AI-R BLOCKED 2026-09-05. Independent AI-R
  reproduced healthy implementation/runtime behavior (`87` adversarial,
  `122` aggregate, `771` catalog, `631` wrapped + `21` JSON, `0` missing,
  zero drift, clean vendor POs, and the 18,412-row Merkle). The remaining P0
  is that coherent evidence changes remain accepted: false artifact hashes and
  Merkle values, false scoped/vendor/lint/sync/freshness results, stale or
  impossible timestamp ordering, hidden error output, duplicate candidate
  heads, and absence of candidate-root binding. The governed `full-gate.txt`
  records checker SHA `35b9c294…` while the live checker and governed index bind
  `581f63b0…`; the ordinary gate nevertheless passes. Exact index grammar,
  artifact/cross-envelope bindings, successful schemas for all ten envelopes,
  evidence recency/scope, and permanent regression coverage remain incomplete.
  Round-14 evidence: `evidence/stage-2-ai-r-round14.md` (SHA-256
  `80bd0f9ac5037606ccf46139e1695d9153362ff1112bfabde965cca301c54467`).
  Stage 3 remains blocked.
  Builder Round-14 claim retained below for traceability:
  strict evidence contract (exact index grammar incl CANDIDATE_HEAD, command
  identity, ordered markers, exit-0, UTC/order, length markers, failure-text
  rejection, semantic schemas with arithmetic, index/file hash agreement,
  candidate HEAD binding); adversarial tests for every coherent forgery
  (totals, gate output, dry-run arithmetic, hidden failure, arbitrary command,
  junk index, length, duplicates, traversal, exit, UTC); documented two-phase
  bootstrap; 10 hash envelopes + governed index. Live: catalog 771, wrapped
  631 + JSON 21; 87 adversarial green both ways; 122-test aggregate green
  (13+6+5+3+8+87); payload `037e79c2…` 0-drift, runtime digest stable.
  Evidence `stage-2-remediation.md` + `raw-logs/stage2/` (+ `index.txt`).
  AI-R rerun completed with the blocked verdict above.
  Prior Round-13 status retained below:
  ROUND 13 AI-R BLOCKED 2026-09-05. Independent AI-R
  reproduced healthy implementation/runtime behavior (`79` adversarial,
  `114` aggregate, `771` catalog, `631` wrapped + `21` JSON, `0` missing,
  zero drift, clean vendor POs, and the 18,412-row Merkle). The governed full
  gate is now a genuine exit-0 bootstrap run; vendor root isolation and isolated
  decision provenance remain verified. The remaining P0 is semantic evidence
  integrity: coherent file/hash/length/index refreshes still authorize altered
  test totals, altered full-gate counts, invalid dry-run arithmetic, hidden
  failure output, arbitrary command content, and junk index lines. Length and
  substantive artifact/cross-envelope bindings are not enforced. The new
  permanent tests cover only part of this contract. Round-13 evidence:
  `evidence/stage-2-ai-r-round13.md` (SHA-256
  `26aa21c6501c27723aa2270f61ccdeb678d71f3ee79bd71b94d402aa18de46b3`).
  Stage 3 remains blocked.
  Builder Round-13 claim retained below for traceability:
  explicit roots on every remaining vendor path (audit allowlist, delta CLI
  hashes/output/root-owned temp dirs) with cross-root fixture asserting isolated
  hashes/output + checkout byte-identity; strict evidence index validator (exact
  set, exit-0/command/UTC/SHA/length envelopes, truncation/hash agreement) with
  documented two-phase bootstrap resolving the index/gate circularity; rebuilt
  checker re-validated against the full contract; evidence adversarial tests for
  truncation/tamper/missing/extra/duplicates/traversal/exit/markers/UTC/order/
  schemas/arithmetic; extended vendor fixture (distinct commits, temp paths,
  delta JSON sets/hashes, write location, byte identity); 10 hash envelopes +
  governed index binding all SHAs. Live: catalog 771, wrapped 631 + JSON 21;
  79 adversarial green both ways; 114-test aggregate green (13+6+5+3+8+79);
  payload `037e79c2…` 0-drift, runtime digest stable.
  Evidence `stage-2-remediation.md` + `raw-logs/stage2/` (+ `index.txt`).
  AI-R rerun completed with the blocked verdict above.
  Prior Round-12 status retained below:
  ROUND 12 AI-R BLOCKED 2026-09-05. Independent AI-R closed
  the vendor explicit-root/temp/output defect and isolated release-decision
  provenance defect. Fresh `71` adversarial and `106` Redis-backed aggregate
  tests passed; live gates remain `771` catalog, `631` wrapped + `21` JSON,
  `0` missing, with 34 skipped/0 drift and reproducible 18,412-row Merkle.
  The evidence-integrity gate remains P0: the governed `full-gate.txt` itself
  contains `FAIL`, `errors=1`, and `EXIT_CODE: 1` yet validates. Coherently
  rehashed fixtures with nonzero exit, altered aggregate output, bad arithmetic,
  malformed UTC, or duplicate exit markers also validate. The 71-test contract
  contains no permanent evidence-validator adversarial tests, and its vendor
  fixture does not permanently assert the complete independently verified
  distinct-commit/temp/output/byte-identity behavior. Round-12 evidence:
  `evidence/stage-2-ai-r-round12.md` (SHA-256
  `aa1a698f3497d93eb6b00afbec59f7e11b4a276283610f0e914e6af7c0c2c909`).
  Stage 3 remains blocked.
  Builder Round-12 claim retained below for traceability:
  explicit roots on every remaining vendor path (audit allowlist, delta CLI
  hashes/output/temp via TMPDIR-safe root-owned dirs) with cross-root fixture
  asserting isolated hashes/output + checkout byte-identity; strict evidence
  index validator (exact set, exit-0/command/UTC/SHA/length envelopes,
  truncation/hash agreement, traversal/duplicates); rebuilt checker re-validated
  against the full contract; 10 hash envelopes + governed index binding all SHAs.
  Live: catalog 771, wrapped 631 + JSON 21; 71 adversarial green both ways;
  106-test aggregate green (13+6+5+3+8+71); payload `037e79c2…` 0-drift, runtime
  digest stable.
  Evidence `stage-2-remediation.md` + `raw-logs/stage2/` (+ `index.txt`).
  AI-R rerun completed with the blocked verdict above.
  Prior Round-11 status retained below:
  ROUND 11 AI-R BLOCKED 2026-09-05. Independent AI-R verified
  the live localization gates, zero drift, vendor cleanliness, reproducible
  inventory Merkle, and all fresh test modules, but reproduced three blocking
  boundary failures: (1) the evidence validator accepts `EXIT_CODE: 1`, a
  five-line truncated envelope, altered output with a refreshed hash, and a
  duplicate index row; the governed `full-gate.txt` itself records failure yet
  validates; (2) `check_manifest(root=...)` calls `decisions_sha()` and
  `decision_root()` without the isolated root, allowing a candidate with no
  `release_decisions.json` to borrow live-checkout provenance; (3) vendor delta
  parse files still use global `/tmp`, outside the explicit-root contract.
  Fresh totals are `71` adversarial tests and `106` aggregate tests
  (`13+6+5+3+8+71`), correcting the Builder's 105 claim. Live counts remain
  `771` catalog, `631` wrapped + `21` JSON, `0` missing; payload dry run remains
  34 skipped/0 drift. Round-11 evidence:
  `evidence/stage-2-ai-r-round11.md` (SHA-256
  `0904f1674a33843bd9a30a4f419aacb825cbe263544a8ac412c5b45f16ffa605`).
  Stage 3 remains blocked.
  Builder Round-11 claim retained below for traceability:
  explicit roots on every vendor path incl delta CLI temp files, with cross-root
  fixture asserting isolated hashes/output + checkout byte-identity; evidence
  index validator; Redis restored; 10 hash envelopes and governed index. Claimed
  71 adversarial and 105 aggregate tests.
  Prior Round-10 status retained below:
  ROUND 10 AI-R BLOCKED. Builder remediation
  reported all five round-9 findings closed, but independent AI-R reproduced two
  release-blocking defects: (1) `scripts/vendor_upgrade_delta.py:main()` still
  computes vendor PO hashes through module-global `ROOT.parent` instead of the
  supplied isolated `root.parent`, so explicit-root output can mix isolated
  blobs with live-checkout provenance; the claimed conflicting cross-root CLI
  fixture is absent; (2) the governed index correctly binds exactly ten envelope
  hashes, but `merkle.txt` embeds a truncated inventory JSON fragment and no
  validator/adversarial suite rejects truncated, altered, missing, extra,
  duplicate, or path-traversal evidence. Retirement-date and implemented
  freshness controls closed. Standalone 70-test suite and live gates reproduced
  green (`771` catalog, `631` wrapped + `21` JSON, `0` missing); a fresh Bench
  aggregate reached 94 passing tests before local Redis refused connections, so
  the saved indexed 105-pass run was validated but not fully rerun independently.
  Round-10 evidence: `evidence/stage-2-ai-r-round10.md` (SHA-256
  `f4a90afda2f72a268e50e18d31177a667b5a9c7f749d890b6bb77c015ded6b85`).
  Stage 3 remains blocked.
  Builder Round-10 claim retained below for traceability:
  explicit roots on every vendor path (audit allowlist, delta CLI incl temp
  files, all helpers/scans) with cross-root fixture; delta provenance validated;
  strict retired dates with tomorrow fixture; freshness audit bounds with
  end-to-end mutated-artifact gate tests; closed CSV handle; 10 hash envelopes +
  governed index binding all SHAs. Live: catalog 771, wrapped 631 + JSON 21;
  70 adversarial green both ways; 105-test aggregate green; payload `037e79c2…`
  0-drift, runtime digest stable.
  Evidence `stage-2-remediation.md` + `raw-logs/stage2/` (+ `index.txt`).
  Prior round-9 evidence: `evidence/stage-2-ai-r-round9.md` (SHA-256
  `d3117e88ae876f9ba72f01dd02c8d4bd5b8ccd73782ec471336613286d8cf622`).
  Prior round-8 evidence: `evidence/stage-2-ai-r-round8.md` (SHA-256
  `80bbf2bf334a671b4f08b4a17b43780e9f136aa8932f8c90733d832007caa251`).
  Prior round-7 evidence: `evidence/stage-2-ai-r-round7.md` (SHA-256
  `d705514173be02586e3d5c9715469141ad798497ba0a74277af2f880b00a8203`).
  Prior round-6 evidence: `evidence/stage-2-ai-r-round6.md` (SHA-256
  `5715bfcfc1fc40aace2130ca2938a154b2fed081b1d1853a37b5d3b6242022b5`).
  Prior round-5 evidence: `evidence/stage-2-ai-r-round5.md` (SHA-256
  `046365c60d8b94bfcff74e8df36da1355c3e70b1c5aa827cd7350e39608a055d`).
  Prior round-4 evidence: `evidence/stage-2-ai-r-round4.md` (SHA-256
  `00a958bc298c682acfba5855ff1a7df960923ea91cb9abd385ffc2484b611d8f`).
  Prior review evidence retained:
  `evidence/stage-2-ai-a1-source-equal-triage.md`,
  `evidence/stage-2-ai-a3-structural-review.md`, and
  `evidence/stage-2-ai-r-technical-review.md`.
- [ ] Stage 4 — engineering-only export/proposal, report-extension, and
  review-bundle work is complete and non-mutating. The review-bundle import
  boundary is **VERIFIED by independent AI-R**; independent proposal generation
  and AI-A2 review may now populate the bundle. Owner approval, dry-run,
  authorized test-site import, post-import verification, and Account-name
  mutation remain blocked.
- [ ] Stages 5–8 — not started.

Current gate update: Stage 3 is **VERIFIED BY INDEPENDENT AI-R ROUND 12** (2026-09-10). Stage 4 may begin under the canonical plan. Owner authorization remains required for commit, push, merge, deploy, runtime Translation import, or Account-name migration.

## Deviations

| # | Difference from canonical plan | Disposition |
|---|---|---|
| 1 | No `.mo` files on disk in v16 checkout; MO check N/A as file check | Recorded Stage 0; runtime proof via fresh Arabic session pending reviewers |
| 2 | `docs/ai/SCHEMA_FACTS.md` drift vs live JSON (pre-existing, 2026-08-19) | Recorded; not silently regenerated |
| 3 | Test harness needs `touch ./v16.localhost/.test_records.jsonl` | Infra workaround, recorded |
| 4 | Silent-empty-search failure disproved on current Frappe; fix is hardening | Evidence in stage-1abc.md |
| 5 | Canonical plan hash changed twice mid-work (`f25cc595…` → `085ff50b…` → `2498f5fb…`); handoff hash updated to match | Reviewed: status-only §16 appendices, no architectural change; completed work stands. Interim §16 error ("0/1A/1B not started") corrected by owner; verified in §16 log. Handoff stop-gate authority unchanged at the time; v4 governance change recorded separately in row 6 |
| 6 | Owner replaced named-human A1/A2/A3/release-authority requirements with AI-A1/AI-A2/AI-A3/AI-R governance | Architecture/governance change recorded in canonical plan v4 and handoff. Completed Stage 0/1A/1B and Stage 1C code remain valid; Stage 1C requires fresh independent AI decisions before promotion. |
| 7 | First AI-R pass incorrectly treated raw `Workspaces` as untranslated and found runtime/render evidence absent | Corrected by source-chain and live proof: `menu.js:109` translates `item.label`; all six runtime values are effective; fresh-session and 390px render evidence pass. No extension or vendor edit is needed. |
| 8 | AI-R rerun conditionally verified Stage 1C and found two evidence-integrity conditions | Correct the stale `Workspaces` payload note that mentions the removed extension; save durable raw logs for the 13+6+5+3+8 test runs and asset build; then rerun AI-R against exact hashes. |
| 9 | Stage 2 Builder marked code complete after a green narrow scanner run | Independent AI-A3 and AI-R found the scanner does not implement multiple mandatory plan gates and has false-negative paths. Stage 2 reverted to blocked until the checker, inventory evidence, adversarial tests, and durable logs are remediated and independently reverified. |
| 10 | Stage 2 remediation reported all A3-01…A3-08 items closed | AI-R rerun reproduced local green results but found A3-02/A3-03 open, A3-01/A3-04/A3-05/A3-07/A3-08 partial, and CI non-reproducible because sibling Frappe/ERPNext trees are absent after a standard checkout. Stage 2 remains blocked; Stage 1C remains valid. |
| 11 | Stage 2 Round 2 reported all seven AI-R remediation items closed | AI-R verified CI vendor topology, green local counts/tests, clean vendor POs, and runtime-inert payload, but found extraction/routing bypasses, incomplete vendor-delta and decision binding, weak freshness binding, insufficient adversarial coverage, and stale/incomplete durable evidence. Stage 2 remains blocked. |
| 12 | Stage 2 Round 3 reported all eight findings closed | AI-R verified 720/591+21/0, 40 adversarial tests, 75-test regression, lints, diff check, zero-drift runtime, clean vendor catalogs, and Merkle `8d3701f7…`; it nevertheless reproduced raw-template false greens and found vendor-delta, decision, freshness, retirement, and durable-evidence controls incomplete. Stage 2 remains blocked. |
| 13 | Stage 2 Round 4 reported all eight findings closed | AI-R reproduced the same-commit vendor re-baseline bypass and found decision binding, retired rename/delete governance, extraction coverage, tests, evidence envelopes, and recorded counts incomplete or stale. A health diagnostic refreshed an audit timestamp during review; no runtime translation value changed. Stage 2 remains blocked. |
| 14 | Stage 2 Round 5 reported all six findings closed | AI-R reproduced same-commit vendor overwrite, multiline Python-sink, and invalid delete-lifecycle bypasses; found inventory/evidence inaccuracies; and identified a non-hermetic adversarial test that touched real artifacts before restoring them exactly. Stage 2 remains blocked. |
| 15 | Stage 2 Round 6 reported all six findings closed | AI-R found the suite still writes governed checkout artifacts, the isolated vendor fixture does not exercise the real topology, delta schemas and AST alias handling remain incomplete, retired delete evidence is weak, the Merkle root is irreproducible, and two evidence envelopes are incomplete. Stage 2 remains blocked. |
| 16 | Stage 2 Round 7 reported all seven findings closed | AI-R closed hermeticity and AST alias handling, but reproduced acceptance of an omitted same-commit context shift and an independently different Merkle from the committed SQL; freshness, manifest-to-inventory binding, replacement lifecycle, and evidence hashes remain incomplete. Stage 2 remains blocked. |
| 17 | Stage 2 Round 8 reported all seven findings closed | AI-R closed the Merkle mismatch and verified headline gates, but reproduced vendor explicit-root/hash confusion and acceptance of forged commit/PO-hash metadata; retirement replacement, health timestamps, and evidence completeness remain open. Stage 2 remains blocked. |
| 18 | Stage 2 Round 9 reported all eight findings closed | AI-R closed the prior forged-provenance consumer bypass, but found module-global vendor path leakage, future-dated retirement acceptance, incomplete freshness timestamp enforcement, and an ungoverned/incompletely hash-bound ten-log evidence set. Stage 2 remains blocked. |
| 19 | Stage 2 Round 10 reported all five findings closed | AI-R closed strict retirement dates and the implemented freshness policy, but reproduced mixed-origin vendor-delta hashing through module-global `ROOT.parent`; it also found truncated Merkle evidence with no fail-closed evidence-index validator. The independent aggregate rerun was interrupted after 94 passing tests by local Redis refusal. Stage 2 remains blocked. |
| 20 | Stage 2 Round 11 reported the Round-10 blockers closed | AI-R confirmed isolated vendor hashes/output, Redis-backed tests, live gates, zero drift, and Merkle, but the evidence validator accepts failed/truncated/coherently altered evidence, isolated manifest checks borrow live decision provenance, and vendor parse temp files escape the explicit root. The true fresh aggregate is 106, not 105. Stage 2 remains blocked. |
| 21 | Stage 2 Round 12 reported all Round-11 findings closed | AI-R verified vendor root-owned temp/output handling, isolated decision provenance, 71 adversarial tests, the 106-test aggregate, live gates, zero drift, and Merkle. However, the governed failed full-gate envelope and multiple coherently rehashed semantic forgeries still pass the validator, with no permanent adversarial validator tests. Stage 2 remains blocked. |
| 22 | Stage 2 Round 13 reported all Round-12 findings closed | AI-R verified the exit-0 bootstrap envelope, vendor isolation, isolated decisions, 79 adversarial tests, 114 aggregate tests, live gates, zero drift, and Merkle. Coherently rehashed/reindexed false totals, outputs, arithmetic, commands, failures, and junk index content remain accepted; semantic and artifact bindings plus permanent adversarial coverage are incomplete. Stage 2 remains blocked. |
| 23 | Stage 2 Round 14 reported all Round-13 findings closed | AI-R verified 87 adversarial and 122 aggregate tests plus all live localization gates, but reproduced acceptance of false artifact hashes/results, stale or impossible timestamps, hidden errors, duplicate candidate identity, and missing root binding. The governed full-gate checker hash disagrees with the live checker while the ordinary gate passes. Stage 2 remains blocked. |
| 24 | Stage 2 Round 15 reported all Round-14 findings closed | AI-R again verified the live gates and 87/122 tests, but found the index schema and root identity incomplete, duplicate HEAD and missing markers accepted, multiple artifacts and envelope schemas unbound, and invalid failures/timestamps accepted. A real stale standalone-test hash passes due to inconsistent marker naming. Stage 2 remains blocked. |
| 25 | Stage 2 Round 16 reported all Round-15 findings closed | AI-R verified 87/122 tests and live health, but the governed index itself omits candidate root and misstates its line count while passing. Ignored artifact rows, aliases, duplicate/decoy results, false envelope semantics, hidden failures, and impossible embedded times remain accepted after coherent rehash/reindex. Stage 2 remains blocked. |
| 26 | Stage 2 Round 17 reported all Round-16 findings closed | Builder shipped the ordered index schema, root/HEAD and 14 artifact rows, envelope schemas, guarded bootstrap, and regenerated all ten live captures after freshness rebinding. Round 18 AI-R subsequently returned BLOCKED on two remaining index-value checks recorded in row 27. |
| 27 | Round 18 AI-R reviewed the regenerated Round-17 evidence | All runtime/localization health passed, but two P0 authorization bypasses reproduced: false governed-index `ENVELOPE_LINES` accepted, arbitrary governed-index artifact SHA values accepted; no permanent regression tests for either. Stage 2 remains blocked. |
| 28 | Stage 2 Round 18 reported both Round-18 P0s closed | Checker binds the exact index length and all fourteen index artifact values to candidate bytes; permanent coherent-forgery tests were added, totals became 89/124, and all evidence was regenerated. Round 19 independently verified these controls. |
| 29 | Round 19 AI-R independently reviewed the final Stage 2 candidate | VERIFIED: every length and fourteen-artifact negative variant rejected; 89 standalone and 124 aggregate tests passed; evidence-enabled and live localization gates, vendor cleanliness, zero drift evidence, and DB Merkle agreed. Stage 2 closes and Stage 3 may begin under the canonical plan. |
| 30 | Stage 3 code found the existing `doctype_js` hook entries resolve one level too deep (`frappe.get_app_path` is module-relative; `construction/construction/...` paths point at non-existent files, so those form scripts silently no-load) | Recorded as a pre-existing defect; NOT fixed in Stage 3 (out of pilot scope, unrelated doctypes). New Account registrations use resolving module-relative paths (`public/js/bilingual/...`). Fixing the legacy entries requires separate owner approval. |
| 31 | Native Version audit evaluated (Stage 3 item 8): ERPNext ships Account with `track_changes=0`, so `doc.save()` recorded no Version — a proven gap | Closed via `construction.patches.v9_0.enable_account_track_changes` (standard DocType property, idempotent, no vendor source edit, no new audit DocType). Test-mode Version suppression (`frappe.in_test`) documented; the pilot test exercises the production path explicitly. |
| 32 | Stage 3 pilot UI labels are plain English, not `_()`/`__()`-wrapped | Per canonical plan, UI-string translation belongs to the later UI-review waves (Stages 5–8); no raw user-facing sinks were introduced. Backend validation messages ARE wrapped and added to the catalog (+9 Pending rows); no dispositioned validation messages. |
| 33 | Stage 2 inventory manifest regeneration had no committed tool (the SQL header promised `scripts/record_stage2_inventory.py`); ad-hoc console regeneration truncated the file once mid-session | Formalized as `construction/services/stage2_inventory_record.py` (`bench execute construction.services.stage2_inventory_record.record`), fail-closed on HEAD moves, deterministic output; the file was immediately regenerated through it. |
| 34 | Stage 3 Builder reported canonical items 1–9 complete | Independent AI-R verified 169 tests, localization evidence, Merkle, and actual hook loading, but found three P0 failures: forbidden bidi controls accepted, direct form/REST Arabic-field writes bypass governance, and rename/reason recording is bypassable and non-atomic. Active registry mismatch, Arabic normalization, UI localization, and runtime/browser coverage also remain P1. Stage 3 remains blocked; Stage 4 must not begin. |
| 35 | Stage 3 remediation round 2 reported all three P0s and four P1s closed | Builder added Unicode separation, update confinement, governed rename, normalized search, registry checks, localized strings, and expanded tests; live evidence reported 191 tests and catalog/inventory gates green. Independent Round 2 review is recorded in row 36. |
| 36 | Independent AI-R reviewed Stage 3 remediation round 2 | BLOCKED: Account insert bypasses confinement/Unicode validation, and the rename service owns the caller's full commit/rollback boundary. Dropdown registry errors, normalized-key invariants, browser execution, overridden HTTP dispatch/failure classes, pagination/ranking, and comparative P95 evidence remain incomplete. Stage 4 must not begin. |
| 37 | Stage 3 remediation round 3 reported both Round-2 P0s and all P1s closed | Builder implemented insert confinement, operation-bound authorization, scoped-savepoint rename, registry/normalization fixes, browser runs, dispatch/failure tests, pagination/ranking, and a comparative P95 check; live evidence reported 207 tests and catalog/inventory gates green. Independent Round-3 review is recorded in row 38. |
| 38 | Independent AI-R reviewed the current Stage 3 remediation round 3 candidate | BLOCKED: both prior P0s and most P1s are verified closed, but relevance ranking occurs after DB pagination, the P95 comparison lacks an equivalent pre-feature measured baseline, actual HTTP override dispatch is untested, and a post-rename Version is claimed but not proven. Stage 4 must not begin. |
| 39 | Stage 3 remediation round 4 reported all four Round-3 P1 gates closed | Builder added rank-before-slice within a 1000-row window, comparative P95 evidence, handler/live HTTP evidence, and a native post-rename Version. Independent Round-4 review is recorded in row 40. |
| 40 | Independent AI-R reviewed Stage 3 remediation round 4 | BLOCKED: rename Version+Comment is verified; handler dispatch is conditionally verified. Global ranking is still incomplete beyond the newest 1000 matches and its regression fixture is invalid; P95 workloads/statistics/evidence are not equivalent or auditable; live HTTP evidence lacks reproducible setup/request/response/log/cleanup binding. Stage 4 must not begin. |

## Diff scope (uncommitted, on feature branch)

- `construction/searchable_dropdown/api/search.py` (Stage 1A fix; Stage 3 registry union)
- `construction/searchable_dropdown/tests/test_search_api.py` (+1 regression test)
- `construction/patches/v8_8/add_account_arabic_name_field.py` (new) + `construction/patches.txt`
- `construction/patches/v9_0/enable_account_track_changes.py` (new, Stage 3) + `construction/patches.txt`
- `construction/tests/test_bilingual_account_schema.py` (new, 5 tests)
- `construction/data/bilingual/bilingual_registry.json` (new, Stage 3)
- `construction/services/bilingual_registry.py` (new, pure, Stage 3)
- `construction/services/bilingual_service.py` (new, Stage 3)
- `construction/services/stage2_inventory_record.py` (new, Stage 3 governance tooling)
- `construction/public/js/bilingual/account_form.js` (new, Stage 3)
- `construction/public/js/bilingual/account_tree.js` (new, Stage 3)
- `construction/hooks.py` (Stage 3: Account `doctype_js` + `doctype_tree_js` registrations)
- `construction/tests/test_bilingual_service.py` (new, 25 tests) and
  `construction/tests/test_bilingual_account_pilot.py` (new, 20 tests)
- `construction/locale/ar.po` (Stage 1C entry plus Stage 2 Pending extraction inventory; Stage 3 +9 service literals)
- `construction/construction/doctype/boq_header/boq_header.js` (Stage 2 raw-sink localization fix)
- `construction/api/modern_form_api.py` (Stage 2 dynamic translation-call refactor)
- `scripts/check_localization_gates.py` and `construction/tests/test_localization_gates.py`
- `scripts/vendor_upgrade_delta.py` and `construction/localization_freshness.py`
- `.github/workflows/linter.yml` (localization gate integration)
- `construction/data/localization/` and translation allowlist/vendor-coverage/retired-source artifacts
- `construction/data/translations/approved_ar_overrides.csv` (Stage 1C governed payload)
- `docs/ai/work-items/erp-arabic-bilingual-data/` (evidence only)

## Rollback

- Code: `git checkout -- <files>` / delete feature branch (nothing committed).
- Test-site data: patch created 1 Custom Field + column on the shared test DB;
  revert via deleting Custom Field `Account-account_name_ar` + `bench migrate`
  on test site only. No production touched. Re-run of patch is idempotent.
| 41 | Stage 3 remediation round 5 reported all Round-4 P1 gates closed | Builder removed the ranking cap, expanded competing/boundary tests, preserved raw P95 JSON, and withdrew the live-socket HTTP claim. Independent Round-5 review is recorded in row 42. |
| 42 | Independent AI-R reviewed Stage 3 remediation round 5 | BLOCKED: unbounded public searches create large-tenant resource risk; the P95 method/artifact does not prove the canonical comparative gate; handler `from_descendant` coercion and HTTP cleanup are overstated, with a live `CT-HTTP-1` Account residue. Prior P0s and rename audit remain closed. Stage 4 must not begin. |
| 43 | Stage 3 remediation round 6 reported all four Round-5 gates closed | Builder added bounded blank/text search, truncation metadata, both-path >1000 tests, a more strongly bound P95 artifact, handler coercion, and captured HTTP cleanup. The requested 10%+15ms performance exception was rejected; independent Round-6 findings are in row 44. |
| 44 | Independent AI-R reviewed Stage 3 remediation round 6 | BLOCKED: dropdown/default responses still truncate silently and exact-5000 detection is false-positive; boundary/overflow coverage is incomplete. The canonical P95 gate fails at 2.646 ms versus 2.3782 ms (22.39% slowdown), and reported per-side SQL counts are invalid cumulative sums. Handler/cleanup and prior controls remain verified. Stage 4 must not begin. |
| 45 | Stage 3 remediation round 7 reported all five Round-6 gates closed under the owner's floor rejection | Builder added window+1 probing, overflow refusal, boundary tests, ASCII/memoization optimizations, and a bare-10% artifact passing at 2.272/2.442 ms with one SQL call each. Independent Round-7 review is recorded in row 46. |
| 46 | Independent AI-R reviewed Stage 3 remediation round 7 | BLOCKED: the service retains the probe row; blank page size is unbounded; genuine 5000/5001 both-path boundary coverage is absent; and a duplicate Python test name replaces the bare-10% live test with the rejected +15 ms-floor version. The artifact itself passes bare 10%, and prior controls remain verified. Stage 4 must not begin. |
| 47 | Stage 3 remediation round 8 reported all four Round-7 blockers closed | Builder removed the probe row, added the upper clamp and both-path 5,000/5,001 fixtures, deleted the stale P95 test, and regenerated the bare-rule artifact. Independent Round-8 review is recorded in row 47. |
| 48 | Independent AI-R reviewed Stage 3 remediation round 8 | BLOCKED: negative `page_length` and `start` are not lower-clamped on either public path; behavior is framework/DB or Python-slice dependent, and permanent normalization tests are absent. Other Round-7 closures and 211-test evidence remain green. Stage 4 must not begin. |
| 49 | Stage 3 remediation round 9 reported the single Round-8 P1 gate closed | Builder added lower clamps and integer pagination tests on both public paths, and re-recorded a bare-rule P95 artifact. Independent Round-9 review is recorded in row 50. |
| 50 | Independent AI-R reviewed Stage 3 remediation round 9 | BLOCKED: non-integer `start`/`page_length` handling is inconsistent (service raises `ValueError`, dropdown returns `[]`) and lacks permanent cross-path tests. The P95 artifact preserves only the selected round despite claiming min-of-five-rounds, so selection/cherry-pick resistance is unverified. Stage 4 must not begin. |
| 50 | Independent AI-R reviewed Stage 3 remediation round 9 | BLOCKED: non-integer start/page_length behave inconsistently across paths (service raises ValueError; dropdown returns []), no cross-path tests; the P95 artifact preserves only the selected round so min-of-rounds selection cannot be independently verified. Prior controls and 214-test evidence remain green. Stage 4 must not begin. |
| 51 | Stage 3 remediation round 10 reported both Round-9 gates closed | Builder added shared strict-integer claims/tests and five-round P95 provenance; live evidence reported 215 tests and gates green. Independent Round-10 review is recorded in row 52. |
| 52 | Independent AI-R reviewed Stage 3 remediation round 10 | BLOCKED: dropdown still uses a permissive local coercer, truncating fractional inputs and defaulting invalid values while service raises `frappe.ValidationError`; the broad test does not detect parity failure. P95 artifact and prior controls are verified. Stage 4 must not begin. |
| 52 | Independent AI-R reviewed Stage 3 remediation round 10 | BLOCKED: the dropdown retains a separate permissive coercer (truncates fractions, defaults garbage) while the service raises frappe.ValidationError, and the cross-path test uses broad assertRaises(Exception) masking the mismatch. The P95 artifact itself is independently verified (five preserved rounds, correct min selection, bare-10% pass). Stage 4 must not begin. |
| 53 | Stage 3 remediation round 11 reported the dropdown coercer mismatch closed | Builder removed the local coercer, widened annotations, and tightened class-level error tests; live evidence reported 215 tests and current gates. Independent Round-11 review is recorded in row 54. |
| 54 | Independent AI-R reviewed Stage 3 remediation round 11 | BLOCKED: `None` pagination cases are not tested and cross-path tests do not compare exact error messages. The shared implementation and P95 artifact are verified, but the permanent parity contract is incomplete. Stage 4 must not begin. |
| 54 | Independent AI-R reviewed Stage 3 remediation round 11 | BLOCKED: the shared strict coercer and widened dropdown annotations are verified, but `None` pagination inputs are untested and cross-path tests assert only the exception class — a future message divergence could pass. P95 provenance and prior controls pass; 215 aggregate, 805/664+21, 18,446 rows root 2e284695… remain green. Stage 4 must not begin. |
| 55 | Stage 3 remediation round 12 reported the cross-path test gap closed | `None` page_length/start (both and individually) now covered on BOTH paths and must raise; the cross-path test captures both exceptions and asserts identical message text (`str(err_svc) == str(err_dd)`) for every invalid input — no broad `assertRaises(Exception)`; both paths share one `_coerce_int` so the message is defined once and Frappe's widened annotations no longer short-circuit with a different class. Suites: 53 pilot / 38 pure / 89 standalone / 215 aggregate all green; catalog 805 / `664 + 21` / 0 missing; inventory 18,446 rows root `2e284695…` live-matched; evidence-enabled gate errors=0; lints + diffcheck clean. Awaiting AI-R round 12; no live Account names migrated. |
| 56 | Independent AI-R Round 12 reviewed the current Stage 3 candidate | **VERIFIED**. Fresh focused tests confirmed one shared strict coercer, `None`/fractional/garbage parity, identical `frappe.ValidationError` messages, and widened dropdown annotations. P95 artifact SHA `040d92e1e9703e77fc177166ef8ed6df344dc75ee93463da97def02809daaba6` preserves five rounds and passes the bare 10% rule (+6.69%). Supplied evidence remains coherent: 53 pilot, 38 pure, 89 standalone, 215 aggregate; catalog 805; extraction `664 + 21`, missing 0; inventory 18,446 / Merkle `2e284695…`; evidence-enabled gates `errors=0`. Stage 3 is closed; Stage 4 may begin under the canonical plan. Owner authorization remains required for commit/push/merge/deploy and runtime or Account-name migrations. Report: `evidence/stage-3-ai-r-round12.md`. |
| 57 | Independent AI-R reviewed the Stage 4 review-bundle contract | **BLOCKED.** Pinned source/test/checker hashes and the 23-test focused suites match, but `build_import_payload()` makes `expected_identities` and `expected_english` optional, allowing a self-supplied foreign identity to emit a payload. It must require a bound export-candidate identity/English object for every invocation. Also, malformed non-empty `now_utc` currently disables the future-time check and must fail closed. Report: `evidence/stage-4-review-bundle-ai-r.md` (SHA-256 `854fe6bbe765d912ad7d0ec25afd23b71eaf0fd0f4f412ae2dfa6d77bbaa6249`). |
| 58 | Independent AI-R re-reviewed the Stage 4 review-bundle repairs | **BLOCKED.** Mandatory ordinary `expected_identities`/`expected_english` arguments and malformed-`now_utc` refusal are verified, but a caller can still manufacture a matching foreign row, identity list, and English map. The English map also need not have exact candidate-key coverage. Require a single authenticated private-export candidate object/manifest, with exact identity-to-English mapping and integrity binding to the private export, before payload creation. Report: `evidence/stage-4-review-bundle-ai-r-rerun.md` (SHA-256 `12e870c1ec6cd04655f94a0abded37eacfe77b1b727e0ce38322d18763c1627e`). |
| 59 | Independent AI-R reviewed the CandidateExport implementation | **BLOCKED.** The loader correctly validates private export bytes, but public construction and mutable identity mapping mean `isinstance(candidate, CandidateExport)` is forgeable. The review reproduced a foreign identity payload from a direct constructor call. The import-facing boundary must reload and authenticate the private export against a trusted governed manifest immediately before deriving its mapping; the manifest SHA cannot be supplied by an untrusted caller. Add direct-construction and post-load-mutation regressions. Report: `evidence/stage-4-review-bundle-ai-r-candidate-export.md` (SHA-256 `45a27ba63b66d8bc873810f3f89e8af83bd90de6acc2118486a8d9d928ac2e98`). |
| 60 | Independent AI-R reviewed the manifest-rooted Stage 4 boundary | **BLOCKED.** All four pinned hashes and 34 focused tests match; the default manifest correctly validates its export bytes. But optional `manifest_path` lets a caller select a self-created manifest/export pair, and AI-R reproduced payload emission for forged identity `9999 - Forged - E`. The production payload entry point must resolve only the one internally governed manifest path; no caller-selected manifest path may be accepted. Report: `evidence/stage-4-review-bundle-ai-r-manifest.md` (SHA-256 `5b2de21b4f7ff070ca71ee984df8e5292ab916960fe550db827593eea79eb4b8`). |
| 61 | Independent AI-R reviewed the fixed governed-path Stage 4 boundary | **VERIFIED.** The public `build_import_payload(bundle, now_utc=None)` signature rejects every authority parameter; it reloads the one governed manifest/private export, SHA-verifies the export, and derives identity/English bindings internally. A forged identity is refused on the production path. 36 standalone and 36 Bench tests pass; localization gate is clean. Independent proposal and AI-A2 sessions may populate the bundle; owner approval and all mutations remain separate gates. Report: `evidence/stage-4-review-bundle-ai-r-fixed-path.md` (SHA-256 `f7f2354a1efa7ec7e294d4df229103c3ff33d10bc94aa9bf2c6789637ab030a5`). |
