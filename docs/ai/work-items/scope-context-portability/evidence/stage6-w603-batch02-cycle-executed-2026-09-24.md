# Stage 6 — W6-3 Stock batch-02 cycle (test site, 2026-09-24)

## Scope and boundary

Executed only the owner-authorized scope on `v16.localhost`:

- Scope: `docs/translation/stage6_w603_batch02_rows_2026-09-23.csv` — 250 rows, SHA-256 `701ad13e6b4cc530ebd7dbd95705979b70055c46f39da37d4532a26ba60439ef`.
- Proposal: `docs/translation/stage6_w603_proposal_batch02_2026-09-23.csv` — SHA-256 `aaac0e04b364f63e55dcfbd59bd72a19156952523f500226cb919aa387a8349e`.
- Final applied-row record: `docs/translation/stage6_w603_payload_applied_rows_batch02_2026-09-23.csv` — SHA-256 `47f5c970e78e376eedfa89bf0f9ca6f58d8aa75aa8ba1998f4ad1aca3adfb88a`.

No batch-03 scope, Stage 8 production activity, or production mutation was included. Four rows were explicitly withheld: two technical tokens (JAN/PZN) and two source defects (a `{3}` placeholder/formatter mismatch and a Stock Reconciliation “not zero” message contradicted by vendor behavior). Vendor files were not changed.

## Disposition and review

The exact 250 rows reconcile to **103 quorum-approved release rows + 143 preserved Site Overrides + 2 technical exceptions + 2 deferred source defects**. The 143 existing Site Override values were preserved; they were not overwritten. AI-A1/A2/A3 reviews are recorded in the three batch-02 evidence files. Independent AI-R verified the exact scope/proposal bindings, final decisions and site state; its final record is `docs/ai/work-items/scope-context-portability/evidence/stage6-w603-ai-r-batch02-2026-09-24.md`.

## Test-site result and gates

- Final live importer DRY-run: **2,540 total; 0 created; 0 updated; 2,540 skipped; 0 drift**. Independent site readback confirmed all 103 approved batch-02 releases and all 143 preserved overrides match the approved values; the four withheld rows were not released.
- Catalog: **2,540 Released**. Approved catalog SHA-256 `0101fc9d209956510032bf6686e293b98ed261198c48e880d50580e413b74325`; release-decision SHA-256 `dfdd46334e75386b5ec47f4526007eb6310c53cc29fecea993d186cef47c4e9a` (decision root `abb0e5a1de466edd40d35a4ddd5cbb47c4bd905832c4a7c6d2091d89d133f128`).
- Arabic browser evidence: **8/8 checks pass**, including exact matches for 246 payload/preserved strings in the boot dictionary, rendered Arabic DOM, no page errors, and logout. Artifacts: `evidence/raw-logs/stage6-w603/browser_evidence_w603_batch02.json` and `browser-ar-desk-w603-batch02.png`.
- Preflight components freshly verified read-only: Redis 13000/11000 both PONG and `/api/method/ping` HTTP 200. The authenticated browser evidence independently verifies a fresh `ar` Desk boot, the message payload and logout. Administrator language is `en` (direct database read); AI-R also verified System Settings language `en`. The temporary password file is absent. The stale same-named temporary UAT stdout was not used as evidence.
- Module suite: **270/270**; standalone gate suite: **91/91**. Scope/translation lints and diff check passed.
- Inventory: **20,957 rows**, `LIVE_MATCH`, Merkle root `7ff7884d6a2d6255735a1fc659e1dcc17d0a676f2b94afe772babf6ca811791a`.
- Freshness: **critical_pass**, no drift, 2,540 packaged rows.
- Independently rerun evidence-inclusive localization gate at base HEAD `e8d4846d26c5066ab0b9e900d513434f8b1392db`: **exit 0, errors=0**, 2,540 catalog rows. The ten-envelope index is bound to that pre-commit HEAD; after the closure commit, the expected single HEAD-binding staleness applies until the next approved catalog event/re-pin.

## Evidence integrity note

Some same-named files in `/tmp/opencode/stage2/` were stale captures from earlier W6 batches and were excluded from this closure evidence. The tracked Stage-2 envelopes/index, current live DRY-run, current gate rerun, browser JSON, and independent AI-R site readback were used instead. Host and database timestamps do not share a reliable clock basis here; no ordering claim depends on comparing those timestamps.

**W6-3 batch-02 CLOSED for the test site only.** Batch-03 remains unapproved. Stage 8 production rollout remains gated by real production data, a named production site and rollout window, and explicit production authorization.
