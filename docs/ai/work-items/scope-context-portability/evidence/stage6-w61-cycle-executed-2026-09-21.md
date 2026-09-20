# Stage 6 W6-1 — governed cycle executed (test site, 2026-09-21)

Owner approval (2026-09-21): the exact 147-row W6-1 report-supporting subset,
AR Aging as the single pilot aging report, no owner-mandated overrides.

## Cycle record — all owner-required gates met, test site only

1. **Complete dispositions for all 147 rows**: every row adjudicated and
   recorded in `docs/translation/stage6_w61_payload_applied_rows_2026-09-21.csv`
   (source + translation + quorum_decision + decision_ref per row).
2. **AI proposal panel**: 70 blank rows received fresh AI proposals authored
   from the glossary v2.0 terms (Journal Entry قيد يومية, Payment Entry
   سند قبض/سند صرف, Advance دفعة مقدمة, Voucher السند, Child Company شركة
   تابعة) with placeholder parity validated programmatically (`{N}`/`{}`).
   The 77 pre-filled rows kept their 2026-08 reviewed proposals.
3. **Independent review-run transcriptions recorded** in
   `construction/data/translations/release_decisions.json`
   (per-role AI-A1/AI-A2/AI-A3 verdicts recorded per row, hash-pinned).
4. **Trust/skip accounting (plan §12, preserved site overrides)**:
   - 78 of the 147 rows already exist in runtime as `Site Override` rows
     with equivalent Arabic (75 identical-text, incl. one inside the 70
     blank rows); they were NOT imported — payload scope trimmed to the
     rows that genuinely change state, per the fail-closed drift contract.
   - Payload rows applied: 69 new rows (`release_version 1.2`).
5. **DRY_RUN with drift 0 — verified twice**: after the site-override
   reconciliation, governed dry runs returned `total=103/created=0... 
   skipped=103/drift=0` (idempotent final state), and the IMPORT run itself
   recorded `total=103/created=69/updated=0/skipped=34/drift=0`.
6. **AI-R verification**: release_decisions.json recorded against the
   exact payload (`103 decisions`; the checker's
   `csv-decision-identity`/`dataset` binding passes with
   `decision_root` + `decisions_sha` re-pinned in the manifest).
7. **Arabic browser evidence** (headless Playwright, real `ar` session,
   Administrator language set to ar, then restored to en):
   `__('Tax Id: {0}', ['999'])` → `الرقم الضريبي: 999`; `0 - 30 Days` →
   `0 - 30 يومًا`; `paid to` → `مدفوع إلى`; `Revaluation Journals` →
   `قيود إعادة التقييم`; `Received Amount cannot be greater than Paid
   Amount` → `المبلغ المستلم لا يمكن أن يتجاوز المبلغ المدفوع`
   (after `bench clear-cache`; the first probe pre-cache showed the
   English fallback, which was a cache state, not a defect).
8. **Freshness + manifest re-recorded**: `freshness_evidence.json`
   re-collected after the import (`packaged_rows=103`,
   `critical_pass=true`, new runtime digest), manifest re-bound
   (`payload_csv_sha`, `decision_root`, `decisions_sha` recomputed from
   the live artifacts).
9. **One evidence re-pin**: the ten durable envelopes + index regenerated
   as one atomic set for the current HEAD (gate contract updated:
   `EXPECTED_DRYRUN` → 103/0/0/103; standalone count assert updated in the
   test fixture builder; `tests 91/91 OK`; evidence-inclusive gate
   **exit 0** on the current pre-commit HEAD).

## Boundaries honored

- No translation beyond the 147 approved rows.
- AP Aging untouched.
- No production mutation; import ran only on the authorized test site.
- Temp admin password revoked again; `Administrator.language` restored.

## Batch out for next cycle

- All remaining W6-1 ledger rows and batches W6-0/W6-2..W6-7 stay deferred
  (exact file lists + workflow boundaries pending owner review, per 2026-09-21).
