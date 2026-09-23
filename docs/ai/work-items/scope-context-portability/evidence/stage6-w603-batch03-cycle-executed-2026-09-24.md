# Stage 6 — W6-3 Stock batch-03 cycle (test site, 2026-09-24)

## Scope and authorization

Executed only the owner-approved 234-row CSV on `v16.localhost`:

- Scope: `docs/translation/stage6_w603_batch03_rows_2026-09-23.csv`, SHA-256 `a5f0e9f604ea52d89072d2c744864fdcbc733bc8307fd427a5c2658f4855dbc9`.
- Final proposal SHA-256 `0b9f7a86923b4c53fbf65dfa3d7b6bfbed2518fbfbbf5dedd2012c414bcb8025`; disposition record SHA-256 `cc232448ca848e9431af8063fdf0224c51ebb924c70f23aad22263e2dcda5657`.
- Independent AI-A1/A2/A3 all PASS; AI-R independently verified the exact scope, proposals, decision bundle, preserve set, and live pre-import dry-run. See the four review records alongside this report.

Exact partition: **111 quorum-released payload rows + 121 preserved Site Overrides + 2 technical exceptions (`UPC`, `UPC-A`) = 234**. No other batch or production scope was included.

## Test-site result

- Live import created **111**, updated 0, skipped 2,540; drift 0.
- Final importer dry-run: **2,651 total / 0 created / 0 updated / 2,651 skipped / 0 drift**.
- Catalog sync: 0 created / 0 updated.
- Catalog now has **2,651 Released** rows; the 121 pre-existing Site Overrides were kept unchanged.
- Inventory: **21,068 rows**, live Merkle `57951175001159a0187ef6ea876b06ee67ae9b13f63524fa7cb89f9456f8e70c`.
- Freshness: `critical_pass=true`, packaged rows 2,651, runtime digest `5060fb01663fdce4b3a68b09c73d780f0ce07353498da6cd5f6e188c0db69670`.

## Verification

- Hardened UAT preflight: PASS — Redis 13000/11000 PING, site ping 200, fresh `ar` boot, 12,953 boot messages, representative batch key, logout.
- Headless Arabic Desk verification: **8/8 PASS**, including exact `__()` and boot-message matches for all **232** release/preserve strings, Arabic DOM, no page errors, and logout. See `raw-logs/stage6-w603/browser_evidence_w603_batch03.json` and screenshot.
- Module suite: **270/270**; standalone localization gate tests: **91/91**.
- Scope metadata lint, translation-write lint, `git diff --check`, scoped gate, vendor audit: all PASS.
- Stage-2 evidence bundle regenerated atomically: ten envelopes + index bound to pre-commit HEAD `fb3e056d90047697015b9f53ca8d54b4e68f32b1`. Evidence-inclusive localization gate on that HEAD: **errors=0**. A later closure commit makes the established single `evidence-index-head` mismatch expected until the next approved catalog event/re-pin.

## Credential/setup note

The first interactive-console attempt exited before running UAT. During recovery, the local test Administrator password was briefly set to the literal placeholder `test`; it was immediately replaced with a generated random credential before UAT, and the subsequent UAT credential was rotated again in a `finally` teardown. Final Administrator language is `en`. No production credentials or site were involved; no generated secret was recorded in argv or evidence. This is recorded for a complete audit trail.

**W6-3 batch-03 is CLOSED for the test site only.** No Stage-8 or production action was performed or authorized. `v16.localhost/` remains an untracked local log directory and was not modified or staged.
