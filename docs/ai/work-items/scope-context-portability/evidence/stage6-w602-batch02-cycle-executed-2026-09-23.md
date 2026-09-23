# Stage 6 W6-2 — batch-02 governed cycle executed (test site, 2026-09-23)

**Status: CLOSED (governed cycle complete on `v16.localhost`).**

Owner approval (verbatim): Approve W6‑2 batch 02 only: the exact 48-row CSV
with SHA `9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce`.
Proceed with the governed cycle on `v16.localhost`; Stage 8 and production
remain gated.

Batch-02 scope CSV (owner-approved, historical — not edited this cycle):
`docs/translation/stage6_w602_batch02_rows_2026-09-23.csv`
(sha256 `9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce`, 48 rows).

## 1. Scope & disposition reconciliation (total 48 rows)

Authoritative site recon:
`docs/translation/stage6_w602_batch02_site_recon_2026-09-23.json`
(sha256 `2dc96898405eb9ad01495e8f26db7724b510affe36994493f9b2ea0e2afdb977`).

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override (not imported, plan §12)` | **1** | `Address` → `العنوان` (exact-key SO; empty catalog row + SO row retained) |
| `already-released (catalog row retained; not re-appended)` | **0** | — |
| `exception_technical` | **3** | `doctype`, `doc_type`, `quotation_item` (snake_case identifiers; keep vendor rendering) |
| `quorum-confirmed (release payload row)` | **44** | Released into managed override catalog (version 1.5) |
| **Total approved batch 2** | **48** | Exact match to approved scope CSV |

**Partition: 48 = 1 + 3 + 0 + 44.**

## 2. Quorum governance

Independent A1/A2/A3 + AI-R recorded for the 44 AI-proposal payload rows:

- `stage6-w602-ai-a1-batch02-2026-09-23.md` (APPROVE 44)
- `stage6-w602-ai-a2-batch02-2026-09-23.md` (ACCEPT 44)
- `stage6-w602-ai-a3-batch02-2026-09-23.md` (PASS 44)
- `stage6-w602-ai-r-batch02-2026-09-23.md` (APPROVE)

Build script (historical): `stage6_w602_ai_proposal_build_batch02_2026-09-23.py`.

## 3. Governed import cycle (authoritative)

| Step | Result |
|---|---|
| Pre-import DRY | `total=2319 created=44 updated=0 skipped=2275 drift=0` |
| IMPORT | `total=2319 created=44 updated=0 skipped=2275 drift=0` |
| Post-import idempotent DRY | `total=2319 created=0 updated=0 skipped=2319 drift=0` → `IDEMPOTENT_OK` |
| Catalog sync | `{'created': 0, 'updated': 0}` |
| Packaged runtime rows found | **44/44** |
| Address SO intact | empty catalog row + SO row |
| Freshness | `packaged_rows=2319`, `critical_pass=true`, `has_drift=false` |

Catalog: **2275 → 2319 Released** (all Released, 0 Pending);
`approved_ar_overrides.csv` sha `73f40e324f3169ec0d6fa1ff53fae5eb5850489825c04d744e995da2d31e8df3`.

Decisions regenerated: `release_decisions.json` **2319** decisions, sha
`1a9475d92acbca3cc6218b83d710027953787a7712962d06c65479cfb17b5590`.

Inventory re-recorded: rows **20736**, merkle root
`bb438f9fd3650201fb316e45584c02d4481c15fda56e82074ab8417a4d728bdc`,
base commit `90bc65e…` (recorded with `allow_commit_move=True`). Manifest
re-bound via `--update-baselines` (freshness_sha / inventory_sha /
decisions_sha all match live; packaged 2319).

Gate pins updated: `EXPECTED_DRYRUN` total **2319**
(`check_localization_gates.py:1510`); test pin `n=2319`
(`test_localization_gates.py:509`).

### Import note

Parallel/repeat IMPORT runs can fail with
`UniqueValidationError … ct_translation_key_digest` after rows exist —
harmless (state already correct). Never run IMPORT twice in parallel.

## 4. Evidence gates

| Gate | Result |
|---|---|
| Full localization gate (`--skip-evidence` bootstrap) | **`errors=0`** (`csv_rows=2319`) |
| Full localization gate (**with evidence**, pre-commit at base HEAD) | **`errors=0`** |
| Standalone `test_localization_gates.py` | **Ran 91 tests … OK** |
| Module tests (11 modules) | **AGGREGATE total=270 failed=0** |
| Lints + `git diff --check` | **PASS / DIFFCHECK_CLEAN** |
| Scoped gate | **`errors=0`** |
| Vendor audit | **`errors=0`** |
| Evidence assembler | **10 envelopes + index** (`index.txt` sha `955f5905fa7a6a92816c75d663895acaae4cf0a1c9ce5b460509df8bcdb90c62`) |
| Post-commit tip gate (`STAGE2_EVIDENCE_BOOTSTRAP=1 --skip-evidence`) | **`errors=0`** |

Stage-2 evidence path:
`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/`.

### Evidence HEAD binding

Stage-2 evidence `index.txt` `CANDIDATE_HEAD` binds the **pre-cycle base HEAD**
(`90bc65e403dfe3ee5530fa27997f3d5d5832af39`, parent of the cycle commit
`b3b0681`), matching the batch-7/batch-01 pattern. The authoritative full gate
with evidence was run **at that base HEAD with the full working tree staged**
→ **`errors=0`**, then the cycle was committed. Re-running the
evidence-inclusive gate on the post-commit tip reports `evidence-index-head`
against live tip — that is the expected self-reference limitation (the index
cannot contain its own commit hash). Bootstrap/`--skip-evidence` remains
available for post-commit source checks; the contract proof is the pre-commit
`errors=0` run recorded above.

## 5. UAT preflight & Arabic browser session evidence

### Hard preflight (`scripts/uat_preflight.py`)

```text
PASS redis-cache: port 13000 PING ok
PASS redis-queue: port 11000 PING ok
PASS site-http: /ping 200
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=12621
PASS desk-boot-key: 'Address' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

