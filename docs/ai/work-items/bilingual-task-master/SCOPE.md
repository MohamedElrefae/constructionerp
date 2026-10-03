# Scope Descriptor — bilingual-task-master

**Work item:** `bilingual-task-master`
**Branch:** `feature/bilingual-task-master`
**Base commit:** `abffaaa` (16 active masters)
**Scope:** Task (`subject` / `subject_ar` / `subject_ar_norm`)
**Date:** 2026-10-02
**Authority:** owner instruction given in session; transcribed by the agent

Master #17. Wave 2 of `ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` §3.2, which
specifies: source `subject`, Arabic `subject_ar`, code/identity document ID, and the note
*"Treat as operational name, not every comment."*

---

## 1. Starting state (verified on `v16.localhost`)

| Property | Value |
|---|---|
| `autoname` | `TASK-.YYYY.-.#####` (naming series, pure ASCII) |
| `is_tree` | 1 |
| `istable` | 0 |
| live rows | 3 (`task1`, `task 2`, `hhhh`) |
| existing custom fields | none |
| `subject` | Data, required |
| `parent_task` | Link → Task (self-link, ASCII) |
| `project` | Link → Project |
| `status` | Select |
| `description` | Text Editor (rich HTML) |

## 2. Scope

### A. Schema — idempotent patch `v9_8`

`construction/patches/v9_8/add_task_arabic_fields.py`, mirroring `v9_7`.

| Field | Properties |
|---|---|
| `subject_ar` | Data, `insert_after` = `subject`, `translatable=0` |
| `subject_ar_norm` | Data, `hidden=1`, `read_only=1`, `no_copy=1`, `translatable=0` |

`execute()` idempotent with backfill; `revert()` removes both. Registered in
`construction/patches.txt` after `v9_7`.

### B. Registry

| Key | Value |
|---|---|
| `state` | `schema_installed` |
| `english_field` | `subject` |
| `arabic_field` | `subject_ar` |
| `norm_field` | `subject_ar_norm` |
| `code_field` | `null` — Task has no separate code column |
| `identity_field` | `name` |
| `search.fields` | `["subject", "subject_ar"]` |
| `tree.enabled` | `true` |

### C. Hooks

Attach `enforce_bilingual_arabic_policy` to `validate` for `Task` in `construction/hooks.py`.

### D. Identity invariant

`name` is a naming-series key (`TASK-2026-00001`) and is therefore ASCII by
construction; there is no ASCII-PK risk to mitigate. `parent_task` is a self-link
carrying the same series key. The invariant to hold is narrower than for the
classification trees:

1. Arabic occupies only `subject_ar` and the derived `subject_ar_norm`.
2. Neither `name` nor `parent_task` ever receives Arabic, because neither is derived
   from `subject`.
3. `enforce_bilingual_arabic_policy` satisfies this unmodified, as for every prior master.

### E. Explicitly excluded

| Excluded | Reason |
|---|---|
| `status` | `Select` controlled vocabulary. Belongs to Frappe's static translation catalog (`.po` / `Custom Translation`), not the dynamic master-data registry. Conflating workflow states with entity names would blur the Wave 2b boundary. |
| `description` | `Text Editor` rich HTML — a **narrative** field. `unicode_policy` distinguishes `identity_rejected` from `narrative_rejected`, and narrative policy has never been exercised across the sixteen active masters. Deferred per Wave 2b §10. |
| `project` join | Matches the Wave 2b transactional decision: no relational join in the search path. Task resolves its own `subject` / `subject_ar`; the linked Project's `project_name_ar` is not surfaced. |
| `BOQ Item` shape | Task carries no separate name field beyond `subject`, so no analogue of the Wave 2b numerical-line exclusion is needed. |

### F. Zero service edits

`construction/services/bilingual_service.py` and
`construction/searchable_dropdown/api/search.py` must have **zero** modified lines. Any
edit invalidates this candidate's primary claim. This is the seventeenth consecutive
candidate asserting that invariant.

### G. Tests

`construction/tests/test_bilingual_task_pilot.py`, mirroring the Wave 2a / Employee /
Department pattern:

- Patch idempotency and reversibility for both fields.
- `get_mapping` resolves `norm_field`; fail-closed on a missing declared field.
- Server-authoritative norm derivation; a client-supplied poisoned `subject_ar_norm` is
  overwritten.
- Bidi control rejection on `subject_ar`.
- Identity invariant: after writing Arabic, `name` and `parent_task` are unchanged;
  `rename_doc` preserves `subject_ar` and `subject_ar_norm`.
- Search normalisation across Alef / Taa Marbuta / tatweel variants, with synthetic
  fixtures providing realistic cardinality.
- Guard test asserting `bilingual_service.py` and `search.py` are byte-identical to
  `abffaaa`.

### H. Thin-data note

Only 3 live `Task` rows exist. Like `Employee` (3 rows), search verification relies on
synthetic fixtures rather than baseline cardinality. This is recorded so a future reviewer
does not read the latency figures as representative of production `Task` volume.

### I. State gate

`Task` remains `schema_installed` through this candidate. Promotion to `active` requires
the suite to pass, matching the Wave 1 / Wave 2a precedent.

## 3. Invariants preserved

- `bilingual_service.py` / `search.py`: 0 modified lines
- `boq_export_service.py` / print templates: 0 modified lines (print is out of scope here)
- `apps/frappe` / `apps/erpnext`: 0 modified lines
- `orchestrator/`: 0 modified lines
- `erp-arabic-bilingual-data` evidence: 0 modified lines

## 4. Out of scope

- Any modification under `orchestrator/`.
- Any modification to vendor sources.
- Any modification to `bilingual_service.py`, `search.py`, or the print subsystem.
- `Task.status` controlled-vocabulary translation.
- `Task.description` narrative Arabic (deferred with the rest of narrative policy).
- Promotion of any registry state to `active`.
- `Company` (governance-gated on legal/tax statutory-name review).
- `Asset` / `Asset Category`, `Payment Terms` (subsequent mechanical repeats).
