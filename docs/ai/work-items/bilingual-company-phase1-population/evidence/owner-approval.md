# Owner Approval — bilingual-company-phase1-population (Tier 5H)

**Date:** 2026-10-05
**Approved by:** Owner (via in-session question tool)
**Base commit:** `5d96f12`
**Proposal:** `sites/v16.localhost/private/company-phase1-population/proposal.json`
**Proposal sha256 (bound to this approval):**
`b5fcc02a6854ebb27b71082b71c1b3f9d4ac43f737b013809697c2a23e79478a`

## Decision

**Approved: primary display form** — apply the proposal's primary Arabic value to
Company `Elrefae` (exactly 1 row). The 20 test companies stay empty (Phase 2+, default
never).

- Review cycle: fresh-session review of v1 (`e707a850851c4724…551f23`) returned
  **REVISE** (3 required changes) → amendments applied → v2 (this sha). `arabic` +
  alternates byte-unchanged between v1 and v2; rationale/precedent text corrected; R4
  scrubbed to sha16 precedent matching; F-5H-6 (Currency `modified` bump) disclosed.
- Operational condition approved implicitly via F-5H-2: apply runs with queue redis
  (port 11000) up, torn down afterwards.
- Display-form scope: primary value as stored; alternates remain documented for a future
  rename-by-choice cycle only if the owner requests it (never automatic).

## Gate condition

Apply/dry-run scripts must verify the proposal file's sha256 equals the bound sha above
before any write; mismatch ⇒ fail-closed abort.
