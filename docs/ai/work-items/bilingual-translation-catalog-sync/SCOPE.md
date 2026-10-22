# SCOPE — bilingual-translation-catalog-sync

**Work item:** `bilingual-translation-catalog-sync`
**Session:** C (OpenCode autonomous agent)
**Date:** 2026-10-05
**Site:** `v16.localhost` (non-production test)
**Base commit at audit time:** `6c721b8` (`develop`) — note: the briefing named `234c024`,
but three concurrent partner sessions (A: transactional print formats; B: financial reports
allowlist expansion; D: production cutover runbook) committed `3bd3d1e`, `da7c3c6`, `6c721b8`
during this cycle, so the audited tree is `6c721b8`.
**Private workspace:** `sites/v16.localhost/private/translation-catalog-sync/`
**Authority:** `docs/ai/BRIEFING_TRANSLATION_CATALOG_SYNC.md`; owner decisions via the
in-session question tool; `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`.

---

## 1. Mission

Audit the system Translation catalog (`Translation` doctype, `language='ar'`, **22,761 rows**)
against the 47-term Egyptian Construction & Accounting glossary (schema v2,
`construction/data/glossary/egyptian_construction_glossary.json`, sha256
`aefbbf63…46b51b4`) and the ratified master-data terminology; identify contradictory or
confusing translations in Desk views, list views and standard action buttons; remediate under
a governed, sha-bound, zero-write-dry-run cycle.

## 2. Scope

| ID | Scope | Writes |
|----|-------|--------|
| **S1** | Read-only audit: stored rows, inert catalog rows, and the **effective rendered** output (`frappe.translate.get_all_translations('ar')`, **14,439 keys**) | none |
| **S2** | Harmonise the **single** glossary/payload divergence on the **glossary artefact** | 1 app-data file, 0 `Translation` writes |
| **S3** | Report-only disposition of inert/empty rows and competing-value producers | none |

**Authority model.** Pass C (rendered conformance) is authoritative user-facing truth. The
construction runtime loader `construction/translation_loader.py` replaces
`frappe.translate.get_user_translations` and reads only rows with
`ct_is_catalog_entry = 0` (`:25`), skipping empty values (`:47-48`). Rows with
`ct_is_catalog_entry = 1` therefore **never render** and are reported as inert hygiene, not as
user-facing defects.

## 3. Invariants and resolved conflicts

1. **Zero vendor edits** — no file under `apps/frappe` or `apps/erpnext` is touched.
2. **No `Translation` mutation** — this cycle performs **0** `Translation` writes.
3. **Briefing §Step 2 conflict — resolved.** The briefing prescribes applying via
   `frappe.get_doc("Translation", …).save()`. That pattern is **forbidden** by
   `scripts/lint_translation_writes.py` outside the canonical allowlist and would fail a
   required `gates.log` gate. The sanctioned routes are
   `construction.translation_service.upsert_runtime_translation` /
   `import_released_overrides`. This cycle needs neither because it performs no `Translation`
   writes.
4. **Briefing §Step 1 conflict — resolved.** Flagging against the glossary requires reading
   `source_text`/`approved_ar` (schema v2). `construction/api/translation_tools.py::_load_glossary`
   reads the obsolete schema-v1 keys `en`/`ar` and returns **0 terms**, so
   `apply_glossary_corrections()` is a silent no-op (finding **C-04**). The audit reads the
   glossary directly.
5. **Ephemeral Redis protocol** — ports 11000/13000 were already listening at session start
   (not started by this cycle); they are terminated after test execution per invariant 6.
6. **Privacy R4** — private proposal holds Arabic values; every committed artefact carries
   sha16 digests (first 16 hex of sha256 of the UTF-8 value) only.

## 4. Audit inventory (authoritative)

| Metric | Value |
|--------|-------|
| `Translation` rows, `language='ar'` | 22,761 |
| `ct_is_catalog_entry` 0 / 1 | 7,028 / 15,733 |
| `ct_origin`: Site Override / Packaged Release / none | 2,691 / 4,337 / 15,733 |
| empty `translated_text` rows | 3,653 |
| rendered dictionary keys | 14,439 |
| **glossary terms rendered: match / divergent / absent-empty** | **46 / 1 / 0** |
| forbidden-term violations at term keys | 0 |
| context-variant contradictions (runtime rows) | 0 |
| master labels present | 12 / 12 (2 / 12 value-verified; see C-05) |
| standard action buttons present | 42 / 45 (3 English fallback) |
| inert catalog divergence (report-only) | 3 divergent + 21 empty rows across 20 sources |
| site Translation writes | **0** |
| glossary term patches | **1** |

