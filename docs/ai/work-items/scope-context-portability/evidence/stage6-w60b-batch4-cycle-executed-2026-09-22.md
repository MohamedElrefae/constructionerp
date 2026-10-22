# Stage 6 W6-0b — batch-4 governed cycle executed (test site, 2026-09-22)

Owner approval chain: W6-0b cut + proposal package → explicit batch split →
batches 1–3 closed/accepted (`55006db`, `ba66a80`, `6cbd6c6` + UAT `d0f9c5d`) →
batch-4 proposal package (`89dd15a`) → owner approved **batch 4 only** (exact 271-row CSV
sha `21dcdd54…` + 21 technical exclusions unchanged; full governed cycle on `v16.localhost` only;
no Stage 8, no production, no batches 05–07).

Batch-4 scope CSV:
`docs/translation/stage6_w60b_batch04_rows_2026-09-22.csv`
(sha256 `21dcdd54164c5086b84ecd1e2c87979d6c1436fa663efced949b1fea573bad64`).

## 1. Scope & Disposition Reconciliation (Total 271 Rows)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **256** | Released into managed override catalog (`approved_ar_overrides.csv`) |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **12** | Source-equal technical rows; kept as vendor rendering |
| `preserved-site-override (not imported, plan §12)` | **3** | Existing site overrides preserved (case-insensitive match) |
| **Total approved batch 4** | **271** | Exact match to approved scope CSV (sha256 `21dcdd54…`) |

### Accounting for Technical Exclusions: 21 Shared Exclusions vs. 12 Batch-4 Technical Exceptions

There are two distinct categories of technical exclusions under W6-0b governance:

1. **Shared W6-0b Out-of-Band Exclusions (21 rows)**:
   Documented in `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (sha256 `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095`).
   These 21 rows are permanent technical exclusions (symbols, HTML fragments, `${...}`) removed from the 1,915-row cut to produce the 1,894 candidate rows. They are **outside all batches** (batches 01–07) and remain permanently excluded across all cycles.

2. **Batch-4 In-Scope Technical Exceptions (12 rows)**:
   Within the 271 rows of Batch 4, exactly 12 rows were confirmed by the quorum panel as `EXCEPTION-technical`:
   `Client URI`, `Client Metadata`, `Client Secret Basic`, `Client Secret Post`, `Code Challenge`, `Condition JSON`, `Form Dict`, `JS Message`, `Header, Robots`, `Logo URI`, `Introspection URI`, `Normalized Query`.

### Preserved Site Overrides (3):
| Batch key | Runtime `source_text` (DB, exact casing) | Preserved Arabic | Origin |
|---|---|---|---|
| `Client Id` | `Client ID` | معرف العميل | `Site Override` |
| `Delimiter Options` | `Delimiter options` | خيارات الفاصل | `Site Override` |
| `Missing Field` | `Missing field` | حقل مفقود | `Site Override` |

Note: scope keys match case-insensitively (plan §12). Browser probes use exact DB `source_text` casing so `__()` resolves the preserved runtime rows.

### Released payload correction (in-cycle, fail-closed)
Initial build briefly left 3 Released rows source-equal (`MIT License`, `MariaDB Variables`, `Normalized Copies`). Gate `csv-source-equal` failed closed; quorum translations were corrected to `ترخيص MIT` / `متغيرات MariaDB` / `نسخ مُطبّعة`, catalog + runtime DB rows re-bound, decisions re-recorded, payload CSV regenerated. Final catalog has **zero** source-equal Released rows.

---

## 2. Quorum Governance & AI-R Review Artifacts

- **Site Recon**: `docs/translation/stage6_w60b_batch04_site_recon_2026-09-22.py` → `.json` (sha256 `eebc35baf8097ea9ff7a4e66803ad65d7b565fcafc09cb9819d22a2e8ed715f3`)
- **Panel Build Script**: `docs/translation/stage6_w60b_ai_proposal_build_batch04_2026-09-22.py`
- **Applied Payload CSV**: `docs/translation/stage6_w60b_payload_applied_rows_batch04_2026-09-22.csv`
  (sha256 `28f6e5fd7129a1db3e6523226864ca21f6455f1228deb01873e786cfa0784182`)
- **Quorum Review Records**:
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a1-batch4-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a2-batch4-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a3-batch4-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-r-batch4-2026-09-22.md`
- **Release Decisions Ledger**: `construction/data/translations/release_decisions.json`
  - Total recorded decisions: **1,439** (binding batch-4 `decision_ref: content:docs/translation/stage6_w60b_payload_applied_rows_batch04_2026-09-22.csv`)
  - sha256: `cbdcdbe4f34b5407c3f707486bc3a5dffc9d5845e0380f8fb16e9cad3ed31e5c`

