# Construction ERP - GM Recommendation Execution Plan

**Owner:** General Manager  
**Audience:** Development, QA, Product, Sales, and Operations  
**Purpose:** Execute the GM recommendations from the owner report in a clear, end-to-end sequence before and after release.

---

## 1. Objective

Turn the GM recommendations into a practical release plan that the team can execute without ambiguity.

This plan covers:

- the final release step,
- post-push verification,
- client handoff,
- manual user testing readiness,
- and the next-sprint follow-up items.

---

## 2. Source of Truth

This plan is based on:

- `docs/GM_STATUS_REPORT_TO_OWNER.md`
- the current branch state: `feat/scope-context-option-a-plus-clean`
- the release tag requirement: `rc-1.1`

If any conflict appears between this plan and the owner report, the owner report takes precedence.

---

## 3. Executive Summary

The team has already delivered the agreed product scope and cleared the technical blockers.

The only release-blocking action is administrative:

- push the finished branch to GitHub,
- tag the release as `rc-1.1`,
- then re-run verification on the pushed state.

After that, the team can proceed with client-facing release steps and manual user testing.

---

## 4. Roles and Ownership

| Area | Owner | Responsibility |
|------|-------|-----------------|
| Release admin | Development Lead / Operator | Push branch, create tag, confirm remote state |
| Verification | QA + Development | Re-run targeted checks after push/tag |
| GM signoff | General Manager | Confirm release readiness and approve handoff |
| Client communication | Product / Sales / GM | Share release notes and walkthrough plan |
| Manual user testing | QA + Client users | Execute UAT against the tagged release |
| Post-release cleanup | Development Lead | Handle next-sprint housekeeping items |

---

## 5. Release Execution Plan

### Phase 1 - Final Release Admin Step ✅ COMPLETE

**Goal:** Make the reviewed code available in GitHub and lock the release marker.

**Completed on:** 2026-06-20
**Final state:** Branch `feat/scope-context-option-a-plus-clean` pushed; tag `rc-1.1` moved to and dereferences to commit `afc0b7f`.

#### Tasks

1. Push `feat/scope-context-option-a-plus-clean` to GitHub.
2. Create tag `rc-1.1` on the final reviewed commit.
3. Confirm the remote branch and tag exist on GitHub.
4. Record the final commit SHA in the release notes.

#### Exact commands

```bash
cd /tmp/option-a-plus-clean

# 1. Push the clean branch
git push -u origin feat/scope-context-option-a-plus-clean

# 2. Tag the release on the actual final commit (verify HEAD first)
git log --oneline -1 HEAD
# Should show the final reviewed commit (e.g., afc0b7f)

git tag -a rc-1.1 -m "Construction ERP release candidate 1.1"

# 3. Push the tag
git push origin rc-1.1

# 4. Verify remote state
git ls-remote --tags origin rc-1.1
git ls-remote --heads origin feat/scope-context-option-a-plus-clean
```

#### Important: verify the tag target

After pushing, confirm that the tag points to the **actual final commit** on the branch, not an earlier commit. If later CI/lint fixes are added after the tag, the tag must be moved or a new tag created.

```bash
# Local tag target
git log --oneline -1 rc-1.1

# Remote branch tip
git log --oneline -1 origin/feat/scope-context-option-a-plus-clean

# These should match. If they do not, retag:
# git tag -d rc-1.1
# git tag -a rc-1.1 -m "..."
# git push origin --delete rc-1.1
# git push origin rc-1.1
```

#### Acceptance criteria

- The branch exists on the remote.
- The tag `rc-1.1` exists on the remote.
- The tagged commit matches the final reviewed commit.
- Remote branch and release tag available for deployment and audit.

#### Output

- Remote branch and release tag available for deployment and audit.

---

.

### Phase 1b — Align Local Bench Worktree with the Pushed Release ✅ COMPLETE

**Goal:** Ensure the local bench (`/home/mohamed/frappe-bench/apps/construction`) runs the same code that was pushed to GitHub, not an older or dirty state.

**Completed on:** 2026-06-20
**Final state:** Main worktree reset to `feat/scope-context-option-a-plus-clean` at `afc0b7f`; upstream aligned; broader-app work preserved in backup branch `backup/main-worktree-2026-06-20` (`dce164e`) and archive `/tmp/construction-main-worktree-backup-2026-06-20`; `bench migrate` completed successfully.

**Background:** The local bench loads code from the main worktree. If that worktree is dirty or behind the pushed branch, local tests and UAT will validate the wrong state.

#### Tasks

1. Check the current local main worktree commit vs. the pushed branch tip.
2. Stash or commit any truly separate work that must be preserved.
3. Reset the main worktree to match `origin/feat/scope-context-option-a-plus-clean`.
4. Run `bench migrate` to align the database/schema.

#### Exact commands

```bash
cd /home/mohamed/frappe-bench/apps/construction

# 1. Check divergence
git log --oneline -1 HEAD
git log --oneline -1 origin/feat/scope-context-option-a-plus-clean

# 2. If they differ, save anything that must be preserved, then reset
git stash push -m "pre-release-local-work"
git fetch origin
git checkout -B feat/scope-context-option-a-plus-clean origin/feat/scope-context-option-a-plus-clean

# 3. Align the site
cd /home/mohamed/frappe-bench
bench --site v16.localhost migrate
```

#### Acceptance criteria

- `git log --oneline -1 HEAD` in the main worktree matches the pushed branch tip.
- `git status --short` is clean (or any remaining dirty files are explicitly documented and accepted).
- `bench migrate` completes without errors.

