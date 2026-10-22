# Owner approval — bilingual-uom-phase1-population (Tier 5F)

**Approved artefact:** `sites/v16.localhost/private/uom-phase1-population/proposal.json`
(version 2, 15 rows)
**Proposal sha256:** `18a16a953ebbaad704acc7982ed96de71808235c7fc5b258b6825fbd80598bbf`
**Parent (v1, 17 rows, preserved):** `proposal-v1.json` sha256
`00cff4cda58629e5c4e31393d58129739f213379d17b89c1127a02be971c4b30` — v2 rows 1–15 are
byte-identical to v1 rows 1–15 (verified programmatically at v2 build time).

**Approvals given:** 2026-10-05, in-session, by the owner (Mohamed Elrefae):

| # | Decision | Choice |
|---|---|---|
| 1 | Phase-1 values | Round-1 independent review returned **16 approve / 1 revise** on v1; the single revise (`Pint (US)` transliteration) is moot after decision 2. Effective v2 verdict: **15/15 approve** (record: `evidence/review-ai-a2.md`; private record sha256 `2e58a4f06359319587af56ba3387c5934e31dfc1095a61e5fa238ea0fa07921b`). |
| 2 | F4 membership | **Prune to 15** — drop `Pint (US)` (9/11 BOQ rows under `_Test Security Audit Project`) and `Acre` (1 test-project draft). Both stay classified `in_use`, untranslated (Phase 2+). |
| 3 | F1 enablement | **Bundle this cycle** — `construction/fixtures/uom.json` gains `"enabled": 1` for all 12 fixture rows + one-time site enable in the same apply. |
| 4 | F5 durability | **Bilingual fixture** — `uom.json` additionally gains `uom_name_ar` for the 12 fixture rows, so `bench migrate` (fixture sync = delete+reinsert, wipes absent keys) preserves translations. `uom_name_ar_norm` is NOT stored in JSON — the validate hook re-derives it server-side on every import (proven by round-trip probe). This amends SCOPE R3/R4: Arabic values enter a committed app file for the first time (owner-authorized). |

**Authorized sequence (SCOPE §7):** dry-run (zero writes, proposal sha gate) → `uom.json`
bilingual edit (sha recorded) → apply via `doc.save()` for 15 DB rows (+ `enabled=1` on the
12 fixture rows) → post-import verification (15/15, norm/identity/exception checks, fixture
durability round-trip proof under suppressed commit + rollback) → matrix + reconciler +
lints → SCOPE flip + MANIFEST → commit proposed for separate approval.

**Hard gates:** any byte change to `proposal.json` after this point invalidates the
approval (scripts verify the sha before every write); no writes before the dry-run; no
vendor files; production remains untouched.
