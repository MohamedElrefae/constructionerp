# Stage 6 — W6-6 CRM, Support & Maintenance proposal

**Status: owner-approved governed cycle executed on the non-production test site.**
The scope is bound to the exact CSV hashes below. Renewed independent A1/A2/A3
reviews and final AI-R passed, the corrected payload was imported, and only the
38 payload rows were released. See
`stage6-w606-crm-support-maintenance-cycle-executed-2026-09-24.md` for closure
verification.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w606_crm_support_maintenance_rows_2026-09-24.csv`
- Rows: **119**
- SHA-256: `a77b43a908859c0aea3e2c58525ec3765772c09af8617f1f17fb8c8bf12833f9`
- Proposal CSV: `docs/translation/stage6_w606_crm_support_maintenance_proposal_2026-09-24.csv`
- Proposal SHA-256: `d8a2a8df2c040434b82d4d813f96e510e454b0f11114a31cf709db62bf60f266`
- Deterministic builder: `scripts/stage6_w606_crm_support_maintenance_cut_2026-09-24.py`
- Domains: ERPNext CRM, Support, and Maintenance from the committed ERPNext Arabic gap ledger.

## Reconciliation and Dispositions Partition

Reconciled against `v16.localhost` via `docs/translation/stage6_w606_crm_support_maintenance_site_recon_2026-09-24.py` (JSON output: `docs/translation/stage6_w606_crm_support_maintenance_site_recon_2026-09-24.json`):

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override` | 76 | Match live test-site `tabTranslation` verbatim; preserve unchanged (plan §12); not imported |
| `PROPOSED-payload` | 38 | Corrected candidate translations; require renewed independent A1/A2/A3 review |
| `DEFERRED-source-defect` | 4 | Three unresolved CRM Prospect terminology rows and one reused SLA response/resolution source key; keep deferred |
| `EXCEPTION-technical` | 1 | `fieldname` code token; keep vendor rendering; empty translation |
| **Total** | **119** | **76 + 38 + 4 + 1** |

## Boundaries

The proposal is strictly non-production and proposal-only. No mutations have been made to `v16.localhost` or git. Stage 8 and production remain untouched.

## Owner decision and execution

The owner-authorized corrected continuation used the exact 119-row scope on
`v16.localhost` only. The reviewed CRLF proposal bytes had SHA-256
`3d80277b516663b00f2240ed2d9476eef7eeb62803df867dbd029d74f0dcd354`; the
repository-normalized LF proposal committed here has SHA-256
`d8a2a8df2c040434b82d4d813f96e510e454b0f11114a31cf709db62bf60f266`.
Translation content is identical. Stage 8 and production remain untouched.
