# Owner approval — bilingual-wave1-masters-population (proposal v3)

**Date:** 2026-10-04 · **Site:** `v16.localhost` (non-production test)

The owner reviewed the full proposal table in-session (values shown in the session transcript;
file values remain private per SCOPE R4) and **approved it for import**:

- **Approved artefact:** `sites/v16.localhost/private/wave1-population/proposal.json` — proposal
  **v3**, sha256 `a00cfb432ed6680eefb20f22cc852923f059ff9320533569cdb57791e1cd1c77`
- **Scope approved:** 8 Item rows + 1 Customer row (9 total), with the documented exception list
  (all `_Test*` / `TEST-CONC-*` vendor fixtures, `Loyal Item`, 3× `Stock-Reco-*`,
  `Test Asset Item`, `Test Esstimate`, `Test Loyalty Customer`, and zero-population Supplier
  exception) — zero writes to any other row, zero Account writes.
- **Owner verification performed before approval:** private proposal file read + sha256
  recomputed and matched; registry field/norm parity for `Item` → `item_name_ar` and
  `Customer` → `customer_name_in_arabic`; spot-check of the glossary/lexicon anchors cited by
  the review rounds; acceptance of the exclusion scope and the disclosed stray-backtick identity
  flag (identity to remain untouched).
- **Authorized execution sequence:** dry-run (0 writes) → apply via standard `doc.save()`
  (existing validate hook server-derives `*_norm`) → post-import verification (9/9, norm
  consistency, Unicode/bidi compliance) → matrix (21/258) + reconciler (19/19) + lints →
  evidence manifest & commit.

This approval is the `owner-approval` gate of the SCOPE R2 chain
(`export → independent proposal → independent AI-A2 review → **owner approval** → dry-run →
import → verification`). Dry-run and apply must operate on exactly the approved sha; any
proposal byte change invalidates this approval.
