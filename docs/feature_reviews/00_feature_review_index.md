# Construction ERP Feature Review Index

Date: 2026-06-04

This folder contains separate implementation review reports for the main Construction ERP features currently in the app. The goal is to let each area be revised independently before the next implementation step.

## Reports

1. [BOQ Header Review](./01_boq_header_review.md)
2. [BOQ Structure Review](./02_boq_structure_review.md)
3. [BOQ Item Review](./03_boq_item_review.md)
4. [BOQ Item Stage Review](./04_boq_item_stage_review.md)
5. [Vite UI, List Views, and Form Config Review](./05_vite_ui_form_config_review.md)
6. [Modern Theme CSS and Theme System Review](./06_modern_theme_system_review.md)
7. [Egypt/Gulf Construction ERP Feature Sensitivity Matrix](./07_egypt_gulf_enterprise_roi_review.md)
8. [Improve Now Execution Plan](./08_improve_now_execution_plan.md)
9. [Improve Now Implementation Task Tracker](./09_improve_now_task_tracker.md)

## Current Implementation Snapshot

- The app is implemented as a Frappe app under `/home/mohamed/frappe-bench/apps/construction`.
- Active hooks register BOQ DocType scripts, BOQ Structure tree script, Desk CSS, Desk JS, website CSS, website JS, boot extensions, doc events, permission query conditions, and install/migrate setup.
- BOQ is split into four core DocTypes: `BOQ Header`, `BOQ Structure`, `BOQ Item`, and `BOQ Item Stage`.
- Transaction integration is active through custom child-row fields, client-side cascade filters, and server-side validation for Purchase, Stock, Timesheet, Journal Entry, Sales Invoice, and Material Request documents.
- The "Vite UI" implementation is not a standalone Vite application in this repo. It is a set of Frappe Desk client scripts and CSS assets named `vite_*` and `vfc_*`.
- The theme system is active on both Desk and website/login surfaces. Browser verification on `http://127.0.0.1:8000/login` showed the Construction Dark toggle visible and construction theme assets loaded.
- Live records exist for system themes (`Construction Dark`, `Construction Light`, `_Test Theme`) and default layout profiles for `BOQ Header`, `BOQ Structure`, `BOQ Item`, `BOQ Item Stage`, `Project`, and `User Scope Context`.

## Overall Assessment

The BOQ domain model is structurally sound: each layer has a clear responsibility, and most business rules are enforced server-side. The current risk is not missing functionality; it is complexity, duplication, and several places where UI behavior can drift from server truth.

The UI/theme layer is powerful but heavy. It uses broad global hooks, DOM re-parenting, late-loading CSS, custom dropdown controls, and a large theme loader. That gives broad coverage, but it also raises maintainability and regression risk.

## Recommended Next Review Order

1. Stabilize BOQ stage and transaction rules first, because they affect accounting attribution.
2. Clean up the Vite/Form Config terminology and guardrails, because it affects every form.
3. Reduce theme authority conflicts, especially static CSS versus generated CSS versus JS inline styling.
4. Add focused regression tests for state transitions, WBS generation, stage distribution, transaction attribution, and layout profile validation.
