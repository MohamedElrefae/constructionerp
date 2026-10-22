# Stage 6 W6-0b — governed cycle executed (test site, 2026-09-22)

Owner approval chain: W6-0b cut + proposal package (`ab92075`) →
explicit batch split (do not approve 1,915 as one batch) → owner approved
**batch 1 only** (exact 271-row CSV + 21 technical exclusions; commit the
batch package; full governed cycle on `v16.localhost` only; no batches
02–07, no Stage 8, no production).

Batch package commit: `8c9fece` — exact scope
`docs/translation/stage6_w60b_batch01_rows_2026-09-22.csv`
(sha `8916118e…`) + batch plan + 21-row technical exclusions
(sha `6400f6d3…`).

## Disposition split of the 271 (final)

| Disposition | Rows | Treatment |
|---|---:|---|
| `quorum-confirmed (release payload row)` | **232** | Released into managed override catalog |
| `EXCEPTION-technical (keep vendor rendering; no translation)` | **32** | Source-equal technical rows; not shipped as Arabic |
| `preserved-site-override (not imported, plan §12)` | **7** | Existing site overrides preserved (case-insensitive DB match) |
| **Total approved batch 1** | **271** | |

Preserved site-override preserves: Collapse All (طيّ الكل), Expand All
(توسيع الكل), Dark (داكن), Light (فاتح), DELETE (حذف), email (البريد
الإلكتروني), Phone (الهاتف).

32 technical exceptions (source==translation): CSV, PDF, HTML, L, DocType,
M, GET, POST, K, yyyy-mm-dd, JSON, dd.mm.yyyy, B, DocField, T, Python, JS,
Helvetica Neue, HEAD, Kh, DocPerm, Meta, SQL, chrome, Ctrl + Down,
Ctrl + Up, A0, A1, A2, A3, A5, A6. RQ Job fixed `" مهمة RQ"` →
`"مهمة RQ"`.

Payload file: `docs/translation/stage6_w60b_payload_applied_rows_2026-09-22.csv`
(sha `c7c7ce66…`) — all 271 rows with `quorum_decision` + `decision_ref`
binding `stage6-W6-0b batch-1 owner-approved 2026-09-22`.

## Cycle gates — executed on the test site only

1. **Scope**: exact owner-approved 271-row batch 1; 21 technical exclusions
   documented out-of-band; no rows beyond the approved CSV.
2. **AI proposals**: batch-1 proposal panel authored and validated
   (`stage6_w60b_ai_proposal_build_2026-09-22.py`); `check_csv` 0 errors
   on the released catalog (placeholders, whitespace/affix, html-unsafe,
   source-equal, quorum columns).
3. **Payload**: 232 Released rows appended to
   `construction/data/translations/approved_ar_overrides.csv`
   (sha `1036b9a9…`; `release_version 1.2`; reviewers
   `AI-A1/AI-A2/AI-A3 (recorded review run)`; domain `desk-short-ui`;
   `ct_app frappe`).
4. **Governed importer runs**: DRY first
   `total=682/created=232/updated=0/skipped=450/drift=0`; IMPORT
   `total=682/created=232/updated=0/skipped=450/drift=0`; final idempotent
   DRY `total=682/created=0/updated=0/skipped=682/drift=0` — zero drift
   across the cycle; IMPORT test-site only.
5. **Dispositions recorded**: `release_decisions.json` — 682 decisions
   (sha `fe3089fd…`); AI-R record
   `stage6-w60b-ai-r-batch1-2026-09-22.md`; decision binding
   `decision_ref` → payload CSV; contract test asserts `n == 682`.
6. **Runtime verification (server)**: live DRY readback idempotent;
   freshness re-collected `packaged_rows=682`, `critical_pass=true`
   (collected `2026-09-22T10:42:46Z`, sha `db6cc5e2…`).
7. **Inventory + merkle**: `stage2_inventory_manifest.json` regenerated
   from live DB after the 232-row import
   (`rows=19099`, root `73e7161c…`, base_commit `8c9fece…`,
   sha `b20f9f6b…`); merkle session `LIVE_MATCH: True`.
