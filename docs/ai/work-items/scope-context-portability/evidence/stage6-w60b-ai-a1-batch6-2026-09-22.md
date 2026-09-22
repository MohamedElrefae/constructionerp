# Stage 6 W6-0b batch-6 — AI-A1 linguistic review (2026-09-22)

Session: `/root/ai_a1_arabic` (recorded review run)
Role: AI-A1 linguistic reviewer — independent of Builder/proposer.
Input: owner-approved `docs/translation/stage6_w60b_batch06_rows_2026-09-22.csv` (sha `68500fae981aacec08e9841fc858dfd43e7473c7b12156ac8ca528b678d309e0`) + proposal panel `stage6_w60b_ai_proposal_build_batch06_2026-09-22.py` output.

## Verdict

**APPROVE** all 258 Released rows (Egyptian professional Arabic; placeholder parity; no source-equal on Released; no HTML-unsafe; no affix drift).

## Exceptions acknowledged

- 11 `EXCEPTION-technical` (InnoDB, Geoapify, Keycloak, Nomatim, DocShare, Awesomebar, Mx, Code challenge method, Collapsible Depends On (JS), Mandatory Depends On (JS), By \"Naming Series\" field) — source-equal format/identifier/brand tokens, no distinct Arabic form.
- 1 `preserved-site-override` (City → المدينة) — plan §12; not rewritten.

## Review checks

- Placeholder parity on 54 `{…}`/`{}`/`{e}` rows: pass.
- Distinct Arabic ≠ source on Released: pass.
- Glossary v2.0 (47 terms): no batch-6 term collisions requiring override.
- Site recon non-empty keys reconciled (1 Site Override preserved; remaining Released as managed catalog rows).
