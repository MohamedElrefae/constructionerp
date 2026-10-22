# Fresh-Session Review — bilingual-company-phase1-population proposal v1

**Reviewer:** independent non-author session (`general` subagent, read-only; SELECT-only DB
inspection with rollback; did not author SCOPE, export, or proposal)
**Date:** 2026-10-05
**Reviewed bytes:** `sites/v16.localhost/private/company-phase1-population/proposal-v1.json`
(archived), sha256 `e707a850851c472459c3b7cb6dbf60eaf5892ee4a80d9ac8ff0eab606b551f23`
(recomputed independently via `sha256sum` + `hashlib` — match)

> Privacy R4: all Arabic candidate values in this committed record are replaced by
> sha16 fingerprints. Values live only under `sites/v16.localhost/private/`.

**Verdict: `VERDICT: REVISE (3 required changes) — e707a850851c472459c3b7cb6dbf60eaf5892ee4a80d9ac8ff0eab606b551f23`**

## Check table

| check | expected | observed | verdict |
|---|---|---|---|
| A. Proposal sha256 recomputed | matches file bytes | `e707a850…551f23` (1060 bytes, trailing newline; JSON parses; 1 row) | PASS |
| A2. Proposal location (R4) | values only under `sites/…/private/company-phase1-population/` | only file in dir; no copy elsewhere | PASS |
| B. Row set / identity | exactly 1 row `Elrefae`; no test company; no name/abbr/currency/country edits | rows=[Elrefae]; `english_label`/`company` duplicate identity only; no abbr/currency/country keys | PASS |
| C1. Transliteration quality | candidate_primary defensible for brand "Elrefae" | root is the correct Arabic proper noun (article elision `el`←`al`, final `e`←`ī`); idiomatic legal-entity form | PASS |
| C2. Precedent framing | precedent = committed artefact corroboration | **FAIL — overstated**: `measure_company_p95.py:40` is `AR_FIXTURES[0]`, a synthetic 4-string pool applied to throwaway `CT-COMP-Test-NN` rows; `test_bilingual_company_pilot.py:135` is a test value on a `_Test Company%` row with restore+commit. Not an established display name | FAIL |
| C3. Primary form | recommendation + rationale | keep `candidate_primary` as primary (correct root, idiomatic legal form matching owner's Egyptian contracting domain, only full string appearing verbatim in committed non-test code); bare root = strict-English alternate; pilot variant = broader alternate; final form = **owner display-form decision** (0 glossary terms govern company names) | NOTE |
| D1. Inventory evidence | log ends PASS, frozen counts | `INVENTORY RESULT: PASS`; 21 rows; active_owner=1 / test_noise=20; `PHASE1_FROZEN_MATCH yes`; `PRE_STATE_ARABIC 0` | PASS |
| D2. DB pre-state | 21 companies, 0 Arabic, Elrefae attributes | TOTAL 21 / AR_POPULATED 0; name==company_name=='Elrefae', abbr E, EGP, Egypt, parent NULL, is_group 0, AR NULL; usage GL 4 / JE 2 / SI 1 / Project 5 / Account 86 / CC 3 / Scope-Context 5 confirmed | PASS |
| D3. F-5H-1..5 + R1 | SCOPE findings reproduce | F-5H-1/2/3/4 match; F-5H-5 root claim true but "established brand" framing overstated (see C2) | PASS |
| D4. R4 private values | values only in private dir | confirmed (A2) | PASS |
| D5. R4 committed evidence | counts/verdicts/sha16/digests only | **FAIL — literal breach**: export script lines 111-112 and regenerated log hardcoded both full candidate strings (mitigation: both already committed verbatim in the two precedent files — no *new* value entropy) | FAIL |
| E1. Fixture / hooks | no Company fixture; validate hooks bound | only `uom.json`/theme/boq template fixtures; `hooks.py:366-370` Company validate = `enforce_bilingual_arabic_policy` + `narrative_sanitizer.validate_narrative_fields` | PASS |
| E2. Frozen tracked files | byte-identical to `5d96f12` | `git diff HEAD` empty for hooks/fixtures/registry/precedents; `uom.json` sha `d6e27a01…33ad2` unchanged | PASS |
| E3. Prior bilingual surfaces | frozen counts | Department 14/276, UOM 15/253, Account 81/2102, Item 8/43, Customer 1/12, Supplier 0/10, CC 3/47, WH 6/118, Project 5/11, Company 0/21 — all match 5F/5G frozen lists | PASS |
| E4. Test-company / rename risk | touches only Elrefae, no rename/abbr | 1 `doc.save()`; no rename path; no Translation/hook/JS/patch edits; no tracked diffs | PASS |
| E5. `Company.on_update` blast radius | 1 row | on_update side effects gated off for Elrefae (defaults/COA/country/NSM checks all bypassed) — **but** `company.py:362` unconditionally re-sets `Currency EGP enabled=1`, bumping `tabCurrency.modified` → "exactly 1 row" imprecise | NOTE |
| F. Queue-redis (F-5H-2) disclosure | port 11000 required during apply, disclosed | disclosed in F-5H-2, §3, R3, §7 and export log; `common_site_config.json` `redis_queue: …:11000`; consistent with prior tiers' start→run→teardown discipline | PASS |

### NOTE-level observations (recorded)

1. **E5 / invariant wording:** disclose the `tabCurrency.modified` bump (F-5H-6) so the
   1-row gate neither fails spuriously nor hides a side-write.
2. **F-5H-2 mechanism:** enqueue source not statically isolated by review; capture the
   traceback/job name in `apply.log` so the mechanism is recorded, not inferred.
3. Pilot test's `_get_target_company()` filters `_Test Company%` first (13 rows exist) —
   OK today; its `limit=1` fallback could resolve to Elrefae only if all `_Test Company%`
   rows were ever removed (out of scope; matrix runs with redis up).
4. Glossary holds a generic child-company term (near-match to two
   test-company names; sha16 only here per R4 — already committed in the glossary file) — "no company-name terms" slightly loose; irrelevant to Phase 1.
5. Keep `git add` scoped to the work-item dir; never commit untracked `dump.rdb`.
6. `english_label`/`company` duplicate identity — the applier must never treat
   `english_label` as a writable `company_name` target.

## Required changes (applied before approval)

1. Rewrite proposal `rationale`/`precedent` (text only; `arabic` + alternates byte-
   unchanged) to state the two artefacts are **in-repo corroboration of the brand root,
   NOT an established display name** (with the synthetic-pool / test-value facts).
2. Add an explicit **owner display-form decision marker** (primary + alternates; no
   glossary term governs company names).
3. Restore R4 conformance in committed evidence — sha16 digests instead of full strings
   in the export script, regenerate `inventory-export.log`, then re-sha and return for
   owner approval.

**Post-review disposition:** all 3 applied → proposal **v2** sha256
`b5fcc02a6854ebb27b71082b71c1b3f9d4ac43f737b013809697c2a23e79478a`
(owner-approved 2026-10-05); export log regenerated value-free (`INVENTORY RESULT: PASS`,
0 Arabic-value lines); findings F-5H-5 corrected, F-5H-6 added; SCOPE invariant/§3
wording amended (Currency bump + enqueue-mechanism capture).
