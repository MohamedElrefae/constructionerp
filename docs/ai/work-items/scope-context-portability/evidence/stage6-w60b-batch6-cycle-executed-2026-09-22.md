# Stage 6 W6-0b — batch-6 governed cycle executed (test site, 2026-09-22)

Owner approval chain: W6-0b cut + proposal package → explicit batch split →
batches 1–5 closed/accepted (`55006db`, `ba66a80`, `6cbd6c6` + UAT `d0f9c5d`,
`89dd15a` / `396ae87`, `d26ed54`) → batch-6 proposal package (`f7a1c16`) →
owner approved **batch 6 only** (exact 270-row CSV sha
`68500fae981aacec08e9841fc858dfd43e7473c7b12156ac8ca528b678d309e0`; full
governed cycle on `v16.localhost` only; batch 7 deferred; no Stage 8, no
production).

Batch-6 scope CSV:
`docs/translation/stage6_w60b_batch06_rows_2026-09-22.csv`
(sha256 `68500fae981aacec08e9841fc858dfd43e7473c7b12156ac8ca528b678d309e0`).

## 1. Scope & Disposition Reconciliation (Total 270 Rows)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **258** | Released into managed override catalog (`approved_ar_overrides.csv`) |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **11** | Source-equal technical rows; kept as vendor rendering |
| `preserved-site-override (not imported, plan §12)` | **1** | Existing site override preserved (case-insensitive match) |
| **Total approved batch 6** | **270** | Exact match to approved scope CSV (sha256 `68500fae…`) |

### Accounting for Technical Exclusions: 21 Shared Exclusions vs. 11 Batch-6 Technical Exceptions

There are two distinct categories of technical exclusions under W6-0b governance:

1. **Shared W6-0b Out-of-Band Exclusions (21 rows)**:
   Documented in `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (sha256 `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095`).
   These 21 rows are permanent technical exclusions (symbols, HTML fragments, `${...}`) removed from the 1,915-row cut to produce the 1,894 candidate rows. They are **outside all batches** (batches 01–07) and remain permanently excluded across all cycles.

2. **Batch-6 In-Scope Technical Exceptions (11 rows)**:
   Within the 270 rows of Batch 6, exactly 11 rows were confirmed by the quorum panel as `EXCEPTION-technical`:
   `InnoDB`, `Geoapify`, `Keycloak`, `Nomatim`, `DocShare`, `Awesomebar`, `Mx`, `Code challenge method`, `Collapsible Depends On (JS)`, `Mandatory Depends On (JS)`, `By \"Naming Series\" field`.

### Preserved Site Overrides (1):
| Batch key | Runtime `source_text` (DB, exact casing) | Preserved Arabic | Origin |
|---|---|---|---|
| `City` | `City` | المدينة | `Site Override` |

Site recon: 273 case-insensitive matches; only `ct_origin == "Site Override"` preserved (1). Other non-empty rows import normally as Released. Browser probes use exact DB `source_text` casing so `__()` resolves the preserved runtime row.

---

## 2. Quorum Governance & AI-R Review Artifacts

- **Site Recon**: `docs/translation/stage6_w60b_batch06_site_recon_2026-09-22.py` → `.json` (sha256 `89e467c681b66add960e18b803cd43977a139cb6c037bd28e03bf73b863f9ef6`)
- **Panel Build Script**: `docs/translation/stage6_w60b_ai_proposal_build_batch06_2026-09-22.py`
- **Released List**: `docs/translation/stage6_w60b_batch06_released_list.txt` (258)
- **Applied Payload CSV**: `docs/translation/stage6_w60b_payload_applied_rows_batch06_2026-09-22.csv` (270 dispositions, tab-separated, no CSV quote-doubling so raw-text decision-binding substring check passes)
  (sha256 `744a5ecf896c88ab8333f3f6397039d1456c4e9d70367af0426ae42e869bc364`)
