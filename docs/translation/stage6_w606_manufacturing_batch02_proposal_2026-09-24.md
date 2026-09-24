# Stage 6 — W6-6 Manufacturing batch 02 (remainder) proposal

**Status: owner-approved governed cycle executed on the non-production test site.**
The scope remains exactly bound to the 202-row CSV hash below; the final proposal
was independently reviewed by A1/A2/A3, and only its 82 payload rows were
released. The closure report records the test-site import and verification.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w606_manufacturing_batch02_rows_2026-09-24.csv`
- Rows: **202**
- SHA-256: `195c789945cf2b069a1620e855b22ad38aa9cb0adf03b9b2342166c47b6e88ff`
- Proposal CSV: `docs/translation/stage6_w606_manufacturing_batch02_proposal_2026-09-24.csv`
- Proposal SHA-256: `fde2fa6722c8b69bb87cbdc2c9927cf1a545e0f78f4c3b71f292f567d6f544f5`
- Deterministic builder: `scripts/stage6_w606_manufacturing_batch02_cut_2026-09-24.py`
- Domain: ERPNext Manufacturing remainder from the committed ERPNext Arabic gap ledger.

Batch 02 covers the final 202 fresh eligible source keys in Manufacturing, exhausting all eligible Manufacturing strings.

## Reconciliation and Dispositions Partition

Reconciled against `v16.localhost` via `docs/translation/stage6_w606_manufacturing_batch02_site_recon_2026-09-24.py` (JSON output: `docs/translation/stage6_w606_manufacturing_batch02_site_recon_2026-09-24.json`):

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override` | 119 | Match live test-site `tabTranslation` verbatim; preserve unchanged (plan §12); not imported |
| `PROPOSED-payload` | 82 | Candidate translations authored for missing runtime keys; require independent A1/A2/A3 review |
| `EXCEPTION-technical` | 1 | Technical snake_case identifier (`material_request_item`); keep vendor rendering; empty translation |
| **Total** | **202** | **119 + 82 + 1** |

The first two proposal hashes were blocked during review and superseded after
terminology/grammar corrections. Final A1/A2/A3 PASS records bind to the exact
proposal hash above; earlier verdicts on prior hashes do not carry over. A2
noted that the new Bucket View phrase differs from the preserved live label,
but accepted its clear time-period meaning as non-blocking.

The three pre-existing Site Override rows whose source keys have edge spaces
(` Is Subcontracted`, ` Skip Material Transfer`, `Returned Qty `) are explicitly
marked in the proposal CSV as preserved edge-whitespace exceptions. Their exact
source keys and Arabic Site Override values are retained; they must not be
trimmed, normalized, or re-imported.

## Boundaries and closure

The owner approved this exact scope for `v16.localhost` only. No other batch
was included. Stage 8 and production remain untouched. See
`stage6-w606-manufacturing-batch02-cycle-executed-2026-09-24.md` for the
dispositions, importer/UAT/browser results, and evidence bindings.
