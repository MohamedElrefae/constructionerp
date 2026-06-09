# EV-061 — Frappe Cloud Deployment Plan

Date: 2026-06-10

## 1. Target Environment

| Item | Value / Decision Needed |
|------|------------------------|
| **Bench / Team** | `construction-prod` *(confirm with Cloud admin)* |
| **Site name** | `construction-erp.frappe.cloud` *(confirm)* |
| **Deploy branch** | `develop` *(manager to confirm: `develop`, `main`, or `release/v6.8`)* |
| **Environment type** | Production *(staging deploy strongly recommended first)* |

## 2. Pre-Deploy Checklist

- [ ] Manager signs off on `EV-058` (security), `EV-059` (migration), `EV-060` (hygiene).
- [ ] Target site has a **fresh backup** (or is a greenfield deploy).
- [ ] Administrator password on target site is **not** the temp QA password.
- [ ] Feature flags are all `false` (default) — confirmed.
- [ ] Staging deploy completed and smoked (see Section 5).

## 3. Deploy Steps

### Step 1: Staging Deploy (Strongly Recommended)

1. Create a **staging site** on Frappe Cloud (e.g., `construction-staging.frappe.cloud`).
2. Deploy the `develop` branch to staging.
3. Run `bench migrate` on staging.
4. Execute post-deploy smoke (Section 4).
5. If smoke fails, **do not proceed to production**.

### Step 2: Production Deploy

1. Schedule deploy during **low-traffic window** (e.g., weekend evening).
2. Take a **final DB snapshot** before deploy.
3. Push/merge code to the agreed deploy branch.
4. Trigger Frappe Cloud deploy.
5. Monitor `bench migrate` output for errors.

### Step 3: Migration Timing Estimate

| Migration Phase | Estimated Time | Notes |
|-----------------|----------------|-------|
| DocType schema updates | 5–15 seconds | New fields on existing tables |
| `BOQ Import Batch` table creation | 2–5 seconds | Empty table, standard schema |
| `Variation Order` / `VO Line` table creation | 2–5 seconds | Empty table, standard schema |
| Unique constraint patch (`v6_8`) | 1–3 seconds | Idempotent; skipped if index exists |
| `Construction Settings` flag sync | 1–2 seconds | 13 flag fields |
| **Total estimated** | **~15–30 seconds** | Low risk of timeout |

## 4. Post-Deploy Smoke (Before Enabling Any Flag)

Run these commands **immediately after** deploy to confirm the build is healthy:

```bash
# 1. WBS health check (should be clean even on empty site)
bench --site <site> execute construction.services.boq_wbs_health.run_wbs_health_check

# 2. Feature flags readable
bench --site <site> execute construction.services.feature_flags.get_flags

# 3. DocType schema confirmed
bench --site <site> mariadb -e "SHOW TABLES LIKE 'tabBOQ Import Batch'"
bench --site <site> mariadb -e "SHOW TABLES LIKE 'tabVariation Order'"
bench --site <site> mariadb -e "SHOW TABLES LIKE 'tabVO Line'"

# 4. Unique index confirmed
bench --site <site> mariadb -e "SHOW INDEX FROM tabBOQ Structure WHERE Key_name = 'unique_boq_header_wbs_code'"

# 5. Translation build
bench build --app construction

# 6. Asset compilation
bench --site <site> execute frappe.utils.bench_helper.get_sites
```

**If any of the above fails, halt flag enablement and investigate.**

## 5. Rollback Plan

| Scenario | Rollback Action |
|----------|-----------------|
| `bench migrate` fails | Frappe Cloud will block the deploy. Fix locally, re-deploy. |
| Post-deploy smoke fails | Restore DB snapshot. Revert deploy branch. Debug on staging. |
| Feature flag causes issue | Disable the specific flag in `Construction Settings`. No DB rollback needed. |
| Critical production bug | Restore DB snapshot + revert deploy branch. Communicate downtime window. |

## 6. Feature Flag Enablement Order

Recommended staged rollout:

| Order | Gate | Flag(s) to Enable | Verification Before Next Gate |
|-------|------|-------------------|------------------------------|
| 1 | G1 | `enable_boq_wbs_resequence` | WBS health clean, resequence smoke OK |
| 2 | G2 | `enable_boq_excel_import_preview`, `enable_boq_excel_import_commit` | Import dry-run + commit smoke OK |
| 3 | G3 | `enable_stage_measurement_ui` | Stage policy smoke OK |
| 4 | G4 | `enable_boq_scope_registry` | Transaction validation smoke OK |
| 5 | G5 | `enable_bilingual_boq_print` | Arabic PDF/Excel smoke OK |
| 6 | G6 | `enable_variation_orders` | VO creation + approval smoke OK |

**Policy:** Enable **one gate at a time**, wait 24–48 hours of production usage, then enable the next.

## 7. Monitoring (First 24 Hours)

| Monitor | Tool / Method | Escalation |
|---------|--------------|------------|
| Error logs | Frappe Cloud Error Log / `bench --site <site> show-error-log` | If >5 new error types appear |
| Migration patch status | `bench --site <site> migrate --dry-run` (next deploy) | If patches show as pending |
| Site performance | Frappe Cloud dashboard | If response time >2x baseline |
| User-reported issues | Support channel / QS feedback | If any BOQ/VO workflow breaks |

## 8. Manager Decisions (Second Pass, 2026-06-10)

| # | Question | Manager Decision |
|---|----------|------------------|
| 1 | **Staging site** | Use same Frappe Cloud bench, create separate site `construction-staging.frappe.cloud`. If unavailable, create new bench. |
| 2 | **Deploy branch** | Create `release/v6.8` from `develop`. Do not deploy from `develop` directly. Tag `v6.8.0` after merge to `main`. |
| 3 | **Backup retention** | Default Frappe Cloud retention is 7 daily backups. **Confirm with Cloud admin before production deploy.** |
| 4 | **Notification** | Notify QS team lead, PM lead, and Engineering Manager on each flag enable. Use shared Slack channel or email thread with timestamp. |

## 9. Scheduled Jobs Check

**Action item:** Before production deploy, verify no new scheduled jobs were introduced by WP1–WP6.

Current assessment:
- WP1–WP6 do **not** introduce any new `hooks.py` scheduled jobs.
- WBS health check is an **on-demand** service (`construction.services.boq_wbs_health.run_wbs_health_check`), not a scheduled task.
- Export/import cleanup is handled by Frappe's standard File lifecycle.

**Status:** No new scheduled tasks introduced by this release.

If this assessment changes during staging deploy, update this section and notify the manager.

## 10. Rollback Drill (Required Before Production)

**Condition from manager:** Run a rollback drill on staging before production deploy. Test `bench rollback` (or chosen method) and confirm it works as expected. Document the result in `EV-062`.

**Staging rollback test plan:**
1. Deploy `release/v6.8` to staging.
2. Run post-deploy smoke (Section 4).
3. Simulate a failure (e.g., disable a critical feature, or restore pre-deploy DB snapshot).
4. Confirm rollback restores the site to pre-deploy state.
5. Document steps, timing, and any issues in `EV-062`.

## 11. Sign-Off

| Role | Name | Signature / Date |
|------|------|------------------|
| Engineering Manager | | |
| DevOps / Cloud Admin | | |
| Product Owner | | |
