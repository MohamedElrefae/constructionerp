# Final Read-Only Bundle Verification: W6-1 Accounts Batch 04 (v16.localhost)
**Reviewer:** Subagent AI-R (Independent Read-Only Verification Auditor)
**Target Environment:** `v16.localhost`
**Governed Scope:** Stage 6 — W6-1 Accounts Batch 04
**Mode:** Strictly Read-Only (Zero Mutations, Zero Site Writes)
**Formal Verdict:** **PASS**

---

### Executive Summary

Independent subagent **AI-R** has completed the rigorous read-only cryptographic, invariant, quorum, partition, and envelope bundle verification for the governed **W6-1 Accounts Batch 04** cycle on `v16.localhost`.

All 15 target artifacts, checksums, row alignments, quorum approvals, browser runtime regressions, freshness metrics, inventory merkle trees, and localization gate outputs have been inspected and confirmed to strictly match the expected governed specifications.

---

### Verification Summary Table

| Check # | Target Artifact / Dimension | Expected Specification | Verified Evidence / Value | Status |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **Scope CSV** (`stage6_w601_accounts_batch04_rows_2026-09-27.csv`) | SHA: `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30`<br>Rows: 250 | SHA: `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30`<br>Rows: 250 | **PASS** |
| **2** | **Proposal CSV** (`stage6_w601_accounts_batch04_proposal_2026-09-27.csv`) | SHA: `4c72e83b3d41476914dcf884a8798c51ec5f6e662500105509fc2b8aad6bc47a`<br>Rows: 250 | SHA: `4c72e83b3d41476914dcf884a8798c51ec5f6e662500105509fc2b8aad6bc47a`<br>Rows: 250 | **PASS** |
| **3** | **Review Quorum Records** (`AI-A1`, `AI-A2`, `AI-A3`) | AI-A1, AI-A2, AI-A3 evidence records present in `docs/ai/work-items/scope-context-portability/evidence/` with verdict `PASS` | `stage6-w601-ai-a1-accounts-batch04-2026-09-27.md`: **PASS**<br>`stage6-w601-ai-a2-accounts-batch04-2026-09-27.md`: **PASS**<br>`stage6-w601-ai-a3-accounts-batch04-2026-09-27.md`: **PASS** | **PASS** |
| **4** | **Applied Payload CSV** (`stage6_w601_accounts_batch04_payload_applied_rows_2026-09-27.csv`) | 250 rows:<br>- 125 preserved-site-override<br>- 3 preserved-site-override strip-collisions<br>- 1 `EXCEPTION-technical` (`Rgt`)<br>- 121 quorum-confirmed payload released | Total rows: 250<br>- preserved-site-override: 125<br>- strip-collision overrides: 3 (`Role Allowed to Over Bill `, `Sales Partner `, `Select Dispatch Address `)<br>- EXCEPTION-technical: 1 (`Rgt`)<br>- quorum-confirmed payload: 121 | **PASS** |
| **5** | **Released List TXT** (`stage6_w601_accounts_batch04_released_list_2026-09-27.txt`) | Rows: 121 | Rows: 121 | **PASS** |
| **6** | **Content Evidence TXT** (`stage6_w601_accounts_batch04_content_evidence_2026-09-27.txt`) | Rows: 121 tab-delimited pairs | Rows: 121 tab-delimited pairs | **PASS** |
| **7** | **Released Catalog CSV** (`construction/data/translations/approved_ar_overrides.csv`) | Rows: 3,790 Released data rows | Rows: 3,790 Released data rows (lines 2–3791) | **PASS** |
| **8** | **Release Decisions JSON** (`construction/data/translations/release_decisions.json`) | Decisions: 3,790 decisions<br>SHA: `4b48e46c6da87c9f50eb4ea3739060d4e0d1a3a0999e7a2ac6615a11d490fecc` | Decisions: 3,790 decisions<br>SHA: `4b48e46c6da87c9f50eb4ea3739060d4e0d1a3a0999e7a2ac6615a11d490fecc` | **PASS** |
| **9** | **Freshness Evidence** (`construction/data/localization/freshness_evidence.json`) | packaged_rows: 3790<br>critical_pass: true<br>has_drift: false<br>payload_csv_sha: `89e09b42...` | packaged_rows: 3790<br>critical_pass: true<br>has_drift: false<br>payload_csv_sha: `89e09b42b43e3d965824ce6523c0fdd7677f6ff2b917f137748242f8b76152e0` | **PASS** |
| **10** | **Localization Manifest** (`construction/data/localization/localization_manifest.json`) | packaged_rows: 3790<br>inventory_rows: 22,207<br>payload_csv_sha: `89e09b42...`<br>decisions_sha: `4b48e46c...` | packaged_rows: 3790<br>inventory_rows: 22207<br>payload_csv_sha: `89e09b42b43e3d965824ce6523c0fdd7677f6ff2b917f137748242f8b76152e0`<br>decisions_sha: `4b48e46c6da87c9f50eb4ea3739060d4e0d1a3a0999e7a2ac6615a11d490fecc` | **PASS** |
| **11** | **Inventory Manifest** (`construction/data/localization/stage2_inventory_manifest.json`) | rows: 22,207<br>Merkle root: `a6432de6a030b2bf4883b721a9a515d9a12bf526764461307c53de235db332cb`<br>base_commit: `84919dd4ff11ed31b604ba43d1770d51405b4841` | rows: 22207 (2678 + 832 + 10683 + 8014)<br>Merkle root: `a6432de6a030b2bf4883b721a9a515d9a12bf526764461307c53de235db332cb`<br>base_commit: `84919dd4ff11ed31b604ba43d1770d51405b4841` | **PASS** |
| **12** | **Evidence Index** (`raw-logs/stage2/index.txt`) | Pins pre-commit candidate HEAD `84919dd4ff11ed31b604ba43d1770d51405b4841` | CANDIDATE_HEAD: `84919dd4ff11ed31b604ba43d1770d51405b4841`<br>EXIT_CODE: 0 | **PASS** |
| **13** | **Stage 2 Envelopes Integrity** (`raw-logs/stage2/`) | All 10 envelopes present and matching `index.txt` hashes | 10 envelopes verified matching `index.txt`:<br>- `all-tests.txt`<br>- `final-dryrun.txt`<br>- `freshness-envelope.txt`<br>- `full-gate.txt`<br>- `gate-tests-standalone.txt`<br>- `lints-diffcheck.txt`<br>- `merkle.txt`<br>- `scoped-gate.txt`<br>- `sync.txt`<br>- `vendor-audit.txt` | **PASS** |
| **14** | **Browser Runtime Evidence** (`browser_evidence_w601_batch04.json`) | 8/8 checks PASS<br>121/121 released payload matched<br>249/249 batch keys matched | 8/8 checks PASS (pass: 8, fail: 0)<br>released payload: matched 121, total 121<br>batch keys: matched 249, total 249 | **PASS** |
| **15** | **Localization Gates Execution** (`scripts/check_localization_gates.py`) | Exit code 0, errors=0 | `checked={"construction/locale/ar.po": 810, "csv_rows": 3790, "extract": {"files": 265, "json_labels": 22, "missing": 0, "wrapped": 667}, "raw_text": {"files": 7, "missing": 0, "texts": 2}} errors=0`<br>EXIT_CODE: 0 | **PASS** |

