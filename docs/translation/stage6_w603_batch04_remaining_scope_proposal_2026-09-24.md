# Stage 6 — W6-3 Stock batch-04 proposal-only package (2026-09-24)

## Result

The committed W6-3 candidate universe is exhausted by batches 01–03. There are **zero new eligible payload rows** for a normal batch 04. The only unresolved remainder is a previously dispositioned exception backlog of 23 rows.

This package is proposal-only and is not an import scope:

- Withheld CSV: `docs/translation/stage6_w603_batch04_withheld_rows_2026-09-24.csv`
- Rows: **23**
- SHA-256: `16210edefa13746e8689874e4df84b81d49fa0dc9d92963f87c12373daf22aaf`
- Serialization: UTF-8, LF line endings, no BOM, parent-universe order, header plus 23 rows

## Source and prior-batch accounting

| Artifact | Rows | SHA-256 |
|---|---:|---|
| W6-3 parent universe | 734 | `a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535` |
| Batch 01 | 250 | `5eb34bc2dbaf3cf201efc5d856085e32375a68fca959082b3afd8111f7b08380` |
| Batch 02 | 250 | `701ad13e6b4cc530ebd7dbb95705979b70055c46f39da37d4532a26ba60439ef` |
| Batch 03 | 234 | `a5f0e9f604ea52d89072d2c744864fdcbc733bc8307fd427a5c2658f4855dbc9` |
| Current Released catalog | 2,651 | `78ee35b2c0ea322527ccbe6272244794cd8524dd86f5df84a0c4f34f262d0016` |
| Current release decisions | 2,651 | `18d6dcecb373d955b759ddb5a4eb0aeb1e413889739851f509f20438232388ee` |

Batch 01 + 02 + 03 = 734, with zero pairwise overlap. Their final disposition is 332 released payload, 379 preserved Site Overrides, 21 technical exceptions, and 2 deferred source defects.

The 23-row package is the exact technical/deferred subset of the 402-row catalog complement. The other 379 complement rows are preserved Site Overrides and must not be reopened as packaged releases.

## Proposed dispositions

| Disposition | Rows | Treatment |
|---|---:|---|
| `EXCEPTION-technical` | 21 | Retain vendor rendering; do not import or propose Arabic payload |
| `DEFERRED-source-defect` | 2 | Keep deferred pending vendor-source correction; no translation/import action |
| **Total** | **23** | **0 new payload** |

Technical keys: `A - B`, `A - C`, `CODE-39`, `D - E`, `EAN`, `EAN-12`, `EAN-8`, `G - D`, `GS1`, `GTIN`, `H - F`, `I - J`, `I - K`, `ISBN`, `ISBN-10`, `ISBN-13`, `ISSN`, `JAN`, `PZN`, `UPC`, `UPC-A`.

Deferred source defects:

- `Reserved Qty ({0}) cannot be a fraction. To allow this, disable '{1}' in UOM {3}.` — the inspected formatter does not provide positional argument `{3}`.
- `Row # {0}: Please enter quantity for Item {1} as it is not zero.` — the source condition/message conflicts with the zero-quantity branch.

## Overlap checks

All checks below are repository-read-only checks against the committed files.

| Check | Result |
|---|---:|
| Withheld rows in current Released catalog, exact | 0 |
| Withheld rows in current catalog after edge-whitespace normalization | 0 |
| Withheld rows in release decisions | 0 |
| Withheld rows in prior W6-0/W6-0b/W6-1/W6-2 union | 0 |
| Withheld rows in shared technical exclusions | 0 |
| Withheld rows in shared dedup exclusions | 0 |
| Withheld rows in HTML/newline/length structural residual | 0 |
| Withheld rows overlapping prior W6-3 batch scopes | 23 (17 batch-01, 4 batch-02, 2 batch-03) |
| Withheld rows overlapping prior final dispositions | 23 |
| Internal duplicates | 0 |

The prior-batch overlap is intentional: these rows were already classified during batches 01–03. It confirms that the residual is an exception backlog, not fresh unprocessed scope.

## Boundary

Branch state at preparation: `develop` at `b62b8dd`, one commit ahead of `origin/develop` (`fb3e056`). The untracked `v16.localhost/` directory was not read, modified, staged, or pushed.

No quorum, import, catalog write, release-decision write, evidence re-pin, live-site mutation, Stage 8 action, or production action was performed. Batch 03 remains closed; any future remediation or new batch requires a separately approved exact CSV and SHA. Stage 8 and production remain gated.
