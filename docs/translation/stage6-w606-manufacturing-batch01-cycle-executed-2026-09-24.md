# W6-6 Manufacturing Batch 01 — governed cycle closed

Date: 2026-09-24
Site: `v16.localhost` (non-production test only)
Pre-commit HEAD pinned by the Stage-2 evidence index: `30c6277a6b128a712d69001bf2958cf68dd1979e`

## Authorized scope and disposition

The owner approved exactly the 250-row CSV at
`docs/translation/stage6_w606_manufacturing_batch01_rows_2026-09-24.csv`, SHA-256
`0d5098f61e2f97d26fa40e4e8b5d3b90ab1ec22e9dafd543564cb07ec8d39286`.
No rows outside Manufacturing Batch 01 were processed; the remaining 200 Manufacturing rows remain untouched.

| Final disposition | Rows | Action |
|---|---:|---|
| Quorum-approved payload | 83 | Released and imported as v1.7 (`ct_app=erpnext`) |
| Existing Site Overrides | 167 | Preserved unchanged; not imported |
| Technical Exceptions | 0 | None required in this scope |
| **Total** | **250** | **83 + 167 + 0** |

AI-A1, AI-A2, and AI-A3 independently passed the final proposal SHA-256
`d64adaa6f9d6d201623dfbd4156dd414c000abd389d3864643994aba3bbfdfb9`.
AI-R independently passed the complete evidence-inclusive bundle on the exact
pre-commit HEAD; its record is
`docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch01-ai-r-2026-09-24.md`.
The A1/A2/A3 records are in the same evidence directory:
- AI-A1 (Linguistic): `docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch01-ai-a1-2026-09-24.md`
- AI-A2 (Domain): `docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch01-ai-a2-2026-09-24.md`
- AI-A3 (Structural): `docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch01-ai-a3-2026-09-24.md`

All 167 existing Site Overrides on `v16.localhost` were preserved verbatim without alteration.

## Final live state and verification

- Approved catalog: **3,161 → 3,244 Released**; catalog file SHA-256
  `cbe5961bdc3d45c4af03a5fa3b3a55413ae996622187be485295a79564478319`.
- Decisions: 3,244 content-bound decisions; file SHA-256
  `c2e6da428e4a70b2037820faa39487df173eace77fb79d44d92979ed2cbf785e`.
- Final live importer dry-run: **3,244 total / 0 created / 0 updated /
  3,244 skipped / drift 0**. Translation health reports no drift, duplicates,
  or orphan Site Overrides. All 83 released values and 167 preserved values
  match live readback.
- UAT preflight: **PASS** — Redis 13000/11000, site HTTP 200, fresh `ar` Desk
  boot, 13,546 messages (+83 new), representative key `Learn Manufacturing` present, session logged out.
- Browser: **8/8 checks PASS**; **250/250** payload/preserved lookups match,
  Arabic DOM rendered, no page errors, logout observed. Raw JSON and screenshot
  are in `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w606-mfg-batch01/`.
- Tests: standalone localization-gate suite **92/92**; targeted module suite
  **271/271**.
- Full evidence-inclusive localization gate: **errors=0** on pre-commit HEAD
  `30c6277a6b128a712d69001bf2958cf68dd1979e`; scoped gate, vendor audit,
  scope-metadata lint, translation-write lint, and `git diff --check` passed.
- Inventory: **21,661 rows**, Merkle
  `a86152119e6c0fa08fa8bc6d91805aa93feec776e774dd2c642d2ff4197626c3`;
  freshness `critical_pass=true`, no runtime drift.
- Evidence: ten envelopes and index regenerated atomically and validated by
  the evidence-inclusive gate. As designed, committing this closure record
  advances HEAD beyond the pinned pre-commit HEAD; that single HEAD binding is
  expected to remain stale until the next approved catalog-change re-pin.

## Boundaries and teardown

Only the local test site was used. Administrator language was restored to
English, the temporary password was rotated, temporary credentials cleared,
and UAT/browser sessions logged out. The pre-existing untracked
`v16.localhost/` directory was not staged or changed. Stage 8, production,
the remaining 200 Manufacturing rows, and pushing to `origin` were not
authorized by this scope and remain untouched.
