# Construction ERP — GM Release Readiness Update

**From:** General Manager
**To:** Company Owner, Development Lead, QA
**Date:** 2026-06-20
**Subject:** Tag/branch mismatch and local worktree divergence before final sign-off

---

## 0. Resolution (added after follow-up work)

**All release-process blockers described in this document are now resolved.**

| Blocker | Resolution | Verified |
|---------|------------|----------|
| `rc-1.1` tag pointed to `1f3707a` instead of final commit | Tag moved to `afc0b7f`; remote tag dereferences to `afc0b7f` | ✅ Verified |
| Main worktree not aligned with pushed release | Worktree reset to `feat/scope-context-option-a-plus-clean` at `afc0b7f`; upstream set to `origin/feat/scope-context-option-a-plus-clean` | ✅ Verified |
| Main worktree had untracked files | Preserved via backup branch `backup/main-worktree-2026-06-20` (`dce164e`) and external archive `/tmp/construction-main-worktree-backup-2026-06-20` (~62M) | ✅ Verified |
| Local verification blocked by dirty state | `bench migrate` completed; backend tests 50/50 pass; Node tests 31/31 pass; 10-report UAT passes with zero 403s | ✅ Verified |
| CI/lint status on final commit | GitHub Actions CI run `201` success; Linters run `24` success | ✅ Verified |

**GM decision:** Release `rc-1.1` on commit `afc0b7f` is approved for production and client handoff. See `docs/GM_SIGN_OFF_CERTIFICATE.md` for the formal release authorization.

---

## 1. What changed since the last report

The development team pushed the release branch to GitHub. However, verification of the local state has revealed two issues that must be resolved before the GM can sign off:

### Issue A: The `rc-1.1` tag is behind the final commit

| Reference | Commit | Notes |
|-----------|--------|-------|
| `rc-1.1` tag | `1f3707a` | Tagged before CI cleanup |
| CI cleanup commit | `7f69932` | Formatter/linter fixes |
| Final branch HEAD | `afc0b7f` | Semgrep fix — the actual final state |

The diff between `rc-1.1` (`1f3707a`) and HEAD (`afc0b7f`) is **only formatting and lint fixes** — no functional security changes. The Option B bypass logic, allowlist, and P0 regression test are unchanged. However, the tag does not represent the final validated state.

### Issue B: The local bench worktree is not aligned with the pushed branch

| Location | `scope_report.py` state | Status |
|----------|-------------------------|--------|
| GitHub branch `feat/scope-context-option-a-plus-clean` | `afc0b7f` | ✅ Final state |
| Clean worktree `/tmp/option-a-plus-clean` | `afc0b7f` | ✅ Matches GitHub |
| Main worktree `/home/mohamed/frappe-bench/apps/construction` | `b891518` (older) | ⚠️ **Out of sync** |

The local bench loads from the main worktree, which is dirty and behind the pushed branch. Attempting to run tests against the local bench fails with:

```
Failed to discover tests for construction.tests.test_option_a_plus:
cannot import name 'get_scope_dimension_permissions'
from 'construction.api.scope_context_api'
```

This is because the main worktree's `scope_context_api.py` is missing a function that exists in the clean/pushed branch.

---

## 2. Why this matters

- **The earlier UAT I reported ran against the local dirty main worktree** (`b891518` era), not the final pushed commit (`afc0b7f`).
- **The local bench cannot be used for final verification** until the main worktree is reset to match the pushed branch.
- **Production deployment must use the GitHub state** (`afc0b7f`), not the local main worktree.
- The `rc-1.1` tag needs to be moved or a new tag created so that the release marker points to the actual final commit.

---

## 3. Required actions before GM sign-off

| # | Action | Owner | Priority |
|---|--------|-------|----------|
| 1 | **Move the `rc-1.1` tag to `afc0b7f`** OR create a new tag (`rc-1.2`) on `afc0b7f` and push it to GitHub | Development Lead | **P0** |
| 2 | **Reset/clean the local main worktree** (`/home/mohamed/frappe-bench/apps/construction`) to match `afc0b7f` from GitHub | Development Lead | **P0** |
| 3 | **Re-run verification** (backend 50 tests, Node 31 tests, restricted-user UAT) on the aligned local bench | QA + Development | **P0** |
| 4 | Confirm GitHub Actions CI passed on `afc0b7f` (if CI is the authoritative verification) | Development Lead | P1 |
| 5 | Document the final release commit SHA and tag in the release notes | Development Lead | P1 |

---

## 4. Exact commands for the development lead

```bash
# 1. Update the local clean worktree to match remote
cd /tmp/option-a-plus-clean
git fetch origin
git log --oneline -1 origin/feat/scope-context-option-a-plus-clean
# Should show afc0b7f

# 2. Move the rc-1.1 tag to the final commit and force-push the tag
git tag -d rc-1.1
git tag -a rc-1.1 -m "Construction ERP release candidate 1.1 - final state afc0b7f"
git push origin --delete rc-1.1
git push origin rc-1.1

# OR create a new tag instead:
# git tag -a rc-1.2 afc0b7f -m "Construction ERP release candidate 1.2"
# git push origin rc-1.2

# 3. Reset the main worktree to the final pushed state
cd /home/mohamed/frappe-bench/apps/construction
git fetch origin
git checkout -B feat/scope-context-option-a-plus-clean origin/feat/scope-context-option-a-plus-clean
# WARNING: this will discard uncommitted changes in the main worktree.
# Stash or commit anything that must be preserved first.

# 4. Run bench migrate to align the database/schema
bench --site v16.localhost migrate

# 5. Re-run verification
bench --site v16.localhost run-tests --module construction.tests.test_option_a_plus
node construction/tests/test_scope_context_report_filters.js
node /tmp/opencode/test_option_b_uat.js
```

---

## 5. GM recommendation

**Do not sign off on `rc-1.1` as it currently stands** because it points to `1f3707a`, not the final `afc0b7f`.

**Approve the release once:**
1. The tag is moved to `afc0b7f` (or `rc-1.2` is created on `afc0b7f`),
2. The local main worktree is reset to `afc0b7f`,
3. And verification tests pass on the aligned local bench (or GitHub Actions CI on `afc0b7f` is confirmed green).

The product itself is still functionally ready. These are release-process and environment-hygiene blockers, not product defects. But they are real blockers — releasing from a tag that does not match the final commit, or deploying from a dirty local worktree, is not acceptable.

---

## 6. Impact on client timeline

| Scenario | Impact |
|----------|--------|
| Tag moved and local worktree aligned today | Client handoff can proceed as planned |
| Tag not moved | Risk that deployment uses the wrong commit; GM cannot sign off |
| Local worktree not aligned | Cannot validate the actual release commit on this machine; deployment risk |

Assuming the development lead acts within 24 hours, there is no material delay to the client release.

---

## 7. Supporting documents

- `docs/GM_STATUS_REPORT_TO_OWNER.md` — original status report
- `docs/CONSULTANT_REVIEW_PART_1_MANAGER.md` — non-technical review
- `docs/CONSULTANT_REVIEW_PART_2_TECHNICAL.md` — technical evidence (note: verification there ran against the earlier aligned state)
- `docs/GM_RECOMMENDATION_EXECUTION_PLAN.md` — release execution plan (must be updated after this issue is resolved)

---

*Prepared by: General Manager*
*Date: 2026-06-20*