---

## 3. Governed Importer Runs (`v16.localhost` only)

1. **Pre-import DRY Run** (catalog 1,439):
   `total=1439, created=0, updated=0, skipped=1439, drift=0`
   (256 batch-4 runtime rows already present from the in-cycle import; 3 corrected keys re-bound to Arabic)
2. **IMPORT Execution**:
   `total=1439, created=0, updated=0, skipped=1439, drift=0` (idempotent)
3. **Post-import Idempotent DRY Run**:
   `total=1439, created=0, updated=0, skipped=1439, drift=0` (100% idempotent, zero drift)

Catalog: `approved_ar_overrides.csv` **1183 → 1439** (+256 Released).
Gate pin: `EXPECTED_DRYRUN = {"total": 1439, "created": 0, "updated": 0, "skipped": 1439, "drift": 0}`.

---

## 4. Fresh Runtime & Evidence Verification Gates

1. **Runtime Freshness Collector**:
   - `packaged_rows`: **1,439**
   - `critical_pass`: `true`
   - `runtime_digest`: `eb03c87a6a6fef970e5e7341812ad7983c42a592f2f10c946f0b9a3d0d0fa4ea`
   - sha256: `2eb0490f869acd0e710685f594b3b26b6e4a2954c9ac40e88ead137258c5d8dc`
2. **Inventory Manifest & Merkle**:
   - `rows`: **19,856** (`19,600 + 256 = 19,856`)
   - `root`: `c048467d0fa825ae01bd310daf47c7047298103c0f83223e31fd8dfc49dc9f1c`
   - `LIVE_MATCH`: `True`
3. **Full Localization Gates**:
   - `python3 scripts/check_localization_gates.py` → **`errors=0`**, exit code `0`.
   - Gate counts: `po: 810`, `csv_rows: 1439`, `files: 265`, `json_labels: 22`, `missing: 0`, `wrapped: 667`.
4. **Standalone Gate Test Suite**:
   - `python3 construction/tests/test_localization_gates.py` → **91/91 tests PASS (`OK`)**.
5. **Evidence Assembler** (10 envelopes + index):
   - `python3 construction/tests/tools/stage2_evidence_assemble.py` → assembled 10 envelopes + index; aggregate 270 tests.
   - index: `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt`
   - sha256: `a1bd68c5df4bea0a3dd94b9565320c904b91890f86544f0548de0930a115fe71`
6. **Lint suite**:
   - `lint_scope_metadata.py` PASS, `lint_translation_writes.py` PASS, `git diff --check` clean.

---

## 5. UAT Preflight & Arabic Browser Session Evidence

### Hard Preflight Gate (`scripts/uat_preflight.py`):
```
PASS redis-cache: port 13000 PING ok
PASS redis-queue: port 11000 PING ok
PASS site-http: /ping 200
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=11741
PASS desk-boot-key: 'Click here' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

### Headless Playwright Browser DOM Verification:
- **Test Script**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch04.py`
- **Result Summary**: **23/23 checks PASS (0 FAIL)**, exit code `0`.
- **Structured Log**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch04.json`
  (sha256 `e11b49763ad040c22fcb2deda7de112d9e4996b5eed912ebd5112c3393742195`)
- **Visual Capture**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser-ar-desk-batch04.png`

