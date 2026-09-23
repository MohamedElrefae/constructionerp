# Stage 6 W6-2 — batch-01 governed cycle executed (test site, 2026-09-23)

**Status: CLOSED (governed cycle complete on `v16.localhost`).**

Owner approval (verbatim): approve W6-2 Buying+Selling batch 1 only — exact
270-row CSV sha `b017df4787ff8754be0bf43425151b748ba0aa019348fa29187f660130408fae`;
governed cycle including quorum for the 85 AI-proposal rows + required import
and evidence gates; keep all other scopes and production work out of this
approval.

Batch-01 scope CSV (owner-approved, historical — not edited this cycle):
`docs/translation/stage6_w602_batch01_rows_2026-09-22.csv`
(sha256 `b017df4787ff8754be0bf43425151b748ba0aa019348fa29187f660130408fae`, 270 rows).

## 1. Scope & disposition reconciliation (total 270 rows)

Authoritative site recon:
`docs/translation/stage6_w602_batch01_site_recon_2026-09-22.json`
(sha256 `f8be402aa95a4acdeeff6139d7f34a90e6f4c4effbc71bddad6659bacdd70ef8`).

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override (not imported, plan §12)` | **184** | 183 exact-key `ct_origin='Site Override'` + 1 import-time strip-collision preserve (`' Address'` → runtime Address SO) |
| `already-released (catalog row retained; not re-appended)` | **1** | Advance Payment |
| `exception_technical` | **0** | — |
| `quorum-confirmed (release payload row)` | **85** | Released into managed override catalog |
| **Total approved batch 1** | **270** | Exact match to approved scope CSV |

### Address strip-collision amendment (§12)

`' Address'` reclassified **out** of the Released catalog (2276 → **2275**),
disposition `preserved-site-override (strip-collision)`. Partition
**270 = 184 preserved + 1 already-released + 0 exception + 85 payload**.
Gates/tests repinned to 2275 (`EXPECTED_DRYRUN` at
`check_localization_gates.py:1510`, `test_localization_gates.py:509`).
Historical build script still asserts 2276 — **not rerun**. Owner-approved
scope CSV retains the historical trailing-space form — **not edited**.

### CSV row gate fixes applied this cycle (catalog/payload only)

Three placeholder/affix failures fixed so `csv-*` gates reach `errors=0`:

1. Line 2199 `Could not find path for ` → `Could not find path for`
   (Arabic trailing space stripped on both sides — fixes `csv-whitespace`
   affix + payload/runtime strip-collision drift).
2–3. `% of materials billed/delivered against this Sales Order` Arabic now
   carries the required `% o` token (`PRINTF_RE` matches English `% of`);
   convention mirrors existing `Use % for…` → `استخدم % f…`.

Payload disposition CSV + released list updated to match. Scope CSV line 27
historical trailing-space form left as-is (owner-approved).

### Version-gate fix (`translation_service.py`)

Same-version (1.4 = 1.4) value corrections were skipped despite
`needs_update=True`. Two edits:

1. Import skip requires `existing_val == val`.
2. `upsert_runtime_translation` version gate also requires
   `doc.translated_text == translated_text`.

Stabilization tests 8/8 pass. DRY then shows exactly the 3 pending updates.

## 2. Quorum governance

Independent A1/A2/A3 + AI-R recorded for the 85 AI-proposal rows:

- `stage6-w602-ai-a1-batch01-2026-09-22.md`
- `stage6-w602-ai-a2-batch01-2026-09-22.md`
- `stage6-w602-ai-a3-batch01-2026-09-22.md`
- `stage6-w602-ai-r-batch01-2026-09-22.md`

Build script (historical, asserts 2276 — never rerun):
`stage6_w602_ai_proposal_build_batch01_2026-09-22.py`.

## 3. Governed import cycle (authoritative)

| Step | Result |
|---|---|
| Pre-import DRY (after 3-row CSV fixes + version-gate fix) | `total=2275 created=0 updated=3 skipped=2272 drift=0` |
| IMPORT | `total=2275 created=0 updated=3 skipped=2272 drift=0` |
| Post-import idempotent DRY | `total=2275 created=0 updated=0 skipped=2275 drift=0` → `IDEMPOTENT_OK` |
| Catalog sync | `{'created': 0, 'updated': 0}` |
| Health | `has_drift=False`, `drift_details=[]` |

Decisions regenerated:
`release_decisions.json` **2275** decisions, sha
`2d37302845ce9a385036529ff14316256e40b4b549278fe93de6ab30324fae02`,
generated `2026-09-23T11:36:36Z`.

Freshness re-collected after import:
`packaged_rows=2275`, `critical_pass=true`, `has_drift=false`,
payload sha `44dfdfa89e31990f…`.

Inventory re-recorded: rows **20692**, root
`3905ee76849de3d1be03c9860901e304606c85f1f122adffd2910ddd6b110195`,
base commit `e522739…`. Manifest re-bound via `--update-baselines`.

## 4. Evidence gates

| Gate | Result |
|---|---|
| Full localization gate (`--skip-evidence` bootstrap) | **`errors=0`** |
| Full localization gate (**with evidence**, no skip) | **`errors=0`** |
| Standalone `test_localization_gates.py` | **Ran 91 tests … OK** |
| Module tests (11 modules) | **AGGREGATE total=270 failed=0** |
| Lints + `git diff --check` | **PASS / DIFFCHECK_CLEAN** |
| Scoped gate | **`errors=0`** |
| Vendor audit | **`errors=0`** |
| Evidence assembler | **10 envelopes + index** (`index.txt` sha `153a19a2c7ce8d5db0bde12078bb6ea82e537957aefe3fdd96287a52b3edd82b`) |

Stage-2 evidence path:
`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/`.

## 5. UAT preflight & Arabic browser session evidence

### Hard preflight (`scripts/uat_preflight.py`)

```text
PASS redis-cache: port 13000 PING ok
PASS redis-queue: port 11000 PING ok
PASS site-http: /ping 200
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=12577
PASS desk-boot-key: 'Could not find path for' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

