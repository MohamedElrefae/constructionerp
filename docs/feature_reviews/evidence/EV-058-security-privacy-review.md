# EV-058 — Security & Privacy Review

Date: 2026-06-10

## Scope

Review permissions, file access control, and data exposure for new Improve Now DocTypes and services.

## 1. Variation Order DocType Permissions

### Current Permission Matrix

| Role | Create | Read | Write | Delete | Export | Print | Share | Report |
|------|--------|------|-------|--------|--------|-------|-------|--------|
| System Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Construction Owner | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Project Manager | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |

**Finding:** No "Engineer" or "Client" role-specific permissions exist for the `Variation Order` DocType. The approval workflow (`Draft` → `Submitted` → `Approved by Engineer` → `Approved by Client`) is enforced by **status-transition validation** (`validate_status_transition` in `variation_order.py:44-60`), not by **role-based permission checks**.

**Risk:** Any user with `write` permission on `Variation Order` (e.g., Project Manager) can change the status directly to `Approved by Client` without an explicit role gate. The only hard gate is the signed PDF attachment check (`validate_client_approval_gate`).

**Mitigation:** The current design assumes Frappe's standard document-level permissions are sufficient for v1. If the organization requires strict segregation of duties (Engineer cannot also be Client approver), a future enhancement should add role-based transition hooks or custom workflow rules.

### VO Line (Child DocType) Permissions

`VO Line` has **no explicit permissions array** in its DocType JSON. It inherits access from the parent `Variation Order` document through Frappe's standard child-table permission model.

**Status:** Acceptable for v1. Child rows are only accessible through the parent VO form.

## 2. Private File Access Control

### Signed PDF Attachments (VO Client Approval)

- `client_approval_document` is an `Attach` field on `Variation Order`.
- Frappe stores uploaded attachments via the `File` DocType.
- The attachment URL (e.g., `/private/files/signed-vo2.pdf`) is served through Frappe's standard file handler, which enforces:
  - Session authentication
  - Document read permission on the parent `Variation Order`

**Status:** Files are not publicly accessible. Access requires both login AND read permission on the parent VO.

### Import Error Report Workbooks (WP2.8)

`BOQImportService.generate_error_report()` creates `File` records with:
- `file_url`: `/private/files/...`
- `is_private`: `1`

Verified in `boq_import_service.py:580-584`.

**Status:** Private by default. Only the uploading user and System Manager can access.

### Export Files (Excel/PDF)

`BOQExportService` creates `File` records with:
- `file_url`: `/private/files/...`
- `is_private`: `1`

Verified in `boq_export_service.py:789-793`.

**Status:** Private by default.

## 3. `is_variation_item` Field Exposure

### BOQ Item List View

List view fields in `boq_item.json`:
- `structure`, `boq_header`, `item_type`, `quantity`, `unit`, `contract_unit_price`, `line_total`

**Finding:** `is_variation_item` is **NOT** included in `in_list_view`.

**Status:** Variation items do not leak their status in list view. The field is visible only on the BOQ Item form.

### BOQ Structure List View

Similarly, `is_variation_item` is present in the form but not promoted to list view columns.

## 4. Secrets Scan

Scanned construction app for hardcoded credentials:

```bash
grep -ri 'admin12345\|Admin@2026-temp\|password\|api_key\|secret_key\|token' \
  --include='*.py' --include='*.js' --include='*.json' --include='*.html' \
  construction/
```

**Finding:**
- `Admin@2026-temp` appears **only** in evidence document `EV-019-wp1-browser-tree-qa.md` (not in committed code).
- `admin12345` (current temp password) **not found** anywhere in the codebase.
- No API keys, secrets, or tokens hardcoded in source files.

**Status:** Clean.

## 5. Recommendations

| Priority | Item | Action |
|----------|------|--------|
| **Low** | VO role-based approval | Add custom workflow or `has_permission` hook if segregation of duties is required. Not a v1 blocker. |
| **Low** | VO Line explicit permissions | Add child-table permissions if direct VO Line access is needed via API. Not a v1 blocker. |
| **None** | Private file exposure | Already correctly scoped. No action needed. |
| **None** | `is_variation_item` leak | Already hidden from list view. No action needed. |

## Conclusion

Security posture is acceptable for v1 release. The main gap is the absence of role-based approval gates on VO status transitions, which is a workflow design choice rather than a vulnerability. All file attachments are private by default. No secrets are hardcoded in source code.
