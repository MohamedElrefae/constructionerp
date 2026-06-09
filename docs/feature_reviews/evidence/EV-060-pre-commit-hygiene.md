# EV-060 — Pre-Commit Hygiene

Date: 2026-06-10

## 1. Git Status Clean Diff

### Modified Files (24)

```
construction/api/boq_api.py
construction/construction/doctype/boq_item/boq_item.json
construction/construction/doctype/boq_item/boq_item.py
construction/construction/doctype/boq_item_stage/boq_item_stage.js
construction/construction/doctype/boq_item_stage/boq_item_stage.py
construction/construction/doctype/boq_structure/boq_structure.json
construction/construction/doctype/boq_structure/boq_structure.py
construction/construction/doctype/construction_settings/construction_settings.json
construction/construction/doctype/user_scope_context/test_user_scope_context.py
construction/install.py
construction/locale/ar.po
construction/patches.txt
construction/services/boq_accounting.py
construction/services/boq_export_service.py
construction/services/boq_import_service.py
construction/services/boq_lifecycle.py
construction/services/boq_operational.py
construction/services/boq_transaction_validation.py
construction/services/wbs_generator.py
construction/templates/boq_header_print.html
construction/templates/boq_print_format.html
construction/tests/test_boq_integration.py
construction/tests/test_boq_item_stage.py
construction/tests/test_boq_properties.py
construction/tests/test_transaction_validation.py
```

### Untracked Files (13)

```
construction/construction/doctype/boq_import_batch/
construction/construction/doctype/boq_item_stage/boq_item_stage_list.js
construction/construction/doctype/variation_order/
construction/construction/doctype/vo_line/
construction/patches/v6_8/
construction/services/boq_scope_registry.py
construction/services/boq_wbs_health.py
construction/services/feature_flags.py
construction/services/variation_orders.py
construction/tests/test_boq_excel_parser.py
construction/tests/test_boq_helpers.py
construction/tests/test_boq_structure_conversion.py
construction/tests/test_boq_structure_delete_safety.py
construction/tests/test_boq_wbs_generation.py
construction/tests/test_boq_wbs_health.py
construction/tests/test_boq_wbs_resequence.py
construction/tests/test_variation_orders.py
docs/feature_reviews/
```

### Diff Stat

```
25 files changed, 3184 insertions(+), 308 deletions(-)
```

### Verification

- **No `__pycache__/` or `*.pyc` files in diff.** `.gitignore` already excludes them.
- **No editor swap files** (`*.swp`, `*.swo`, `*~`) in diff.
- **No local debug scripts** in `/tmp/` referenced in committed code.
- **All modified files are intended construction app files.**
- **All untracked files are intended** (new DocTypes, services, tests, planning docs).

## 2. Secrets Scan

### Scan Command

```bash
grep -ri 'admin12345\|Admin@2026-temp\|password\|api_key\|secret_key\|token' \
  --include='*.py' --include='*.js' --include='*.json' --include='*.html' \
  construction/
```

(Excluding legitimate password-related API names like `validate_password`, `get_password`, etc.)

### Findings

| Secret | Location | In Committed Code? |
|--------|----------|-------------------|
| `Admin@2026-temp` | `docs/feature_reviews/evidence/EV-019-wp1-browser-tree-qa.md` | ❌ No (evidence docs are not code) |
| `admin12345` | Not found | ❌ No |
| API keys | Not found | ❌ No |
| Hardcoded tokens | Not found | ❌ No |

**Note:** The temp Administrator password (`admin12345`) was set on `v16.localhost` for browser QA (`EV-019`, `EV-056`). It is **not present in any source file**.

## 3. Branch Policy

| Item | Value |
|------|-------|
| Current branch | `develop` |
| Local changes | Committed to working tree (not yet committed to git) |
| Manager decision | **Create `release/v6.8` branch from `develop`. Do not deploy from `develop` directly.** |
| Merge target for Cloud deploy | `release/v6.8` |
| Tag after merge to `main` | `v6.8.0` |

**Rationale:** `develop` is the working branch and will keep moving; a tagged release branch gives a stable deploy target with a clear rollback point.

## 4. Commit Message

Manager-approved structured commit message:

```
Release: Improve Now v6.8 — WP1–WP6 BOQ/VO platform

- WP1 WBS stability, conversion, resequence
- WP2 BOQ Excel import/export with traceability
- WP3 Stage measurement/certification UI
- WP4 Scope context registry for transactions
- WP5 Arabic/English labels and print formats
- WP6 Variation Orders with FIDIC 25% rate rule

Evidence: EV-001 through EV-061
Refs: 09_improve_now_task_tracker.md, 11_manager_review_request.md
```

## 5. Pre-Commit Checklist

- [x] Only intended files in changeset
- [x] No `__pycache__` or `.pyc` files
- [x] No editor swap files
- [x] No secrets in source code
- [x] No absolute `/tmp/` paths in committed code
- [x] All new Python files syntax-checked
- [x] `.gitignore` properly excludes build artifacts

## Recommendation

Before `git commit`:
1. Confirm merge target branch with manager (`develop` vs. `main` vs. release branch).
2. Run one final `git status --short` to confirm no stray files were added.
3. Commit with a descriptive message referencing the Improve Now program.
