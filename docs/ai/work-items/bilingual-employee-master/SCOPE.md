# Scope Descriptor — bilingual-employee-master

**Work item:** `bilingual-employee-master`
**Branch:** `feature/bilingual-employee-master` in worktree `worktrees/bilingual-employee-master`
**Base commit:** `b311377` (from `develop`)
**Scope:** Employee (13th master, completing ERPNext organizational and operational masters)
**Date:** 2026-10-03
**Authority:** Owner directive transcribed into codebase governance

---

## 1. Purpose

Wave 1 established bilingual enablement for six core business masters (`Item`, `Customer`,
`Supplier`, `Cost Center`, `Warehouse`, `Project`). Wave 2a enabled five classification
and grouping masters (`Item Group`, `Customer Group`, `Supplier Group`, `Territory`, `UOM`).
`Employee` was deliberately deferred from Wave 2a due to its distinct structural attributes:
it is an organizational tree (`reports_to`) whose primary key is a `naming_series` sequence
rather than a canonical English string, its `employee_name` is synthesized on save from
name parts (`first_name`, `middle_name`, `last_name`), and it carries HR user-permission
scoping.

This work item enables bilingual capabilities on `Employee` following the exact proven
framework, proving the zero-service-edit invariant for the 13th master.

## 2. Starting State (Verified on `v16.localhost`)

| Property | Value | Notes |
|---|---|---|
| DocType | `Employee` | Standard ERPNext HR master |
| in registry | no | Absent from `bilingual_registry.json` |
| `is_tree` | `1` | Org hierarchy via `reports_to` self-link |
| autoname | `naming_series:` | PK is ASCII serial (e.g. `_T-Employee-00001`, `HR-EMP-00001`) |
| canonical English field | `employee_name` | Derived in `Employee.validate()` from `first_name` + `middle_name` + `last_name` |
| parent link field | `reports_to` | Points to manager's `Employee.name` (ASCII PK) |
| custom fields | 0 | Clean starting schema |
| live rows | 3 | Existing test records on `v16.localhost` |

## 3. Field Naming & Architecture

| DocType | Canonical English | Arabic Display | Normalized Search Key |
|---|---|---|---|
| Employee | `employee_name` | `employee_name_ar` | `employee_name_ar_norm` |

- `employee_name_ar`: Single Data field inserted after `employee_name`. Users author the full
  Arabic name (e.g. "محمد أحمد علي"). `translatable=0` to prevent UI string collision.
- `employee_name_ar_norm`: Server-derived search key. `hidden=1, read_only=1, no_copy=1, translatable=0`.

## 4. Scope

### A. Schema — Idempotent Patch `v9_5`
`construction/patches/v9_5/add_employee_arabic_fields.py`:
- Adds `employee_name_ar` and `employee_name_ar_norm` to `Employee`.
- Registered in `construction/patches.txt` following `v9_4`.
- Idempotent `execute()` with backfill support; clean `revert()` removing both custom fields.

### B. Registry
Add `Employee` to `construction/data/bilingual/bilingual_registry.json`:
- `state`: `schema_installed`
- `english_field`: `employee_name`
- `arabic_field`: `employee_name_ar`
- `norm_field`: `employee_name_ar_norm`
- `code_field`: `null` (since `name` is already the primary identifier / serial)
- `identity_field`: `name`
- `tree.enabled`: `true`
- `search.fields`: `["employee_name", "employee_name_ar"]`

### C. Hooks
Attach `enforce_bilingual_arabic_policy` to `validate` for `Employee` in `construction/hooks.py`.

### D. Identity & Org-Chart Invariant
- `name` remains an ASCII naming series sequence.
- `reports_to` pointer remains an ASCII naming series sequence.
- Arabic occupies exclusively `employee_name_ar` and derived `employee_name_ar_norm`.
- Renaming an employee preserves Arabic and norm keys.

### E. Zero Service Edits
`bilingual_service.py` and `search.py` must have **zero** diff lines against base commit `b311377`.
Mechanically enforced by `test_zero_service_edits_guard`.

### F. Tests
`construction/tests/test_bilingual_employee_pilot.py`:
- Patch idempotency and reversibility.
- Registry mapping resolution and fail-closed validation.
- Server-authoritative norm derivation (POISONED-KEY overwritten).
- Bidi control character rejection on `employee_name_ar`.
- Org-chart identity invariant (`name` and `reports_to` unaltered; rename preservation).
- Normalized search matching despite Alef variants, tatweel, and diacritics.
- Zero-service-edits guard against `b311377`.

### G. Performance & Two-Tier SLA Compliance
- Local comparative P95 measurement harness (`measure_employee_p95.py`).
- Governed by the approved Two-Tier SLA:
  - Universal absolute ceiling: $\le 1.50$ ms P95.
  - Relative ratio evaluated and documented honestly.
