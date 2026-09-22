# Stage 6 W6-0b batch-5 — AI-A1 linguistic review (2026-09-22)

Session: `/root/ai_a1_arabic` (recorded review run)
Role: AI-A1 linguistic reviewer — independent of Builder/proposer.
Input: owner-approved `docs/translation/stage6_w60b_batch05_rows_2026-09-22.csv` (sha `56f6432688d902fe8de5d2d2dfdccc501a36d78ec6534973c1f9cede3ad43544`) + proposal panel `stage6_w60b_ai_proposal_build_batch05_2026-09-22.py` output.

## Verdict

**APPROVE** all 252 Released rows (Egyptian professional Arabic; placeholder parity; no source-equal on Released; no HTML-unsafe; no affix drift).

## Exceptions acknowledged

- 17 `EXCEPTION-technical` (Not Nullable, Policy URI, Redirect URI, Resource Policy URI, Resource TOS URI, Revocation URI, SQL Explain, SQL Output, Success URI, TOS URI, Token URI, Userinfo URI, RQ Worker, Realtime (SocketIO), SocketIO Ping Check, Use STARTTLS, Setup > User) — source-equal format/identifier tokens, no distinct Arabic form.
- 1 `preserved-site-override` (Postal Code → الرمز البريدي) — plan §12; not rewritten.

## Review checks

- Placeholder parity on 8 `{…}` rows: pass.
- Distinct Arabic ≠ source on Released: pass.
- Glossary v2.0 (47 terms): no batch-5 term collisions requiring override.
- Site recon non-empty keys reconciled (1 Site Override preserved; remaining Released as managed catalog rows).
