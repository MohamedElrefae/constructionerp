# Construction ERP — GM Release Sign-Off Certificate

**Release:** `rc-1.1`
**Commit:** `afc0b7f`
**Branch:** `feat/scope-context-option-a-plus-clean`
**Repository:** `MohamedElrefae/constructionerp` on GitHub
**Sign-off date:** 2026-06-20
**Signed by:** General Manager

---

## Release authorization

The Construction ERP application is **approved for production deployment and client release** as of this certificate.

The release is identified by:

```
Tag:    rc-1.1
Commit: afc0b7f
Branch: feat/scope-context-option-a-plus-clean
```

---

## What is released

| Feature Area | Status |
|--------------|--------|
| Scope Context (Company → Cost Center → Project → Department) | Released |
| BOQ Header / BOQ Structure (WBS) / BOQ Item lifecycle | Released |
| BOQ Item Stage measurement tracking | Released |
| Cascade Blocker visual form guidance | Released |
| Transaction Grid Blocker (8 transaction DocTypes) | Released |
| Variation Orders + BOQ Quantity Revision | Released |
| BOQ Excel Import (preview mode by default) | Released |
| Modern theme system, RTL, Arabic localization | Released |
| Typography settings v21 | Released |
| Option A+ scope-context hardening | Released |
| Option B v3 restricted-user report access | Released |

---

## Verification evidence

| Check | Result | Evidence location |
|-------|--------|-------------------|
| Backend automated tests | 50/50 passed | `construction/tests/test_option_a_plus.py` |
| Frontend/Node tests | 31/31 passed | `construction/tests/test_scope_context_report_filters.js` |
| Restricted-user report UAT | 10/10 passed, zero 403s | `/tmp/opencode/test_option_b_uat.js` |
| GitHub Actions CI | Success (run `201`) | GitHub Actions |
| GitHub Actions Linters | Success (run `24`) | GitHub Actions |
| Local bench alignment | Clean, at `afc0b7f` | `/home/mohamed/frappe-bench/apps/construction` |
| `bench migrate` | Completed successfully | Site `v16.localhost` |

---

## Release-process confirmation

| Step | Status |
|------|--------|
| Branch pushed to GitHub | ✅ Complete |
| Tag `rc-1.1` points to `afc0b7f` on remote | ✅ Complete |
| Local main worktree aligned with pushed branch | ✅ Complete |
| Broader-app work preserved before reset | ✅ Complete — backup branch `backup/main-worktree-2026-06-20` (`dce164e`) and archive `/tmp/construction-main-worktree-backup-2026-06-20` |
| Verification re-run on aligned state | ✅ Complete |
| Release documentation committed and pushed | ✅ Complete — commit `5888446` (`docs: release documentation for rc-1.1`) |

**Final branch state:** `feat/scope-context-option-a-plus-clean` now points to `5888446`, which contains the release docs on top of the verified release commit `afc0b7f`. The `rc-1.1` tag remains on `afc0b7f`.

---

## Known limitations documented to client

1. Only 10 financial reports are scope-filtered; other ERPNext standard reports are not.
2. Local system fonts depend on the user's device; web fonts render reliably when Google Fonts is reachable.
3. BOQ Excel import is preview-only by default; record creation is admin-gated.
4. Collapsed grid rows show dimmed state only; full guidance appears on expand.
5. Project-wise Profitability report is not installed in the current database.

These limitations are documented in `docs/USER_GUIDE.md` v1.1 and `docs/CONSULTANT_REVIEW_PART_1_MANAGER.md`.

---

## Post-release follow-up items (next sprint)

These items are **not blockers** for `rc-1.1` but are scheduled for the next sprint:

1. Audit and integrate the preserved broader-app work from the backup branch/archive.
2. Remove or convert `scratch_test.py`.
3. Convert/update remaining handover documents.
4. Gate VFC diagnostic logging behind a debug flag.
5. Install Project-wise Profitability report if the client requires it.
6. Add an Admin Settings toggle for Option B.
7. Add audit logging for restricted-user report access.

---

## GM sign-off

I, as General Manager, confirm that:

- The release has been independently reviewed and tested.
- All release-process blockers are cleared.
- The code deployed to production must be taken from GitHub commit `afc0b7f` (tag `rc-1.1`).
- The client may now be given access to the release.

**Approved for production and client release.**

---

*General Manager*
*2026-06-20*

---

*Supporting documents:*
- `docs/USER_GUIDE.md` v1.1
- `docs/GM_STATUS_REPORT_TO_OWNER.md`
- `docs/GM_RELEASE_READINESS_UPDATE.md`
- `docs/CONSULTANT_REVIEW_PART_1_MANAGER.md`
- `docs/CONSULTANT_REVIEW_PART_2_TECHNICAL.md`
- `docs/GM_RECOMMENDATION_EXECUTION_PLAN.md`
- `docs/scope_context_option_b_acceptance.md`

*End of certificate.*
