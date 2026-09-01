# Translation Subsystem Stabilization Plan (Consultant Handoff v4)

> **Purpose:** Self-contained execution plan for the next agent. All decision gates and follow-up questions have been answered by the owner. Do NOT re-ask them; execute.
>
> **This file supersedes prior drafts.** It consolidates the attached "Final Translation Subsystem Stabilization and Review Plan" (v2) with a consultant review pass (§0 below). The v2 plan is the basis; the §0 items are mandatory revisions baked into the phases.
>
> **Status:** Decision-complete; ready for implementation. Verified against code on 2026-09-01 (commit `338baba` is HEAD of `construction/develop`).

---

## 0. Consultant Review Pass — 11 Mandatory Revisions to v2

The attached v2 plan is implementable as-is, except these items. The executing agent must treat them as part of the plan, not optional commentary:

1. **Glossary exists and must be upgraded, not recreated.** Verified: `construction/data/glossary/egyptian_construction_glossary.json` (8,669 bytes, 47 provisional terms). P0 preserves and checksums it; P4 migrates it to schema v2.
2. **`Add Child` .po timeline.** Rather than waiting for P2 to clean the tree, the equivalent released override MUST be created in P1 (pre-migration). Gate: all three repo roots clean before P2 begins.
3. **`ct_origin` is a DB CHECK constraint (chosen implementation).**

   ```text
   catalog row → ct_origin may be empty
   runtime row → ct_origin IN ('Packaged Release', 'Site Override') only
   ```

   Migration backfills existing runtime rows as `Site Override` unless a row matches a released packaged record, which is set as `Packaged Release`.
4. **Health endpoint response is exactly this field set (booleans + timestamps, no translation content):**

   ```text
   loader_installed
   using_safe_fallback
   has_duplicates
   has_null_digests
   constraint_present
   has_drift
   has_orphan_site_overrides
   last_catalog_sync_at
   last_release_import_at
   last_drift_checked_at
   ```
5. **AST lint allowlist must be a checked-in list** in `scripts/lint_translation_writes.py` (e.g. `ALLOWLIST = ["construction/patches/2019_…py"]`); CI fails on any new write outside the list.
6. **`Deprecated` behavior is defined:**

   ```text
   - Removed upstream catalog row → retain as Deprecated for provenance.
   - Packaged runtime override → remove from runtime.
   - Site override → preserve but flag as orphaned for review.
   - Deprecated rows never count as released.
   ```

   State diagram extends with `Released → Deprecated` for upstream `.po` removal, else orphan overrides accumulate.

7. **Cross-app conflict resolution option 1 is not honest.** If a conflict cannot be resolved with a genuinely global term, it MUST be left unresolved and block release; never relabel `Item` → `بند` globally.

8. **Dry-run is strictly zero-mutation.** `import_released_overrides(dry_run=True)` and every service dry-run must perform no commits, cache changes, timestamp changes, or DB materialization of preview rows. (Allegation about current code defects removed after inspection; the requirement stands.)

9. **`review-summary.csv` counts "proposed" — define it.** Proposed == non-empty `ct_proposed_translation` on catalog rows. Explicitly decided, else reviewers cannot reconcile.

10. **Loss-of-uniqueness regression test wording stays explicit**; do not let "unique-constraint existence" absorb it.

11. **Production version recorded.** Primary target: Frappe `16.18.1` with ERPNext `16.18.3`. Frappe v15 is best-effort compatibility only.

---

## 1. Summary and Locked Decisions

Commit `338baba` remains as the immediate hotfix. The next implementation remediates duplicate data, consolidates all translation writes, preserves exact keys, produces review files for later linguistic enhancement, and establishes a reproducible release process.

Locked decisions:

- Approved corrections are versioned in the Construction repository, **not** committed to Frappe or ERPNext `.po` files.
- Vendor `.po` files remain upstream baselines; vendor repositories must remain untouched. The sole release payload is `construction/data/translations/approved_ar_overrides.csv` — any earlier mention of per-app `.po.fix` drafts is removed from this plan.
- Released corrections are applied idempotently to canonical runtime Translation rows.
- Loader degrades safely: ERP starts, DB overrides disabled, `.mo` active, health failure visible.
- Every released override requires A1 linguistic review, A2 domain review or `Not Applicable`, and A3 structural QA.
- Full review files cover all 15,106 strings; full linguistic completion is not a blocker for technical stabilization.
- Only `Released` rows affect runtime.
- Historical patches immutable; new code must not edit executed patches.

