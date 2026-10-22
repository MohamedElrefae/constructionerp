# W6-6 CRM, Support & Maintenance — governed cycle closed (2026-09-24)

## Scope and review

The owner-authorized corrected continuation applied only to
`stage6_w606_crm_support_maintenance_rows_2026-09-24.csv` (119 rows;
SHA-256 `a77b43a908859c0aea3e2c58525ec3765772c09af8617f1f17fb8c8bf12833f9`)
on the non-production test site `v16.localhost`. The corrected proposal is
`stage6_w606_crm_support_maintenance_proposal_2026-09-24.csv` with the
repository-normalized LF SHA-256
`d8a2a8df2c040434b82d4d813f96e510e454b0f11114a31cf709db62bf60f266`.
The reviewed CRLF bytes had SHA-256
`3d80277b516663b00f2240ed2d9476eef7eeb62803df867dbd029d74f0dcd354`; translation
content is identical. Independent renewed A1/A2/A3 reviews and final AI-R PASS
are bound to these hashes. The original 42-payload proposal and its expected
total of 3,368 were superseded by this corrected bundle.

| Disposition | Rows | Result |
| --- | ---: | --- |
| Released payload | 38 | Imported as CRM Support Maintenance release v1.10 |
| Preserved Site Override | 76 | Left unchanged; not imported |
| Deferred source defect | 4 | Withheld; empty translation retained |
| Technical exception | 1 | `fieldname`; empty translation retained |
| **Total** | **119** | **38 + 76 + 4 + 1** |

Quote-containing Arabic provenance is bound to
`stage6_w606_crm_support_maintenance_content_evidence_2026-09-24.txt`
(SHA-256 `0dac6864f3e67bd774cab92930046148cc3befae9926ea7db9e8e128e13dab9e`).
The final applied-row ledger SHA-256 is
`69006c070a38c9090b94ff8996fb395803a61eaf17c5ae755738941c46618487`.

## Test-site execution and verification

- Import: **38 created**, 0 updated; 76 preserved overrides, four deferred
  source defects, and one technical exception were not imported.
- Post-import dry-run: `total=3364 created=0 updated=0 skipped=3364 drift=0`.
- Catalog sync: 0 created, 0 updated.
- Catalog and release decisions: **3,364/3,364**; catalog SHA
  `ad737758756dca0d69b83ff89d05908eb18df52a0d58afb889cef9f59253e080` and
  decisions SHA `84a6a078f6ef1c5f96b097f6487633178681ed16c1354d2dae1f4efeef89f844`.
- Applied-row ledger SHA-256:
  `69006c070a38c9090b94ff8996fb395803a61eaf17c5ae755738941c46618487`.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar`
  boot with 13,666 messages, representative key, and session logout.
- Browser evidence: **9/9 PASS**; all **114/114** payload-plus-preserved
  translations matched exactly in the live Arabic session, the five excluded
  rows were absent, Arabic DOM rendering was present, and no page errors were
  recorded.
- Tests: standalone **92/92**, module suite **271/271**.
- Scoped gate, vendor audit, translation/scope lints, diff check, and the full
  evidence-inclusive localization gate: PASS; `errors=0`, `csv_rows=3364`.
- Freshness: packaged rows **3,364**, `critical_pass=true`,
  `has_drift=false`, runtime digest
  `a9fa30af935ca26c94c1bb277c25901443f911984f7303d8a8fde3f9ce13d579`.
- Inventory: **21,781 rows**, Merkle root
  `f1d00e38582fd5604b11355b744376b408f100a74ba376d59ce276d7f1c2e4e1`; inventory
  manifest SHA `842c0b6c882234e787396c83854477a38e9e79cede5b61aaea221c98b5045345` and
  localization manifest SHA `1d72c13adededa2516749cad73e9152dc1185ae6dd2f38a0fa383a24ecc701ff`.
- Ten Stage-2 evidence envelopes and the index were assembled against
  pre-commit HEAD `ea553f2`; all artifact bindings validate. The established
  post-commit evidence-index HEAD mismatch is expected after closure.
- Final independent AI-R: **PASS**; report:
  `docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-r-crm-support-maintenance-final-2026-09-24.md`.

## Teardown and boundaries

UAT Administrator language was restored to `en` and the temporary credential
was rotated. No browser operation was performed after teardown. Only
`v16.localhost` was used; production and Stage 8 were not accessed or
authorized. No push was performed. The untracked `v16.localhost/` app-root
log directory remains untouched and unstaged.
