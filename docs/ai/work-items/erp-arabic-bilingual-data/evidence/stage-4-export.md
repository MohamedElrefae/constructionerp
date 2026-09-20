# Stage 4 — Account-language export + proposal machinery (builder record)

Date: 2026-09-09 · HEAD: `e7be48855bde540464ea302e53c9bfca62b7c462` (uncommitted)
Scope: authorized non-production copy only. No live Account-name migration,
no translation import, no commit/deploy.

## What was engineered

- `construction/services/account_language_proposal.py` — governed export +
  proposal scaffolding:
  - `export_account_catalog(company="Elrefae", write=True)` exports the
    authorized non-production Account catalog with the required proposal
    fields (identity, English value, account_number, hierarchy, proposed
    Arabic, glossary match, source reference, confidence, flags, provenance).
  - `glossary_lookup()` reads the governed Egyptian overrides CSV to flag a
    glossary match for the English label.
  - `validate_proposal()` asserts the proposal record contract.
  - `dry_run_apply_proposals()` produces a zero-mutation preview plan (no
    DB writes).
- `construction/tests/test_stage4_account_language.py` — 6 tests covering
  the manifest contract (no invented reference, pending proposal, no
  current Arabic), glossary lookup, proposal validation, dry-run
  zero-mutation plan, and the private-dir write path.

## Policy (canonical Stage 4 items 1–4)

- **No invented MOF/EAS/ETA reference**: every row is flagged
  `no_verified_reference`; "No verified reference" is acceptable evidence
  until an independent AI-A2 review supplies a verified source reference.
- **Proposal fields are NOT invented here**: `proposed_arabic` /
  `confidence` are left empty and the rows are flagged `pending_proposal`;
  filling them belongs to an independent AI proposal + AI-A2 Egyptian
  accounting/QS review session (the proposal agent cannot approve its own
  output).
- **Sensitive export stays private**: raw rows are written only to
  `<site>/private/stage4/` (outside the app git repo, never committed);
  the committed evidence contains only the non-sensitive manifest
  (schema, row counts, export file SHA-256, provenance).

## Executed export (non-production copy, zero mutation)

| Field | Value |
|---|---|
| schema | `construction-stage4-account-language-proposal/v1` |
| company | Elrefae |
| rows | 81 (26 group nodes + 55 leaves) |
| with current Arabic | 0 |
| glossary-match count | 0 (account names do not collide with the UI glossary) |
| export file | `account_catalog_20260909_225212.json` |
| export file SHA-256 | `d969924356cf7c6fe5e3ee7f4e4d817346ca12b0bc4afdd76812657bc5b3414b` |
| private location | `<site>/private/stage4/account_catalog_20260909_225212.json` |
| source site | v16.localhost (non-production test) |
| recorded_utc | 2026-09-09T22:52:12Z |
| recorded_by | Administrator |

The export performed no DB writes and touched no Account values.

## Validation

- `bench --site v16.localhost run-tests --module construction.tests.test_stage4_account_language` → 6/6 OK.
- Aggregate now 221 (13+6+5+3+8+89+38+53+6) all green; standalone 89/89;
  catalog 805 / `664 + 21` / 0 missing; inventory 18,446 rows root
  `2e284695…` live-matched; evidence-enabled gate errors=0; lints +
  `git diff --check` clean.

## Next Stage 4 gates (not performed)

- Independent AI proposal session producing `proposed_arabic` +
  `confidence` for each row (this builder does not invent values).
- Independent AI-A2 Egyptian accounting/QS review signing every row or
  recording an explicit exception (with verified references, confidence,
  rationale, model/session provenance, timestamp).
- Zero-mutation dry-run import with optimistic current-value checks, then
  the actual `account_name_ar`-only import behind owner authorization and
  the §11 gates.
- Report extension-point spike (GL / Trial Balance / Balance Sheet / P&L —
  Construction-side only).