- **Quorum Review Records**:
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a1-batch6-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a2-batch6-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a3-batch6-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-r-batch6-2026-09-22.md`
- **Release Decisions Ledger**: `construction/data/translations/release_decisions.json`
  - Total recorded decisions: **1,949** (binding batch-6 `decision_ref: stage6-W6-0b batch-6 owner-approved 2026-09-22`)
  - sha256: `8e11094f9ee501860504d8a6a9b1e3c13d4f86413b6a0bc33d15730eac41c2ff`

---

## 3. Governed Importer Runs (`v16.localhost` only)

1. **Pre-import DRY Run** (catalog 1,949 after build append):
   `total=1949, created=258, updated=0, skipped=1691, drift=0`
2. **IMPORT Execution**: `IMPORT total=1949 created=258 updated=0 skipped=1691 drift=0` (258 Released rows bound to runtime)
3. **Post-import Idempotent DRY Run**:
   `total=1949, created=0, updated=0, skipped=1949, drift=0` (100% idempotent, zero drift) → `IDEMPOTENT_OK`
4. **Catalog Sync** (`sync_translation_catalog(dry_run=False)`): `created=0, updated=0` (no further writes required)

Catalog: `approved_ar_overrides.csv` **1691 → 1949** (+258 Released).
Gate pin: `EXPECTED_DRYRUN = {"total": 1949, "created": 0, "updated": 0, "skipped": 1949, "drift": 0}`.
`source_equal=0` on all 258 batch-6 decision refs.

---

## 4. Fresh Runtime & Evidence Verification Gates

1. **Runtime Freshness Collector**:
   - `packaged_rows`: **1,949**
   - `critical_pass`: `true`
   - `runtime_digest`: `6a4990428e1233b9eb57671c8bd6131f06937ff20920f0815d42be4c2c556545`
   - sha256: `96be5e2a50cc3d25a03bbe9834e0270ee3df3572924e973c0864fbb799aabb5a`
2. **Inventory Manifest & Merkle**:
   - `rows`: **20,366** (`20,108 + 258 = 20,366`)
   - `root`: `f8c526c947897504ce2e7b2a13d7881bf76a0ad4b1ce11175674714c676f8c4d`
   - `LIVE_MATCH`: `True`
   - `base_commit`: `f7a1c1648261c8944aa82c6677dfb568aad7af3c` (proposal HEAD at re-record)
   - sha256: `bb82ccda197fba25d463f4ce08c1b8f63c77c7b350a82bd9b73f8130a7d86d43`
3. **Full Localization Gates** (with evidence):
   - `python3 scripts/check_localization_gates.py` → **`errors=0`**, exit code `0`.
   - Gate counts: `po: 810`, `csv_rows: 1949`, `files: 265`, `json_labels: 22`, `missing: 0`, `wrapped: 667`.
4. **Standalone Gate Test Suite**:
   - `python3 construction/tests/test_localization_gates.py` → **91/91 tests PASS (`OK`)**.
5. **Evidence Assembler** (10 envelopes + index):
   - `python3 construction/tests/tools/stage2_evidence_assemble.py` → assembled 10 envelopes + index; aggregate 270 tests; HEAD `f7a1c1648261`.
   - index: `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt`
   - sha256: `66fd210e7efafbefb20a2b286f002a68c6cbe2fed1053ffee72b8f4cafee2f4f`
6. **Lint suite**:
   - `lint_scope_metadata.py` PASS, `lint_translation_writes.py` PASS, `git diff --check` clean.
7. **Scoped gate / Vendor audit**:
   - `--files` scoped gate: `errors=0`
   - `--audit-vendor-coverage`: `errors=0`

---

## 5. UAT Preflight & Arabic Browser Session Evidence

### Hard Preflight Gate (`scripts/uat_preflight.py`):
```
PASS redis-cache: port 13000 PING ok
PASS redis-queue: port 11000 PING ok
PASS site-http: /ping 200
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=12251
PASS desk-boot-key: '2 years ago' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

### Headless Playwright Browser DOM Verification:
- **Test Script**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch06.py`
- **Result Summary**: **21/21 checks PASS (0 FAIL)**, exit code `0`.
- **Structured Log**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch06.json`
  (sha256 `96bdd623b5414f6bee47e802159e8a397347373edf7d48961433ecbdc70397db`)
