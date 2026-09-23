# Stage 6 W6-0b — batch-7 corrected governed cycle executed (test site, 2026-09-22)

**Status: CLOSED (corrected cycle).** This report supersedes the rejected cycle at
commit `8bfc23a` (empty translations, polluted decision ledger, `--skip-evidence`
gate, missing quorum records). `8bfc23a` remains in history and does **not**
constitute batch-7 closure.

Owner approval chain: W6-0b cut + proposal package → explicit batch split →
batches 1–6 closed/accepted (`55006db` … `3c25b25`) → batch-7 proposal
(`dfbced4`) → owner approved **batch 7 only** (exact 270-row CSV sha
`1716d01c20129b86d629034d2c826a17a3029feb44b7006e1e19b7faa9bc76d4`; full
governed cycle on `v16.localhost` only) → first cycle `8bfc23a` **rejected** →
owner chose Outcome 1 (corrected governed payload with actual Arabic
proposals, quorum/AI-R, DRY→IMPORT→DRY, browser evidence, fully valid
re-pin) → this corrected cycle.

Batch-7 scope CSV:
`docs/translation/stage6_w60b_batch07_rows_2026-09-22.csv`
(sha256 `1716d01c20129b86d629034d2c826a17a3029feb44b7006e1e19b7faa9bc76d4`).

## 1. Scope & Disposition Reconciliation (Total 270 Rows)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **241** | Released into managed override catalog (`approved_ar_overrides.csv`) |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **29** | Format/identifier/brand/protocol/event tokens; not imported |
| `preserved-site-override (not imported, plan §12)` | **0** | Zero `ct_origin='Site Override'` rows among batch-7 keys |
| **Total approved batch 7** | **270** | Exact match to approved scope CSV (sha256 `1716d01c…`) |

### Technical exclusions (29) — row-level, confirmed by AI-R

```text
OAuth, OpenLDAP, PATCH, PUT, PID, Outlook.com, Sendgrid, SparkPost, Yandex.Mail,
UIDNEXT, UIDVALIDITY, processlist, s256, vim, emacs, login_required, on_cancel,
on_trash, on_update, on_update_after_submit, workflow_transition, version_table,
fairlogin, wkhtmltopdf, macOS Launchpad, Webhook, Websocket, XLSX,
Read Only Depends On (JS)
```

### Site-override preserves (0)

Authoritative runtime dump (20367 `Translation` rows): **zero**
`ct_origin='Site Override'` rows among the 270 keys (case-insensitive).
Case-variant rows `Patch`→`بقعة` / `purple`→`أرجواني` carry operator Arabic
values but are **not** Site Override origin (PATCH is technical; Purple
imports against its exact-cased empty row). Drift contract: importer must
report `drift=0` — confirmed by the actual governed dry runs below.

### Why 238 pre-existing runtime rows are not "overlap" with the zero-overlap report

The zero-overlap report was a **scope/catalog dedup check**: batch-7
`source_text` values do not collide with batches 1–6 payload keys, the 21
shared technical exclusions, or the 302 dedup exclusions — i.e. no duplicate
*governed release*. It said nothing about the runtime `Translation` table.

The 238 rows are **catalog entries** (`ct_is_catalog_entry=1`) created by
vendor `.po` sync / prior site state with **empty** `translated_text` and
empty `ct_origin` — neither `Site Override` nor `Packaged Release`. The
importer's `_get_runtime_rows` filters `ct_is_catalog_entry=0`, so these
rows are invisible to the runtime-layer matcher: every Released key with no
non-catalog runtime row is reported as **created**, and the catalog-entry
values are updated as a side path during the real IMPORT (not as `updated`
in the DRY counters). The "3 created + 238 updated" split counted **all**
exact-cased runtime-table rows (including catalog entries); the importer's
counters count only non-catalog runtime rows.

Actual governed counts (authoritative):

1. **Pre-import DRY**: `total=2190 created=241 updated=0 skipped=1949 drift=0`
2. **IMPORT**: `total=2190 created=241 updated=0 skipped=1949 drift=0`
   (241 = 238 catalog-entry-backed keys + 3 keys with no runtime row at all:
   `Page to show on the website`, `Route: Example \"/app\"`,
   `There is no task called \"{}\"`; catalog layer value-updated in the same run)
3. **Post-import idempotent DRY**: `total=2190 created=0 updated=0 skipped=2190 drift=0` → `IDEMPOTENT_OK`
4. **Catalog sync** (`sync_translation_catalog(dry_run=False)`):
   `{'created': 0, 'updated': 0}` — no further writes required

**`drift=0` confirmed by both governed dry runs** (no Site Override conflict
source exists for this batch; the actual runs are the proof).

---

## 2. Corrected Proposal Build & Quorum Governance

