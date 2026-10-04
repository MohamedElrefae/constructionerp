# Owner approval — bilingual-wave1-phase2-population (Tier 5C)

**Approved artefact:** `sites/v16.localhost/private/wave1-phase2-population/proposal.json`
(version 2)
**Proposal sha256:** `e68ef0c687516a110ed553a52cfe7d871808ba6007d9c1444ec1739730108557`

**Approval given:** 2026-10-05, in-session, by the owner (Mohamed Elrefae), immediately
after reviewing the full 13-row table (values shown in-session; committed evidence keeps
digests only per R4).

**Decision:** "Approve all 13 as proposed" — no amendments. The two flagged rows
(`Elrefae - E` proper-name transliteration, `PROJ-0008` VO reading) were accepted as
proposed; optional translation-string parity swaps for the three warehouse labels were
declined (values stay as reviewed).

**Independent review bound to this approval:** round 2 session
`ses_ef7027ce9ffe2qYPR6EuUV2Ei5` returned overall **approve** with 13/13 row approvals
against exactly this sha (record: `evidence/review-ai-a2.md`).

**Authorized sequence (unchanged from SCOPE §5/§7):** dry-run (zero writes, must match
the approved row set) → apply via `doc.save()` → post-import verification (13/13,
norm/bidi/identity/exception checks) → matrix 21/258 + reconciler 19/19 + lints →
SCOPE flip + MANIFEST → commit proposed for separate approval.

**Hard gates:** any byte change to `proposal.json` after this point invalidates the
approval (scripts verify the sha before every write); no writes before the dry-run; no
shared-file changes; production remains untouched.
