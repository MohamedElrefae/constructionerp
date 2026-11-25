# Stage-2 evidence contract — CURRENT measurement record (2026-10-20; reconciled 2026-10-22)

**This is a CURRENT measurement record, not a historical one.** It is kept
separate from the historical evidence set under
`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2`, which
is bound to its own root, its own HEAD and the 2026-09-29 expectation. That
historical set is **not** rewritten by this record.

- Machine-readable twin: `construction/tests/tools/stage2_current_measurements.json`
- Raw artifacts: `construction/tests/tools/measurements/2026-10-20-current/`
  (the 2026-10-20 measurement set) and
  `construction/tests/tools/measurements/2026-10-22-je-current/`
  (the 2026-10-22 reconciliation artefact, M1B)
- Reviewer: F44 Qualified Successor <successor@f44.invalid>
- Reviewed: 2026-10-20 (reconciled and re-reviewed 2026-10-22 — see the last
  section of this document)

## Environment of the measurements

| item | value |
|---|---|
| working directory | `/tmp/opencode/f44-bench/apps/construction` |
| root (checker `--root`) | `/tmp/opencode/f44-bench/apps/construction` |
| site | `v16-protocol.localhost` (db `_9dc78eb5bb385977`, apps frappe/erpnext/construction) |
| app source | `/tmp/opencode/protocol-roundtrip`, branch `codex/f44-protocol-roundtrip-20261019`, rsync-synced into the owned bench app copy |
| app HEAD sha | `73b49077c0395d370752bb1591a6536584a76566` |
| app tree sha | `e9cc7ec8f68039c04ad45b39b6f156a3ea23a6a1` |
| vendor HEAD frappe | `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` |
| vendor HEAD erpnext | `7474d9e786277383de1242ab882f16856d17a9c9` |
| python | `/home/mohamed/frappe-bench/env/bin/python` (CPython 3.14.5) |

`PYTHONPATH=/tmp/opencode/f44-bench/apps/construction` was exported for every
`bench` invocation so that `import construction` resolves to the app copy under
measurement and not to the shared checkout.

## Commands and raw results

| id | command (run from the working directory above) | exit | result |
|---|---|---|---|
| M1 | `STAGE2_EVIDENCE_BOOTSTRAP=1 python scripts/check_localization_gates.py --root=/tmp/opencode/f44-bench/apps/construction --skip-evidence` | 0 | `catalog=1052 files=328 wrapped=861 json_labels=77 missing=0 csv_rows=4337 errors=0` |
| M2 | `python construction/tests/test_localization_gates.py -v` | 0 | `Ran 101 tests` / `OK` |
| M3 | `bench --site v16-protocol.localhost console` → `construction.translation_service.import_released_overrides(dry_run=True)` | 0 | `total=4337 created=0 updated=0 skipped=4337 drift=0` |
| M4 | `python construction/tests/tools/stage2_measure_extract_counts.py <root>` | 0 | independent AST extraction, aggregate 283 |
| M5 | `bench --site v16-protocol.localhost run-tests --app construction --module <module>` for **every** module of the required set | 0 (all 11) | 13, 6, 5, 3, 8, 101, 38, 53, 6, 14, 36 → aggregate 283, all `OK` |

Raw stdout/stderr of every command is stored verbatim under
`construction/tests/tools/measurements/2026-10-20-current/`; the sha256 of each
artifact is recorded in `stage2_current_measurements.json`.

## The frozen contract these measurements produced (as frozen on 2026-10-20)

`stage2-current-contract/2026-10-20` in `scripts/check_localization_gates.py`
— **superseded on 2026-10-22 for the extract file count only**; the contract
that is frozen today is `stage2-current-contract/2026-10-22` (see the last
section). The 2026-10-20 values below are kept verbatim as history and are
preserved machine-readably under `previous_frozen_contract_kept_as_history`:

- gate: `catalog=1052 files=328 wrapped=861 json_labels=77 missing=0`
- modules: `13, 6, 5, 3, 8, 101, 38, 53, 6, 14, 36` (aggregate 283)
- dry run: `total=4337 created=0 updated=0 skipped=4337 drift=0`
- source pins (content digests of the measured sources — a drifted pin is
  refused with `evidence-contract-source-drift`):
  - `construction/locale/ar.po` → `8b065ad4ae18b59421a24f230ce2069e94103a1b6f8249c87b06464fcb015c0b`
  - `construction/data/translations/approved_ar_overrides.csv` → `845ab43ea0bef6d7db9f3875b8ceadafa0c923934c69607e6d6ceda715262318`
  - `construction/data/localization/localization_manifest.json` → `816ccc57fb233a5ad95ea391c43bafba34809a5bc894cfe8a5cc3fe29d10b85e`
  - `construction/data/localization/vendor_catalog_baseline.json` → `8407099579b8f99a1ed04258ae2df70021d2c4205aad149c8d43dffec531fd69`
  - `construction/data/localization/stage2_inventory_manifest.json` → `7e639ec8182f14aaa7f1c23a71519100f789c6ec05d20d83cbe4d4335e051d60`

