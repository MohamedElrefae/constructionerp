# Scope Descriptor — bilingual-company-phase1-population

**Work item:** `bilingual-company-phase1-population`
**Branch:** `develop`
**Base commit:** `5d96f12`
**Date:** 2026-10-05
**Status:** `CLOSED_PENDING_COMMIT` — export PASS, review REVISE→amended, owner approved
v2 (`b5fcc02a…9478a`), dry-run PASS (0 writes), apply PASS (1/1), post-verify PASS,
gates green (reconciler 19/19, matrix 21/21 / 264 tests). Full results in §8; evidence
under `evidence/`.
**Authority:** Owner's in-session choice after Tier 5G (`5d96f12`) closed: "Company Arabic
(Recommended)" — last untranslated core master; governed translation review, read-only
until the population proposal is approved
**Scope:** Inventory and classify every Company row on `v16.localhost` (active owner
company vs test-noise records), freeze the Phase-1 allowlist (`Elrefae` — the only company
in live owner use), draft the governed Arabic value for that row, and — only after owner
approval — run the standard dry-run → apply → verify cycle. The 20 test companies are
audited and disclosed, **not** populated.

---

## 1. The gap this closes

Company is a fully *enabled* bilingual surface with zero *data*:

- Registry `doctypes.Company` active: `company_name` / `company_name_ar` /
  `company_name_ar_norm`, identity `name`, tree false, search on.
- `enforce_bilingual_arabic_policy` + narrative sanitizer bound to Company `validate`
  (`hooks.py:366`).
- Every verification gate since 5C has frozen `Company company_ar=empty` — this tier
  closes that line for the owner's company.
- `User Scope Context` (5 rows, live user `site.engineer.ob2@example.com`) selects
  `Elrefae` — the company name rendered at the top of the desk for every scoped screen.

## 2. Findings (from `inventory-export.log`, PASS)

| ID | Finding |
|---|---|
| **F-5H-1** | **21 companies**: 1 active owner (`Elrefae` — abbr `E`, EGP, Egypt, flat/non-group, live in GL 4 / JE 2 / SI 1 / Project 5 / Scope-Context 5 / Account 86 / Cost Center 3) + **20 test noise** (13 `_Test*` + 7 demo/test records `Best Test`, `Child Company India/US`, `Parent Group Company India`, `Test Quality Company`, `Trial Balance Company`, `Wind Power LLC`; 5 `is_group`, 5 parented — all test). |
| **F-5H-2** | **`Company.save()` enqueues jobs** — without queue redis (port 11000) a save raises `ConnectionError` mid-flight (probe P1). Apply must run with the queue up; teardown after (same operational discipline as the matrix). |
| **F-5H-3** | No Company fixture JSON → no sync-wipe risk (5F-F5 class does not apply); hook binding present; registry active. |
| **F-5H-4** | Arabic pre-state **0** site-wide; identity `name == company_name == 'Elrefae'`; **name edits never permitted** — ERPNext rename cascades abbr across Accounts/Cost Centers/Departments (frozen invariant: identity untouched). |
| **F-5H-5** | Glossary has **no company-name terms** governing the brand (only a generic child-company entry); the brand root is **corroborated** by two committed artefacts — P95 harness `AR_FIXTURES[0]` (synthetic pool applied to throwaway `CT-COMP-Test-NN` companies) and pilot test `_Test Company%` value — **in-repo corroboration, not an established display name for Elrefae**. Primary + alternates in the proposal are an **owner display-form decision** (sha16-matched in the export; values never in committed evidence). |
| **F-5H-6** | `Company.on_update` unconditionally re-sets `Currency EGP enabled=1` (already `1`) → bumps `tabCurrency.modified`; the 1-row invariant covers **company fields**; post-verify expects/discloses the Currency modified bump (review NOTE). |

### 2.1 Probe disclosures (all rolled back, zero residue)

