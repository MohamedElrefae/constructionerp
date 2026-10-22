# Stage 6 W6-0b batch-4 — AI-A1 linguistic review (2026-09-22)

Session: `/root/ai_a1_arabic` (recorded review run)
Role: AI-A1 linguistic reviewer — independent of Builder/proposer.
Input: owner-approved `docs/translation/stage6_w60b_batch04_rows_2026-09-22.csv` (sha `21dcdd54164c5086b84ecd1e2c87979d6c1436fa663efced949b1fea573bad64`) + proposal panel `stage6_w60b_ai_proposal_build_batch04_2026-09-22.py` output.

## Verdict

**APPROVE** all 256 Released rows (Egyptian professional Arabic; placeholder parity; no source-equal on Released; no HTML-unsafe; no affix drift).

## Exceptions acknowledged

- 12 `EXCEPTION-technical` (Client URI, Client Metadata, Client Secret Basic, Client Secret Post, Code Challenge, Condition JSON, Form Dict, JS Message, Header, Robots, Logo URI, Introspection URI, Normalized Query) — source-equal format/identifier tokens, no distinct Arabic form.
- 3 `preserved-site-override` (Client Id → معرف العميل; Delimiter Options → خيارات الفاصل; Missing Field → حقل مفقود) — plan §12; not rewritten.

## Review checks

- Placeholder parity on 10 `{…}` rows: pass.
- Distinct Arabic ≠ source on Released: pass.
- Glossary v2.0 (47 terms): no batch-4 term collisions requiring override.
- Site recon non-empty keys reconciled (3 Site Overrides preserved; remaining Released as managed catalog rows).