Follow-up (2026-10-21, P13-CI-003): the `vendor_catalog_baseline.json` pin followed the reviewed scoped one-field
`apps.frappe.commit` re-record (2871914b → af4409) in that same file. No measured count changed; the vendor
catalog bytes the counts were measured from are identical (only the recorded commit identity moved), so the
2026-10-20 measurements stand and only this content digest was re-recorded.

M4 is an **independent** cross-check: it counts the test methods the loader
would collect straight from the source, without reading the evidence and
without reading the contract constants, and it agrees with the executed M5
counts module by module.

## The historical expectation is kept separately

`stage2-legacy-contract/2026-09-29` keeps the recorded 2026-09-29 values
verbatim (`817/265/667/29`, modules `… 92 … 11 …`, aggregate 271). It is
reachable only through the explicit `--evidence-contract=legacy` invocation
choice and is never overwritten by the current contract. The active contract is
always an explicit invocation choice; it is never inferred from the evidence
under validation.

## Independent verification addendum (2026-10-20, second reviewer)

A second reviewer re-executed the site-independent parts of this record
against HEAD `eca546d0c6a4031225ce10fb6ab6f70753c4065e` and re-verified the
committed artefacts. This addendum **adds** to the record above; it does not
replace it and it does not rewrite any of the measurements it cites.

| check | command (from `/tmp/opencode/f44-bench/apps/construction`) | exit | result |
|---|---|---|---|
| V1 | `STAGE2_EVIDENCE_BOOTSTRAP=1 python3 scripts/check_localization_gates.py --root=/tmp/opencode/f44-bench/apps/construction --skip-evidence` | 0 | identical to M1: `catalog=1052 files=328 wrapped=861 json_labels=77 missing=0 csv_rows=4337 errors=0` |
| V2 | `python3 construction/tests/test_localization_gates.py -v` | 0 | identical to M2: `Ran 101 tests` / `OK` |
| V3 | `python3 construction/tests/tools/stage2_measure_extract_counts.py .` | 0 | identical to M4: aggregate 283, no per-module drift against the frozen contract |
| V4 | sha256 of every artefact the JSON record cites | — | 15 artefacts checked, **0 mismatches** |
| V5 | `python3 construction/tests/tools/test_stage2_evidence_roundtrip.py -v` | 0 | 8 tests, `OK` |
| V6 | `python3 construction/tests/tools/test_stage2_evidence_cli_matrix.py -v` | 0 | 10 tests, `OK` |
| V7 | `STAGE2_PROTOCOL_CI=1` + pinned `frappe/public/js/frappe/form/script_manager.js` removed from the pinned vendor tree | 1 | the required run **FAILS** (it does not skip and does not report green) |
| V8 | `pre-commit run --all-files` (the gate the Linters CI job runs) | 0 | all hooks pass |

Three facts that this addendum adds and that the record above does not state:

0. **The branch as delivered was not lint-clean.** `pre-commit run --all-files`
   failed at the delivered HEAD: `ruff-format` rejected three delivered files
   (`scripts/check_localization_gates.py`,
   `construction/tests/tools/stage2_evidence_assemble.py`,
   `construction/tests/tools/stage2_measure_extract_counts.py`) and the `ruff`
   linter rejected one (`UP038` in `stage2_measure_extract_counts.py`). The
   Linters CI job runs exactly that gate, so those findings would have failed
   a required job. They are corrected in this addendum; the corrections are
   formatting/lint only and change no measured value — the source-scan counts
   (V1), the standalone count (V2) and the aggregate (V3) are unchanged by
   them.

1. **The frozen contract can now be proven against the live source.** The
   independent extractor (M4) was previously only a manual cross-check. It is
   now a required guard,
   `construction/tests/tools/test_stage2_contract_source_agreement.py`, which
   fails closed and names the module and both numbers when the frozen counts
   drift from the source. It also proves that the dated record still matches
   the contract constants, that the recorded artefact digests are intact, and
   that the historical expectation is preserved verbatim and is never compared
   against the live source. It runs in the required `stage2-evidence-protocol`
   CI job.

