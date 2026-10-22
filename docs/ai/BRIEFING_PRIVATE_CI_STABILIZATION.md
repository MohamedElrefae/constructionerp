# Briefing: Private CI Stabilization & Remote Fixture Validation (Session 3)

**Target Location:** `/home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes`  
**Publication Checkout:** `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/private-ci-20261005/repo`  
**Target Repository:** Private GitHub repository `MohamedElrefae/constructionerp-private`  
**Target Branch:** `codex/customer-release-ci-20261005`  
**Authority:** Owner authorization for private CI in [`HANDOFF_2026-10-05_PRIVATE_CI.md`](/home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes/docs/ai/work-items/customer-release-gap-fixes/HANDOFF_2026-10-05_PRIVATE_CI.md).  
**Role:** Independent OpenCode Agent (CI Engineering & Remote Diagnosis)  
**Lead Verifier:** Antigravity (Lead Verifier Lane)

---

## 1. Objective

Resume the customer-release private CI qualification for `MohamedElrefae/constructionerp-private`:
1. Inspect the completed results of **GitHub Actions Run 8** (`37342111971`) on `codex/customer-release-ci-20261005`.
2. Diagnose and address any remaining test failures or fixture requirements (e.g. synthetic `Company` or `Fiscal Year` fixtures required by the 17 business test modules in the headless CI container).
3. Ensure all Python test modules run and achieve a passing CI run on the private repository.
4. Document full results and logs in the worktree.

---

## 2. Deliverables & Expected Files

Inside `/home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes/docs/ai/work-items/customer-release-gap-fixes/`:
1. `PRIVATE_CI_STATUS.md`: Complete audit of CI runs (Run 8 and any follow-up runs), root causes of module failures, fixture corrections, and passing status.
2. Updated `STATUS.md` and `VERIFICATION.md` reflecting actual provider test results.
3. Mirror any CI workflow / fixture commits in `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/private-ci-20261005/repo` and push ONLY to the authorized private repository `MohamedElrefae/constructionerp-private`.

---

## 3. Strict Invariants & Owner Confidentiality

1. **Owner Confidentiality Policy**:
   - The private repository `MohamedElrefae/constructionerp-private` is the ONLY authorized remote destination.
   - NEVER push to public repositories (`MohamedElrefae/constructionerp.git`), open PRs, or public branches.
   - Do NOT upload credentials, private reports, site backups, or customer site records.
2. **Byte Preservation of App Logic**:
   - Do NOT modify approved application logic or weaken test assertions merely to make CI pass.
   - CI adjustments are restricted to GitHub Actions workflow configuration (`.github/workflows/`), CI helpers (`.github/ci/`), and headless test fixtures.
3. **Local Commits**:
   - In all local checkouts, disable transmitting hooks per command:
     `git -c core.hooksPath=/dev/null commit -m '...'`
4. **Preserved Working Files**:
   - Preserve `SESSION_MEMORY.md` and `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`.

---

## 4. Execution Sequence

1. **Inspect Run 8 Outcome**:
   - Inspect job logs from GitHub Actions Run 8 (`37342111971`) / Job (`111871477488`).
   - Identify whether the synthetic company fixture succeeded and which Python modules failed.
2. **Diagnose Fixture Requirements**:
   - If modules fail due to missing `Company`, default `Warehouse`, or `Fiscal Year`, enhance `.github/ci/business_fixtures.py` with the required synthetic fixtures.
3. **Verify Locally / Push Clean Update**:
   - Verify workflow and script syntax locally:
     `python3 -m py_compile .github/ci/business_fixtures.py`
     `bash -n .github/workflows/*.yml`
   - Commit cleanly in the publication checkout (`/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/private-ci-20261005/repo`).
   - Push to `MohamedElrefae/constructionerp-private` on branch `codex/customer-release-ci-20261005`.
4. **Monitor & Document Provider Run**:
   - Capture the final provider run outcome, step durations, and module test outputs in `PRIVATE_CI_STATUS.md`.
5. **Handover**:
   - Provide summary of provider CI status to Antigravity.
