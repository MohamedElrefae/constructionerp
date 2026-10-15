# Construction ERP — Developer Maintenance Guide

Audience: engineers maintaining this app. Engineering scripts and governance references below require the authorized private maintainer checkout; they are not all included in the curated customer distribution. For the permission model in full, read
`docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md` and `AGENTS.md` first; this guide is the
day-to-day companion, not a replacement.

## 1. Architecture map

- `construction/api/` — whitelisted RPC boundaries. Every endpoint validates input,
  enforces document permission + scope, and restricts mutation methods. Whitelisting alone
  is never authorization.
- `construction/services/` — business logic (BOQ lifecycle, import, cost database, reports
  as internal helpers, transaction validation, bilingual policy).
- `construction/overrides/` — framework hooks. The full inventory with upstream targets
  and signatures lives in
  `docs/ai/work-items/next feature 07102026/construction_foundation_f24_evidence_2026-10-14.md`.
  Re-check it on every vendor bump.
- `construction/public/js/` — Desk JS. `vite_layout_controls.js` (VFC panel),
  `vfc_layout_engine.js`, `construction_export_menu.js`, `generic_export_menu.js`,
  `print_settings_dialog.js`, compat shims. **Any touched file bumps its `?v=` in
  `hooks.py`, then `bench --site <site> clear-cache`, then verify the served HTML carries
  the new versions** (the embedding HTML is server-cached; `get_hooks` alone is not proof).
- `construction/construction/` — DocTypes, pages, workspaces, the app-shipped Sidebar
  fixture (`sidebar/construction_home/`), print formats.

## 2. Non-negotiable conventions

1. All SQL parameterized (`%(name)s`), never f-strings.
2. New transactional DocType with scope dimensions → the Scope Context checklist in
   `AGENTS.md` §4.9, then `python3 scripts/lint_scope_metadata.py`.
3. Translation writes go through `construction.translation_service.upsert_runtime_translation`
   (never direct `tabTranslation` edits) — see `scripts/lint_translation_writes.py`.
4. Tests run as non-admin personas where scope matters; one process per persona in
   multi-user probes (`@request_cache` survives `set_user`).
5. Python 3.10 quote-nesting compatible, even though the runtime is 3.14.

## 3. Everyday commands

```bash
python3 scripts/ai_context_check.py          # context + schema gate
python3 scripts/schema_drift_checker.py      # live schema vs JSON
python3 scripts/lint_translation_writes.py   # translation-write lint
bench --site <site> run-tests --module construction.tests.<module>
bench --site <site> clear-cache              # after any ?v= bump
python3 scripts/permission_reconciliation.py --site <site>   # effective vs standard perms
python3 scripts/permission_reconciliation.py --site <site> --baseline <file>  # drift gate
```

## 4. Packaging

Canonical: Flit via `pyproject.toml` (dynamic version from `construction/__init__.py`).
Source maps under `construction/public/dist/js/*.map` are build outputs — never commit them,
excluded from sdist. Test screenshots live under evidence docs, never in `construction/tests/`.
`bench get-app` ships the whole checkout, so internal evidence under `docs/ai/` must stay out
of any customer route (see `docs/DISTRIBUTION.md`).

## 5. What never changes without an owner decision

Permission grants, Page read, shell renames, scope-model changes, deletion of approved
history or legacy tables, delivery-route changes, vendor-bump adoption.