Baseline to preserve:

- 15,106 catalog rows.
- 3,005 runtime rows.
- 299 duplicated runtime keys / 300 surplus rows.
- 7,338 catalog strings with no Arabic translation.
- 3 regression tests pass.
- Existing provisional glossary (47 terms, verified on disk) — preserved in P0, upgraded in P4 (§0.1).
- Frappe `ar.po` `Add Child` uncommitted change — see §0.2.

## 2. Implementation Changes

### P0 — Baseline and rollback package

Before editing code, running `bench migrate`, importing translations, or rebuilding assets:

- Full DB backup + targeted export of every Arabic Translation row incl. custom fields/owner/created/modified/modified-by.
- Export every duplicate group with winner `modified DESC, creation DESC, name DESC`.
- Checksums for three `ar.po` + generated `ar.mo`.
- Capture Frappe `ar.po` diff as patch.
- **§0.1 task:** preserve and checksum the verified existing glossary (47 terms); it is upgraded to schema v2 in P4.
- Snapshot effective translations for critical accounting/hierarchy/BOQ/retention/subcontracting/WIP/document-action keys.
- Backups under `sites/v16.localhost/private/backups/translation-stabilization-<timestamp>/`; commit only a non-sensitive manifest (counts/checksums/hashes/site id/backup location).
- Gate: parsed targeted export + verified DB backup; otherwise stop.

**§0.2 task (P1.0):** after equivalent `Add Child` override exists in Construction release dataset, restore `apps/frappe/frappe/locale/ar.po` to HEAD; confirm all three roots clean before P2.

### P1 — Translation identity and duplicate migration

Custom fields (add `ct_origin` guard per §0.3):

| Field | Type | Purpose |
|---|---|---|
| `ct_key_digest` | Data 64, read-only | SHA-256 identity |
| `ct_search_normalized` | Small Text, read-only | Search-only normalized |
| `ct_proposed_translation` | Code | Unreleased reviewer proposal |
| `ct_origin` | Guarded enum: Packaged Release / Site Override | Origin precedence |
| `ct_release_version` | Data | Packaged release version |
| `ct_released_at` | Datetime | Runtime release timestamp |
| `ct_released_by` | Data | Human or review-agent id |

Digest = UTF-8 SHA-256 over compact JSON array:

- Runtime: `[language, exact_source_text, context_or_empty, "runtime"]`
- Catalog: `[language, exact_source_text, context_or_empty, ct_app_or_empty, "catalog"]`

Rules:

- Preserve `source_text`/`translated_text` EXACTLY (no trim/collapse/transliteration). Reject embedded NUL.
- `ct_search_normalized` = `strip_html_tags(source).strip()`, never a runtime key.
- `ct_app` = provenance only, not runtime identity.

Migration order (with §0.4 derived-boolean health and §0.5 checked-in lint allowlist):

1. Add fields, no uniqueness.
2. Backfill digests & normalized helper.
3. Group runtime/catalog duplicates by digest.
4. Archive losers to rollback package.
5. Keep deterministic winner, preserve timestamps.
6. Delete surplus rows.
7. `UNIQUE INDEX ct_translation_key_digest`.
8. Non-null 64-char digest constraint.
9. Verify zero duplicates/null digests.
10. Second run = zero changes.

Normal saves compute digest; bulk sync supplies it; insert race = catch IntegrityError → reload canonical row → update retry.

### P2 — Canonical service and loader

`construction/translation_service.py` is the only active mutation layer.

Interface:

```text
get_runtime_rows(language, source_text, context="")
get_effective_translation(language, source_text, context="")
upsert_runtime_translation(..., origin, release_version=None, reason=None)
delete_or_revert_runtime_translation(...)
sync_catalog(apps=None, dry_run=True)
import_released_overrides(path=None, dry_run=True)
submit_review_decision(key, persona, decision, notes, references)
release_proposal(key, release_version)
invalidate_translation_caches(language)
get_translation_health()      # derived booleans + timestamps (§0.4)
assert_translation_health()
```