---

### Detailed Findings

1. **Partitioning & Boundary Rigor:**
   - The batch scope of 250 rows strictly partitions into:
     - **125 `preserved-site-override`**: Verbatim preservation of existing live site overrides on `v16.localhost`, protecting site customizations.
     - **3 `preserved-site-override (strip-collision)`**: Row 35 (`Role Allowed to Over Bill `), Row 82 (`Sales Partner `), and Row 93 (`Select Dispatch Address `) correctly reclassified per Plan §12 to prevent strip collisions with live runtime site overrides.
     - **1 `EXCEPTION-technical`**: Row 33 (`Rgt`) correctly exempted as a developer column label for NestedSet right-bound tree indexing, left untranslated.
     - **121 `quorum-confirmed-payload`**: Quorum-approved candidate translations released under release version `1.14` with domain `accounts`.
   - Identity holds: 125 + 3 + 1 + 121 = 250.

2. **Quorum Reviewer Alignment:**
   - All three reviewers (`AI-A1`, `AI-A2`, `AI-A3`) conducted independent read-only assessments, recorded zero regressions, zero placeholder mismatches, zero whitespace anomalies, and published unanimous `PASS` verdicts with full verification tokens.

3. **Runtime & Live Verification:**
   - Automated browser verification on `v16.localhost` confirmed 8 out of 8 checks passed with 100% key resolution in Arabic UI mode, no console errors, and clean logout.
   - Freshness evidence confirms zero drift (`has_drift: false`), active database key digest constraints, and strict critical keys alignment.

---

### Final Verdict

**FINAL VERDICT: PASS**

The W6-1 Accounts Batch 04 cycle on `v16.localhost` meets all architectural, governance, cryptographic, linguistic, domain, and localization gate requirements. Ready for final cycle closure.
