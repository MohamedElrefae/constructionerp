# W6-4 Projects + Subcontracting batch-01 — governed cycle closed

Date: 2026-09-24
Site: `v16.localhost` (non-production test only)
Pre-commit HEAD pinned by the Stage-2 evidence index: `eaadb0141e8695dcd1afc9acf27e1d6c42322311`

## Authorized scope and disposition

The owner approved exactly the 147-row CSV at
`docs/translation/stage6_w604_projects_boq_rows_2026-09-24.csv`, SHA-256
`93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe`.
No rows outside Projects + Subcontracting were processed.

| Final disposition | Rows | Action |
|---|---:|---|
| Quorum-approved payload | 48 | Released and imported as v1.7 (`ct_app=erpnext`) |
| Existing Site Overrides | 96 | Preserved unchanged; not imported |
| Deferred | 3 | Blank, excluded from release and import |
| **Total** | **147** | **48 + 96 + 3** |

AI-A1, AI-A2, and AI-A3 independently passed the final proposal SHA-256
`a9b9abaf3111b5ca0310aa7c3291f4c45e7fc04807242894848c707542694e2c`.
AI-R independently passed the complete evidence-inclusive bundle on the exact
pre-commit HEAD; its record is
`docs/ai/work-items/scope-context-portability/evidence/stage6-w604-ai-r-2026-09-24.md`.
The A1/A2/A3 records are in the same evidence directory.

The three explicit deferrals are:

- `Progress % for a task cannot be more than 100.` — formatter ambiguity;
- ` Summary` — a dynamic source fragment, not a standalone runtime key;
- `Distribute Additional Costs Based On ` — edge whitespace is stripped by the governed importer, so the exact source cannot bind safely.

An initial 50-row draft exposed the last two runtime-key normalization issues
through the freshness check. The two corresponding rows created by that draft
were identified exactly and removed from the test site; the package was rebuilt
and independently rechecked at 48 releases. No production site was accessed.

## Final live state and verification

- Approved catalog: **2,651 → 2,699 Released**; catalog file SHA-256
  `177e6db8874743172637cacc366b68e58312f7b061e697c262bf53a5e9af586f`.
- Decisions: 2,699 content-bound decisions; file SHA-256
  `5ef185a9a74467ea049468a3682697ec45c91d213b20a98a97d0bf3782cf77f0`.
- Final live importer dry-run: **2,699 total / 0 created / 0 updated /
  2,699 skipped / drift 0**. Translation health reports no drift, duplicates,
  or orphan Site Overrides. All 48 released values and 96 preserved values
  match live readback.
- UAT preflight: **PASS** — Redis 13000/11000, site HTTP 200, fresh `ar` Desk
  boot, 13,001 messages, representative key present, session logged out.
- Browser: **8/8 checks PASS**; **144/144** payload/preserved lookups match,
  Arabic DOM rendered, no page errors, logout observed. Raw JSON and screenshot
  are in `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w604/`.
- Tests: standalone localization-gate suite **92/92**; targeted module suite
  **271/271**.
- Full evidence-inclusive localization gate: **errors=0** on pre-commit HEAD
  `eaadb0141e8695dcd1afc9acf27e1d6c42322311`; scoped gate, vendor audit,
  scope-metadata lint, translation-write lint, and `git diff --check` passed.
- Inventory: **21,116 rows**, Merkle
  `c62fb5396398a001b1c885474a4bf3c64030aa3b788ac1a4a1b2375334c162e4`;
  freshness `critical_pass=true`, no runtime drift.
- Evidence: ten envelopes and index regenerated atomically and validated by
  the evidence-inclusive gate. As designed, committing this closure record
  advances HEAD beyond the pinned pre-commit HEAD; that single HEAD binding is
  expected to remain stale until the next approved catalog-change re-pin.

## Boundaries and teardown

Only the local test site was used. Administrator language was restored to
English, the temporary password was rotated, the temporary secret file was
removed, and UAT/browser sessions logged out. The pre-existing untracked
`v16.localhost/` directory was not staged or changed. Stage 8, production,
other Stage-6 batches, and pushing to `origin` were not authorized by this
scope and remain untouched.