2. **A bench measurement can silently measure the wrong tree.** In the owned
   bench, `apps/frappe` and `apps/erpnext` are symlinks into the shared
   checkout, so Frappe's `get_bench_path()` resolves to
   `/home/mohamed/frappe-bench` and an unpinned
   `bench --site <site> run-tests` imports `construction` from the **shared**
   checkout instead of the owned app copy. The reviewer observed exactly that:
   an unpinned run reported `Ran 92 tests … FAILED (failures=3)` with the
   traceback pointing at `/home/mohamed/frappe-bench/apps/construction/…` and
   the legacy `catalog=817`. That is **not** a measurement of this candidate.
   The M5 measurements above were therefore taken with
   `PYTHONPATH=/tmp/opencode/f44-bench/apps/construction` exported, and every
   future bench measurement of this contract must do the same and must record
   the resolved app path.

**Not re-verified by the second reviewer:** M3 (the released-override dry run)
and M5 (the eleven site-backed module runs) could not be re-executed, because
the owned site `v16-protocol.localhost` and its database `_9dc78eb5bb385977`
were dropped from the owned bench while the review was in progress. The
committed M3/M5 artefacts are unchanged and their digests still verify
(V4); they were executed by the first reviewer at HEAD `73b49077…`, which
differs from the current HEAD only by the measurement artefacts and this
record — no file in the required module set, and no file the source scan
reads, changed between them. A fresh site-backed run against the final
qualified HEAD is still owed before the contract joins a qualification
candidate.

## Current-contract reconciliation (2026-10-22) — measurement M1B

**What changed and why.** The frozen CURRENT contract said the source scan
counts `extract.files=328`, but the reviewed JE candidate's actual source scan
reports `extract.files=329`. This is a **measured contract drift**, not a new
implementation: the reviewed JE project-preservation production patch added
exactly **one NEW production module**,
`construction/services/boq_journal_project.py`, and the source scan counts
every localizable file under `construction/`, so that single new `.py` file
adds exactly `1` to `extract.files` and to nothing else.

**The executed measurement (M1B).**

| item | value |
|---|---|
| command | `cd /tmp/f44-je-private-ci-preparation-20261022/apps/construction && GITHUB_ACTIONS=true python3 scripts/check_localization_gates.py --ci-source-only` |
| root | `/tmp/f44-je-private-ci-preparation-20261022/apps/construction` |
| source HEAD | `a7686c518ce7be7d91758a0cc8854199e1304e45` |
| source tree | `5ebd6ba9a5b22a50c51efa0aa91a43cfc98a4960` |
| branch | `codex/customer-release-ci-je-project-20261022` (parentless, 2381 tracked files, clean) |
| exit | `0` |
| result | `catalog=1052 files=329 wrapped=861 json_labels=77 missing=0 csv_rows=4337 raw_text=7/0/2 errors=0` |
| raw artefact | `construction/tests/tools/measurements/2026-10-22-je-current/m1_source_scan.txt` |
| raw artefact sha256 | `8d9109845421d44ef8d87d60877c25f8448870b743ed4f35b5428902fa3a6d36` |

The raw artefact is a **byte-for-byte copy of the primary's own actual run**
(`qualified62-je-private-ci-parent/source-only-corrected.log`, same sha256). It
was not reconstructed from a hash and it is not the 2026-10-20 log relabelled —
that artefact (`6c63f583…`) is preserved unchanged at its own path and differs
in exactly one number (`files` 328 vs 329). The six `SKIP` lines in the raw
stdout are the checker's own **static markup/print-format classification** (a
markup/code blob excluded from the string gate); they are **not** skipped tests
and **not** a skipped gate.

The measurement is bound to the source HEAD it was taken at
(`a7686c51…`), **before** this metadata amendment. No binding to a commit that
does not exist yet is claimed.

**Cause, proven by ablation.** Removing *only*
`construction/services/boq_journal_project.py` from the candidate tree
reproduces `files=328` with `catalog=1052`, `csv_rows=4337`, `wrapped=861`,
`json_labels=77`, `missing=0`, `raw_text 7/0/2`, `errors=0` and exit `0`;
restoring it reproduces `files=329` with a byte-identical stdout. No other
file was added, removed or changed, and all five `CURRENT_SOURCE_PINS` still
match the live files on the candidate.

