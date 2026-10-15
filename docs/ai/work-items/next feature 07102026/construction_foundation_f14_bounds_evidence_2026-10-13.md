# F14 — Bounded imports, exports and PDFs: transport evidence

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, ordinary sessions + Administrator (cost-DB bounds only)
**Status:** 27/27 checks pass. F14 **Engineering verified** for the verified paths; two open items below. Worker/queue sizing under load belongs to F37.

## 1. Results (27/27)

| Area | Evidence |
|---|---|
| Transport guards | Anonymous import/export denied (403); GET on POST-only import refused |
| BOQ preview/commit | Valid 3-row preview succeeds with zero writes; commit persists exactly 3 items + batch; counts verified before/after |
| Just-over-limit (10,001 rows vs 10,000 cap) | Refused with limit message; zero writes |
| Malformed (bad zip) + wrong type (.txt) | Clean 417 refusals; zero writes |
| Role denials | Engineer import 403; cross-scope accountant 403 |
| Cost DB | Preview/commit/over-2000-refusal proven as Administrator (3 items + 3 history rows created); PM/SM denied (see D001); cross-scope + company-mismatch denied |
| Exports | PM Excel 200; accountant/anon denied; PM PDF 200 with private file |
| Error report | Structured errors on bad file; zero writes |
| Rapid previews | 5/5 consistent (smoke only, not a rate-limit proof) |

## 2. Open items

- **F14-D001 (S1 role design):** cost-DB import demands doctype-level create on Company-read + Resource Price History + Item + BOQ Cost Analysis. No ordinary role holds RPH/Item create (Owner/PM read-only; SM-with-User-Permissions fails the Item check) — only Administrator can import. F18's authorized-user workflow is unreachable until owner designates the importing role(s).
- **F14-D002 (S2 operations):** BOQ PDF export depends on the shared `assets_json` cache entry, which is populated from CWD-relative `assets/assets.json`. A cache miss from a bench-root CWD stores None bench-wide and breaks every PDF export until evicted (observed, reproduced, cleared; export then succeeded). Remediation: warm/verify the cache after builds and restarts, pin worker CWD expectations in the operator runbook (F33/F41). Not app code.

## 3. Notes

- Byte-limit (25 MiB) path shares the pre-read guard with the verified row-limit path; no 25 MB fixture was uploaded (deliberately avoided). Cost-DB test data (F14C-*) and F14 import batches are namespaced dedicated fixtures.
- **Operator note:** the site Administrator password was rotated to a temporary value during this session (required for the Administrator-leg cost-DB evidence). Rotate it again before the UI block.
- **F14-D002 cache recovery procedure (for the F33/F41 runbook):** symptom — all PDF exports fail with `'NoneType' object has no attribute 'get'` from `bundled_asset`. 1) `redis-cli -p 13000 DEL assets_json` (shared key; verify gone). 2) Re-run one export from a process with CWD=sites (or any correctly-resolved context) to repopulate with the real manifest. 3) Verify `sites/assets/assets.json` contains `print.bundle.css`. Recurrence prevention (F25/F38): warm/verify this key after every build/restart/upgrade before acceptance runs.
