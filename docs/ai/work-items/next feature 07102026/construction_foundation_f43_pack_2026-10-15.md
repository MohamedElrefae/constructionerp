# F43 — Consolidated owner acceptance pack (complete, 2026-10-15)

Executor: Mohamed, one consolidated block after engineering readiness. Engineering
automation never substitutes. Blank results stay Not run. No compression to protect a date.

Step text lives in `existing_features_owner_ui_acceptance_plan_2026-10-12.md` (UI-01–UI-69),
`construction_foundation_f18_service_contract_design_2026-10-12.md` (F18-U01–12) and
`construction_foundation_f19_service_contract_design_2026-10-12.md` (F19-U01–12). This pack
adds the session plan, prerequisites, persona/fixture map, evidence rules and retest loop.
Coverage additions (COV-01–10, F21-U, corrected defects) are mapped in §5 — they extend the
69 groups, never replace them.

## 1. Preflight (every session)

Site identity (site-only login) · scope ON readback · service health · candidate HEAD +
snapshot hash · clean browser context per persona · backups present.

## 2. Prerequisites and fixtures

- Accounts: Owner, PM, Engineer, Finance, Procurement/Stores, Restricted, Setup admin —
  per §4 of the UI plan (distinct identities; role names alone prove nothing; export
  effective permissions before execution).
- Company + Project A1 scoped to each account; Cost Database Maintainer holds no automatic
  rights (production activation separately gated).
- Acceptance fixtures: ACC dataset expectations where needed; legacy records stay out of
  acceptance scope (F10 limitation disclosed).
- Credentials via the secure local handoff only — never in guides, evidence or chat.

## 3. Session plan (with retest reserve)

| Session | Cases | Personas | Duration |
|---|---|---|---|
| S1 Access, settings, scope | UI-01–UI-06 | All + Restricted | 1 hr |
| S2 BOQ foundation | UI-07–UI-14 | PM, Engineer | 1.5 hr |
| S3 Estimation + stages | UI-15–UI-28 | PM, Engineer, Owner | 2 hr |
| S4 VO + transactions | UI-29–UI-44 + row checks | PM, Engineer, Owner, Procurement, Finance | 2.5 hr |
| S5 Finance + import/export + reports | UI-45–UI-60 | Finance, PM | 2 hr |
| S6 Theme/layout + recovery + rehearsal | UI-61–UI-69 | PM + Engineer | 1.5 hr |
| S7 Cost DB + views | F18-U01–12, F19-U01–12 | Maintainer, PM, Finance | 2 hr |
| S8 Additions | COV-01–10, F21-U, defect retests below | per case | 1.5 hr |
| Reserve | retests + overflow | — | half day |

Total: ~14 hours across sessions; schedule with breaks, not back-to-back.

## 4. Evidence and retest rules

Per case: Pass/Fail/Blocked, actual values, candidate/site, account, record IDs, date,
evidence path. Variants get subrows; parent passes only when all required subrows pass. Old
attempts kept. Negative tests: refusal = Pass; crash or silent acceptance = Fail; missing
prerequisite = Blocked. Recording rules per §5 of the UI plan (screenshot naming, no
credentials in evidence).

## 5. Mapped additions (extend, never replace)

- **COV-01–10** (F03 inventory): bilingual report, account rename/translation admin, VO-to-MR,
  WBS conversion/resequence/health, bulk stages, generic exports, guest/dormant routes,
  deployed metadata, existing-service UI.
- **F21-U**: one workspace per role with filtered navigation (see F21 evidence).
- **Corrected-defect retests:** K-01 preview→confirm→persisted rows (F36-D003); price-history
  zero-rows for unauthorized roles (F21-D002); BOQ file-attachment boundary (F11);
  mandatory-field Arabic refusal; unsaved-layout indicator + warnings (F23-D002).

## 6. Defect form

Case ID · role · URL · clicks in order · expected vs actual · evidence slot · retest
instruction. Engineering fixes land on isolated copies with candidate changes documented;
retests stay inside this block. If unfinished, acceptance stays open — never silently passed.
