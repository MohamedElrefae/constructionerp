# Stage 4 Milestone: Proposal and Panel VERIFIED (2026-09-20)

**Work item:** erp-arabic-bilingual-data
**Stage:** 4

The Stage 4 proposal pipeline reached its verification gate.

```
status        = VERIFIED_FOR_RELEASE
sub_status    = OWNER_PAYLOAD_AUTHORIZATION
gate          = DRY_RUN / dry_run-77eafe61b25f1e5b74c5477e
candidate     proposal_sha256 ccfaed93… → later 769394db…, candidate_id e3c8bc2f…
bundle_sha256 = a047c286a4b11996ab5dfa14e799c66fe000cc56c9bdde31b0badc0808f39f4b
payload_sha256= 79ea924117f4345dc2974b825457fdbd0530f8c21c06adc2786cc34c2b7ec76b
```

## What ran

1. The independent proposer generated the Arabic proposal for all 81 accounts, applying
   the owner-mandated translations for rows 8/12/23/36/80.
2. The independent panel (ai-a1, ai-a2, ai-a3) returned **PASS / PASS / PASS** with exact
   81-identity coverage and distinct sessions.
3. The bundle and payload were composed with panel provenance recorded.
4. The independent verifier (separate Codex session) returned **PASS with 0 findings**,
   confirming artifact hashes, 81-identity coverage, panel bindings, and the 67-test
   offline suite.

## Engine changes that enabled this

- Native reviewer path: private output blob instruction, runner-attested sessions, sandbox
  write permissions, single-envelope result parsing with artifact recovery.
- Finding reconciliation: stale row rejections clear on panel approval; escalation budget
  applied on the quorum path.
- Reviewer projection: governed catalog metadata for structural verification.
- Verifier access: frozen proposal/bundle/payload plus panel review blobs mounted
  read-only with a checksum manifest.
- Bundle provenance: `compose_bundle` records role/session/verdict/review digests.

## Boundary

`committed = false`, `active_jobs = []`. The workflow now waits at the **DRY_RUN owner
authorization gate**. No ERP mutation, DRY_RUN, IMPORT, commit, push, or merge occurred.
The production checkout remains untouched.