Secret via STDIN only (never argv). `Administrator.language` temporarily `ar`.

### Headless Playwright browser evidence

- **Script**: `docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w602/browser_evidence_w602_batch02.py`
- **Result**: **21/21 PASS (0 FAIL)**, exit `0`
- **JSON**: `browser_evidence_w602_batch02.json`
  (sha256 `4c22072648da7fdcc0ec919da39f8f23cf6d09c2fbf6ac80a2ccf0d53e1b58e7`)
- **Screenshot**: `browser-ar-desk-w602-batch02.png`
  (sha256 `44806e8acd444efa2125d4d8646502ced9b7413dfac696768542ab8fd3bccb69`)

Verified: `boot.lang=ar`, `__messages` 12,621; client `__()` 12/12 exact
(including preserved `Address` → `العنوان`); placeholder `{0}` resolution
(`POS has been closed at {0}…`); boot messages lookup; rendered DOM Arabic;
workspace modules; Arabic sidebar.

### Teardown (after browser evidence completed)

- Temporary UAT password rotated to `ct-w60b-rotated-off` (evidence password
  `ct-w602-evidence-1` rejected with HTTP 401).
- `Administrator.language` restored to `en`.

## 6. Pre-commit artifact hashes

| Artifact | sha256 |
|---|---|
| batch-02 scope CSV (48, owner-approved) | `9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce` |
| payload disposition CSV (48) | `09c492039774180b5cdc6d374c6979730d6d60adb1f05b0788ee4ae9ca6fab64` |
| released list (44) | `90988a93437ef1fa38309bf6dd54ff74448f3313882fb3e4be80c4ec07376f09` |
| site recon JSON | `2dc96898405eb9ad01495e8f26db7724b510affe36994493f9b2ea0e2afdb977` |
| `approved_ar_overrides.csv` (2319 Released) | `73f40e324f3169ec0d6fa1ff53fae5eb5850489825c04d744e995da2d31e8df3` |
| `release_decisions.json` (2319) | `1a9475d92acbca3cc6218b83d710027953787a7712962d06c65479cfb17b5590` |
| `freshness_evidence.json` | `e1bc6d8583757724a167f87f5d201de7cc75bcc221ccd8214296b9f68dca4cb9` |
| `localization_manifest.json` | `ef65794f1ae253f0e67bda6df2d973a01d56426c5b21a4b516ba9f624ea47975` |
| `stage2_inventory_manifest.json` | `0ad60058cfb42f6ac371ed52022616da00b9caf33203029c9ede02c560b0c9b0` |
| `vendor_catalog_baseline.json` | `5777a0ff81568550619e74babab660dac04310c08ead6a0a01d4f0faf5a6d82d` |
| `scripts/check_localization_gates.py` | `fb5b05254a2a0bdca6deca5e1bd02db60392e3ac56c3950bde4804a68185493d` |
| `construction/tests/test_localization_gates.py` | `13faa26bb185db32ca675677d05fd7a15a5891cf57a662a6aeec9895b7ed35ce` |
| Stage-2 evidence `index.txt` | `955f5905fa7a6a92816c75d663895acaae4cf0a1c9ce5b460509df8bcdb90c62` |
| browser evidence JSON | `4c22072648da7fdcc0ec919da39f8f23cf6d09c2fbf6ac80a2ccf0d53e1b58e7` |
| browser screenshot | `44806e8acd444efa2125d4d8646502ced9b7413dfac696768542ab8fd3bccb69` |
| browser evidence script | `2f20618b80074f21d8a2af6165d6e478e5cda64668a1d5757c428ca3f2aaf768` |

Cycle commit: **`b3b0681`** (parent `90bc65e`).

## 7. Scope of this approval (explicit exclusions)

- **In**: W6-2 Buying+Selling batch-02 only (exact 48-row CSV above), test
  site `v16.localhost` only, quorum for 44 payload rows, import + evidence
  gates, UAT browser evidence + teardown.
- **Out**: all other W6 matrix batches; any production mutation / catalog /
  DB rollout / Stage 8 production work (still gated on real production data +
  named production site + rollout window + AI-R on exact release commit).
