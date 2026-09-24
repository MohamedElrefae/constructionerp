# W6-5 Setup Batch — governed cycle closed

Date: 2026-09-24
Site: `v16.localhost` (non-production test only)
Pre-commit HEAD pinned by the Stage-2 evidence index: `51b8b73917047014776b3340c799129de92b4428`

## Authorized scope and disposition

The owner approved exactly the 469-row CSV at
`docs/translation/stage6_w605_setup_rows_2026-09-24.csv`, SHA-256
`e2d672c4a1b479f9cd52c017f76a3c8a8b1b24dced24ed4b5f5c6d8113900a09`.
No rows outside Setup were processed.

| Final disposition | Rows | Action |
|---|---:|---|
| Quorum-approved payload | 349 | Released and imported as v1.7 (`ct_app=erpnext`) |
| Existing Site Overrides | 107 | Preserved unchanged; not imported |
| Technical UOM Exceptions | 13 | Classified as EXCEPTION-technical with empty translations to retain vendor rendering |
| **Total** | **469** | **349 + 107 + 13** |

AI-A1, AI-A2, and AI-A3 independently passed the final proposal SHA-256
`7b0a4215c710d0c7f9469ee76d3be7ea1d964767d605acd465282294e7578970`.
AI-R independently passed the complete evidence-inclusive bundle on the exact
pre-commit HEAD; its record is
`docs/ai/work-items/scope-context-portability/evidence/stage6-w605-ai-r-2026-09-24.md`.
The A1/A2/A3 records are in the same evidence directory.

The 13 explicit technical UOM exceptions are:
- `Ampere-Hour`, `Ampere-Minute`, `Ampere-Second`, `Gram-Force`, `Horsepower-Hours`,
  `Kilogram-Force`, `Kilopound-Force`, `Kilowatt-Hour`, `Litre-Atmosphere`,
  `Ounce-Force`, `Pound-Force`, `Volt-Ampere`, `Watt-Hour`.

All 107 existing Site Overrides on `v16.localhost` (including FIFO `الأول داخل أول خارج` and LIFO `الأخير داخل أول خارج`) were preserved verbatim without alteration.

## Final live state and verification

- Approved catalog: **2,699 → 3,048 Released**; catalog file SHA-256
  `fbc40cdc4e4fb36d7ac94c1c08b14a584198e6668c3554caf58a4f2f854073a2`.
- Decisions: 3,048 content-bound decisions; file SHA-256
  `e77fb439c4f009c5056fd6065fced2ee77598b5374da9868145b46efda374102`.
- Final live importer dry-run: **3,048 total / 0 created / 0 updated /
  3,048 skipped / drift 0**. Translation health reports no drift, duplicates,
  or orphan Site Overrides. All 349 released values and 107 preserved values
  match live readback.
- UAT preflight: **PASS** — Redis 13000/11000, site HTTP 200, fresh `ar` Desk
  boot, 13,350 messages, representative key present, session logged out.
- Browser: **8/8 checks PASS**; **456/456** payload/preserved lookups match,
  Arabic DOM rendered, no page errors, logout observed. Raw JSON and screenshot
  are in `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w605/`.
- Tests: standalone localization-gate suite **92/92**; targeted module suite
  **271/271**.
- Full evidence-inclusive localization gate: **errors=0** on pre-commit HEAD
  `51b8b73917047014776b3340c799129de92b4428`; scoped gate, vendor audit,
  scope-metadata lint, translation-write lint, and `git diff --check` passed.
- Inventory: **21,465 rows**, Merkle
  `8d8301d16455f5e01ca9fb31e88c86c038446e54bb45e4cc455bbd9ff4f08249`;
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
