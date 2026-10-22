# Stage 6 W6-0b batch-7 — AI-A1 linguistic review (2026-09-22)

Session: `/root/ai_a1_arabic` (recorded review run)
Role: AI-A1 linguistic reviewer — independent of Builder/proposer.
Input: owner-approved `docs/translation/stage6_w60b_batch07_rows_2026-09-22.csv` (sha `1716d01c20129b86d629034d2c826a17a3029feb44b7006e1e19b7faa9bc76d4`) + corrected proposal panel `stage6_w60b_ai_proposal_build_batch07_2026-09-22.py` output (supersedes the rejected empty-translation stub at `8bfc23a`).

## Verdict

**APPROVE** all **241** Released rows (Egyptian professional Arabic; placeholder parity; no source-equal on Released; no HTML-unsafe; no affix drift).

## Exceptions acknowledged

- **29** `EXCEPTION-technical` (OAuth, OpenLDAP, PATCH, PUT, PID, Outlook.com, Sendgrid, SparkPost, Yandex.Mail, UIDNEXT, UIDVALIDITY, processlist, s256, vim, emacs, login_required, on_cancel, on_trash, on_update, on_update_after_submit, workflow_transition, version_table, fairlogin, wkhtmltopdf, macOS Launchpad, Webhook, Websocket, XLSX, Read Only Depends On (JS)) — format/identifier/brand/protocol/event tokens, no distinct Arabic form.
- **0** `preserved-site-override` — authoritative recon found zero `ct_origin='Site Override'` rows among batch-7 keys.

Accounting: 0 + 29 + 241 = 270 (fail-closed in build script).

## Review checks

- Placeholder parity on all `{…}`/`{0}`-style rows: pass (build asserts; including the `Use % for any non empty value.` PRINTF edge case).
- Distinct Arabic ≠ source on all 241 Released: pass.
- Glossary v2.0 (47 terms): no batch-7 term collisions requiring override.
- Decision binding: each Released catalog row binds to `content:docs/translation/stage6_w60b_payload_applied_rows_batch07_2026-09-22.csv` (raw-text source+translation substring).
