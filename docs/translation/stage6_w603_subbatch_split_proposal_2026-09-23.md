# Stage 6 — W6-3 Stock sub-batch split (2026-09-23)

**Status: PROPOSAL ONLY — batch 1 presented for approval. No quorum, no import, no catalog change, no evidence re-pin, no production, no Stage-8.**

**Proposal only. No quorum, no import, no evidence re-pin. Awaiting owner approval of batch 1 exact scope. Stage 8 and production remain gated.**

## Parent universe (already owner-approved as candidate universe, not as one import batch)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w603_stock_rows_2026-09-23.csv` |
| Rows | **734** |
| sha256 | `a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535` |
| Arithmetic | `789 = 734 scope + 55 exclusions` (13 HTML + 3 newline + 39 `len>120`) |
| Dispositions (universe) | 720 PROPOSED-payload + 14 PROPOSED-EXCEPTION-technical = 734 |

Owner directive: split deterministically into manageable sub-batches (~200–300 rows each); present batch 1 for approval before quorum/import; leave the seven prior commits intact (no squash).

## Deterministic split rule

Reproduce with `python3 scripts/stage6_w603_stock_split_2026-09-23.py` (fail-closed; asserts universe sha256 before write).

1. Load universe CSV; assert sha256 `a60b1c8e…` and row count 734.
2. Rows already unique and sorted by `(area, source_text)`.
3. Contiguous slices in that order: **250 + 250 + 234** (`BATCH_SIZE=250`; final batch remainder; all sizes in `[200, 300]`).
4. Union of batch keys == universe; pairwise intersections empty.
5. Per-batch disposition uses the same `is_technical_token` rule as the cut builder.
6. Per-batch overlap proof vs released catalog and prior Stage-6 keys.

## Sub-batch inventory (all three; proposal only)

| Batch | File | Rows | sha256 | PROPOSED-payload | PROPOSED-EXCEPTION-technical | already-released | pre-filled | unfilled |
|---|---|---:|---|---:|---:|---:|---:|---:|
| **01** | `docs/translation/stage6_w603_batch01_rows_2026-09-23.csv` | **250** | `5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380` | 240 | 10 | 0 | 115 | 135 |
| 02 | `docs/translation/stage6_w603_batch02_rows_2026-09-23.csv` | 250 | `701ad13e6b4cc530ebd7dbd95705979b70055c46f39da37d4532a26ba60439ef` | 248 | 2 | 0 | 143 | 107 |
| 03 | `docs/translation/stage6_w603_batch03_rows_2026-09-23.csv` | 234 | `a5f0e9f604ea52d89072d2c744864fdcbc733bc8307fd427a5c2658f4855dbc9` | 232 | 2 | 0 | 121 | 113 |
| **Σ** | | **734** | (parent `a60b1c8e…`) | **720** | **14** | **0** | **379** | **355** |

Columns identical to parent: `source_text,suggested_ar,locations,area,has_pre_filled`.

## Overlap proof (all three batches; independently re-checked)

| Check | Batch 01 | Batch 02 | Batch 03 |
|---|---:|---:|---:|
| vs released catalog (2,319) | **0** | **0** | **0** |
| vs prior Stage-6 scope/payload/released union | **0** | **0** | **0** |
| vs technical exclusions (21) | **0** | **0** | **0** |
| vs a1/a2 dedup exclusions (302) | **0** | **0** | **0** |
| vs W6-2 batch 01 / batch 02 / W6-1 | **0 / 0 / 0** | **0 / 0 / 0** | **0 / 0 / 0** |
| vs other W6-3 sub-batches | **0** | **0** | **0** |
| internal duplicates | **0** | **0** | **0** |

**Partition integrity:** pairwise batch overlap **0** (all pairs); union == universe (**734**); contiguous slices of sorted parent verified; sizes `[250, 250, 234]`.

**Headline:** `universe=734; batches disjoint; union=734; catalog_overlap=0 all; proposed payload/tech sum to universe (720+14=734).`

## Batch 01 — presented for approval (only)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w603_batch01_rows_2026-09-23.csv` |
| Rows | **250** |
| sha256 | `5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380` |
| Dispositions (pre-cycle proposal recommendations) | PROPOSED-payload **240** · PROPOSED-EXCEPTION-technical **10** · already-released **0** · total **250** |
| Pre-filled / unfilled | 115 / 135 |
| Overlap | catalog **0** · prior stage6 **0** · tech/dedup **0/0** · other batches **0** · internal dups **0** |
| Site (if approved to run) | `v16.localhost` test site only |

Batch 02 and batch 03 remain **unapproved** until separate owner mark-up after batch 01’s governed cycle (or earlier if the owner pre-approves their exact shas).

## Exclusions (unchanged from parent proposal)

- 55 residual raw rows (13 HTML + 3 newline + 39 `len>120`) — not in universe, not in any batch
- Already-released catalog keys: **0** found in raw 789
- Other matrix rows W6-0/1/2/4/5/6/7 and non-`stock` areas
- Shared technical (21) + dedup (302) exclusion files — 0 intersection
- Production / Stage-8 / evidence re-pin / site import — gated
- Site overrides deferred to cycle-time recon (plan §12); none pre-removed

Evidence re-pin was performed as part of the approved batch-01 governed cycle.

## Post-approval disposition correction

The governed gate reclassified seven formula/letter source-equal keys (`A - B`, `A - C`, `D - E`, `G - D`, `H - F`, `I - J`, `I - K`) from payload to `EXCEPTION-technical`. Final batch-01 disposition is **115 preserved + 17 technical + 0 already-released + 118 payload = 250**. The approved scope CSV sha is unchanged; batch 02 and batch 03 remain unapproved.

## Boundary

- **Quorum and import will NOT start until the owner approves batch 01 exact scope** (CSV path + sha256 above).
- Approving batch 01 authorizes **only** the 250-row CSV above to enter the governed cycle on the test site when the owner says go.
- Batch 02 (`701ad13e…`) and batch 03 (`a5f0e9f6…`) are inventory only until separately approved.
- Expanding or re-cutting any batch requires a new exact CSV + sha256.
- The seven prior W6-3 proposal commits remain intact (no squash per owner).
- Matrix row W6-3 owner box stays ☐ until mark-up.

## Owner mark-up requested

- [x] **Approve W6-3 batch 01 only** — the 250-row CSV
      (`docs/translation/stage6_w603_batch01_rows_2026-09-23.csv`,
      sha256 `5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380`)
      as the exact next governed import batch.
- [x] Acknowledge batch 02 and batch 03 are split inventory only (not approved for quorum/import).
- [x] Acknowledge partition integrity: 250+250+234=734, pairwise overlap 0, catalog overlap 0.
- [x] Leave production / Stage-8 gated.
