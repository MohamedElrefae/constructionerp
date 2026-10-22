# Stage 6 W6-0b batch-7 — AI-R verification record (2026-09-22)

Canonical session: `/root/stage6_w60b_ai_r_batch7`
Agent/role: independent release verifier (AI-R) — not Builder/A-proposer.

## Scope under verification

| Item | Value |
|---|---|
| Owner-approved batch CSV | `docs/translation/stage6_w60b_batch07_rows_2026-09-22.csv` |
| Batch sha256 | `1716d01c20129b86d629034d2c826a17a3029feb44b7006e1e19b7faa9bc76d4` |
| Batch rows | **270** |
| Site | `v16.localhost` only |

## Disposition of all 270 approved rows (fail-closed)

| Disposition | Rows | Imported? |
|---|---:|---|
| Released payload (governed import candidates) | **241** | yes (test site) |
| `EXCEPTION-technical` — format/identifier/brand/protocol tokens; keep vendor rendering | **29** | no |
| `preserved-site-override` — plan §12 drift contract | **0** | no |
| **Σ** | **270** | |

Paper trail: `docs/translation/stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv` (all 270 dispositions, tab-separated).

## Technical exclusions confirmed (29) — AI-R suppress-check

Format/identifier/brand/protocol/event tokens with **no distinct Arabic form**. Classification: `EXCEPTION-technical`.

Confirmed sources (exact, row-level):

```text
OAuth, OpenLDAP, PATCH, PUT, PID, Outlook.com, Sendgrid, SparkPost, Yandex.Mail,
UIDNEXT, UIDVALIDITY, processlist, s256, vim, emacs, login_required, on_cancel,
on_trash, on_update, on_update_after_submit, workflow_transition, version_table,
fairlogin, wkhtmltopdf, macOS Launchpad, Webhook, Websocket, XLSX,
Read Only Depends On (JS)
```

Rationale: keep vendor code/symbol/brand/protocol content untouched — technical fragment, no translation. These rows are **not** Released and **not** in `approved_ar_overrides.csv`.

## Site-override preserves (0) — AI-R drift contract (plan §12)

Authoritative runtime dump (20367 `Translation` rows): **zero** `ct_origin='Site Override'` rows among batch-7 keys (case-insensitive). `PATCH`/`Purple` have exact-cased empty runtime rows; case-variant `Patch`/`purple` rows carry operator Arabic values but are **not** Site Override origin (PATCH is technical; Purple imports against its exact-cased row).

Importer must report `drift=0` — confirmed only by the actual governed dry runs (pre/post).

## Released payload (241) — AI-R proposal checks

- Every Released row has distinct Arabic ≠ source (`csv-source-equal` clean).
- Placeholder parity (`{N}` / `{}`) enforced programmatically at proposal build — zero mismatches.
- Unicode + affix + unsafe-HTML checks: zero errors on the 241.
- Runtime match: **238** of 241 Released keys have exact-cased empty-origin runtime rows (→ expected `updated`); **3** have no runtime row (→ expected `created`: `Page to show on the website`, `Route: Example \"/app\"`, `There is no task called \"{}\"`).
- `decision_ref` binds each row to `content:docs/translation/stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv`.
- Quorum columns: `AI-A1/AI-A2/AI-A3 (recorded review run)` + `2026-09-22 00:00:00`.

## Supersession note

Corrected cycle supersedes rejected commit `8bfc23a`. Batch 7 is closed only when: DRY pre/post show the predicted counts with `drift=0`, full evidence gate ends `errors=0` **without** `--skip-evidence`, browser evidence batch07 passes, and the corrected cycle report is committed with `8bfc23a` retained in history.