**Verified Browser Checks & Rendered Strings**:
- `boot.lang`: `ar`
- `boot.__messages`: **11,741** entries
- Client `__()` in-page resolution **14/14 PASS**:
  - `Click here` → `انقر هنا`
  - `Desk Settings` → `إعدادات المكتب`
  - `Desk Theme` → `سمة المكتب`
  - `Desktop Settings` → `إعدادات سطح المكتب`
  - `Download Template` → `تنزيل القالب`
  - `Email Domain` → `نطاق البريد الإلكتروني`
  - `Form Builder` → `منشئ النماذج`
  - `Login Methods` → `طرق تسجيل الدخول`
  - `MIT License` → `ترخيص MIT`
  - `MariaDB Variables` → `متغيرات MariaDB`
  - `Normalized Copies` → `نسخ مُطبّعة`
  - `Client ID` → `معرف العميل` (site override preserve verified in browser)
  - `Delimiter options` → `خيارات الفاصل` (site override preserve verified in browser)
  - `Missing field` → `حقل مفقود` (site override preserve verified in browser)
- Placeholder handling: `Cannot {0} {1}.` with args `['delete', 'item']` → `لا يمكن delete item.`
- Rendered DOM text:
  - 13 unique Arabic words extracted from body
  - Rendered Workspace module cards: `الأدوات`, `المحاسبة`, `المشتريات`, `المشاريع`, `المخزون`, `البيع`
  - Arabic Sidebar items present
- Security teardown: UAT temporary credentials rotated; `Administrator.language` restored to `en`.

---

## 6. Pre-Commit Artifact Hashes

| Artifact | sha256 |
|---|---|
| `approved_ar_overrides.csv` (1439 Released) | `8fa2cae8c4e6cc667a0f006e6524d6a0f43999bac8b6f47bde0cc9a796388679` |
| `release_decisions.json` (1439) | `cbdcdbe4f34b5407c3f707486bc3a5dffc9d5845e0380f8fb16e9cad3ed31e5c` |
| `freshness_evidence.json` | `2eb0490f869acd0e710685f594b3b26b6e4a2954c9ac40e88ead137258c5d8dc` |
| `localization_manifest.json` | `4ae627881b196f91ac3c4ac2520f7dd37f3c40cdb0fd1a1ea60addcf5edc67f0` |
| `stage2_inventory_manifest.json` | `816fa6143a184a707052c1bb8ec36565a8480fda0eae5af83fc17c3b59b69e8e` |
| `vendor_catalog_baseline.json` | `fb061d54ad1dc96f4c0326358fe46806b7e3542bcf8f697e17d013995162c637` |
| `test_localization_gates.py` | `7550445f626b9e78e9709c3552bab5739a1ca2398b6bb2dc794dbdae40af1b2d` |
| `scripts/check_localization_gates.py` | `863f02a08decd0bd37c78475162d357dcefc8830561adbbd2f87f2704157e526` |
| batch-4 payload CSV (271 dispositions) | `28f6e5fd7129a1db3e6523226864ca21f6455f1228deb01873e786cfa0784182` |
| batch-4 scope CSV (271) | `21dcdd54164c5086b84ecd1e2c87979d6c1436fa663efced949b1fea573bad64` |
| evidence index | `a1bd68c5df4bea0a3dd94b9565320c904b91890f86544f0548de0930a115fe71` |
| browser evidence JSON | `e11b49763ad040c22fcb2deda7de112d9e4996b5eed912ebd5112c3393742195` |
| site recon JSON | `eebc35baf8097ea9ff7a4e66803ad65d7b565fcafc09cb9819d22a2e8ed715f3` |

---

## 7. Strict Boundaries Honored

- Exact 271 rows from `docs/translation/stage6_w60b_batch04_rows_2026-09-22.csv` processed; zero candidate rows beyond approved scope.
- Batches 05–07 untouched, not cut, not proposed, not imported.
- Stage 8 not started; production mutation remains `production_mutation_authorized: false`.
- All operations conducted exclusively on non-production test site `v16.localhost`.
