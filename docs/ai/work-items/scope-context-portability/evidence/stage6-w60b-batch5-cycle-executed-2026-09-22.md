# Stage 6 W6-0b — batch-5 governed cycle executed (test site, 2026-09-22)

Owner approval chain: W6-0b cut + proposal package → explicit batch split →
batches 1–4 closed/accepted (`55006db`, `ba66a80`, `6cbd6c6` + UAT `d0f9c5d`,
`89dd15a` / `396ae87`) → batch-5 proposal package (`ddb6f3f`) → owner approved
**batch 5 only** (exact 270-row CSV sha
`56f6432688d902fe8de5d2d2dfdccc501a36d78ec6534973c1f9cede3ad43544`; full
governed cycle on `v16.localhost` only; batches 06–07 deferred; no Stage 8, no
production).

Batch-5 scope CSV:
`docs/translation/stage6_w60b_batch05_rows_2026-09-22.csv`
(sha256 `56f6432688d902fe8de5d2d2dfdccc501a36d78ec6534973c1f9cede3ad43544`).

## 1. Scope & Disposition Reconciliation (Total 270 Rows)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **252** | Released into managed override catalog (`approved_ar_overrides.csv`) |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **17** | Source-equal technical rows; kept as vendor rendering |
| `preserved-site-override (not imported, plan §12)` | **1** | Existing site override preserved (case-insensitive match) |
| **Total approved batch 5** | **270** | Exact match to approved scope CSV (sha256 `56f64326…`) |

### Accounting for Technical Exclusions: 21 Shared Exclusions vs. 17 Batch-5 Technical Exceptions

There are two distinct categories of technical exclusions under W6-0b governance:

1. **Shared W6-0b Out-of-Band Exclusions (21 rows)**:
   Documented in `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (sha256 `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095`).
   These 21 rows are permanent technical exclusions (symbols, HTML fragments, `${...}`) removed from the 1,915-row cut to produce the 1,894 candidate rows. They are **outside all batches** (batches 01–07) and remain permanently excluded across all cycles.

2. **Batch-5 In-Scope Technical Exceptions (17 rows)**:
   Within the 270 rows of Batch 5, exactly 17 rows were confirmed by the quorum panel as `EXCEPTION-technical`:
   `Not Nullable`, `Policy URI`, `Redirect URI`, `Resource Policy URI`, `Resource TOS URI`, `Revocation URI`, `SQL Explain`, `SQL Output`, `Success URI`, `TOS URI`, `Token URI`, `Userinfo URI`, `RQ Worker`, `Realtime (SocketIO)`, `SocketIO Ping Check`, `Use STARTTLS`, `Setup > User`.

### Preserved Site Overrides (1):
| Batch key | Runtime `source_text` (DB, exact casing) | Preserved Arabic | Origin |
|---|---|---|---|
| `Postal Code` | `Postal Code` | الرمز البريدي | `Site Override` |

Site recon: 274 case-insensitive matches; only `ct_origin == "Site Override"` preserved (1). Other non-empty rows (`Success Message`, `Sequence ID`, `Reference name`, empty ct_origin) import normally as Released. Browser probes use exact DB `source_text` casing so `__()` resolves the preserved runtime row.

---

## 2. Quorum Governance & AI-R Review Artifacts

- **Site Recon**: `docs/translation/stage6_w60b_batch05_site_recon_2026-09-22.py` → `.json` (sha256 `7642cd4160b99dc6c73ff8a4e38c7f8f1ea4e7063cdfd3a25911e5f16f43d826`)
- **Panel Build Script**: `docs/translation/stage6_w60b_ai_proposal_build_batch05_2026-09-22.py`
- **Released List**: `docs/translation/stage6_w60b_batch05_released_list.txt` (252)
- **Applied Payload CSV**: `docs/translation/stage6_w60b_payload_applied_rows_batch05_2026-09-22.csv` (270 dispositions, tab-separated)
  (sha256 `a50bf24cc6acd2c5436dd4b085f5cc8cb15b77339f172343b62d9254ea06abb0`)
- **Quorum Review Records**:
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a1-batch5-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a2-batch5-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a3-batch5-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-r-batch5-2026-09-22.md`
- **Release Decisions Ledger**: `construction/data/translations/release_decisions.json`
  - Total recorded decisions: **1,691** (binding batch-5 `decision_ref: content:docs/translation/stage6_w60b_payload_applied_rows_batch05_2026-09-22.csv`)
  - sha256: `fd25763dfed88f80b053aa01e54c9be8d6e0311a3163d71c3e782f577c646db0`

