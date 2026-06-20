# Restored Work Follow-up Report

Date: 2026-06-15
Repo: `/home/mohamed/frappe-bench/apps/construction`
Branch: `feat/scope-context-standardization`

## Summary

The restored working tree is mostly staged local work recovered from the local
`recover-lost-files` branch. The changes are not committed on the current branch
and are not on GitHub. This report lists the pieces that appear to need
follow-up before the restored work should be treated as production-ready.

## Findings

### P1: Typography handoff does not match the restored code

Evidence:

- `AGENTS_HANDOFF.md` says `typography_settings.js` was refactored from v9 to
  v16 and `hooks.py` was bumped to `?v=16`.
- The current `construction/hooks.py` still loads
  `/assets/construction/js/typography_settings.js?v=9`.
- The current `construction/public/js/typography_settings.js` still emits
  CSS-variable-based typography rules in `ensureStyleTag`, while the handoff
  claims the fix replaced that path with literal static font stacks.
- Neither `construction/hooks.py` nor `construction/public/js/typography_settings.js`
  is in the staged restore.

Risk:

The handoff may describe work that was not restored, or it may be stale and
should not be committed as-is. If committed unchanged, it will mislead the next
agent/team about the actual state of the typography/Edge fix.

Recommended finish plan:

1. Decide whether the v16 typography fix should be restored, reimplemented, or
   dropped.
2. If it should ship, update `typography_settings.js` and bump `hooks.py`.
3. Run `node --check construction/public/js/typography_settings.js`.
4. Run `bench build --app construction`.
5. Manually verify the Edge font-family repaint issue.
6. Update or remove `AGENTS_HANDOFF.md` so it matches reality.

### P1: BOQ Excel import has mixed "commit implemented" and "preview-only" signals

Evidence:

- `BOQImportService._commit_import()` exists and creates structures/items when
  `enable_boq_excel_import_commit` is enabled.
- `BOQImportService.get_import_status()` still returns:
  `status: "preview-only"` and `message: "Commit import not implemented yet"`.
- `BOQImportService.create_import_template()` still returns:
  `"Excel template creation to be implemented in WP2.8"`.
- Large imports set `requires_async` and synchronous commit throws:
  `"must use async import"`, but no async import queue/status implementation was
  found in the staged changes.

Risk:

Users or API clients may see contradictory status. Small synchronous commits may
work behind the feature flag, but the status/template/async paths are unfinished
or at least not aligned.

Recommended finish plan:

1. Decide the intended release scope:
   - preview-only,
   - small synchronous commit only,
   - or full sync plus async commit.
2. If preview-only, remove or keep disabled the commit path and update UI/API
   messaging accordingly.
3. If sync commit should ship, update `get_import_status()` and tests so status
   reflects real committed/failed/preview states.
4. Implement or explicitly disable the Excel template endpoint.
5. Implement async commit queue/status, or lower the UX promise so async-sized
   files are clearly blocked with a product message.
6. Run BOQ parser/import tests after choosing the scope.

### P1: Scope context global standardization still needs runtime verification

Evidence:

- The new `docs/scope context globally/SCOPE_CONTEXT_GLOBAL_IMPLEMENTATION_HANDOFF.md`
  defines a broad app-wide mission: zero 403 errors for restricted users across
  lists, trees, and forms.
- The repo metadata lint now passes:
  `PASS: no scope-dimension field has in_standard_filter=1 (15 DocTypes checked).`
- A search of staged client JavaScript found no direct
  `frappe.db.get_value("Project" | "Company" | "Cost Center", ...)` calls.
- The handoff's definition of done still requires manual restricted-user
  browser verification across the Construction app.

Risk:

Static checks look good, but the main failure mode is runtime behavior in Frappe
list/tree/form bootstrapping. The work should not be considered complete until a
restricted user can navigate the app without Project/Company/Cost Center 403s.

Recommended finish plan:

1. Run `python3 scripts/lint_scope_metadata.py` in CI.
2. Run `bench migrate` after metadata changes.
3. Log in as a restricted role such as Site Engineer or Accountant.
4. Visit key Construction list/tree/form views and capture network/console logs.
5. Fix any remaining 403s at the DocType metadata or safe API layer.
6. Convert the handoff into an implementation report once verified.

### P2: `construction/scratch_test.py` is a debug artifact

Evidence:

- `construction/scratch_test.py` is newly added.
- It inserts a private PNG `File`, creates a `Construction Theme`, prints debug
  output, then rolls back.
- It is not named as a standard test module and has no assertions.

Risk:

This looks like a one-off debug script for private login background image
behavior. Committing it in the app package may confuse test discovery,
maintenance, or deployment hygiene.

Recommended finish plan:

1. Decide whether the behavior is worth preserving.
2. If yes, convert it into a real test under the appropriate test module with
   assertions and cleanup.
3. If no, remove it from the commit.

### P2: Added handoff files should be converted or excluded

Evidence:

- `AGENTS_HANDOFF.md` is newly added and currently mismatches the code.
- `docs/scope context globally/SCOPE_CONTEXT_GLOBAL_IMPLEMENTATION_HANDOFF.md`
  is newly added and reads as instructions to begin work, not a completion
  report.

Risk:

Handoff files are useful during recovery, but they can make the repository look
less finished if committed alongside implementation work without being updated.

Recommended finish plan:

1. Keep only handoff files that are intentionally part of project documentation.
2. Rename/update them as status reports if the work is complete.
3. Remove stale or agent-only instructions from the production commit.

### P2: VFC layout engine contains heavy diagnostic logging

Evidence:

- `construction/public/js/vfc_layout_engine.js` contains many `console.log`
  diagnostics such as attach, profile fetch, verification, wrapper movement, and
  initialization logs.
- The staged restore modifies this file substantially.

Risk:

The logging may be intentional during layout-engine hardening, but if left
enabled in production it can make browser consoles noisy and obscure real errors.

Recommended finish plan:

1. Decide whether diagnostics should remain enabled by default.
2. Gate layout-engine logs behind a debug flag or remove low-value logs.
3. Run browser verification after any logging or timing changes.

## Verification Already Performed During This Review

- Confirmed the current branch tracks GitHub and is not ahead/behind:
  `feat/scope-context-standardization == origin/feat/scope-context-standardization`.
- Confirmed restored changes are staged, not unstaged.
- Confirmed the staged restore has 62 files, not 64.
- Ran `python3 scripts/lint_scope_metadata.py`; it passed.
- Searched staged client JavaScript for direct restricted
  `frappe.db.get_value("Project" | "Company" | "Cost Center", ...)` calls; none
  were found.

## Suggested Planning Order

1. Resolve the typography handoff mismatch.
2. Decide BOQ Excel import release scope and fix status/template/async behavior.
3. Run restricted-user scope-context browser verification.
4. Remove or convert scratch/handoff artifacts.
5. Reduce or gate VFC diagnostic logging if this branch is headed to production.
6. Run the focused Python and JS test suites for the touched areas.
