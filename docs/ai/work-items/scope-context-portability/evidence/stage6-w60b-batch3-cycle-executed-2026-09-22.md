# Stage 6 W6-0b — batch-3 governed cycle executed (test site, 2026-09-22)

Owner approval chain: W6-0b cut + proposal package → explicit batch split →
batch 1 closed/accepted (`55006db`) → batch 2 closed/accepted (`ba66a80`) →
batch 3 proposal package (`fb604cf`) → owner approved **batch 3 only** (exact 271-row CSV sha `21ac507e…` + 21
technical exclusions unchanged; full governed cycle on `v16.localhost` only;
no Stage 8, no production, no batches 04–07).

Batch-3 scope CSV:
`docs/translation/stage6_w60b_batch03_rows_2026-09-22.csv`
(sha256 `21ac507ede96f72e86e4825aca1a6888a5b38ca56ffed7c35682b16dc475a89a`).

## 1. Scope & Disposition Reconciliation (Total 271 Rows)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **258** | Released into managed override catalog (`approved_ar_overrides.csv`) |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **12** | Source-equal technical rows; kept as vendor rendering |
| `preserved-site-override (not imported, plan §12)` | **1** | Existing site override preserved (`Module (for Export)` → `الوحدة (للتصدير)`) |
| **Total approved batch 3** | **271** | Exact match to approved scope CSV (sha256 `21ac507e…`) |

### Accounting for Technical Exclusions: 21 Shared Exclusions vs. 12 Batch-3 Technical Exceptions

There are two distinct categories of technical exclusions under W6-0b governance:

1. **Shared W6-0b Out-of-Band Exclusions (21 rows)**:
   Documented in `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (sha256 `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095`).
   These 21 rows are permanent technical exclusions (symbols, HTML fragments, `${...}`) removed from the 1,915-row cut to produce the 1,894 candidate rows. They are **outside all batches** (batches 01–07) and remain permanently excluded across all cycles:
   `!=`, `#{0}`, `<`, `<=`, `<b>{0}</b> is not a valid URL`, `<span class="h2">Hi,</span>`, `=`, `>`, `>=`, `Enable if on click...`, `Field <code>{0}</code> not found in {1}`, `Workspace <b>{0}</b> does not exist`, `{0}`, `{0} ${skip_list ? "" : type}`, `{0} ${type}`, `{0} ({1})`, `{0} ({1}) - {2}%`, `{0} = {1}`, `{0} with the role <strong>{1}</strong>`, `{0}: {1}`, `{} Possibly invalid python code. <br>{}`.

2. **Batch-3 In-Scope Technical Exceptions (12 rows)**:
   Within the 271 rows of Batch 3, exactly 12 rows were confirmed by the quorum panel as `EXCEPTION-technical`:
   `Arial`, `CMD`, `Config`, `jane@example.com`, `nonce`, `on_submit`, `OR`, `Package`, `Preview:`, `Re:`, `Timeout`, `UUID`.

3. **Reconciliation of the 9 Flagged Candidate Rows (21 vs. 12 difference)**:
   In the proposal note, potential short format/code candidate tokens were flagged for quorum consideration. 9 candidate rows that were candidates for technical exception were evaluated by the quorum panel and determined to be genuine user-facing UI concepts that require Arabic translation, receiving the disposition `quorum-confirmed (release payload row)`:
   - `Portal` → `بوابة` (UI desk portal navigation noun; translated to Arabic)
   - `Partial` → `جزئي` (Payment and status indicator; translated to Arabic)
   - `Hello` → `مرحبًا` (Greeting prompt in communication UI; translated to Arabic)
   - `Dear` → `عزيزي` (Notification salutation; translated to Arabic)
   - `Thanks` → `شكرًا` (Feedback/closure acknowledgment; translated to Arabic)
   - `Orange` → `برتقالي` (Standard UI color tag/label; translated to Arabic)
   - `Pink` → `وردي` (Standard UI color tag/label; translated to Arabic)
   - `Red` → `أحمر` (Standard UI color tag/label; translated to Arabic)
   - `Yellow` → `أصفر` (Standard UI color tag/label; translated to Arabic)

### Preserved Site Override:
| Batch key | Runtime `source_text` (DB) | Preserved Arabic | Origin |
|---|---|---|---|
| `Module (for export)` | `Module (for Export)` (capital `E`) | الوحدة (للتصدير) | `Site Override` |

---

## 2. Quorum Governance & AI-R Review Artifacts

- **Panel Build Script**: `docs/translation/stage6_w60b_ai_proposal_build_batch03_2026-09-22.py`
- **Applied Payload CSV**: `docs/translation/stage6_w60b_payload_applied_rows_batch03_2026-09-22.csv`
  (sha256 `dd83ee5e33554e21c868bcee2c81401b19f26e9dbf8815c4297e90888fdb26b5`)
