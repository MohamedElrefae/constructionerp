# EV-062 — Post-Commit Smoke & Rollback Drill

Date: 2026-06-10

## Scope

Document post-commit smoke results and rollback drill status.

## Post-Commit Smoke Results (Local — v16.localhost)

All smoke commands from `EV-061` Section 4 were executed on `v16.localhost` after commit to `release/v6.8`:

### 1. WBS Health Check

```bash
bench --site v16.localhost execute construction.services.boq_wbs_health.run_wbs_health_check
```

Result:
```json
{
  "boq_header": null,
  "healthy": true,
  "summary": {
    "structures_checked": 8,
    "items_checked": 4,
    "issue_count": 0,
    "by_type": {},
    "by_severity": {}
  },
  "issues": []
}
```

✅ **PASS** — WBS health clean.

### 2. Feature Flags Readable

```bash
bench --site v16.localhost execute construction.services.feature_flags.get_flags
```

Result: All 7 rollout flags default to `false`:
- `enable_bilingual_boq_print`: false
- `enable_boq_excel_import_commit`: false
- `enable_boq_excel_import_preview`: false
- `enable_boq_scope_registry`: false
- `enable_boq_wbs_resequence`: false
- `enable_stage_measurement_ui`: false
- `enable_variation_orders`: false

✅ **PASS** — Flags readable and all disabled.

### 3. DocType Schema Confirmed

```sql
SELECT table_name, COUNT(*) as exists_count
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('tabBOQ Import Batch', 'tabVariation Order', 'tabVO Line')
```

Result: All three tables exist (count = 1 each).

✅ **PASS** — New DocTypes migrated.

### 4. Unique Index Confirmed

```bash
bench --site v16.localhost mariadb -e "SHOW INDEX FROM tabBOQ Structure WHERE Key_name = 'unique_boq_header_wbs_code'"
```

Result: Index exists, `Non_unique = 0`, columns `boq_header` + `wbs_code`.

✅ **PASS** — Unique constraint active.

### 5. Translation Build

```bash
bench build --app construction
```

Result: Build succeeded in ~1.13s. MO file up to date at `sites/assets/locale/ar/LC_MESSAGES/construction.mo`.

✅ **PASS** — Assets compiled.

### 6. VO Tests

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_variation_orders --skip-before-tests --lightmode
```

Result: 10/10 passing.

✅ **PASS** — VO suite green.

## Rollback Drill

### Limitation

A true rollback drill on Frappe Cloud staging was **not executed** because:
- No Frappe Cloud staging site exists in this local environment.
- No Frappe Cloud credentials or bench access are available.

### Local Equivalent Test

The closest local equivalent is verifying that the committed code can be reverted via git:

```bash
git -C apps/construction log --oneline -3
```

Result:
```
ebc82f7 Release: Improve Now v6.8 — WP1–WP6 BOQ/VO platform
...
```

Rollback command available:
```bash
git -C apps/construction revert ebc82f7 --no-edit
# or
git -C apps/construction reset --hard HEAD~1
```

### Frappe Cloud Rollback Plan (To Be Verified on Staging)

Per `EV-061`, the production rollback options are:

| Method | Steps | Estimated Time |
|--------|-------|----------------|
| DB snapshot restore | Restore pre-deploy backup via Frappe Cloud dashboard | 5–15 minutes |
| Git revert + bench migrate | Revert to previous release branch, run migrate | 10–20 minutes |
| Feature flag disable | Disable specific flag in Construction Settings | < 1 minute |

**Required before production:** Run the DB snapshot restore method on `construction-staging.frappe.cloud` and confirm it completes successfully.

## Conclusion

All local post-commit smoke tests **passed**. The code is committed to `release/v6.8` and ready for Frappe Cloud staging deploy.

**Outstanding:** True rollback drill on Frappe Cloud staging remains pending. This must be completed and documented here before production deploy.
