# F09 — Stage planning and correction paths: engineering evidence

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, ordinary sessions (PM/Owner/Engineer)
**Transport:** site-bound WSGI test clients; document REST + whitelisted bulk endpoint
**Status:** 15/15 checks pass. F09 **Engineering verified** for stage scope; owner UI-24–28 + task guides (F40) remain.

## 1. Fixtures

Dedicated header BOQ-2026-8582 (Draft, PROJ-0014) + item qty 100. Stages: foundations planned 60, columns planned 40, adjustment +5 (after revision 100→105).

## 2. Results (15/15)

| Check | Result |
|---|---|
| T1 planned distribution 60+40 accepted against qty 100 | Pass |
| T2 certified>measured, negative qty, percent>100 all refused (417) | Pass |
| T3 PM measures+certifies 60/60; later edits refused even by Owner (417) | Pass |
| T4 Site Engineer certification refused (403); stage unchanged | Pass |
| T5 quantity revision 100→105 approved, then +5 adjustment accepted, certified record intact | Pass |
| T6 bulk update on open stage ok; on certified stage refused, values intact | Pass |

## 3. Correction-path rule (the usable procedure)

- Planned total may not exceed the item quantity (proven 417 at 105/100) — over-planning is refused, not truncated.
- After a quantity change is approved through the revision lifecycle, new planned capacity becomes available and an **adjustment stage** (new record) is accepted. Certified history is never rewritten.
- No new domain rule was required: the existing revision + adjustment-stage combination covers the legitimate correction path. QS/Mohamed decision not needed for this flow.

## 4. Remaining

Owner UI-24–28 journeys + F40 guide wording ("create an adjustment stage instead" of editing certified rows); F11 matrix reuse of these fixtures/sessions. F04/F05/F06/F07/F08 baselines untouched.