| Probe | Path | Result |
|---|---|---|
| **P1** | `Elrefae` plain `doc.save()` with queue redis **down** | `ConnectionError` (queue-connection getter in `frappe/utils/background_jobs.py:608` refused) — no write; established F-5H-2 |
| **P2** | `Elrefae` plain `doc.save()` with queue redis **up** | **SAVE_OK** — only `company_name_ar` + `_norm` changed; name/abbr/currency/country untouched; norm server-derived; **rolled back** |
| **P3** (supplementary, post-review NOTE 2) | same-value re-save with queue up + `rq:queue:*`/`rq:job:*` key diffing | **SAVE_OK**, **0 new RQ keys/entries** — no RQ job is created by this path when the queue is reachable; DB rolled back (committed value intact). Combined with the matrix traceback (`update_global_search → sync_value_in_queue → frappe.cache.lpush('global_search_queue')` on cache redis 13000), mechanism record: Company saves touch the queue-connection getter (11000) and the global-search queue (13000) — both services required during apply (F-5H-2), recorded empirically per review NOTE |

Post-probe state verified: `company_name_ar` populated = **0**, 21 rows (pre-apply).

## 3. Mechanism (no surprises)

- Apply = single `doc.save()` through the registered validate hooks (bidi gate +
  server-derived `_norm`), run with queue redis 11000 up (F-5H-2), transaction
  fail-closed, queue torn down after. The enqueue source of P1's `ConnectionError` was
  not statically isolated — `apply.log` captures the traceback/job name so F-5H-2's
  mechanism is recorded, not inferred (review NOTE).
- No fixture JSON, no `Translation` doctype, no registry/`hooks.py` edit, no rename.

## 4. Invariants

1. **D5 triad + registry byte-identical to `5d96f12`** (call-only).
2. No file under `apps/frappe` / `apps/erpnext` modified; no patch, hook, test, JS, or
   `?v=` change; zero manifest re-pins (Company pinned by no prior manifest — verified
   before commit).
3. Exactly **1** row written (`Elrefae` company fields); `name`, `company_name`, `abbr`,
   currency, country, parent/is_group, defaults all unchanged (verify diffs every frozen
   field). Disclosed side-write: `tabCurrency.modified` bump on `EGP` from
   `Company.on_update` (F-5H-6) — expected by verify, not an anomaly.
4. The 20 test companies and every prior bilingual surface stay untouched (5D + 5F + 5G
  frozen lists carried forward).
5. **Fixture JSON:** untouched (F-5H-3).
6. **Privacy R4:** proposal/review/dry-run/apply values under
   `sites/v16.localhost/private/company-phase1-population/`; committed evidence carries
   counts, classifications, verdicts, sha16 value hashes, digests only.
7. **Production:** `production_mutation_authorized: false` (test site only).

## 5. R1–R7 (frozen rules)

- **R1 — frozen Phase-1 allowlist.** Export derives (`name == 'Elrefae'`), asserts equal
  to frozen literal `['Elrefae']`; totals frozen at 21 / noise 20. Run result:
  `INVENTORY RESULT: PASS` (`PHASE1_FROZEN_MATCH yes`, `PRE_STATE_ARABIC 0`).
- **R2 — phases.** Phase 1 this cycle = 1 row. Phase 2+ = 20 test companies — audited,
  default expectation: never (test noise).
- **R3 — read-only until approval; standard apply.** dry-run (0 writes, sha gate) →
  apply (1 `doc.save()`, queue up) → post-verify. Fail-closed rollback; new quirks become
  disclosed amendments before commit.
- **R4 — privacy.** Private values under `…/private/company-phase1-population/`;
  committed evidence = counts/identities/verdicts/digests.
- **R5 — completeness.** 1/1 populated, norm-consistent, identity/defaults unchanged;
  site Arabic total == 1 exactly; 20 excluded rows empty; scope selector renders Arabic.
- **R6 — repo hygiene.** New files under this work-item directory only → zero shared-file
  edits → zero re-pins; glossary untouched.
- **R7 — no display/config changes.** No doctype_js, no registry change, no rename/abbr
  action, no Company default changes.

## 6. Out of scope

- The 20 test-company rows (Phase 2+, default never).
- Company rename / abbr operations (cascade risk — never authorized).
- Glossary additions for company names (separate governance action if wanted).
- Production: not authorized.

## 7. Evidence causal order

export/inventory (read-only) → classification vs frozen 1-row allowlist → probe
disclosures (P1–P2, §2.1) → proposal v1 (1 value, private) → fresh-session review →
owner approval (sha-bound) → dry-run (0 writes) → apply (queue up; 1 `doc.save()`) →
post-verify → matrix + reconciler + lints → capture logs (`2>&1`) → `git add -f` the
`.log` → SHA-256 digests → `MANIFEST.json` → commit.