- **Build script**: `docs/translation/stage6_w60b_ai_proposal_build_batch07_2026-09-22.py`
  (rewritten; supersedes the 150-line stub that emitted 270 empty
  translations). Full AI-authored A-dict for all 241 Released rows;
  29 `EXCEPTION-technical`; `PRESERVED = {}`; fail-closed accounting asserts
  (`0 + 29 + 241 = 270`), placeholder parity, affix parity, source-equal,
  NUL checks.
- **Applied payload CSV**: `docs/translation/stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv`
  (270 dispositions, tab-separated QUOTE_NONE; **0 empty translations on
  Released rows**)
  (sha256 `4f8d8cf2fd05c0480c407e2ae0a87c31d00652944b914276d8fbeec7f43d227e`)
- **Released list**: `stage6_w60b_batch07_released_list.txt` (241)
  (sha256 `504dd00b4c5aa19eac1f8d7ffa270a483ec7874df486b64392ebba7be5b0fa89`)
- **Site recon JSON** (authoritative rewrite): `stage6_w60b_batch07_site_recon_2026-09-22.json`
  (267 exact-case matches, 3 missing, 0 Site Override, 20367 rows scanned)
  (sha256 `61da882f525e6fd5c9dcf83cc693f8d0d3cad8558effdda71bfc0748897a24a0`)
- **Catalog transform**: `approved_ar_overrides.csv` **2219 → 2190**
  (1949 pre-existing Released kept; 241 Pending → Released with full quorum
  metadata; 29 technical Pending rows removed; **0 Pending remain**)
  (sha256 `30572f1ffa9ad422fffab9e75ff328e0a6f03e229330cd4f9eb9ed0452a960a6`)
- **Release decisions ledger** regenerated via
  `python3 scripts/record_release_decisions.py`: top-level
  `{schema, generated_utc, note, decisions}`, **2190** entries (the 270
  top-level pollution keys from `8bfc23a` are wiped)
  (sha256 `5bfc184517b87ca278d0da40613efe12f45d95f62b1adff1b46da14b4dbd1240`)

### Quorum Review Records (4)

- `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a1-batch7-2026-09-22.md`
- `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a2-batch7-2026-09-22.md`
- `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-a3-batch7-2026-09-22.md`
- `docs/ai/work-items/scope-context-portability/evidence/stage6-w60b-ai-r-batch7-2026-09-22.md`

Quorum columns on every Released row: `AI-A1/AI-A2/AI-A3 (recorded review
run)` + `2026-09-22 00:00:00`; release_version **1.4**; domain
`desk-short-ui`; ct_app `frappe`; `decision_ref`
`content:docs/translation/stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv`.

---

## 3. Gate Pins & Test Suite

- `scripts/check_localization_gates.py:1510`:
  `EXPECTED_DRYRUN = {"total": 2190, "created": 0, "updated": 0, "skipped": 2190, "drift": 0}`
  (sha256 `49c758fcc4d8aad7b1e3d87b332ac3eb1ee78d2f8d51e236c33eb049328343f5`)
- `construction/tests/test_localization_gates.py:509`:
  `assertEqual(n, 2190)` (line 368 synthetic `assertEqual(n, 1)` left untouched)
  (sha256 `eca1efae6821369787cff45f7935d72360453879b6b80406dfcb8a674101dcce`)
- Standalone suite: **Ran 91 tests … OK**
- Module suite (11 modules): **AGGREGATE total=270 failed=0**
  (13+6+5+3+8+91+38+53+6+11+36)

---

## 4. Evidence Envelopes & Fully Valid Gate

Evidence assembled from live captures into
`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/`
(10 envelopes + `index.txt`, `CANDIDATE_HEAD: 8bfc23a57679f5156dc42bc55b54e1eb5f6b5574`).

- **Full evidence gate (no `--skip-evidence`)**:
  `checked={"construction/locale/ar.po": 810, "csv_rows": 2190, …} errors=0` —
  **exit 0**. The `--skip-evidence` flag was used only as the documented
  bootstrap for envelope generation (assembler injects
  `NOTE: bootstrap run for envelope generation; CI and verification never
  pass this flag`); verification is the separate run above.
- Lints: `lint_scope_metadata.py` PASS, `lint_translation_writes.py` PASS,
  `git diff --check` clean (`DIFFCHECK_CLEAN`).
- Scoped gate (`--files …`): `errors=0`.
- Vendor audit (`--audit-vendor-coverage`): `errors=0`.
- Freshness: `packaged_rows=2190`, `critical_pass=true`,
  `inputs.payload_csv_sha` matches current catalog
  (sha256 `783fbc2d4e12b8686e464adb80b4bd060d66384a7d5974fcdb0fac90bbdc9104`).
- Inventory: `base_commit=8bfc23a…`, merkle
  `root=453b676950e1ccb7b878ae98732ed59592db9011c58793d6b03f7b0b861bb931`,
  `rows=20607` (sha256 `c44c4353742295ede37e88e8d14df8cb366225a37773ec93c3d00c304b84eef4`).
