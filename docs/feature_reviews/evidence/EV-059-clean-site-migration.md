# EV-059 — Clean-Site Migration Verification

Date: 2026-06-10

## Scope

Verify that `bench migrate` on a clean site (no existing BOQ data) succeeds without manual intervention.

## Limitation

Live clean-site execution was **not possible** in this environment because:
- No MariaDB root access to create a new database.
- `bench reinstall` on `v16.localhost` would destroy the existing verified dataset (`EV-005`, `EV-056`).

Verification was performed by **code inspection + idempotency smoke** instead.

## 1. WP1.3 Unique Constraint Migration (`patches/v6_8/add_boq_structure_wbs_unique_constraint.py`)

### Patch Code

```python
def execute():
    if not frappe.db.table_exists("tabBOQ Structure"):
        return
    ensure_wbs_unique_constraint()
    frappe.db.commit()
```

### Clean-Site Safety Analysis

| Scenario | Patch Behavior | Risk |
|----------|---------------|------|
| Clean site, `tabBOQ Structure` does not exist yet | Returns immediately (`return`) | **None** |
| Clean site, table exists but is empty | `run_wbs_health_check()` passes (0 structures, 0 issues) | **None** |
| Clean site, table exists with valid WBS | Index added if not already present | **None** |
| Clean site, table exists with duplicate WBS | `ensure_wbs_unique_constraint()` throws before altering table | **Blocked safely** |

### Idempotency Verification

Ran `setup_boq_structure_constraints()` (which calls `ensure_wbs_unique_constraint`) on `v16.localhost`:

```bash
bench --site v16.localhost execute construction.install.setup_boq_structure_constraints
```

Result: No error. Unique index `unique_boq_header_wbs_code` confirmed still present after re-run.

```
SHOW INDEX FROM `tabBOQ Structure` WHERE Key_name = 'unique_boq_header_wbs_code'
→ Index exists, Non_unique = 0
```

**Status:** Idempotent. Safe for clean sites.

## 2. WP2.2B BOQ Import Batch DocType

### DocType Configuration

```json
{
  "autoname": "Prompt",
  "name": "BOQ Import Batch"
}
```

### Clean-Site Safety Analysis

- `autoname`: `"Prompt"` means the user manually names each batch record.
- No naming series, no auto-increment collision risk.
- No fixtures required.
- DocType JSON is standard Frappe schema; `bench migrate` creates the table automatically.

**Status:** No collision risk. Safe for clean sites.

## 3. Install Path (`install.py`)

### `after_install` Hook Sequence

```python
after_install = [
    "construction.install.create_system_themes",
    "construction.install.setup_boq_integration",
    ...
]
```

`setup_boq_integration()` calls `setup_boq_structure_constraints()`, which:
1. Checks `frappe.db.table_exists("tabBOQ Structure")` — on a clean site during `after_install`, this will be `True` (DocTypes are created before `after_install` hooks run in Frappe).
2. Calls `ensure_wbs_unique_constraint()` — idempotent, safe.

**Status:** Clean install path is protected by the same `table_exists` guard and idempotent helper.

## 4. New DocType Migration

The following new DocTypes were added and migrated to `v16.localhost` successfully:

| DocType | Migration Status on v16.localhost |
|---------|-----------------------------------|
| `BOQ Import Batch` | ✅ Migrated |
| `Variation Order` | ✅ Migrated |
| `VO Line` | ✅ Migrated |

On a clean site, Frappe's built-in DocType creation during `bench migrate` will create these tables automatically from their JSON definitions. No manual SQL is required.

## 5. Syntax Verification

All new Python files compiled without syntax errors:

```bash
python -m py_compile \
  construction/construction/doctype/variation_order/variation_order.py \
  construction/construction/doctype/vo_line/vo_line.py \
  construction/services/variation_orders.py \
  construction/services/boq_wbs_health.py \
  construction/patches/v6_8/add_boq_structure_wbs_unique_constraint.py
```

Result: `Syntax OK`

## Conclusion

Clean-site migration is **safe by design**:

1. The unique-constraint patch has a `table_exists` guard and is idempotent.
2. `BOQ Import Batch` uses manual naming (`Prompt`), eliminating auto-name collision risk.
3. New DocTypes are standard Frappe JSON schemas that migrate automatically.
4. All new Python files pass syntax checks.

**Caveat:** Live clean-site `bench migrate` was not executed due to environment constraints. The recommendation is to run a staging deploy on Frappe Cloud (which creates a fresh site container) before production release.