## 8. Results (recorded on completion)

All executed on `v16.localhost` (test site only; production untouched), base `5d96f12`.

| Step | Result |
|---|---|
| Export / inventory | `inventory-export.log` → **PASS** — 21 companies classified (1 active owner `Elrefae` / 20 test noise; 5 `is_group`, 5 parented, all test), `PHASE1_FROZEN_MATCH yes (1 = Elrefae)`, `PRE_STATE_ARABIC 0`, usage attribution + `BRAND_ROOT_CORROBORATION` sha16 lines + F-5H-1..6 findings printed; committed output value-free (0 Arabic-value lines). |
| Probes P1–P3 | §2.1 — P1 queue-down `ConnectionError` (source located: `background_jobs.py:608`), P2 queue-up SAVE_OK, P3 supplementary mechanism capture (0 new RQ keys; global-search path identified via matrix traceback); all DB-rolled-back, 0 residue. |
| Proposal v1 → review → v2 | v1 sha `e707a850…551f23`; fresh non-author round 1: **REVISE (3 required changes)** — precedent framing corrected (synthetic pool + test value = corroboration, not established display name), owner display-form decision marker added, R4 scrubbed to sha16 matching in the export script; plus 6 NOTEs (all recorded: F-5H-6 currency bump, P3 mechanism capture, pilot-test fallback, glossary near-match, `dump.rdb`, `english_label` non-writable). v2 sha256 **`b5fcc02a6854ebb27b71082b71c1b3f9d4ac43f737b013809697c2a23e79478a`** (`arabic` + alternates byte-identical v1→v2); `review-ai-a2.md` committed (redacted); v1 archived privately. |
| Owner approval | `owner-approval.md` — **"Approve primary (Recommended)"**, 1 row (`Elrefae`), 20 test companies stay empty; sha-bound hard gates; queue-redis operational condition. |
| Dry-run | `dry-run.log` → **PASS** — 1/1 validated (PLAIN save planned), frozen-field snapshot captured (abbr E / EGP / Egypt / COA), `EXCLUSIONS excluded_rows=20`, approved sha matched, **`WRITES_PERFORMED: 0`**. |
| Apply | `apply.log` → **PASS first attempt** — `QUEUE_GATE reachable` (F-5H-2), `PREVALIDATE_OK rows=1`, `SUMMARY written=1 skipped=0 failed=0`; only `company_name_ar` + `company_name_ar_norm` changed; identity/frozen fields unchanged; norm server-derived (`63f48828f9f20a78`); `QUEUE_ENQUEUED {}` + disclosed QUEUE_NOTE (see P3). |
| Post-verify | `post-import-verification.log` → **PASS** — `populated=1 norm_consistent=1 identity_unchanged=1 frozen_unchanged=1`; site Arabic total exactly 1 (0 missing / 0 extra); exclusions 20 intact, total 21; usage surface (5 scope-selector rows resolve Arabic company name; `Currency EGP enabled=1`, F-5H-6 modified bump expected); frozen prior surfaces (5D list + 5G Department 14/276 + 5F UOM 15/253 + `uom.json` sha unchanged); `get_root_of` patch restored. |
| Gates | `py_compile` 4 scripts OK; `lint_scope_metadata` PASS; `ai_context_check` PASS; `lint_translation_writes` PASS; `schema_drift` PASS; `bash -n` OK; ADR reconciler **19/19** (`reconciliation.log`); `gates.log` captured; canonical matrix **21/21 modules OK, 264 tests, 0 failures** (`regression-matrix.log`; redis 11000/13000 started → run → torn down; **gate note G1**: attempt 1 failed with cache redis 13000 down — `test_bilingual_account_pilot` setUpClass hits `update_global_search → sync_value_in_queue → frappe.cache.lpush` → `ConnectionRefused(13000)`; started 11000+13000 → full PASS; both torn down after, 6379 left up). `check_localization_gates.py` is a Stage-2 gate outside this tier's chain (not run). |
| Open items flagged to owner | (a) 20 excluded test companies — Phase 2+, default expectation never; (b) glossary has no org/company-name terms — separate governance action if wanted; (c) matrix/bisect runs require cache redis 13000 (and queue 11000 for Company saves) — operational reminder for future gates; (d) 20 test companies + `Test Quality Company`'s 2 scope-context rows remain site noise. |
