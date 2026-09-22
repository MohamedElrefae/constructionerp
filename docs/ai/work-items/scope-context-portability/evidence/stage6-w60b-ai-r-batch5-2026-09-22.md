# Stage 6 W6-0b batch-5 — AI-R verification record (2026-09-22)

Canonical session: `/root/stage6_w60b_ai_r_batch5`
Agent/role: independent release verifier (AI-R) — not Builder/A-proposer.

## Scope under verification

| Item | Value |
|---|---|
| Owner-approved batch CSV | `docs/translation/stage6_w60b_batch05_rows_2026-09-22.csv` |
| Batch sha256 | `56f6432688d902fe8de5d2d2dfdccc501a36d78ec6534973c1f9cede3ad43544` |
| Batch rows | **270** |
| Technical exclusions (prior package) | `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (21) — **outside** this runtime cycle |
| Site | `v16.localhost` only |

## Disposition of all 270 approved rows (fail-closed)

| Disposition | Rows | Imported? |
|---|---:|---|
| Released payload (governed import candidates) | **252** | yes (test site) |
| `EXCEPTION-technical` — source==translation format/identifier tokens; keep vendor rendering | **17** | no |
| `preserved-site-override` — plan §12 drift contract | **1** | no |
| **Σ** | **270** | |

Paper trail: `docs/translation/stage6_w60b_payload_applied_rows_batch05_2026-09-22.csv` (all 270 dispositions, tab-separated).

## Technical exclusions confirmed (17) — AI-R suppress-check

Format/identifier tokens with **no distinct Arabic form** (source-equal under `csv-source-equal`). Classification: `EXCEPTION-technical`.

Confirmed sources:

```text
Not Nullable, Policy URI, Redirect URI, Resource Policy URI,
Resource TOS URI, Revocation URI, SQL Explain, SQL Output,
Success URI, TOS URI, Token URI, Userinfo URI,
RQ Worker, Realtime (SocketIO), SocketIO Ping Check,
Use STARTTLS, Setup > User
```

Rationale: keep vendor code/symbol/markup/format content untouched — technical fragment, no translation. These rows are **not** Released and **not** in `approved_ar_overrides.csv`.

## Site-override preserves (1) — AI-R drift contract (plan §12)

Existing runtime `Site Override` rows (case-insensitive source match) are **not** rewritten:

| source_text | preserved runtime Arabic (site) |
|---|---|
| Postal Code | الرمز البريدي |

Importer must report `drift=0` when the 1 is omitted from the payload CSV.

## Released payload (252) — AI-R proposal checks

- Every Released row has distinct Arabic ≠ source (`csv-source-equal` clean).
- Placeholder parity (`{N}` / `{}`) enforced programmatically at proposal build — zero mismatches on 8 placeholder rows.
- Unicode + affix + unsafe-HTML checks: zero errors on the 252.
- `decision_ref` binds each row to `content:docs/translation/stage6_w60b_payload_applied_rows_batch05_2026-09-22.csv` (source+translation both present).
- Quorum columns: `AI-A1/AI-A2/AI-A3 (recorded review run)` + `2026-09-22 00:00:00`.