**The frozen contract today** — `stage2-current-contract/2026-10-22`:

- gate: `catalog=1052 files=329 wrapped=861 json_labels=77 missing=0`
- modules: `13, 6, 5, 3, 8, 101, 38, 53, 6, 14, 36` (aggregate 283) — **unchanged**
- dry run: `total=4337 created=0 updated=0 skipped=4337 drift=0` — **unchanged**
- source pins: **unchanged** (all five re-verified against the candidate)

**Minimum coherent delta.** Only the fields that had to move moved:

| field | 2026-10-20 | 2026-10-22 |
|---|---|---|
| `CURRENT_EXPECTED_GATE.files` | 328 | **329** |
| `CURRENT_CONTRACT_ID` | `stage2-current-contract/2026-10-20` | **`stage2-current-contract/2026-10-22`** |
| `CURRENT_EXPECTED_GATE.catalog / wrapped / json_labels / missing` | 1052 / 861 / 77 / 0 | unchanged |
| `CURRENT_EXPECTED_MODULES` (11 modules, aggregate 283) | — | unchanged |
| `CURRENT_SOURCE_PINS` (5 digests) | — | unchanged |
| `LEGACY_EXPECTED_GATE` / `LEGACY_EXPECTED_MODULES` / `LEGACY_CONTRACT_ID` / `LEGACY_SOURCE_PINS` | — | **untouched** |

The contract id had to carry the new review date, so the three sites that
name it were updated: `scripts/check_localization_gates.py`
(`CURRENT_CONTRACT_ID`), the JSON twin (`review.contract_id`,
`review.review_history`, `frozen_contract_from_these_measurements.contract_id`)
and this document. Every other consumer reads it **dynamically**
(`stage2_evidence_assemble.py` uses `CHECKER.CURRENT_CONTRACT_ID`;
`test_stage2_contract_source_agreement.py` uses `checker.CURRENT_CONTRACT_ID`),
so no dependent test or fixture needed to change. The legacy contract keeps
its own id, its own values and its explicit `--evidence-contract=legacy` path.

**Preserved, not rewritten.** The 2026-10-20 measurement record (M1–M5), all
of its raw artefacts and all of their digests are preserved unchanged; the
2026-10-20 frozen contract is preserved verbatim under
`previous_frozen_contract_kept_as_history`; the 2026-09-29 historical
expectation and its evidence set are untouched.

**Not re-executed and still owed.** M3 (the site-backed released-override dry
run) and M5 (the eleven site-backed required-module runs) were **not**
re-executed for this reconciliation and no current M3/M5 number was invented;
their committed artefacts and digests are unchanged and still verify. They
remain a fresh site-backed run owed against the final qualified HEAD. The
reconciliation did not change the module set, any module count, the aggregate,
the dry-run arithmetic or the pins, so those recorded values stand as recorded.

**Consequence for the unexecuted full gate.** The full site-aware evidence
gate (the `--skip-evidence` bootstrap capture plus the ten recorded envelopes)
has **not** been re-executed against this candidate. A future capture of
`full-gate.txt` must carry `extract.files=329` (superseded on 2026-11-22: the
current requirement is `341` — see the last section); a capture that carries
`328` or `329` is **refused** by the current contract
(`evidence-schema: full-gate.txt file count differs from contract`). The
historical 2026-09-29 envelope set is unaffected because it is validated
through the explicit legacy path. The unexecuted full gate therefore still
owes a fresh site-backed capture against the final qualified HEAD; this
reconciliation cannot and does not supply it.

This is a technical, measured contract correction for technical review. It is
**not** a release approval, **not** a native (site/bench) acceptance, **not** a
business acceptance and **not** an F44 closure.

---

## 2026-11-22 — re-measurement after the P1 scope merge (M1C)

The P1 execution-tree and scope-context merge added localizable strings and one
production module, and the Arabic catalog moved with it. The contract was
re-measured on the merged source and the seven strings the extraction reported
missing were added to `construction/locale/ar.po`; three dynamic
`frappe.throw(error.message)` sites were wrapped at construction.