#### Output

- Local bench is aligned with the pushed release and ready for verification.

---

### Phase 2 - Verification After Push ✅ COMPLETE

**Goal:** Confirm the pushed release still passes the same quality gates.

**Completed on:** 2026-06-20
**Final results:**
- Backend tests: 50/50 passed
- Node report-filter tests: 31/31 passed
- Restricted-user UAT: 10/10 installed allowlisted reports passed with zero 403s (Project-wise Profitability 404 because not installed)
- GitHub Actions CI run `201`: success
- GitHub Actions Linters run `24`: success

#### Tasks

1. Re-run the relevant backend tests on the pushed state.
2. Re-run the relevant frontend tests on the pushed state.
3. Run the code linter if available in the environment (`ruff check construction/overrides/scope_report.py construction/tests/test_option_a_plus.py`).
4. Validate that no new conflicts or formatting drift were introduced during release admin work.
5. Confirm the `rc-1.1` tag points to the same commit SHA that was reviewed.

#### Exact verification commands

```bash
# 1. Backend tests (the same 50 tests that passed in review)
bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus

# 2. Frontend/Node tests (the same 31 tests that passed in review)
node construction/tests/test_scope_context_report_filters.js

# 3. Restricted-user report UAT (the same 10-report UAT that passed in review)
node /tmp/opencode/test_option_b_uat.js

# 4. Linter (if ruff is installed in the bench env)
ruff check construction/overrides/scope_report.py construction/tests/test_option_a_plus.py
```

> Note: During the consultant review, ruff was not installed in the review environment, so the "clean" result was reported by the prior development session. Re-run it on the pushed state if the environment supports it.

#### Acceptance criteria

- 50/50 backend tests pass on the final pushed state.
- 31/31 frontend tests pass on the final pushed state.
- 10/10 restricted-user UAT reports load with zero 403s.
- Linter is clean (if run).
- No new regressions appear after tagging.

#### Output

- Verification record attached to the release.

---

### Phase 3 - GM Signoff

**Goal:** Provide a clear management decision before client release.

#### Tasks

1. Review the verification results.
2. Confirm the remaining items are non-blocking.
3. Confirm the release note language is owner-safe and client-safe.
4. Approve the release for client handoff.

#### Acceptance criteria

- GM confirms there are no unresolved release blockers.
- GM approves the release package for handoff.

#### Output

- Formal GM approval for production/client release.

---

### Phase 4 - Client Handoff

**Goal:** Give the client a complete and understandable release package.

#### Tasks

1. Share the user guide.
2. Share the release summary and key capabilities.
3. Explain the known limitations clearly.
4. Explain what changed in Option A+ and Option B v3.
5. Confirm the client knows how manual user testing will be conducted.

#### Acceptance criteria

- Client receives the release package.
- Client understands the scope, limitations, and testing plan.
- There is no ambiguity about what is included in this release.

#### Output

- Client-ready handoff packet.

---

### Phase 5 - Manual User Testing

**Goal:** Prove the release works in the intended client workflow.

#### Tasks

1. Run the defined UAT checklist.
2. Verify restricted-user report access.
3. Confirm BOQ, scope, variation order, and theme behavior remain correct.
4. Capture any client feedback.
5. Record pass/fail results against the tagged release.

#### Acceptance criteria

- UAT completes against `rc-1.1`.
- No blocking defects are found.
- Any minor issues are documented and routed correctly.

#### Output

- UAT signoff or a tracked follow-up list.

---

## 6. Recommended Execution Order

Use this sequence to avoid confusion:

1. Push branch to GitHub.
2. Create release tag `rc-1.1`.
3. Verify remote branch and tag.
4. Re-run quality checks.
5. Obtain GM signoff.
6. Send client handoff package.
7. Run manual user testing.
8. Collect signoff or follow-up items.
9. Move post-release items into the next sprint.

---

## 7. Manual Testing Readiness Checklist

Before manual testing starts, confirm:

- The final branch push is visible on GitHub.
- The tag `rc-1.1` is present.
- The tested commit matches the release note.
- The user guide is the latest version.
- Known limitations are written in plain language.
- The testing owner knows what success looks like.

Manual testing should not start if any of the above are unclear.

---

## 8. Post-Release Follow-Up

These items are not blockers for release, but they should be planned next:

1. Audit and commit the broader main-worktree cleanup items.
2. Remove or convert `scratch_test.py`.
3. Convert or update the remaining handover documents.
4. Gate VFC diagnostic logging behind a debug flag.
5. Install Project-wise Profitability if the client needs it.
6. Add an Admin Settings toggle for Option B.
7. Add audit logging for restricted-user report access.

---

## 9. Risks and Controls

| Risk | Control |
|------|---------|
| Release tag not pushed | Confirm remote branch and tag before handoff |
| Client confusion about scope | Use the GM report and user guide as the only source of truth |
| Manual testing starts too early | Enforce the readiness checklist before UAT |
| Minor non-blocking issues get treated as blockers | Separate release blockers from post-release maintenance |

---

## 10. Definition of Done

This plan is complete when all of the following are true:

- the branch is pushed,
- `rc-1.1` is tagged,
- verification passes on the pushed state,
- the GM approves release,
- the client receives the handoff package,
- manual user testing is executed,
- and post-release items are entered into the next sprint.

---

## 11. Owner Instruction

Do not start client-facing manual testing until the release tag and verification record are complete.

Do not treat the post-release housekeeping items as blockers for the current release.

Treat this document as the team execution guide for the GM recommendations.