- Localization manifest re-pinned
  (sha256 `484647ad0cc029c952b60eb2d47be8f14444db358b193dbcf3ddf70c094503b4`).
- Vendor baseline re-pinned
  (sha256 `7ddf1cd04ca8cb4eaef2c0caf0b7f53c14670dc447e8e4109ba49044634870de`).
- Evidence index
  (sha256 `3e95b916173078d3c2e789de9a32221d0b25c4ecefc26d774194769d21976ef3`).

---

## 5. UAT Preflight & Arabic Browser Session Evidence

### Hard Preflight Gate (`scripts/uat_preflight.py`):
```
PASS redis-cache: port 13000 PING ok
PASS redis-queue: port 11000 PING ok
PASS site-http: /ping 200
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=12492
PASS desk-boot-key: 'Non-Conforming' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

### Headless Playwright Browser DOM Verification:
- **Test Script**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w60b/browser_evidence_batch07.py`
- **Result Summary**: **21/21 checks PASS (0 FAIL)**, exit code `0`.
- **Structured Log**: `browser_evidence_batch07.json`
  (sha256 `05142adf84f9e35ed926192190d93b8db9e5fdee50ada413952b33ba26570743`)
- **Visual Capture**: `browser-ar-desk-batch07.png`

**Verified Browser Checks & Rendered Strings**:
- `boot.lang`: `ar`; `boot.__messages`: **12,492** entries
- Client `__()` in-page resolution **12/12 PASS** (batch-7 samples), including:
  - `Non-Conforming` → `غير مطابق`
  - `Outgoing Emails (Last 7 days)` → `رسائل البريد الصادرة (آخر 7 أيام)`
  - `PDF Generation in Progress` → `جارٍ إنشاء PDF`
  - `Reset All Customizations` → `إعادة تعيين كل التخصيصات`
  - `System Manager privileges required.` → `مطلوب صلاحيات مدير النظام.`
  - `{} field cannot be empty.` → `لا يمكن أن يكون حقل {} فارغًا.`
  - `Track milestones for any document` → `تتبع المحطات لأي مستند`
- Placeholder handling: `Not Permitted to read {0}` with args `['Widgets']` → `غير مسموح بقراءة Widgets`
- Rendered DOM: 13 unique Arabic words; Workspace modules present; Arabic sidebar items present
- Security teardown: UAT temporary credentials rotated to
  `ct-w60b-rotated-off`; `Administrator.language` restored to `en`.

---

## 6. Pre-Commit Artifact Hashes

| Artifact | sha256 |
|---|---|
| batch-7 scope CSV (270) | `1716d01c20129b86d629034d2c826a17a3029feb44b7006e1e19b7faa9bc76d4` |
| batch-7 payload CSV (270 dispositions) | `4f8d8cf2fd05c0480c407e2ae0a87c31d00652944b914276d8fbeec7f43d227e` |
| `approved_ar_overrides.csv` (2190 Released) | `30572f1ffa9ad422fffab9e75ff328e0a6f03e229330cd4f9eb9ed0452a960a6` |
| `release_decisions.json` (2190) | `5bfc184517b87ca278d0da40613efe12f45d95f62b1adff1b46da14b4dbd1240` |
| `freshness_evidence.json` | `783fbc2d4e12b8686e464adb80b4bd060d66384a7d5974fcdb0fac90bbdc9104` |
| `localization_manifest.json` | `484647ad0cc029c952b60eb2d47be8f14444db358b193dbcf3ddf70c094503b4` |
| `stage2_inventory_manifest.json` | `c44c4353742295ede37e88e8d14df8cb366225a37773ec93c3d00c304b84eef4` |
| `vendor_catalog_baseline.json` | `7ddf1cd04ca8cb4eaef2c0caf0b7f53c14670dc447e8e4109ba49044634870de` |
| `scripts/check_localization_gates.py` | `49c758fcc4d8aad7b1e3d87b332ac3eb1ee78d2f8d51e236c33eb049328343f5` |
| `construction/tests/test_localization_gates.py` | `eca1efae6821369787cff45f7935d72360453879b6b80406dfcb8a674101dcce` |
| batch-7 site recon JSON | `61da882f525e6fd5c9dcf83cc693f8d0d3cad8558effdda71bfc0748897a24a0` |
| batch-7 released list (241) | `504dd00b4c5aa19eac1f8d7ffa270a483ec7874df486b64392ebba7be5b0fa89` |
| browser evidence JSON | `05142adf84f9e35ed926192190d93b8db9e5fdee50ada413952b33ba26570743` |

---

## 7. Strict Boundaries Honored

- Exact 270 rows from `docs/translation/stage6_w60b_batch07_rows_2026-09-22.csv`
  processed; zero candidate rows beyond approved scope.
- Site: `v16.localhost` only. No production mutation
  (`production_mutation_authorized: false`).
- No new Stage-6 batches started; Stage 8 not started.
- Rejected commit `8bfc23a` retained in history (not amended, not dropped).