| item | value |
|---|---|
| contract | `stage2-current-contract/2026-11-22` |
| gate | `catalog=1121 files=341 wrapped=914 json_labels=79 missing=0` (csv_rows 4337, raw_text 7/0/2) |
| module set, module counts, aggregate, dry-run | unchanged (283; 4337/0/0/4337/0) |
| source pins re-recorded | `construction/locale/ar.po`, `construction/data/localization/localization_manifest.json` |
| source pins unchanged | approved CSV, vendor catalog baseline, inventory manifest |
| raw artifact | `construction/tests/tools/measurements/2026-11-22-p1-current/m1_source_scan.txt` |
| environment | develop `5e6fe93`, working tree with the 2026-11-22 fixes uncommitted at measurement time |

The local scan reports one `vendor-delta` error because this bench's frappe HEAD
is `2871914`, not the pinned private vendor `af440917`. CI checks out the pinned
vendor and does not report it; the vendor check is independent of the counts
recorded here.

The 2026-10-22 block is preserved under
`previous_frozen_contract_kept_as_history` (now a list of both superseded
blocks). The 2026-09-29 historical expectation and its evidence set are
untouched.

**Review status: PENDING.** This is a builder re-measurement. No owner or tester
review of the new contract has occurred, and this record does not claim one. The
site-backed M3/M5 runs remain owed against the final qualified HEAD exactly as
stated above.

---

## 2026-11-24 — re-measurement after WBS P2 Slice 1 (M1D)

WBS P2 Slice 1 (`98fd5a3`) added execution-location mapping modules and 27
localized strings, which were added to `construction/locale/ar.po`, and wrapped
the inheritance warning directly at `frappe.msgprint`. Freshness evidence was
re-collected on `wbs-p1-lab.localhost` (`packaged_rows=4337`, `runtime_digest`
unchanged).

| item | value |
|---|---|
| contract | `stage2-current-contract/2026-11-24` |
| gate | `catalog=1148 files=345 wrapped=941 json_labels=79 missing=0` (csv_rows 4337, raw_text 7/0/2) |
| module set, module counts, aggregate, dry-run | unchanged (283; 4337/0/0/4337/0) |
| source pins re-recorded | `construction/locale/ar.po`, `construction/data/localization/localization_manifest.json` |
| source pins unchanged | approved CSV, vendor catalog baseline, inventory manifest |
| raw artifact | `construction/tests/tools/measurements/2026-11-24-p2s1-current/m1_source_scan.txt` |
| environment | develop `98fd5a3`, working tree with the 2026-11-24 P2 Slice 1 localization fixes |

The 2026-11-22 block is preserved verbatim under
`previous_frozen_contract_kept_as_history`. **Review status: PENDING.**

---

## 2026-11-24 — re-measurement after WBS P2 Slice 2 (M1E)

WBS P2 Slice 2 (on `develop` `a865bc4`) added `set_stage_execution_node`, A1
execution-lock guards across all 8 required BOQ transaction child types, and 6
localized strings to `construction/locale/ar.po`. Freshness evidence was
re-collected on `wbs-p1-lab.localhost` (`packaged_rows=4337`, `runtime_digest`
unchanged).

| item | value |
|---|---|
| contract | `stage2-current-contract/2026-11-24-p2s2` |
| gate | `catalog=1154 files=345 wrapped=947 json_labels=79 missing=0` (csv_rows 4337, raw_text 7/0/2) |
| module set, module counts, aggregate, dry-run | unchanged (283; 4337/0/0/4337/0) |
| source pins re-recorded | `construction/locale/ar.po`, `construction/data/localization/localization_manifest.json` |
| source pins unchanged | approved CSV, vendor catalog baseline, inventory manifest |
| raw artifact | `construction/tests/tools/measurements/2026-11-24-p2s2-current/m1_source_scan.txt` |
| environment | develop `a865bc4`, working tree with the 2026-11-24 WBS P2 Slice 2 changes |

The `stage2-current-contract/2026-11-24` (M1D) block is preserved verbatim under
`previous_frozen_contract_kept_as_history`. **Review status: PENDING.**

---

## 2026-11-24 — re-measurement after WBS P2 Slice 3 (M1F)

WBS P2 Slice 3 (on `develop` `cf42516`) added bilingual EN/AR form UX on
`BOQ Item` (`boq_item.js`) and `BOQ Item Stage` (`boq_item_stage.js`) with
read-only location banners, visible product rule, disabled-ancestor alerts,
new-Stage inheritance preview, authorized picker/clear dialogs, and accessible
audit history modals, plus 50 localized strings in `construction/locale/ar.po`.
Freshness evidence was re-collected on `wbs-p1-lab.localhost`
(`packaged_rows=4337`, `runtime_digest` unchanged).

