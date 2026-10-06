# Customer Release Candidate Summary

**Date:** 2026-10-06
**Release Candidate Identity:** branch `develop`, HEAD `72ec8b3` (545 commits), working tree `/home/mohamed/frappe-bench/apps/construction`. Strictly local; zero push to remotes.

---

## Financial & Commercial Integrity Architecture (G01–G06)

- **G01:** Deletion/current aggregate fixes; named v16 copy has zero rollup discrepancies.
- **G02:** Frozen history/current projections; 219 old revisions preserved, 35 linked approvals resave.
- **G03:** Manual/prior cancellation restoration and reviewed atomic conversion regressions.
- **G04:** Positive factors enforced in native controllers/import/readers; browser zero refusal.
- **G05:** Twelve real overlapping-connection/contention regressions.
- **G06:** Additive direct-cost pricing; factor-aware resources/revisions/export.

## Automated Test & Qualification Coverage (G07, G08, G14, G16)

- 17 modules CI Run 11 green (234 Python tests + 35 JS property tests).
- 21 modules bilingual matrix green.
- 10 UAT commercial workflow tests green (`test_e2e_bilingual_commercial_workflow.py`), deterministic snapshots, 4 bilingual print formats, 7 localized reports.

## Security Hardening & Compensating Controls (G10)

- Frappe v16.36.1 alignment; dependency security remediation.
- SSRF boundary, upload sniffing, PDF page caps, SVG sanitization, bleach rich-text.
- Compensating input guards in `security.py`; 33/33 unit tests.

## Multi-Site Cutover Runbook & Operating Profile (G11, G12, G15)

- 44-step coordinated cutover orchestrator (`orchestrate_cutover.py`) passes.
- Backup validation: 8.62s restore timing; fail-closed rollback drill.
- Production operating profiles: Procfile, supervisord, redis_queue templates.

## Governance & Manifest Integrity

- 40 manifests across 423 file entries verified with zero drift.
- Release decisions ledger ratified; `END_TO_END_TESTED_FILES.json` evidence binding current.
- Standing policy: `OWNER_CONFIDENTIALITY_POLICY.md`; local commits only with hooks bypassed; no vendor edits to `apps/frappe/` or `apps/erpnext/`; system Redis (6379) untouched.