Permissions: review proposals → `Translator` or `System Manager`; release/revert/import/sync/cleanup → `System Manager`. Server-side validation. Dry-run = no commits/cache/timestamps and no materialized preview rows (§0.8).

Packaged-vs-site precedence:

- Packaged release creates a runtime row when none exists.
- Updates an existing Packaged row only when incoming version is newer.
- Never overwrites a Site Override; reports drift.
- Reverting a site override restores current packaged value when available; else deletes runtime row → `.mo`.
- Editing a proposal resets all prior approvals.

Review states (§0.6 adds Deprecated):

```text
Pending → Linguistic Reviewed → Domain Reviewed → QA Passed → Released
Any stage → Rejected
Released → Reverted | Deprecated
```

Catalog edit does not auto-release: `ct_po_translation` stays upstream value; edit stored in `ct_proposed_translation`; status → `Pending`; runtime unchanged until quorum. Revert clears proposal and removes/restores runtime override by origin precedence.

Loader behavior:

- Move loader install + health out of large package initializer.
- Catch missing-column only on fresh pre-migration install.
- Log all unexpected failures with traceback.
- If failure post-catalog-fields → return no DB overrides so `.mo` runs without catalog mirrors.
- Health endpoint: derived booleans + timestamps only (§0.4), System Manager only.
- `assert_translation_health()` raises in deployment verification, not ERP startup.

Cache invalidation centrally clears `USER_TRANSLATION_KEY`, `MERGED_TRANSLATION_KEY`, boot, site, client boot. Browser verification = new session.

### P3 — Retire unsafe writers

- Remove `construction.insert_translations.execute` from recurring `after_migrate`.
- Replace after-install/migrate seeding with idempotent `import_released_overrides`.
- Remove hard-coded `DRAFT_AR_EXACT` / `REVIEWED_AR_GLOSSARY`.
- Remove draft machine-translation + nondeterministic DB glossary loading.
- Convert retained legacy commands to read-only exporters or explicit deprecation errors.
- Historical executed patches: immutable, excluded from write lint by an explicit checked-in allowlist (§0.5).
- AST-based lint detects `get_doc`, `new_doc`, `set_value`, `delete`, direct SQL, bulk insert outside canonical service/new migration/tests/allowlist.
- Boolean API parsing: `cint` or parsed JSON; never `bool("0")`.

### P4 — Authoritative terminology and release dataset

Glossary schema v2 (upgrade of the verified existing glossary per §0.1):

```text
source_text, context, origin_app, domain, approved_ar, forbidden_ar,
usage_notes, references, a1_status, a2_status, version
```

Re-review contextual risks before release (§0.7):

- Manufacturing vs construction subcontracting.
- Retention money vs retained QC samples.
- Construction vs manufacturing WIP.
- Generic Submit vs accounting posting.
- Generic vs initial Handover.
- BOQ Item vs inventory Item.
- Global Payment Entry vs Receive/Pay/Internal Transfer.

Cross-app conflict resolution (§0.7): global term, gettext context, domain-specific label, or BLOCK release if none is honest.

Release payload `construction/data/translations/approved_ar_overrides.csv`:

```text
language, source_text, context, ct_app, translated_text, domain, release_status,
release_version, a1_reviewer, a1_approved_at, a2_reviewer, a2_approved_at,
a3_reviewer, a3_approved_at, references, notes
```

Only `release_status=Released` with complete quorum may import.

## 3. Translation Review Files

Generate UTF-8 CSVs under `construction/data/translations/review/`:

- batch-01 construction accounting / financial statements
- batch-02 contracts/subcontractors/certificates/retention/advances
- batch-03 BOQ/estimation/project costing/cost centers
- batch-04 purchasing/inventory/site materials
- batch-05 core doc actions/errors
- batch-06 payroll/labor
- batch-07 manufacturing actually used
- batch-08 technical/admin

Row columns (§0.9 defines `proposed`):

```text
app, msgid, context, locations, comments, ct_app, po_translation,
runtime_translation, effective_translation, proposed_translation, domain,
priority, a1_status, a1_reviewer, a1_notes, a2_status, a2_reviewer, a2_notes,
a3_status, a3_reviewer, a3_notes, qa_flags, cross_app_conflict,
release_status, references
```

Rules:

