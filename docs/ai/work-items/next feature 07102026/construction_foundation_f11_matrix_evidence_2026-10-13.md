# F11/F12 — Authorization and scope/report controls: matrix evidence

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, five ordinary sessions, site-bound WSGI clients
**Status:** matrix 22/26 allowed/denied as designed + file-leak fix verified (13/13). Three role-design decisions open (no code change without owner). F11/F12 **In progress**.

## 1. Matrix results (26 probes)

Allowed and denied as designed (22): PM reads/writes own scope; accountant/readonly denied cross-company and header reads; engineer item-write denied with state unchanged; readonly stage-create refused with scope message; PM import reaches service while engineer import denied; PM VO-create allowed, engineer API-create denied; unknown report refused; PM file download allowed; PM list scoped (5 fixture headers, no cross-project); readonly list empty; engineer VO-write allowed with cross-header move denied and state intact.

## 2. File leak — FOUND AND FIXED (F11-D001, S1)
**Reproduction:** cross-company accountant downloaded the VO-003 approval PDF (6,895 bytes, valid PDF) via both download URL forms. Root causes: (a) vendor download performs no attached-document check; (b) `File` DocPerm grants `All` full access; (c) approval PDFs stored public (`/files/`), which production web servers serve without any app check.

**Fix (3 files, uncommitted for F38):**
- `construction/overrides/file_permissions.py` (new): BOQ-attached Files inherit parent read (read) / parent write (write, delete). **Critical detail:** controller hooks can only deny — a `None` return counts as denial, so non-BOQ files explicitly return True (first version broke all uploads; caught by G4 and corrected).
- `construction/overrides/file_download.py` (new) + hooks override of `frappe.handler.download_file`: BOQ-attached downloads require parent read; everything else delegates unchanged (verified both URL forms hit the single function).
- `variation_order.py` gate: approval PDF must be **private** (transition-scoped so historical re-saves keep working); 4 existing approval PDFs migrated to `/private/files/` (disclosed data step).
- `hooks.py`: override + `has_permission["File"]` entries.

**Verification (13/13):** PM downloads allowed (both URL forms); accountant denied 403 (both forms); guest denied; non-BOQ delegation unchanged; File-doc read follows parent; fresh VO chain refuses public PDF ("must be private") then approves with private PDF and projects exactly.

## 3. Open role-design decisions (evidence, no unilateral change)

| ID | Observation | Required decision |
|---|---|---|
| F11-D002 (S1) | Read-Only direct document GET succeeds while list views return empty: scope containment covers list/report queries but direct reads rely on DocPerm alone | G08 decision: is selected scope a filter or an authorization boundary? (F12) |
| F11-D003 (S2) | Site Engineer stage creation refused by the same parent-write gate as VO (second instance) | Do engineers create measurement stages, or only PM/Owner? Needs QS/owner role definition before any gate change |
| F12-D001 (S1) | No construction role (PM/Owner/Engineer/Accountant) holds any finance-report role or Company read: `localized_report` denies at the vendor gate before Option B is reached; Company DocPerm has no construction-role rows | Finance/owner disposition of the 15 protected reports: grant vendor Report roles, extend the bypass, or keep finance-only (then F19's PM/Owner views need re-scoping). Option B on/off has no observable effect until this is decided |

SoD, frozen-field, snapshot and PDF-gate denials from F06 were re-verified in passing. Every denied mutation was followed by a persisted-state re-read (all unchanged). Credentials never in tracked docs.

## 4. Policy follow-through (owner decisions 2026-10-13)

- **F11-D002 scope boundary implemented:** `has_boq_parent_permission` now additionally requires the active scope to cover every touched header, and new `has_boq_header_permission` hook applies the same to direct header reads. Native role/User Permission checks remain independent; Administrator/SM bypass mirrors `scope_query`; missing scope denies. Regression: 5-test module (fail-before 5 errors stashed → 5/5 pass); HTTP: readonly direct read denied, PM out-of-scope denied despite Company grant, in-scope allowed.
- **F11-D003 engineer measurement implemented:** parent-read exception extended to stage writes/creates (deletes keep parent-write); new controller `enforce_measurement_field_policy` restricts non-header-writers to measurement fields on non-certified stages (planning fields refused, certification still role-gated). HTTP: engineer creates/measures allowed, planned-edit and certify refused.
- **F12-D001 disposition recorded:** finance-only ledgers stay; F19 construction views carry their own authorization (F19 adapters). Option B remains as designed; observable effect re-tested after F19 lands.
- **F11-D001 closure verified:** direct `/private/files/` serving (PM allowed, accountant/guest denied 403), old public URLs dead (0 DB rows, file gone from disk), attachment reassignment denied with record intact. 13/13 closure checks.
- `allow_tests` enabled only for regression runs, key removed afterwards. All source changes uncommitted for F38.