8. **Evidence re-pin (one atomic set)**: ten durable envelopes + index
   regenerated; `--update-baselines` rebound `freshness_sha` →
   `db6cc5e2…`; `EXPECTED_GATE` catalog 810 / files 265 / wrapped 667;
   `EXPECTED_DRYRUN` `682/0/0/682/0`; standalone suite **91/91 OK**;
   lints + scoped + vendor-audit green; full gate with evidence
   **`errors=0`, exit 0** on the current pre-commit HEAD.
9. **UAT preflight (hard gate)**: `scripts/uat_preflight.py` PASS on
   `v16.localhost` — redis cache `:13000` + queue `:11000` PING, `/ping`
   200, fresh Desk boot `lang=ar`, `__messages` **10984** entries, probe
   key `Ledger` present (password via STDIN only).
10. **Arabic browser evidence** (headless Playwright, real `ar` Desk
    session): **19/19 checks PASS**
    - `boot.lang=ar`, `__messages` ≥ 1000 (10984);
    - in-page `__()` resolution 10/10 batch-1 keys exact, e.g.
      `Ledger` → `دفتر الأستاذ`, `On Payment Failed` → `عند فشل الدفع`,
      `Select Currency` → `تحديد العملة`, `Reset sorting` path keys;
    - placeholder `No currency fields in {0}` →
      `لا توجد حقول عملة في Currency`;
    - boot `__messages` direct lookup matches released Arabic;
    - rendered DOM: workspace modules `الأدوات المحاسبة المشتريات
      المشاريع المخزون البيع`; Arabic sidebar items (`بحث`, `إشعار`,
      `التقارير`, …);
    - screenshots `/tmp/opencode/stage6w60b/browser-ar-desk.png` +
      `browser_evidence.json`.
    Site restored after the run: Administrator language back to `en`,
    temp admin password rotated to an unrecorded value.

## Artifact hashes (live, pre-commit)

| Artifact | sha256 |
|---|---|
| `approved_ar_overrides.csv` | `1036b9a930b56d4d415903bee71e9e3487e211d154e67f225a9806e86117fc9c` |
| `release_decisions.json` | `fe3089fda61bab0fe8229b20686a10d1f1690bd8cd8b70744d4a5c03cbea133e` |
| `freshness_evidence.json` | `db6cc5e2dc834ca4eee4f00bbc93cfd24fc7035cecc3b30ee34b37659ab74e4f` |
| `localization_manifest.json` | `01b6dc970f58da2026ce18d488cd7cea03e9c20910cb1eeba6d666ea8b91e8d7` |
| `stage2_inventory_manifest.json` | `b20f9f6b99befd6e0df9dcae6728f89695868596f624cb447b981a7fd0752c7d` |
| `vendor_catalog_baseline.json` | `0ff2464abd202fe4496f9fd906a77c4da28e4a848c3dac10c0faf04ea6d4081d` |
| `test_localization_gates.py` | `41df0e4734457ff1a9ca7aa5666282cd6d72711ae278d1ab05603af69d95cdeb` |
| `check_localization_gates.py` | `770a6f4600146e62c58f0d28fdb41f59c8f04d89b1b588eb29af4c1fe8fa43b7` |
| payload CSV (271 dispositions) | `c7c7ce66e508ab4e90119589a9a8fe34e97dd85d185e3cc5a6b0b579fb191d10` |
| batch-1 scope CSV | `8916118e82e23a4bc23c338b958090463bc4538d560b954697b33130e73171d3` |

## Boundaries honored

- No candidate rows beyond the owner-approved 271-row batch 1.
- Batches 02–07 not cut, not proposed, not imported.
- Stage 8 not started; production mutation remains
  `production_mutation_authorized: false`.
- Import, freshness, inventory, and browser evidence ran only on
  `v16.localhost` (test, non-production).
- Temp admin password revoked (rotated to unrecorded value);
  `Administrator.language` restored to `en`.

## Owner status (2026-09-22)

W6-0b batch 1 is **operationally complete for the test site**:
232 new Arabic overrides released; 7 site overrides preserved;
32 technical exclusions documented; full governed cycle green
(DRY/IMPORT/idempotent DRY drift 0, evidence gate exit 0,
browser 19/19).