## 5. Findings register

- **C-01 (in scope, remediated).** Exactly one rendered divergence: source `Add Child`,
  rendered sha16 `f548ae03f4cdbef0` vs glossary `46dadab0f9e2eacf`. Root cause: the released
  payload `approved_ar_overrides.csv` carries an **owner-directed 2026-09-03** value (commit
  `4fede75`, payload `release_version 1.1`) that superseded the glossary v1.0 value one day
  after the glossary was last committed (`9011767`, 2026-09-02). Abbreviated trace: `338baba`
  ≥ glossary v1.0 (`ca5cf244…`) → `9011767` glossary v2.0 (`aefbbf63…`) → `4fede75` payload
  v1.1 value change → `9011767`/`9011767` glossary **not** updated.
  **Owner re-adjudicated** (in-session question tool): the glossary is the stale artefact and is
  harmonised **to the released payload**. No established term is re-translated; the site is not
  mutated; `_compute_drift()` is untouched and stays green.
- **C-02 (report-only).** 24 inert rows (`ct_is_catalog_entry = 1`): 3 divergent (`Add Child`,
  `Subcontract`, `Is Subcontracted`) + 21 empty, across 20 sources. Never rendered (loader
  filter). Deliberately not mutated — they are Stage-6-owned review-state rows and mutating them
  risks re-opening sha-pinned batch assertions.
- **C-03 (report).** Briefing-prescribed `frappe.get_doc("Translation").save()` is lint-forbidden
  (see §3.3).
- **C-04 (report).** `construction/api/translation_tools.py::_load_glossary` reads schema-v1
  keys `en`/`ar`; against the schema-v2 glossary it yields 0 terms, making
  `apply_glossary_corrections()` a silent no-op dead endpoint. App-code fix, out of the
  owner-approved change set.
- **C-05 (report).** Only 2 of 12 master labels carry a committed ratified baseline
  (`Cost Center`, `Chart of Accounts`, in `docs/translation/smoke-test-1.0.md`). The rest are
  reported **presence-only** and are explicitly not claimed value-verified. The audit extracts
  the two baselines at runtime (no Arabic literal in committed code).
- **C-06 (report-only).** `construction/patches/v8_4/fix_tree_view_arabic_translations.py`
  hardcodes the glossary-side value and, as a registered patch (`patches.txt:17`), would
  overwrite the runtime row on a fresh install / patch re-run. This latent drift is
  **pre-existing** and is self-healed in the same migrate cycle by
  `construction/translation_service.import_released_overrides_hook`
  (`hooks.py` after_install/after_migrate). Not mutated this cycle.
- **C-07 (report-only).** `construction/public/js/components/TreeView.jsx` passes 10 hardcoded
  Arabic labels to `__()` (Add Child variant digest `0bed7b4494c94ee6`). The file is not in
  `hooks.py app_include_js` and no module imports it, so it never renders. Dormant only.
- **C-08 (report).** Dated evidence `docs/translation/smoke-test-1.0.md`,
  `docs/translation/sign-off-1.0.md` (B-15) and `docs/evidence/smoke/README.md` assert the
  pre-`4fede75` value; they are owned by the closed Stage-2 work item and are not edited here.

## 6. Deliverables

```
docs/ai/work-items/bilingual-translation-catalog-sync/
├── SCOPE.md
└── evidence/
    ├── scripts/{audit,dry_run,apply,verify}_translation_*.py|_catalog.py
    ├── audit-translation-catalog.log     (read-only delta inventory)
    ├── review-ai-a2.md                   (independent non-author review)
    ├── owner-approval.md                 (sha-bound hard gate)
    ├── dry-run.log                       (DB writes: 0)
    ├── apply.log                         (glossary patch; 0 Translation writes)
    ├── post-sync-verification.log        (47/47; drift false; payload byte-identical)
    ├── regression-matrix.log             (21 modules)
    ├── reconciliation.log                (ADR reconciler 19/19)
    ├── gates.log                         (6 lints + reconciler)
    └── MANIFEST.json                     (manifest #34)
```

## 7. Causal order

`startup gates → audit (S1) → private proposal v1 → independent AI-A2 review (round 1, REVISE)
→ amendments (base-commit binding, master-label baseline discipline, app-source scan)
→ proposal v2 → independent AI-A2 round 2 → owner sha-bound approval → dry-run (0 writes)
→ apply (glossary patch, fail-closed on sha) → post-sync verification → regression matrix +
ADR reconciler → 6 lints → capture logs → SHA-256 digests → MANIFEST.json`.
