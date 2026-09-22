# Stage 6 W6-0b — batch-3 governed cycle executed (test site, 2026-09-22)

Owner approval chain: W6-0b cut + proposal package → explicit batch split →
batch 1 closed/accepted (`55006db`) → batch 2 closed/accepted (`ba66a80`) →
batch 3 proposal package (`fb604cf`) → owner approved **batch 3 only** (exact 271-row CSV sha `21ac507e…` + 21
technical exclusions unchanged; full governed cycle on `v16.localhost` only;
no Stage 8, no production, no batches 04–07).

Batch-3 scope CSV:
`docs/translation/stage6_w60b_batch03_rows_2026-09-22.csv`
(sha `21ac507ede96f72e86e4825aca1a6888a5b38ca56ffed7c35682b16dc475a89a`).

## Disposition split of the 271 (final)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **258** | Released into managed override catalog |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **12** | Source-equal technical rows; not shipped as Arabic |
| `preserved-site-override (not imported, plan §12)` | **1** | Existing site override preserved (`Module (for Export)`) |
| **Total approved batch 3** | **271** | |

Preserved site-override preserves:

| Batch key | Runtime `source_text` (DB) | Preserved Arabic |
|---|---|---|
| Module (for export) | `Module (for Export)` (capital `E`) | الوحدة (للتصدير) |

12 technical exceptions (source==translation):
Arial, CMD, Config, nonce, on_submit, OR, Package, Preview:, Re:, Timeout, UUID, jane@example.com.

Payload file: `docs/translation/stage6_w60b_payload_applied_rows_batch03_2026-09-22.csv`
(sha `dd83ee5e33554e21c868bcee2c81401b19f26e9dbf8815c4297e90888fdb26b5`) —
all 271 rows with `quorum_decision` + `decision_ref` binding
`stage6-W6-0b batch-3 owner-approved 2026-09-22`. Previous batch payload files left
intact.

## Cycle gates — executed on the test site only

1. **Scope**: exact owner-approved 271-row batch 3; 21 technical exclusions
   documented out-of-band; no rows beyond the approved CSV.
2. **AI proposals + quorum**: batch-3 proposal panel
   (`stage6_w60b_ai_proposal_build_batch03_2026-09-22.py`); AI-A1/A2/A3/AI-R
   records written; `release_decisions.json` → **1183**; `check_csv` green
   (`csv_rows 1183 errors 0`).
3. **Payload**: 258 Released rows appended to
   `construction/data/translations/approved_ar_overrides.csv`
   (sha `7610989909844cce55ed97e9e57519419aa7ed2a1e14376fab8e042f01810d01`;
   `release_version 1.2`; reviewers `AI-A1/AI-A2/AI-A3 (recorded review run)`).
4. **Governed importer runs** (sequential, never parallel): pre-import DRY
   `total=1183/created=258/updated=0/skipped=925/drift=0`; IMPORT
   `created=258/updated=0/skipped=925/drift=0`; final idempotent DRY
   `total=1183/created=0/updated=0/skipped=1183/drift=0` — zero drift.
5. **Dispositions recorded**: `release_decisions.json` — 1183 decisions
   (sha `aa0ef942d3f72416f8de384d3ae0f5f0d8767a6ff0480b01f7700d738a1010ad`);
   decision binding `decision_ref` → batch-3 payload CSV; contract test
   asserts `n == 1183`.
6. **Runtime verification (server)**: live DRY readback idempotent; freshness
   re-collected `packaged_rows=1183`, `critical_pass=true`
   (sha `df078e48e8063c1f79ff5ce8bf9cb790a21804bc4e7969b2f31c5ab415dfbb44`).
7. **Inventory + merkle**: `stage2_inventory_manifest.json` regenerated from
   live DB after the 258-row import (`rows=19600`, root
   `34b35f2072087936d7777b3f78024840fb83c6b82dc2dc85df98e456f940e5b1`,
   base_commit `fb604cf4615e…`, sha
   `e3b7e3865a2c800c43fc41901aa8d4a45ffeb2baa920abc099dc2d9485f2a175`);
   merkle session `LIVE_MATCH: True`; `--update-baselines` verified
   inventory_manifest_sha / merkle / rows matching localization_manifest.
8. **Gate constants re-pinned**: `EXPECTED_DRYRUN` `1183/0/0/1183/0`;
   decision-count test `n == 1183`; `EXPECTED_GATE` catalog 810 / files 265 /
   wrapped 667 / json_labels 22 **unchanged** after batch-3 (confirmed live).
9. **Evidence re-pin (one atomic set)**: ten durable envelopes + index
   regenerated; assembler `assembled 10 envelopes + index; HEAD fb604cf4615e aggregate 270`; full gate **with evidence `errors=0`, exit 0**;
   standalone suite **91/91 OK**; lints + scoped + vendor-audit green.
10. **Runtime key resolution & casing verification**: Verified resolution for
    batch-3 keys (`Workspace Visibility` → `ظهور مساحة العمل`, `API Keys` →
    `مفاتيح واجهة برمجة التطبيقات (API)`, `Build {0}` → `بناء {0}`,
    `Cannot {0} {1}.` → `لا يمكن {0} {1}.`, `Allow Bulk Editing` → `السماح بالتحرير الجماعي`,
    `Amended Documents` → `المستندات المُعدَّلة`, `Bad Cron Expression` → `تعبير Cron غير صالح`),
    and confirmed preserved site-override resolution (`Module (for Export)` → `الوحدة (للتصدير)`).

## Artifact hashes (live, pre-commit)

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

## Boundaries honored

- No candidate rows beyond the owner-approved 271-row batch 3.
- Batches 04–07 not cut, not proposed, not imported.
- Stage 8 not started; production mutation remains
  `production_mutation_authorized: false`.
- Import, freshness, inventory run only on
  `v16.localhost` (test, non-production).

## Owner status (2026-09-22)

W6-0b batch 3 is **operationally complete for the test site**:
258 new Arabic overrides released (catalog 925 → 1183); 1 site override
preserved (`Module (for Export)`); 12 technical exclusions documented; full governed cycle green
(DRY/IMPORT/idempotent DRY drift 0, evidence gate exit 0, standalone 91/91 OK).