---

## 3. Governed Importer Runs (`v16.localhost` only)

1. **Pre-import DRY Run** (catalog 1,691 after build append):
   `total=1691, created=252, updated=0, skipped=1439, drift=0`
2. **IMPORT Execution**: `created=252` (252 Released rows bound to runtime)
3. **Post-import Idempotent DRY Run**:
   `total=1691, created=0, updated=0, skipped=1691, drift=0` (100% idempotent, zero drift) → `IDEMPOTENT_OK`

Catalog: `approved_ar_overrides.csv` **1439 → 1691** (+252 Released).
Gate pin: `EXPECTED_DRYRUN = {"total": 1691, "created": 0, "updated": 0, "skipped": 1691, "drift": 0}`.
`source_equal=0` on all 252 batch-5 decision refs.

---

## 4. Fresh Runtime & Evidence Verification Gates

1. **Runtime Freshness Collector**:
   - `packaged_rows`: **1,691**
   - `critical_pass`: `true`
   - `runtime_digest`: `c0f096f4a65fd4ffe53fdd89cfe489c648c0d289b93d5e8d52cfe76ab1a8b362`
   - sha256: `5c693ddbff204bde52c19c788e0b5c80abf2e7216173d73f74b4a1abc0761f8a`
2. **Inventory Manifest & Merkle**:
   - `rows`: **20,108** (`19,856 + 252 = 20,108`)
   - `root`: `8d8c8a18b4c712071b5c030cbfa0c77ef80274e4eb1805df5aed110c60ea842f`
   - `LIVE_MATCH`: `True`
   - `base_commit`: `ddb6f3f44e9d62d2b84159801d60942bbd1ff140` (proposal HEAD at re-record)
3. **Full Localization Gates** (with evidence):
   - `python3 scripts/check_localization_gates.py` → **`errors=0`**, exit code `0`.
   - Gate counts: `po: 810`, `csv_rows: 1691`, `files: 265`, `json_labels: 22`, `missing: 0`, `wrapped: 667`.
4. **Standalone Gate Test Suite**:
   - `python3 construction/tests/test_localization_gates.py` → **91/91 tests PASS (`OK`)**.
5. **Evidence Assembler** (10 envelopes + index):
   - `python3 construction/tests/tools/stage2_evidence_assemble.py` → assembled 10 envelopes + index; aggregate 270 tests; HEAD `ddb6f3f44e9d`.
   - Re-captured `final-dryrun.txt` to contract line `In [N]: DRY total=… created=… updated=… skipped=… drift=…` (dict form rejected by evidence-schema).
   - index: `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt`
   - sha256: `cc7638d13b520c1d41484dc7a28514f605bebe7b843f7db07a3aafaf582a4b33`
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
PASS desk-boot: __messages entries=11993
PASS desk-boot-key: 'Postal Code' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

### Headless Playwright Browser DOM Verification:
- **Test Script**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch05.py`
- **Result Summary**: **23/23 checks PASS (0 FAIL)**, exit code `0`.
- **Structured Log**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch05.json`
  (sha256 `fa872514a9aaf8d8799f9be774eefa7b6d9b1c80c1235f88246dd4cf85c1a920`)