- **Visual Capture**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser-ar-desk-batch06.png`

**Verified Browser Checks & Rendered Strings**:
- `boot.lang`: `ar`
- `boot.__messages`: **12,251** entries
- Client `__()` in-page resolution **12/12 PASS**:
  - `2 years ago` → `منذ عامين`
  - `3 minutes ago` → `منذ 3 دقائق`
  - `5 days ago` → `منذ 5 أيام`
  - `Added` → `تمت الإضافة`
  - `API Key cannot be regenerated` → `لا يمكن إعادة إنشاء مفتاح API`
  - `About {0} minutes remaining` → `بقيت حوالي {0} دقائق`
  - `App not found for module: {0}` → `التطبيق غير موجود للوحدة: {0}`
  - `Error in Header/Footer Script` → `خطأ في سكربت الترويسة/التذييل`
  - `Footer HTML set from attachment {0}` → `تم تعيين HTML التذييل من المرفق {0}`
  - `API Endpoint Args should be valid JSON` → `يجب أن تكون وسيطات نقطة نهاية API قيمة JSON صالحة`
  - `Adds a custom client script to a DocType` → `يضيف سكربت عميل مخصصًا إلى نوع مستند`
  - `City` → `المدينة` (site override preserve verified in browser, exact DB casing)
- Placeholder handling: `App not found for module: {0}` with args `['Widgets']` → `التطبيق غير موجود للوحدة: Widgets`
- Rendered DOM text:
  - 13 unique Arabic words extracted from body
  - Rendered Workspace module cards: `الأدوات`, `المحاسبة`, `المشتريات`, `المشاريع`, `المخزون`, `البيع`
  - Arabic Sidebar items present
- Security teardown: UAT temporary credentials rotated; `Administrator.language` restored to `en`.

---

## 6. Pre-Commit Artifact Hashes

| Artifact | sha256 |
|---|---|
| `approved_ar_overrides.csv` (1949 Released) | `31cc9a5eaea8d4370814ce368b46d8937e328cdfcd0057a6c1e71e28c2aa3486` |
| `release_decisions.json` (1949) | `8e11094f9ee501860504d8a6a9b1e3c13d4f86413b6a0bc33d15730eac41c2ff` |
| `freshness_evidence.json` | `96be5e2a50cc3d25a03bbe9834e0270ee3df3572924e973c0864fbb799aabb5a` |
| `localization_manifest.json` | `f8733969201b109faa090177acef8a3e4ead927029e9b5e1d47171dd2066dfa9` |
| `stage2_inventory_manifest.json` | `bb82ccda197fba25d463f4ce08c1b8f63c77c7b350a82bd9b73f8130a7d86d43` |
| `vendor_catalog_baseline.json` | `7345bec0ea74764aee38a2d1bf443ea8fc0bcd34e0503e09c51b16b4339ad885` |
| `test_localization_gates.py` | `777efca18871f03d90a058609001173ba095f7399686d554000232f5d4fceca7` |
| `scripts/check_localization_gates.py` | `80f9e7be3fc61c5f91495ddc639cdfa80bf7801d6a703387a82be283fd947afe` |
| batch-6 payload CSV (270 dispositions) | `744a5ecf896c88ab8333f3f6397039d1456c4e9d70367af0426ae42e869bc364` |
| batch-6 scope CSV (270) | `68500fae981aacec08e9841fc858dfd43e7473c7b12156ac8ca528b678d309e0` |
| batch-6 site recon JSON | `89e467c681b66add960e18b803cd43977a139cb6c037bd28e03bf73b863f9ef6` |
| evidence index | `66fd210e7efafbefb20a2b286f002a68c6cbe2fed1053ffee72b8f4cafee2f4f` |
| browser evidence JSON | `96bdd623b5414f6bee47e802159e8a397347373edf7d48961433ecbdc70397db` |

---

## 7. Strict Boundaries Honored

- Exact 270 rows from `docs/translation/stage6_w60b_batch06_rows_2026-09-22.csv` processed; zero candidate rows beyond approved scope.
- Batch 7 deferred (not proposed, not imported).
- Stage 8 not started; production mutation remains `production_mutation_authorized: false`.
- All operations conducted exclusively on non-production test site `v16.localhost`.
