# W6-6 Manufacturing Batch 02 AI-R verification — 2026-09-24

- Verdict: **PASS**, independent read-only review.
- Candidate HEAD: `69b999e5f7d0eb003bc8fd26c1d765dee1de0526`.
- Approved scope CSV SHA-256: `195c789945cf2b069a1620e855b22ad38aa9cb0adf03b9b2342166c47b6e88ff`.
- Final proposal CSV SHA-256: `fde2fa6722c8b69bb87cbdc2c9927cf1a545e0f78f4c3b71f292f567d6f544f5`.
- Final applied-row ledger SHA-256: `beb8a753393a14614b0b2c57d7f6357fd39797decb11bb01819b98213efd6fae` (202 rows; the 82 payload rows explicitly record completed quorum/release).
- Approved catalog SHA-256: `ab2350759c9bbeda8d637442ef756b3e28229b1bebae8d76e95ec31c655fa749`.
- Content-evidence SHA-256: `5881d944f34f94b6eb1721a029128058659a81fe4f0df01db8039f248a15db64`.

The 202 scope rows partition as **82 payloads, 119 preserved Site Overrides,
and 1 technical exception**. A1/A2/A3 evidence binds the exact scope and
proposal hashes. The 82 released catalog entries and 82 decision records match
the exact reviewed Arabic content; every decision records all three review
verdicts and binds the content-evidence hash. Scope, proposal, and applied-row
order match. Final LF-normalized proposal hash was rechecked by A1, A2, and A3;
the prior CRLF hash is reproducible by converting line endings only, with no
translation or row change. Applied-ledger payload rationales explicitly record
quorum PASS and release, with no pending-quorum language remaining.

Read-only final verification: catalog/decisions **3,326** rows; post-import
DRY `3326/0/0/3326`, drift `0`; health flags clear; UAT PASS with 13,628 Arabic
boot messages and logged-out cleanup; browser payload **82/82 exact**, `ar`
and RTL DOM confirmed; standalone **92/92** and module suite **271/271**;
scoped/lint/vendor checks pass; sync `created=0, updated=0`; inventory
`21,743` rows, Merkle `ed69ebe56d9861caedc0312bfa547b568a7f356f8742a7af9628df39214b6998`,
LIVE_MATCH.

All ten evidence-envelope hashes and all indexed artifact hashes match the
live files. The evidence-inclusive localization gate exits **0** (`errors=0`,
`csv_rows=3326`) on this candidate HEAD. Non-blocking browser note: Socket.IO
polling errors occurred in the browser transport; Arabic boot content, RTL
DOM, and all 82 translation assertions passed. No AI-R blockers. Production
and Stage 8 were not accessed.
