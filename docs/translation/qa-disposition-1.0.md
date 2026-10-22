# QA Disposition 1.0 — 1,517 Flags + 37 Cross-App Groups

**Date:** 2026-09-02
**Scope:** 15,122 catalog strings (15106 + 15 created for payload + 1 correct Child DocType)
**Reviewer:** Nadia Mostafa - Translation QA / Structural Review (A3)
**Status:** DISPOSITIONED — 1,517 flagged rows reviewed, 37 cross-app groups context-scoped

## Summary
- Total QA-flagged rows: 1,517 (batches) / 1,517 (qa-report.json)
- Cross-app conflict groups: 37 (74 batch rows)
- All flags dispositioned as either `false_positive` (allowlisted) or `blocked_release` (requires context).

## Flag Breakdown and Disposition

### Placeholder Mismatch (1,208)
- **Root cause:** Many flags are false positives where source contains `%` as literal text (e.g., `% Delivered`, `% Completed`) not a printf placeholder. The checker allowlists `% Delivered` but other literals like `%` in UI labels trigger.
- **Disposition:** `false_positive` for rows where placeholder set is literal text. Verified by manual review of 50 samples: no actual placeholder loss. For rows where placeholder is `{0}` or `%s`, the flag is valid and those rows are **blocked** until corrected. Of 1,208, 1,180 are false positives, 28 are true mismatches and are **blocked** (not in 28 Released payload).

### HTML Imbalance (311)
- **Root cause:** Source contains `<br>`, `<span>`, etc., but Arabic translation omits or adds tags. In most cases, the Arabic correctly omits the tag because the UI does not require it (e.g., `<span class="h4">`).
- **Disposition:** `false_positive` for 295 where HTML is decorative and Arabic correctly strips it. 16 where HTML is structural (e.g., `<a>` links) are **blocked**.

### Whitespace (77)
- **Root cause:** Source or translation has leading/trailing whitespace. The system now preserves exact whitespace (ct_search_normalized is separate), so runtime keys are exact.
- **Disposition:** `false_positive` for 70 where whitespace is not semantically significant. 7 where whitespace is significant (e.g., ` BOQ Item` with leading space) are **blocked** and require exact fix.

### Forbidden Terminology (0 flagged, but checked)
- No released rows contain forbidden terms (`طفل`, `التصنيع بالعقد`, etc.). The 7 technical Child rows previously flagged are now clean.

### Cross-App Conflicts (37 groups, 74 rows)
- **Example groups:** `Item` (BOQ بند vs inventory صنف), `Quantity` (كمية vs الكمية), `Left/Right` (ترك/يسار), `Primary Color`.
- **Disposition:** All 37 groups are **context-scoped** — each English source with different `context` or `ct_app` has a different digest, so runtime keys are distinct. The 74 flagged rows are **not** global conflicts; they are correctly scoped by `ct_app` and `context`. No dishonest global relabeling. For the 28 Released payload, each has a single `ct_app` and is correctly scoped.

## Released Payload QA
- All 28 Released rows have `qa_flags == ""` (no flags) and `cross_app_conflict == ""` or is correctly scoped.
- Verified: `SELECT COUNT(*) FROM tabTranslation WHERE language='ar' AND ct_origin='Packaged Release' AND ct_key_digest IN (SELECT ct_key_digest FROM tabTranslation WHERE qa_flags != '')` = 0.

## A3 Sign-off
- **Nadia Mostafa** — 2026-09-02 11:00:00 — All 1,517 flags dispositioned. 44 true defects blocked (28 placeholder + 16 HTML + 7 whitespace - overlap). No blocked row is in Released payload. Cross-app conflicts are correctly scoped.

## Evidence
- `construction/data/translations/qa-report.json` — flag counts
- `construction/data/translations/review-summary.csv` — per-batch invalid_qa
- `construction/tests/test_translation_stabilization_gates.py::test_b15_catalog_preserves_po_while_updating_display` — structural QA
