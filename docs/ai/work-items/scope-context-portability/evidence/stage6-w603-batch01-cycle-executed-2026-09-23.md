# Stage 6 — W6-3 batch-01 governed cycle executed (test site, 2026-09-23)

## Authorization and boundary

Owner approval was limited to the exact 250-row scope CSV `docs/translation/stage6_w603_batch01_rows_2026-09-23.csv`, sha256 `5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380`, on `v16.localhost`. W6-3 batches 02 and 03 remain unapproved. Stage 8 and production remain gated; no production mutation was performed.

## Final disposition

The initial build classified 125 rows as payload. The governed gate identified seven formula/letter tokens (`A - B`, `A - C`, `D - E`, `G - D`, `H - F`, `I - J`, `I - K`) as source-equal and unsuitable for the Released payload. They were reclassified as `EXCEPTION-technical`, removed from the catalog payload, and the seven corresponding runtime rows were removed from the test site.

| Disposition | Rows |
|---|---:|
| Preserved site override | 115 |
| EXCEPTION-technical | 17 |
| Already released | 0 |
| Quorum-confirmed payload | 118 |
| **Total** | **250** |

The repaired `%` translation retains the source placeholder. Final catalog: 2,319 → **2,437** Released rows.

## Governed cycle

- Pre-import DRY: `total=2437 created=0 updated=1 skipped=2436 drift=0`.
- IMPORT: `total=2437 created=0 updated=1 skipped=2436 drift=0` (`IMPORT_OK`).
- Post-import DRY: `total=2437 created=0 updated=0 skipped=2437 drift=0` (`POST_DRY_IDEMPOTENT_OK`).
- Catalog sync dry and real: `created=0 updated=0` both times.
- Release decisions: **2,437** recorded; sha256 `14278d8306766aa799c78b8dcd0769cfe48f4faa104dbddc15bfdea9b77a0ef3`.
- Freshness: `packaged_rows=2437`, `critical_pass=true`, `has_drift=false`, runtime digest `bda154122dd8e71214044c18312a9b54b8584c554e802831c4bf58bcf303725f`.
- Inventory: **20,854** rows, Merkle root `04ba4a368184795aca1113b7239d3c44fff078ba335d5fcd987c539b9138d431`.
- Final-dryrun evidence: `2437/0/0/2437/0`, drift `0`.

## Verification

- Full localization gate: `errors=0`, `csv_rows=2437`.
- Standalone localization-gate suite: **91/91 OK**.
- Site module aggregate: **270/270 OK**.
- Scope lint, translation-write lint, and `git diff --check`: pass.
- Arabic UAT preflight: pass; fresh Desk boot `lang=ar`, 12,739 messages, batch key present.
- Arabic browser evidence: **21/21 PASS**, 0 failures.
- Evidence index: `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt`, sha256 `eba181bce1b93f50ae1614e079fa9a6736cf039fa4924eb833f0edccf83e7190`, bound to base HEAD `9a3f44fbd1fd4ab5a94da1bee86ef6db7bd77753`.
- Browser JSON sha256: `dfc42440b9e2917a5bd68be4f33a1cda47904e1a7aff514725c16bf21219617b`.
- Browser screenshot sha256: `0c4ed9acba6187cdf00a93f600da40d5d3bc2dda804885059823d5159a7ac391`.
- Teardown completed: temporary credential rotated to `ct-w60b-rotated-off` and `Administrator.language` restored to `en`.

## Final artifact hashes

- `construction/data/translations/approved_ar_overrides.csv`: `f762440740d97446dca6945c63da9754c9de3e90248641500d1c5aecfcfe7124`.
- `construction/data/translations/release_decisions.json`: `14278d8306766aa799c78b8dcd0769cfe48f4faa104dbddc15bfdea9b77a0ef3`.
- `construction/data/localization/freshness_evidence.json`: `f2d690ba5f19ee5ece97e48c1f3128976dc8229095eaf71633d1d0064b41b847`.
- `construction/data/localization/localization_manifest.json`: `68c44a7194db996bfa8d6f2af4b3305a869c61bb7e87679c8663d215e737bfb6`.
- `construction/data/localization/stage2_inventory_manifest.json`: `6bfb94263c9ff2a39eb30b563f94568e04d80d4965d59dbf9baac2f8e567bdee`.

## Result

**W6-3 batch-01 CLOSED on the authorized test site.** Batches 02/03 and production remain gated.
