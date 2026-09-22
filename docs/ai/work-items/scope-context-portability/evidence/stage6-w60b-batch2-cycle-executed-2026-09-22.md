# Stage 6 W6-0b — batch-2 governed cycle executed (test site, 2026-09-22)

Owner approval chain: W6-0b cut + proposal package → explicit batch split →
batch 1 closed/accepted (`55006db`) → batch 2 proposal package (`48d95c1`) →
owner approved **batch 2 only** (exact 271-row CSV sha `187361ab…` + 21
technical exclusions unchanged; full governed cycle on `v16.localhost` only;
no Stage 8, no production, no batches 03–07).

Batch-2 scope CSV:
`docs/translation/stage6_w60b_batch02_rows_2026-09-22.csv`
(sha `187361ab36ea2ab75f32355bce0b2b1c274b52bebd339b0c19ea3822436895db`).

## Disposition split of the 271 (final)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **243** | Released into managed override catalog |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **26** | Source-equal technical rows; not shipped as Arabic |
| `preserved-site-override (not imported, plan §12)` | **2** | Existing site overrides preserved (case-insensitive DB match) |
| **Total approved batch 2** | **271** | |

Preserved site-override preserves:

| Batch key | Runtime `source_text` (DB) | Preserved Arabic |
|---|---|---|
| Country | `Country` | البلد |
| Not Permitted | `Not permitted` (lowercase `p`) | غير مسموح |

26 technical exceptions (source==translation):
A7, A8, A9, B0, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10,
C5E, Comm10E, CSS, DLE, BCC, XMLHttpRequest Error, Inter,
Folio, Tabloid, vscode, Doctype, Ar.

Payload file: `docs/translation/stage6_w60b_payload_applied_rows_batch02_2026-09-22.csv`
(sha `2bdd17bac6c30e729f0221507372a6f0bc79c86f9ee2f261cf8c7611880a6344`) —
all 271 rows with `quorum_decision` + `decision_ref` binding
`stage6-W6-0b batch-2 owner-approved 2026-09-22`. Batch-1 payload file left
intact.

## Cycle gates — executed on the test site only

1. **Scope**: exact owner-approved 271-row batch 2; 21 technical exclusions
   documented out-of-band; no rows beyond the approved CSV.
2. **AI proposals + quorum**: batch-2 proposal panel
   (`stage6_w60b_ai_proposal_build_batch02_2026-09-22.py`); AI-A1/A2/A3/AI-R
   records written; `release_decisions.json` → **925**; `check_csv` green
   (`csv_rows 925 errors 0`).
3. **Payload**: 243 Released rows appended to
   `construction/data/translations/approved_ar_overrides.csv`
   (sha `fae31d04016c5c51c035b2316716454078735a72ae23c1c8a0fa239a3a7b15b8`;
   `release_version 1.2`; reviewers `AI-A1/AI-A2/AI-A3 (recorded review run)`).
4. **Governed importer runs** (sequential, never parallel): pre-import DRY
   `total=925/created=243/updated=0/skipped=682/drift=0`; IMPORT
   `created=243/updated=0/skipped=682/drift=0`; final idempotent DRY
   `total=925/created=0/updated=0/skipped=925/drift=0` — zero drift.
5. **Dispositions recorded**: `release_decisions.json` — 925 decisions
   (sha `8c50027df99d67b21f814b2a17b884e152079951c3942e697fd926807f528413`);
   decision binding `decision_ref` → batch-2 payload CSV; contract test
   asserts `n == 925`.
6. **Runtime verification (server)**: live DRY readback idempotent; freshness
   re-collected `packaged_rows=925`, `critical_pass=true`
   (collected `2026-09-22T11:07:35Z`, sha
   `68782937efedea84fb5a821d6c53897e7f297dd39b85b9201203264fb6af31be`).
7. **Inventory + merkle**: `stage2_inventory_manifest.json` regenerated from
   live DB after the 243-row import (`rows=19342`, root
   `3412a6758bcf2a03466c5388a1c8497ddb1a9e2bc59f5d22c3d5a45403cd0ba1`,
   base_commit `48d95c19819f…`, sha
   `239c46f5bafb3917b92b57d0227a907293f7b21058be45b93c949da822ebd044`);
   merkle session `LIVE_MATCH: True`; `--update-baselines` verified
   inventory_manifest_sha / merkle / rows matching localization_manifest.
8. **Gate constants re-pinned**: `EXPECTED_DRYRUN` `925/0/0/925/0`;
   decision-count test `n == 925`; `EXPECTED_GATE` catalog 810 / files 265 /
   wrapped 667 / json_labels 22 **unchanged** after batch-2 (confirmed live).
