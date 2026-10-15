# F18 — Cost Database Maintainer: permission matrix and grant specification

**Date:** 2026-10-13
**Candidate:** construction `09c8cb1` · frappe 16.51.1 · erpnext 16.50.0
**Status:** specification only. Role creation pending owner designation. No DocPerm, User Permission, role, or site change made in this task.
**Enforcement context:** scope boundary ON; file/VO/stage guards live; F14-D001 open.

## 1. Why a new role is needed

Cost-DB import/repricing demands doctype-level create on Company-read + Resource Price History + Item + BOQ Cost Analysis (`cost_database_api.py:26`, `:135`; service pre-checks). Installed grants give **no** ordinary role RPH-create or Item-create (Owner/PM read-only on RPH; Company read absent for all construction roles). Only Administrator can import today, so F18's authorized-user workflow is unreachable. Extending PM/Owner with global Item create/write would over-grant the core commercial roles; a narrow dedicated role is the smallest change.

## 2. Exact writes the service performs (traced, current code)

| Operation | Writes | Scope |
|---|---|---|
| Resources import | UOM insert (if missing); Item insert **or update of ANY matching item_code** (renames, sets construction flags); RPH insert (idempotent skip on exact dup) | UOM/Item are **global shared masters**; RPH rows carry company |
| Templates import | BOQ Cost Analysis template insert (+ submit iff auto_submit) | Company-scoped drafts |
| Reprice | Draft analysis detail `cost_rate` updates + `doc.save()` | Explicitly selected drafts only |
| Template download | Read-only | No business data |

**Shared-master risks requiring disclosure and UI warning (F18-U cases):** an import row whose code matches a live ERPNext buying/selling Item will rename it and flip its construction flags; new UOMs are global. Company matching is enforced (proven denial); project scoping does not apply (company-level library).

## 3. Proposed grant specification (to apply at designation, not now)

**Role:** `Cost Database Maintainer` (new, narrow). **Created on UAT 2026-10-13 for qualification** (Custom DocPerm rows + user + Company/Project permissions + scope; auto-submit disabled as directed — no submit grant).

| DocType | read | write | create | delete | submit | cancel | Notes |
|---|---|---|---|---|---|---|---|
| Company | 1 | 0 | 0 | 0 | – | – | Read only; target company via User Permissions |
| Resource Price History | 1 | 0 | 1 | 0 | – | – | Create-only matches insert-only service behavior |
| Item | 1 | 0 | 1 | 0 | – | – | **Create-only after narrowing** (no Item write anywhere); reuse-or-refuse protects existing rows |
| Item Price | 1 | 0 | 0 | 0 | – | – | Read-only rate source for repricing lookups |
| BOQ Cost Analysis | 1 | 1 | 1 | 0 | 0 | 0 | Write covers template + repriced drafts; submit withheld per auto-submit-disabled decision |
| BOQ Header / BOQ Item | 1 | 0 | 0 | 0 | – | – | Read-only reprice targeting; commercial mutation denied |
| UOM | 1 | 0 | 1 | 0 | – | – | Global effect disclosed |

| DocType | read | write | create | delete | submit | cancel | Notes |
|---|---|---|---|---|---|---|---|
| Company | 1 | 0 | 0 | 0 | – | – | Read only; target company via User Permissions |
| Resource Price History | 1 | 0 | 1 | 0 | – | – | Create-only matches insert-only service behavior |
| Item | 1 | 0 | 1 | 0 | – | – | **Create-only after narrowing** (reuse-or-refuse; no Item write anywhere) |
| Item Price | 1 | 0 | 0 | 0 | – | – | Read-only rate source for repricing lookups |
| BOQ Cost Analysis | 1 | 1 | 1 | 0 | 0 | 0 | Write covers template + repriced drafts; submit withheld per auto-submit-disabled decision |
| UOM | 1 | 0 | 1 | 0 | – | – | Global effect disclosed |
| BOQ Header/Item (read) | 1 | 0 | 0 | 0 | – | – | Reprice targeting only; no commercial mutation |

**User Permissions:** Company = assigned company (exactly one per maintainer; multi-company maintainers need one record per company, never a wildcard). Project = assigned project(s) for repricing project analyses (UAT: PROJ-0014). No other permissions.
**Scope context:** company set; project unset (library) — project analyses additionally resolve through their header scope.
**Explicitly withheld:** delete everywhere; analysis submit/cancel (auto-submit disabled); approve/cancel on project cost analyses; any BOQ commercial doctypes beyond read; System Manager/Administrator.

## 4. Implemented narrowings (2026-10-13, verified in §5)

1. Reuse-or-refuse is live: compatible existing Items pass through untouched; any name/flag/type/stream/UOM conflict is a row error in preview AND commit. Item write authority removed from the prerequisite entirely.
2. UOM auto-creation retained with warnings; created UOMs listed in preview (`proposed_creates`) and result.
3. Company-match refusal added for non-empty row companies in preview and commit (previously rows were silently restamped).
4. Per-write authorization map: UOM insert ← UOM-create pre-check; Item insert ← Item-create gate; RPH insert ← RPH-create gate; template insert ← Analysis-create gate + doc enforcement; reprice saves ← Analysis-write gate + doc enforcement. No `ignore_permissions` writes in these paths.
5. Blocking defect found during verification (F18-D001): the "Last Price History" provenance label had no matching Select option, so every RPH-sourced repricing commit failed validation. Option added to `rate_source` (+ migrate on UAT).

## 5. Ordinary-role verification (2026-10-13, maintainer session)

10/10 import probes (preview/propose/commit/conflict-refusal with live item untouched/cross-company/submit/BOQ-write denials) + reprice preview/commit with persisted rate 11 (`Last Price History` provenance) on a permitted Draft analysis. Auto-submit path untested by design (disabled, no submit grant).
