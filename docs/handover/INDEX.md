# Handover Documents Index

> Last updated: 2026-06-21
> Sprint: rc-1.1 Follow-up (WP1–WP7)

## Purpose

This directory consolidates handover documents, technical briefings, and manager reports that document architectural decisions, bug investigations, and feature completion reports for the Construction ERP app.

## Document Index

| Document | Summary | Status |
|----------|---------|--------|
| `BOQ_STRUCTURE_BLOCKER_HANDOFF.md` | Technical briefing on scope context standardization and permission hardening for BOQ Structure tree view (403 Forbidden). Supersedes the root-level `BOQ_STRUCTURE_BLOCKER_HANDOFF.md` (which addresses a separate BOQ Structure UI blocker). | Active |
| `SCOPE_CONTEXT_STANDARDIZATION_APPROVAL_REPORT.md` | Manager approval report for scope context standardization and 403 elimination. | Active |
| `SENIOR_ENGINEER_AUDIT_REPORT.md` | Senior engineer audit of scope context implementation and recommendations. | Active |
| `TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md` | Typography settings implementation report — current state of font system. | Active |
| `VFC_PROJECT_TABS_DEBUG_REPORT.md` | Debug & fix plan for VFC Project Form Tabs — fixes applied and verified. | Active |
| `VFC_PHASE_3_PLUS_REVISION_PLAN.md` | Next-sprint VFC stabilization and Phase 3+ revision plan. | Draft |
| `VFC_PHASE_3_PLUS_ENHANCEMENT_REVIEW.md` | Manager review of the VFC Phase 3+ plan with code-grounded enhancements and decision points. | Draft |
| `VFC_PHASE_3_PLUS_IMPLEMENTATION_PLAN.md` | Approved implementation plan with locked decisions, task tracker, and evidence files. | Active |
| `MANAGER_DECISION_RECORD_2026-06-21_WP5_WP7.md` | Approval note for WP1-WP4/WP6/WP7 and explicit decisions for WP5 deferral and WP7 retention. | Active |
| `CONSTRUCTION_ERP_AI_MEMORY_PLAN_v2.2.md` | AI memory architecture plan (repo-authoritative). Now superseded by `docs/ai/` references + MCP protocol in `AGENTS.md`. | Archive |
| `AGENTS_HANDOFF.md` | Typography settings handoff from feat/edge-typography-fix-v16. Contents merged into `TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md`. | Superseded |
| `SESSION_MEMORY.md` (at repo root) | Living document — sprint state, session log, known issues. | Active |

## External Documents (outside git repo)

The following directories at `/home/mohamed/frappe-bench/` contain legacy planning documents that are OUTSIDE the construction git repo:

| Path | Contents |
|------|----------|
| `01 scope context/` | Legacy scope-context plans (cascade blocker reports, delivery tracker, environment scan). Review and archive locally if still needed. |
| `02BOQ Integratiom/` | Legacy BOQ integration plans, analysis, and progress trackers. Contents mostly duplicated in `docs/boq_*` and `docs/handover/BOQ_STRUCTURE_BLOCKER_HANDOFF.md`. |
| `03 ACCOUNTING INTEGRATAION/` | In-progress accounting integration docs (roadmap, UI implementation report). Keep for reference. |
| `teme debug/` | Deployment instructions and debug reports for various versions (v22–v24). Historical reference. |
| `forms config /` | Form layout engine configuration notes. |

## Convention

- New handoff documents should be placed in `docs/handover/` with a descriptive filename.
- Include a YAML-style header with date, author, and status.
- Update this INDEX.md when adding or archiving documents.