- **Visual Capture**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser-ar-desk-batch05.png`

**Verified Browser Checks & Rendered Strings**:
- `boot.lang`: `ar`
- `boot.__messages`: **11,993** entries
- Client `__()` in-page resolution **14/14 PASS**:
  - `Not Helpful` → `غير مفيد`
  - `Number of Queries` → `عدد الاستعلامات`
  - `OAuth Client Role` → `دور عميل OAuth`
  - `Pending Emails` → `رسائل بريد معلّقة`
  - `Permission Inspector` → `فاحص الأذونات`
  - `Scheduler: Active` → `المجدول: نشط`
  - `Sync {0} Fields` → `مزامنة حقول {0}`
  - `Welcome to {0}` → `مرحبًا بك في {0}`
  - `1 day ago` → `منذ يوم واحد`
  - `'{0}' is not a valid URL` → `'{0}' ليس رابط URL صالحًا`
  - `Click here` → `انقر هنا`
  - `Desk Settings` → `إعدادات المكتب`
  - `MIT License` → `ترخيص MIT`
  - `Postal Code` → `الرمز البريدي` (site override preserve verified in browser)
- Placeholder handling: `Sync {0} Fields` with args `['Fields']` → `مزامنة حقول Fields`
- Rendered DOM text:
  - 13 unique Arabic words extracted from body
  - Rendered Workspace module cards: `الأدوات`, `المحاسبة`, `المشتريات`, `المشاريع`, `المخزون`, `البيع`
  - Arabic Sidebar items present
- Security teardown: UAT temporary credentials rotated; `Administrator.language` restored to `en`.

---

## 6. Pre-Commit Artifact Hashes

| Artifact | sha256 |
|---|---|
| `approved_ar_overrides.csv` (1691 Released) | `c961d700a059d570a1807219fe141c0c6a6aa37b3e3a1fd7f568f4620fb5987d` |
| `release_decisions.json` (1691) | `fd25763dfed88f80b053aa01e54c9be8d6e0311a3163d71c3e782f577c646db0` |
| `freshness_evidence.json` | `5c693ddbff204bde52c19c788e0b5c80abf2e7216173d73f74b4a1abc0761f8a` |
| `localization_manifest.json` | `98473f818ccc7c64f2a5b62287fcce7dd368588b3f93a74a0807ea8203aaf5b1` |
| `stage2_inventory_manifest.json` | `dcc17f380ff63252cd5de3dbd4adf181919c42ebc385aee2fe746e613e711090` |
| `vendor_catalog_baseline.json` | `e3d78d6070e1157a496f36d19ce2ce30d810790b9d29b9312e01eb793b210e94` |
| `test_localization_gates.py` | `2de8c3b96e957dd6b794f7ef76ca76a56e6af2e1c0cd44e1c72919e594b535e5` |
| `scripts/check_localization_gates.py` | `6c5dafb2c8d8b6c9cf3cb6fb658be50d5875576cc081f2a27d9a43ee59626782` |
| batch-5 payload CSV (270 dispositions) | `a50bf24cc6acd2c5436dd4b085f5cc8cb15b77339f172343b62d9254ea06abb0` |
| batch-5 scope CSV (270) | `56f6432688d902fe8de5d2d2dfdccc501a36d78ec6534973c1f9cede3ad43544` |
| batch-5 site recon JSON | `7642cd4160b99dc6c73ff8a4e38c7f8f1ea4e7063cdfd3a25911e5f16f43d826` |
| evidence index | `cc7638d13b520c1d41484dc7a28514f605bebe7b843f7db07a3aafaf582a4b33` |
| browser evidence JSON | `fa872514a9aaf8d8799f9be774eefa7b6d9b1c80c1235f88246dd4cf85c1a920` |

---

## 7. Strict Boundaries Honored

- Exact 270 rows from `docs/translation/stage6_w60b_batch05_rows_2026-09-22.csv` processed; zero candidate rows beyond approved scope.
- Batches 06–07 deferred (not cut, not proposed, not imported).
- Stage 8 not started; production mutation remains `production_mutation_authorized: false`.
- All operations conducted exclusively on non-production test site `v16.localhost`.
