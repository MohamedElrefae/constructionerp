# Stage 6 — W6-0a desk-shell exact CSV (2026-09-21)

**Status: exact proposal delivered for owner review — no translation import authorized by this approval.**

## Contents

`docs/translation/stage6_w60a_desk_shell_rows_2026-09-21.csv` — the exact
362 rows cut from the vendor gap ledger by the approved desk-verbosity
filter (Owner decision 2026-09-21):

| Classification | Count | Meaning |
|---|---|---|
| `translation-candidate` | 340 | natural-language desk strings; eligible for the AI-proposal → quorum (A1/A2/A3) → AI-R → DRY_RUN → IMPORT cycle once this CSV is approved *as the batch scope* |
| `EXCEPTION-technical` | 22 | code-ish strings (embedded HTML help text, `{0}`-heavy validation templates, series/SQL/technical fragments) — proposed as **scope exceptions: keep vendor rendering, no translation**; recorded for AI-R suppress-check instead |

The broad 362-row ledger remains the warden: this CSV is the *candidate
scope for quorum review*, not an authorization to import. Remaining
boundary honored: translations enter only after you approve this exact
batch scope (the same single-cycle pattern as W6-1).

## Also delivered in this commit (decision #2 — endpoint fixes)

- P1 review note applied: pilot module paths are now **import-only**
  (removed the `.execute` suffixes; real `frappe.get_module()` imports the
  module and the endpoint binds `execute` via `getattr`).
- New unmocked smoke test: every pilot path imports and exposes a callable
  `execute` (fails if a function path creeps back in).
- Malformed JSON filters now **fail closed** (`frappe.ValidationError`)
  instead of silently becoming `{}`.
- Endpoint tests: 6/6 OK (2 new unmocked tests).
- Wave-2/3 masters remain `planned`-only (decision #3 honored; no registry
  change in this commit).