| item | value |
|---|---|
| contract | `stage2-current-contract/2026-11-24-p2s3` |
| gate | `catalog=1204 files=345 wrapped=997 json_labels=79 missing=0` (csv_rows 4337, raw_text 7/0/2) |
| module set, module counts, aggregate, dry-run | unchanged (283; 4337/0/0/4337/0) |
| source pins re-recorded | `construction/locale/ar.po`, `construction/data/localization/localization_manifest.json` |
| source pins unchanged | approved CSV, vendor catalog baseline, inventory manifest |
| raw artifact | `construction/tests/tools/measurements/2026-11-24-p2s3-current/m1_source_scan.txt` |
| environment | develop `cf42516`, working tree with the 2026-11-24 WBS P2 Slice 3 changes |

The `stage2-current-contract/2026-11-24-p2s2` (M1E) block is preserved verbatim
under `previous_frozen_contract_kept_as_history`. **Review status: PENDING.**


---

## 2026-11-25 — re-measurement after WBS P3 Slice 1 (M1G)

WBS P3 Slice 1 (on `develop` `e5ba52e`) added the pure Execution Coverage rules
(`execution_coverage_rules.py`), authorized read-only coverage & streaming
CSV/XLSX export service (`execution_coverage.py`), and read-only GET API
(`execution_coverage_api.py`), plus 70 localized strings in
`construction/locale/ar.po`. Freshness evidence was re-collected on the
disposable non-production lab `p3-lab.localhost` (`/tmp/p3-isolated.pmpttI/sites`,
private MariaDB + separate Redis restored from the archived non-production
`wbs-p1-lab` backup; catalog sync +153 rows, packaged override import verified
`4337/0/0/4337/0` preserving the genuine `2026-11-20` packaged release import
timestamp; `runtime_digest` unchanged; `v16.localhost` untouched).

| item | value |
|---|---|
| contract | `stage2-current-contract/2026-11-25-p3s1` |
| gate | `catalog=1274 files=348 wrapped=1068 json_labels=79 missing=0` (csv_rows 4337, raw_text 7/0/2) |
| module set, module counts, aggregate, dry-run | unchanged (283; 4337/0/0/4337/0) |
| source pins re-recorded | `construction/locale/ar.po`, `construction/data/localization/localization_manifest.json` |
| source pins unchanged | approved CSV, vendor catalog baseline, inventory manifest |
| raw artifact | `construction/tests/tools/measurements/2026-11-25-p3s1-current/m1_source_scan.txt` |
| environment | develop `e5ba52e`, working tree with the 2026-11-25 WBS P3 Slice 1 changes |

The `stage2-current-contract/2026-11-24-p2s3` (M1F) block is preserved verbatim
under `previous_frozen_contract_kept_as_history`. **Review status: PENDING.**


---

## 2026-11-25 — re-measurement after WBS P3 Slice 2 (M1H)

Added WBS P3 Slice 2 bilingual EN/AR `execution-coverage` Frappe Page (with
selectable `BOQ Structure` subtree filter) and P1 `execution_breakdown.js`
**View Coverage** navigation (on `develop` `b76abbf`), adding 3 localizable
files, 1 UI JSON title, and 24 Arabic strings in `construction/locale/ar.po`.
Freshness evidence was re-collected on disposable non-production lab
`p3-lab.localhost` (`/tmp/p3-isolated.pmpttI/sites`; packaged override import
verified `4337/0/0/4337/0` preserving the genuine `2026-11-20` packaged release
import timestamp; `runtime_digest` unchanged; `v16.localhost` untouched).

| item | value |
|---|---|
| contract | `stage2-current-contract/2026-11-25-p3s2` |
| gate | `catalog=1298 files=351 wrapped=1094 json_labels=80 missing=0` (csv_rows 4337, raw_text 7/0/2) |
| module set, module counts, aggregate, dry-run | unchanged (283; 4337/0/0/4337/0) |
| source pins re-recorded | `construction/locale/ar.po`, `construction/data/localization/localization_manifest.json` |
| source pins unchanged | approved CSV, vendor catalog baseline, inventory manifest |
| raw artifact | `construction/tests/tools/measurements/2026-11-25-p3s2-current/m1_source_scan.txt` |
| environment | develop `b76abbf`, working tree with the 2026-11-25 WBS P3 Slice 2 changes |

The `stage2-current-contract/2026-11-25-p3s1` (M1G) block is preserved verbatim
under `previous_frozen_contract_kept_as_history`. **Review status: PENDING.**