9. **Evidence re-pin (one atomic set)**: ten durable envelopes + index
   regenerated with true-UTC stamps; dryrun/freshness stamps corrected after
   initial local-time `Z` labels caused `evidence-future`/`evidence-order`
   failures; assembler `assembled 10 envelopes + index; HEAD 48d95c19819f
   aggregate 270`; full gate **with evidence `errors=0`, exit 0**;
   standalone suite **91/91 OK**; lints + scoped + vendor-audit green.
10. **UAT preflight (hard gate)**: `scripts/uat_preflight.py` PASS on
    `v16.localhost` — redis cache + queue PING, site HTTP, Desk boot `lang=ar`,
    `__messages` **11227** entries, probe key present (password via STDIN only).
    Initial fail: `Administrator.language=en` → set `ar` for the UAT window;
    restored to `en` after browser evidence.
11. **Arabic browser evidence** (headless Playwright, real `ar` Desk session):
    **21/21 checks PASS**, exit 0
    (`/tmp/opencode/stage6w60b/browser_evidence_batch02.json`,
    `browser-ar-desk-batch02.png`)
    - `boot.lang=ar`, `__messages` ≥ 1000 (11227);
    - in-page `__()` resolution **12/12** batch-2 keys exact, including
      site-override preserves `Country` → `البلد`, `Not permitted` →
      `غير مسموح`, plus batch-2 Released keys (`Always`, `Apply Filters`,
      `This Month`, `Reset To Default`, placeholder `Cannot {0} {1}.`);
    - boot `__messages` direct lookup matches released Arabic for all probes;
    - rendered DOM: workspace modules `الأدوات المحاسبة المشتريات المشاريع
      المخزون البيع`; Arabic sidebar items (`بحث`, `إشعار`, `التقارير`, …).

### Browser probe casing note (resolved)

First browser run failed 3 checks because the probe keyed capital-P
`Not Permitted` while the preserved Site Override runtime row is
`source_text='Not permitted'` (lowercase `p`; construction
`locale/ar.po` msgid + DB Site Override). Client `__()` / `boot.__messages`
are case-sensitive (`get_all_translations('ar')` returns `null` for the
capital-P key, `غير مسموح` for the lowercase key). Probe corrected to the
actual runtime source_text; re-run **21/21 PASS**. Capital-P frappe UI
string remains untranslated in the packaged catalog (frappe `ar.po` msgstr
empty) and was correctly **not** imported under plan §12 preserved
case-insensitive match — documented, not a gate failure.

## Artifact hashes (live, pre-commit)

| Artifact | sha256 |
|---|---|
| `approved_ar_overrides.csv` (925 Released) | `fae31d04016c5c51c035b2316716454078735a72ae23c1c8a0fa239a3a7b15b8` |
| `release_decisions.json` (925) | `8c50027df99d67b21f814b2a17b884e152079951c3942e697fd926807f528413` |
| `freshness_evidence.json` | `68782937efedea84fb5a821d6c53897e7f297dd39b85b9201203264fb6af31be` |
| `localization_manifest.json` | `727a7b4b5939fe776ce6f357b29e00aa1bcd7fa0edb997512b2e6b5feabfce9d` |
| `stage2_inventory_manifest.json` | `239c46f5bafb3917b92b57d0227a907293f7b21058be45b93c949da822ebd044` |
| `vendor_catalog_baseline.json` | `f9b03c7fe25c30f621aa7cc3c1a8f5e2240fae097b12a2319d5bf17dd20d92b7` |
| `test_localization_gates.py` | `5ee970c14f6a4e88ea0707f7bf4eea4b3d47a839a355a875ca22d56f35512157` |
| `check_localization_gates.py` | `662dbab4accc534bbfd98843417497eab28127bece211e6176596047bb8ce725` |
| batch-2 payload CSV (271 dispositions) | `2bdd17bac6c30e729f0221507372a6f0bc79c86f9ee2f261cf8c7611880a6344` |
| batch-2 scope CSV (271) | `187361ab36ea2ab75f32355bce0b2b1c274b52bebd339b0c19ea3822436895db` |
| evidence index | `bcd5c373dd541cb884a367bd3003063655d7cc6b243d1cf8bd65833b44c93278` |

## Boundaries honored

- No candidate rows beyond the owner-approved 271-row batch 2.
- Batches 03–07 not cut, not proposed, not imported.
- Stage 8 not started; production mutation remains
  `production_mutation_authorized: false`.
- Import, freshness, inventory, and browser evidence ran only on
  `v16.localhost` (test, non-production).
- Temp admin password revoked (rotated to unrecorded value);
  `Administrator.language` restored to `en`.

## Owner status (2026-09-22)

W6-0b batch 2 is **operationally complete for the test site**:
243 new Arabic overrides released (catalog 682 → 925); 2 site overrides
preserved; 26 technical exclusions documented; full governed cycle green
(DRY/IMPORT/idempotent DRY drift 0, evidence gate exit 0, browser 21/21).