- A1 language; A2 domain-or-NA; A3 structural.
- Modified proposal invalidates prior approvals.
- Review files never write runtime.
- Promotion command copies quorum-approved rows into `approved_ar_overrides.csv`.
- Empty translations marked `priority=missing` (7,338 verified count), not silently filled.

Also generate:

- `construction/data/translations/qa-report.json`
- `construction/data/translations/review-summary.csv`
- `docs/translation/sign-off-<release-version>.md`

Summary reports total/translated/missing/proposed/rejected/released/invalid/cross-app-conflict per app+batch (§0.9: `proposed` = non-null `ct_proposed_translation`).

## 4. Test and Deployment Plan

### Automated tests

Unit + migration tests cover: loader install/safe-degrade/health/logged-unexpected-error; fresh-site missing-field; exact source/translation/context/HTML/whitespace; digest generation; duplicate cleanup+rollback; unique-constraint existence; null-digest rejection (§0.10 explicit); parallel creation resolves to one row; catalog proposal/approve/reject/release/revert/delete/lang-change/ctx-change; packaged update + site-override precedence + drift; catalog sync on .po change; cache invalidation on insert/update/release/revert/delete; status-gated import; cross-app conflict blocking; second-run idempotency; AST lint coverage on all active mutation paths.

QA tests: `{0}`/named/printf/Jinja/JS placeholders; HTML balance; whitespace/escaped newlines; `<br>` joined EN/AR duplication; forbidden terminology; untranslated English leftovers; bidi-unsafe identifiers; allowlist for literal `% Delivered`-style strings.

Integration (primary target per §0.11 = Frappe `16.18.1` + ERPNext `16.18.3`; Frappe v15 = best-effort): fresh install, upgrade with 299 duplicate keys, Desk boot/login/workers/REST/print/PDF, representative screens, new Arabic session, loader performance with 15,106 catalog rows.

### Deployment sequence

1. Confirm P0 backup + targeted archive.
2. Deploy code removing recurring legacy writer.
3. Migration dry-run/audit.
4. Review winners/archived losers.
5. Apply migration + constraints.
6. Import initial quorum-approved critical rows.
7. Sync catalogs; no vendor `.po` modification.
8. Build Construction assets via pipeline.
9. Clear translation/boot/website/site caches.
10. Restart web + worker processes.
11. `assert_translation_health()`.
12. New restricted Arabic session test.
13. Smoke tests (accounting/BOQ/subcontracting/inventory/tree-view).
14. Repeat migration + release import; zero changes.
15. Monitor health/errors/duplicates/drift.

Rollback: stop imports → drop digest constraints → restore archived Translation rows or verified DB backup → restore prior approved version → rebuild assets → clear caches → restart → rerun snapshot. Do NOT restore the uncommitted vendor `.po` (§0.2).

## 5. Acceptance Criteria and Assumptions

Technical stabilization accepted when:

- All three repos clean (§0.2).
- Vendor `.po` has no local localization patch.
- Zero runtime + catalog duplicate digests; zero null/malformed digests.
- Concurrency cannot recreate duplicates (§0.10 explicit test).
- Every active mutation path uses canonical service; historical patches are explicit lint exceptions (§0.5).
- Exact stored whitespace/keys preserved (§0.3/0.6 state machine respected).
- Catalog edits do not affect runtime before release (§0.8).
- Rejection/revert/packaged update/site override/deletion behave as specified.
- Loader failure degrades safely and fails deployment health (`assert_translation_health`).
- Review exports show upstream/runtime/effective.
- Released rows have zero unresolved placeholder/markup/whitespace/forbidden/cross-app-conflict.
- Every released row has A1 + A2-or-approved-NA + A3.
- Second migration/import fully idempotent.
- User receives eight review CSVs, QA report, summary, schema-v2 glossary upgraded from the verified 47-term source (§0.1), sign-off template.

Assumptions:

- MariaDB 10.6+.
- Runtime identity = language + exact source + context; app is provenance only.
- Full linguistic completion is ongoing, not a blocker.
- Generated `.mo` are deployment artifacts.
- Tax rates/calculations remain outside translation data.
- Production baseline recorded: Frappe `16.18.1` + ERPNext `16.18.3`; v15 best-effort (§0.11).

---

*Prepared by the software consultant role; owner answered all gates; §0 revisions are mandatory for the executing agent.*
