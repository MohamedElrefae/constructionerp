# Stage 4 COMPLETE — STAGE_4_VERIFIED (2026-09-20)

**Work item:** erp-arabic-bilingual-data
**Final state:** `status=VERIFIED_FOR_RELEASE`, `sub_status=STAGE_4_VERIFIED`, no pending gate

## What completed

1. Independent proposal for all 81 accounts, applying the owner-mandated translations.
2. Independent panel ai-a1/ai-a2/ai-a3: **PASS/PASS/PASS**, exact coverage, distinct sessions.
3. Bundle + payload composed with panel provenance; independent verifier PASS (0 findings).
4. Owner-authorized read-only DRY_RUN: 81/81 live accounts, zero blocking findings.
5. Owner-authorized IMPORT: idempotent write of `account_name_ar`, English/identity
   invariants preserved, rollback export stored privately, post-import verifier PASS.

## Live post-import verification (non-production test site `v16.localhost`)

- Accounts with Arabic names: **81** (total 2097); blank English names: **0**.
- Mandated rows verified live:
  - `1410 - Stock In Hand - E` → `المخزون المحتفظ به`
  - `1650 - Securities and Deposits - E` → `التأمينات والودائع`
  - `1790 - CWIP Account - E` → `مشروعات تحت التنفيذ`
  - `2310 - TDS Payable - E` → `ضريبة الخصم من المنبع المستحقة`
  - `GST - E` → `ضريبة السلع والخدمات`

## Evidence

| Item | Value |
|---|---|
| dry_run_evidence_digest | `22101965dc317ee2ada82c860ad27bf7e38103a8cf69cbcdf58a1ac2c6bff4e5` |
| import_evidence_digest | `c226a753e982cd7b76956f1865bd39782ff418b5d43214f5b02f5506ecf63a15` |
| imported_values_sha256 | `de1ae70e96b92d53d2de9a77a9b9ae7fa58a59b39031d55d9b622537c26c6e8c` |
| rollback_export_sha256 | `d1c6fb42b975e076d58d0f9cb1e5a675213a0cc9d9052b37c86929300e580a1f` |
| post_import_readback_sha256 | `7681602f05e9ab3153f49dd805a62d7d9f02ade9fbd8c475cea4a204d2dc38fe` |

Rollback values (previous `account_name_ar`, all null on first import) remain in private
content-addressed storage; only the manifest hash is public.

## Boundary

This import targeted the declared **non-production test site**. No production ERP data was
touched. The production checkout was not modified. No commit, push, merge, or deployment
occurred. Full orchestrator suite: **236 passed**.