Secret via STDIN only (never argv). `Administrator.language` temporarily `ar`.

### Headless Playwright browser evidence

- **Script**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w602/browser_evidence_w602_batch01.py`
- **Result**: **21/21 PASS (0 FAIL)**, exit `0`
- **JSON**: `browser_evidence_w602_batch01.json`
  (sha256 `abc7977068a5f6db89fbcf44b6061072a1d75257779a495399060c904d15afbc`)
- **Screenshot**: `browser-ar-desk-w602-batch01.png`
  (sha256 `0c4ed9acba6187cdf00a93f600da40d5d3bc2dda804885059823d5159a7ac391`)

Verified: `boot.lang=ar`, `__messages` 12,577; client `__()` 12/12 exact
(including the three corrected rows: path-for, `% of materials billed`,
`% of materials delivered`); placeholder `{0}` resolution; boot messages
lookup; rendered DOM Arabic; workspace modules; Arabic sidebar.

### Teardown (after browser evidence completed)

- Temporary UAT password rotated to `ct-w60b-rotated-off` (evidence password
  rejected with HTTP 401).
- `Administrator.language` restored to `en`.


### Evidence HEAD binding

Stage-2 evidence `index.txt` `CANDIDATE_HEAD` binds the **pre-cycle base HEAD**
(`e522739…`, parent of the cycle commit), matching the batch-7 pattern
(`a0f01cb` binds `8bfc23a`). The authoritative full gate with evidence was run
**at that base HEAD with the full working tree staged** → **`errors=0`**,
then the cycle was committed. Re-running the evidence-inclusive gate on the
post-commit tip will report `evidence-index-head` against live tip — that is
the expected self-reference limitation (the index cannot contain its own
commit hash). Bootstrap/`--skip-evidence` remains available for post-commit
source checks; the contract proof is the pre-commit `errors=0` run recorded
above.

## 6. Pre-commit artifact hashes

| Artifact | sha256 |
|---|---|
| batch-01 scope CSV (270, owner-approved) | `b017df4787ff8754be0bf43425151b748ba0aa019348fa29187f660130408fae` |
| payload disposition CSV (270) | `74b691d6b8fb06fc0092ed9756fc31e6d490f213d03b073fba04b844e0e269d0` |
| released list (85) | `3fe6961c9a640f24d23bfebe74aefc061d4a6eacd7ea671df4d624f4f45c59fc` |
| site recon JSON | `f8be402aa95a4acdeeff6139d7f34a90e6f4c4effbc71bddad6659bacdd70ef8` |
| `approved_ar_overrides.csv` (2275 Released) | `44dfdfa89e31990fc0cbbd37ef5efe8fe75dcbc4079602262b4ae7cab2f9b917` |
| `release_decisions.json` (2275) | `2d37302845ce9a385036529ff14316256e40b4b549278fe93de6ab30324fae02` |
| `freshness_evidence.json` | `fa2491c23a063637a63284d0b864ba67a64e9be2a868dc1dfad8ccb9c80ad387` |
| `localization_manifest.json` | `b2b071ab90abc6f39a46025b0ecc8d198ac2866774dbe32ad1144e9cf7559940` |
| `stage2_inventory_manifest.json` | `c7d63c53963179feb8297a3eba682bec521297fe8e3fa191f878dc6e2219588b` |
| `vendor_catalog_baseline.json` | `6586774f8fcf46e1a2b8ffe85b3a696b49365378a6a40febc9468a4a40a106f6` |
| `scripts/check_localization_gates.py` | `ab341a29b89631baef82b76717147ab5b5ac41f6212f54f6b1298451199c1a1b` |
| `construction/tests/test_localization_gates.py` | `57194e88352a039adab10ae14976764a695bb020507cc6596fa184b43067ba9f` |
| `construction/translation_service.py` | `6a43faf747567b31d155a3263f80944c0d8651ef2c222016d63f134481c4c6c8` |
| Stage-2 evidence `index.txt` | `153a19a2c7ce8d5db0bde12078bb6ea82e537957aefe3fdd96287a52b3edd82b` |
| browser evidence JSON | `abc7977068a5f6db89fbcf44b6061072a1d75257779a495399060c904d15afbc` |
| browser screenshot | `0c4ed9acba6187cdf00a93f600da40d5d3bc2dda804885059823d5159a7ac391` |

## 7. Scope of this approval (explicit exclusions)

- **In**: W6-2 Buying+Selling batch-01 only (exact 270-row CSV above), test
  site `v16.localhost` only, quorum for 85 payload rows, import + evidence
  gates, UAT browser evidence + teardown.
- **Out**: all other W6 matrix batches; any production mutation / catalog /
  DB rollout / Stage 8 production work (still gated on real production data +
  named production site + rollout window + AI-R on exact release commit).