- **Quorum Review Records**:
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a1-batch3-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a2-batch3-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a3-batch3-2026-09-22.md`
  - `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-r-batch3-2026-09-22.md`
- **Release Decisions Ledger**: `construction/data/translations/release_decisions.json`
  - Total recorded decisions: **1,183** (binding `decision_ref: stage6-W6-0b batch-3 owner-approved 2026-09-22`)
  - sha256: `aa0ef942d3f72416f8de384d3ae0f5f0d8767a6ff0480b01f7700d738a1010ad`

---

## 3. Governed Importer Runs (`v16.localhost` only)

1. **Pre-import DRY Run**:
   `total=1183, created=258, updated=0, skipped=925, drift=0`
2. **IMPORT Execution**:
   `created=258, drift=0` (258 rows inserted into `tabTranslation`)
3. **Post-import Idempotent DRY Run**:
   `total=1183, created=0, updated=0, skipped=1183, drift=0` (100% idempotent, zero drift)

---

## 4. Fresh Runtime & Evidence Verification Gates

1. **Runtime Freshness Collector**:
   - `packaged_rows`: **1,183**
   - `critical_pass`: `true`
   - sha256: `df078e48e8063c1f79ff5ce8bf9cb790a21804bc4e7969b2f31c5ab415dfbb44`
2. **Inventory Manifest & Merkle**:
   - `rows`: **19,600** (`19,342 + 258 = 19,600`)
   - `root`: `34b35f2072087936d7777b3f78024840fb83c6b82dc2dc85df98e456f940e5b1`
   - `LIVE_MATCH`: `True`
3. **Full Localization Gates**:
   - `python3 scripts/check_localization_gates.py` → **`errors=0`**, exit code `0`.
   - Gate counts: `po: 810`, `csv_rows: 1183`, `files: 265`, `json_labels: 22`, `missing: 0`, `wrapped: 667`.
4. **Standalone Gate Test Suite**:
   - `python3 construction/tests/test_localization_gates.py` → **91/91 tests PASS (`OK`)**.

---

## 5. UAT Preflight & Arabic Browser Session Evidence

### Hard Preflight Gate (`scripts/uat_preflight.py`):
```
PASS redis-cache: port 13000 PING ok
PASS redis-queue: port 11000 PING ok
PASS site-http: /ping 200
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=11485
PASS desk-boot-key: 'Workspace Visibility' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

### Headless Playwright Browser DOM Verification:
- **Test Script**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch03.py`
- **Result Summary**: **19/19 checks PASS (0 FAIL)**, exit code `0`.
- **Structured Log**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch03.json`
- **Visual Capture**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser-ar-desk-batch03.png`

**Verified Browser Checks & Rendered Strings**:
- `boot.lang`: `ar`
- `boot.__messages`: **11,485** entries
- Client `__()` in-page resolution **10/10 PASS**:
  - `Workspace Visibility` → `ظهور مساحة العمل`
  - `API Keys` → `مفاتيح واجهة برمجة التطبيقات (API)`
  - `Allow Bulk Editing` → `السماح بالتحرير الجماعي`
  - `Amended Documents` → `المستندات المُعدَّلة`
  - `Bad Cron Expression` → `تعبير Cron غير صالح`
  - `Workspace Settings` → `إعدادات مساحة العمل`
  - `Show sidebar` → `إظهار الشريط الجانبي`
  - `Workspace Manager` → `مدير مساحة العمل`
  - `Active Directory` → `دليل Active Directory`
  - `Module (for Export)` → `الوحدة (للتصدير)` (site override preserve verified in browser)
- Placeholder handling: `Cannot {0} {1}.` with args `['delete', 'item']` → `لا يمكن delete item.`
- Rendered DOM text:
  - 13 unique Arabic words extracted from body (`الأدوات`, `الأصول`, `الباطن`, `البيع`, `التصنيع`, `الجودة`, `المحاسبة`, `المخزون`, `المشاريع`, `المشتريات`, `بحث`, `مقاولات`, `منظمة`)
  - Rendered Workspace module cards: `الأدوات`, `المحاسبة`, `المشتريات`, `المشاريع`, `المخزون`, `البيع`
  - Arabic Sidebar items: `بحث Ctrl+K`, `إشعار`, `سجل الطريق`, `إعدادات الإشعارات`, `قائمة المهام`, `التقارير`, `سطح المكتب`
- Security teardown: UAT temporary credentials revoked and `Administrator.language` restored to `en`.

---

## 6. Pre-Commit Artifact Hashes

| Artifact | sha256 |
|---|---|
| `approved_ar_overrides.csv` (1183 Released) | `7610989909844cce55ed97e9e57519419aa7ed2a1e14376fab8e042f01810d01` |
| `release_decisions.json` (1183) | `aa0ef942d3f72416f8de384d3ae0f5f0d8767a6ff0480b01f7700d738a1010ad` |
| `freshness_evidence.json` | `df078e48e8063c1f79ff5ce8bf9cb790a21804bc4e7969b2f31c5ab415dfbb44` |
| `localization_manifest.json` | `46fd2634a538712a4a5a8062a00b7cbbc3bdb509b719588a31cfecbc81de6465` |
| `stage2_inventory_manifest.json` | `e3b7e3865a2c800c43fc41901aa8d4a45ffeb2baa920abc099dc2d9485f2a175` |
| `vendor_catalog_baseline.json` | `aab37b73197b4f781db529819165c2397af7c682d84eab2e9e243ebb03bb2d81` |
| `test_localization_gates.py` | `c3ac2eb67ee7a8a0465010e8d76b092b9cc461c49784f23eaabaee6f29881286` |
| `scripts/check_localization_gates.py` | `c2eebc905629161c0803b863b321492a3ffd098dcd476723d061357aff050094` |
| batch-3 payload CSV (271 dispositions) | `dd83ee5e33554e21c868bcee2c81401b19f26e9dbf8815c4297e90888fdb26b5` |
| batch-3 scope CSV (271) | `21ac507ede96f72e86e4825aca1a6888a5b38ca56ffed7c35682b16dc475a89a` |
| evidence index | `779c954df28d0cbe9d9dc43bdef8fcf6d912e175984b3b01b3692a9470206ae3` |

---

## 7. Strict Boundaries Honored

- Exact 271 rows from `docs/translation/stage6_w60b_batch03_rows_2026-09-22.csv` processed; zero candidate rows beyond approved scope.
- Batches 04–07 untouched, not cut, not proposed, not imported.
- Stage 8 not started; production mutation remains `production_mutation_authorized: false`.
- All operations conducted exclusively on non-production test site `v16.localhost`.
