# Scope Descriptor — bilingual-department-master

**Work item:** `bilingual-department-master`
**Branch:** `feature/bilingual-department-master` in worktree `worktrees/bilingual-department-master`
**Base commit:** `c1d278b` (from `develop`)
**Scope:** Department (14th master, completing ERPNext organizational and operational masters)
**Date:** 2026-10-03
**Authority:** Owner directive transcribed into codebase governance under Plan §3.2

---

## 1. Purpose

Wave 1 established bilingual enablement for six core business masters (`Item`, `Customer`,
`Supplier`, `Cost Center`, `Warehouse`, `Project`). Wave 2a enabled five classification
and grouping masters (`Item Group`, `Customer Group`, `Supplier Group`, `Territory`, `UOM`).
Wave 2c enabled `Employee` as the 13th master with org-chart hierarchy support.

`Department` represents the primary organizational hierarchy across HR, Costing, and Project
management. Like `Cost Center` and `Item Group`, `Department` is a recursive tree DocType
(`is_tree = 1`, `parent_department`, `is_group`, `lft`, `rgt`).

This work item enables bilingual capabilities on `Department` following the proven zero-service-edit
framework, bringing the total number of active bilingual masters to fourteen.

## 2. Starting State (Verified on `v16.localhost`)

| Property | Value | Notes |
|---|---|---|
| DocType | `Department` | Standard ERPNext HR/Company organizational master |
| in registry | no | Absent from `bilingual_registry.json` |
| `is_tree` | `1` | Tree hierarchy via `parent_department` self-link |
| autoname | None | Standard ERPNext naming: `department_name - <company_abbr>` or `department_name` |
| canonical English field | `department_name` | Source field for English name |
| parent link field | `parent_department` | Self-link to parent Department record |
| custom fields | 0 | Clean starting schema |
| live rows | 5 | Standard test records on `v16.localhost` |

## 3. Field Naming & Architecture

| DocType | Canonical English | Arabic Display | Normalized Search Key |
|---|---|---|---|
| Department | `department_name` | `department_name_ar` | `department_name_ar_norm` |

- `department_name_ar`: Single Data field inserted after `department_name`. Users author the full
  Arabic name (e.g. "الموارد البشرية", "الإدارة المالية"). `translatable=0` to prevent UI string collision.
- `department_name_ar_norm`: Server-derived search key. `hidden=1, read_only=1, no_copy=1, translatable=0`.

## 4. Scope

### A. Schema — Idempotent Patch `v9_6`
`construction/patches/v9_6/add_department_arabic_fields.py`:
- Adds `department_name_ar` and `department_name_ar_norm` to `Department`.
- Registered in `construction/patches.txt` following `v9_5`.
- Idempotent `execute()` with backfill support; clean `revert()` removing both custom fields.

### B. Registry
Add `Department` to `construction/data/bilingual/bilingual_registry.json`:
- `state`: `schema_installed` (staged, then promoted to `active` post-benchmarking)
- `english_field`: `department_name`
- `arabic_field`: `department_name_ar`
- `norm_field`: `department_name_ar_norm`
- `code_field`: `null`
- `identity_field`: `name`
- `tree.enabled`: `true`
- `search.fields`: `["department_name", "department_name_ar"]`

### C. Hooks
Attach `enforce_bilingual_arabic_policy` to `validate` for `Department` in `construction/hooks.py`.

### D. Identity & Tree Invariant
- `name` remains canonical identifier / ASCII company suffix.
- `parent_department` pointer remains intact.
- Arabic occupies exclusively `department_name_ar` and derived `department_name_ar_norm`.
- Renaming a department preserves Arabic and norm keys without foreign-key corruption.

### E. Zero Service Edits
`bilingual_service.py` and `search.py` must have **zero** diff lines against base commit `c1d278b`.
Mechanically enforced by `test_zero_service_edits_guard`.

### F. Tests
`construction/tests/test_bilingual_department_pilot.py`:
- Patch idempotency and reversibility.
- Registry mapping resolution and fail-closed validation.
- Server-authoritative norm derivation (POISONED-KEY overwritten).
- Bidi control character rejection on `department_name_ar`.
- Tree identity invariant (`name` and `parent_department` unaltered; rename preservation).
- Normalized search matching despite Alef variants, tatweel, and diacritics.
- Zero-service-edits guard against `c1d278b` and baseline commits.

### G. Performance & Two-Tier SLA Compliance
- Local comparative P95 measurement harness (`measure_department_p95.py`).
- Governed by the approved Two-Tier SLA:
  - Universal absolute ceiling: $\le 1.50$ ms P95.
  - Sub-millisecond Tier 2B trade-off band: $\le 1.50\times$ relative ratio.
