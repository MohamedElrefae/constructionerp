# SCOPE — Wave-2b Transactional Documents Bilingual Print Formats

**Work item:** `bilingual-transaction-print-formats`
**Session:** OpenCode Session A (implementation lane)
**Date:** 2026-10-05
**Status:** `COMPLETE — implemented, verified, evidence captured; awaiting Antigravity verification gate`
**Base commit:** `234c02446deb3dd10567bfcbc995732ccd8cc19e` (`develop`)
**Target site:** `v16.localhost`
**Briefing:** [`docs/ai/BRIEFING_TRANSACTION_PRINT_FORMATS.md`](../../BRIEFING_TRANSACTION_PRINT_FORMATS.md)

---

## 1. Objective

Ship four bilingual (English / العربية) Jinja print formats for the primary construction
transactional documents, with bidirectional isolation through the registered `bdi_join`
filter, automated rendering coverage against live Arabic master data, and full evidence
for independent verification.

| # | Print Format | DocType | File |
|---|---|---|---|
| 1 | Construction Bilingual Purchase Order | Purchase Order | `construction/print_format/bilingual_purchase_order/bilingual_purchase_order.json` |
| 2 | Construction Bilingual Sales Invoice | Sales Invoice | `construction/print_format/bilingual_sales_invoice/bilingual_sales_invoice.json` |
| 3 | Construction Bilingual Stock Entry | Stock Entry | `construction/print_format/bilingual_stock_entry/bilingual_stock_entry.json` |
| 4 | Construction Bilingual Material Request | Material Request | `construction/print_format/bilingual_material_request/bilingual_material_request.json` |

---

## 2. Invariants observed

1. **Role division** — this session implemented, tested and compiled evidence; git staging,
   digest re-verification and the commit remain with the Antigravity verification lane.
2. **Owner confidentiality** — strictly local. No remote push, no CI trigger, no external
   transmission. The installed `post-commit` hook was **not** executed by this session
   because this session performs no commit; the per-command
   `git -c core.hooksPath=/dev/null commit` guidance in the briefing is consistent with
   [`OWNER_CONFIDENTIALITY_POLICY.md`](../../OWNER_CONFIDENTIALITY_POLICY.md) §"Mandatory
   publication boundary" ("disable transmitting hooks per command … do not weaken global
   security settings") and belongs to the committer, not this session.
3. **Zero vendor edits** — no file under `apps/frappe` or `apps/erpnext` was modified.
4. **Frozen surfaces** — byte-identical to base commit, enforced by an automated test:
   `construction/services/bilingual_service.py`,
   `construction/searchable_dropdown/api/search.py`,
   `construction/data/bilingual/bilingual_registry.json`,
   `construction/fixtures/uom.json`.
5. **Bidi isolation** — every dual-language value uses
   `{{ [en, ar] | bdi_join(" / ") }}`; no raw bilingual concatenation appears in any template.
6. **Graceful fallback** — `bdi_join` drops empty/`None` elements, so an entity without an
   Arabic value renders monolingually with no dangling ` / ` separator (asserted).
7. **No `dump.rdb`, no Redis residue** — no Redis cluster was started by this session.

---

## 3. Decisions settled during implementation

### D1 — Supplier / customer Arabic field name (briefing corrected against live schema)

The briefing specified `frappe.db.get_value("Supplier", doc.supplier, "supplier_name_ar")`.
**Live schema does not contain that column.** Verified via `SHOW COLUMNS FROM tabSupplier` /
`tabCustomer` on `v16.localhost`:

| Doctype | Briefing field | Actual DB column (used) |
|---|---|---|
| Supplier | `supplier_name_ar` ❌ | `supplier_name_in_arabic` ✅ |
| Customer | `customer_name_ar` ❌ | `customer_name_in_arabic` ✅ |

`frappe.db.get_value` on a non-existent column raises `OperationalError (1054)` at render
time, so the briefing's literal snippet would have failed on every Purchase Order print.
Templates use the verified columns. `Item.item_name_ar`, `UOM.uom_name_ar`,
`Company.company_name_ar`, `Project.project_name_ar`, `Department.department_name_ar` and
`Warehouse.warehouse_name_ar` were confirmed present and used as specified.

### D2 — Material Request header fields (briefing corrected against live schema)

The briefing listed Department and Project on the Material Request header. `tabMaterial
Request` has neither column (they exist only on `Material Request Item`). The header
therefore prints Company, Request No., Request Type (mapped Arabic), Request Date,
Required Date and Status; Department is printed per line item where the column exists.

### D3 — Stock Entry / Material Request label maps

`purpose` and `material_request_type` are vendor Select fields with no Arabic counterpart
on the DocType. Both templates carry an explicit Jinja dictionary map covering every
option offered by the installed DocType (`Material Issue` → `صرف مواد`, `Purchase` → `شراء`,
…), rendered through `bdi_join` so an unmapped future option degrades to English only.

### D4 — Installation wiring added (extension beyond the briefing's deliverable list)

The briefing listed the four JSON artefacts but no registration path. Per the engineering
standard §13 ("code in an unregistered file is not a completed feature"), the formats are
installed by a new `construction.install.setup_transaction_print_formats()` registered in
both `after_install` and `after_migrate` in `construction/hooks.py`. The existing
`setup_boq_print_formats()` body was extracted into the shared
`_upsert_print_format_file()` helper without behaviour change (the list-value filter and
field skip-set are preserved verbatim).

### D5 — Print path under test

Assertions run against the **real** printview route (`frappe.get_print(doctype, name,
print_format=…)`), not a hand-built Jinja context, so the registered filter, the Print
Format record and the DocType wiring are all exercised.

### D6 — Shared-file amendment: 8 prior manifests re-pinned for `construction/hooks.py`

Registering `setup_transaction_print_formats` in `after_install` / `after_migrate`
(`+2` lines, verified as the *only* diff against `234c024`) changes the digest of a file
pinned by **8 earlier manifests**. All 8 pins held the pre-change value
`3a0abaa0…` and matched `HEAD(234c024)` immediately before this work item, so this
work item is solely responsible for the drift.

Following the convention already applied by Session B
(`bilingual-financial-reports` amendments `5E-repin` / `R1-B`: re-pin the shared file in
the earlier manifest **and** append an amendment note), this session:

| Manifest re-pinned | Amendments before → after |
|---|---|
| `bilingual-asset-master` | 13 → 14 |
| `bilingual-boq-title-ar-wiring` | 14 → 15 |
| `bilingual-brand-master` | 22 → 23 |
| `bilingual-company-master` | 6 → 7 |
| `bilingual-desk-link-dispatch` | 3 → 4 |
| `bilingual-financial-reports` | 2 → 3 (entry `TPF-hooks`) |
| `bilingual-narrative-sanitizer` | 21 → 22 |
| `bilingual-terms-conditions-master` | 18 → 19 |

Each write was a fresh read → modify → `json.dumps(indent=2, ensure_ascii=False)` →
atomic `os.replace`; round-trip fidelity against the pre-edit bytes was verified for all
8 files first, and Session B's uncommitted content in `bilingual-financial-reports`
(their `R1-B` entry and their `bilingual_reports.py` re-pin) was confirmed preserved
afterwards. No other artefact in those manifests was altered, and no artefact was
deleted. After the amendment **every** manifest that pins `construction/hooks.py`
verifies clean — including Session B's in-flight `bilingual-financial-reports-expansion`
manifest, which is not owned by this session.

---

## 4. Verification record

| Gate | Command | Result |
|---|---|---|
| Scope metadata lint | `python3 scripts/lint_scope_metadata.py` | PASS (19 DocTypes) |
| Context consistency | `python3 scripts/ai_context_check.py` | PASS (11/11) |
| Translation write lint | `python3 scripts/lint_translation_writes.py` | PASS |
| Schema drift | `python3 scripts/schema_drift_checker.py` | PASS (21 owners) |
| Python compile | `python3 -m py_compile` on changed modules | PASS (0 errors) |
| Shell syntax | `bash -n scripts/*.sh` | PASS (0 errors) |
| ADR↔evidence reconciler | `…/reconcile_adr_vs_evidence.py` | **19/19 PASS** |
| Module suite | `bench --site v16.localhost run-tests … test_bilingual_transaction_print` | **10/10 OK** |
| Canonical matrix | `bash scripts/run_bilingual_regression_matrix.sh v16.localhost` | **21 modules / 273 tests OK** |

Evidence: `evidence/gates.log`, `evidence/test-rendering.log`,
`evidence/regression-matrix.log`, `evidence/manifest-integrity.log`,
`evidence/MANIFEST.json` (manifest **#32**).

### Test inventory (10)

| Test | Asserts |
|---|---|
| `test_print_format_json_files_are_well_formed` | 4 files parse; name/doc_type/Jinja/custom_format/disabled correct; `bdi_join` present |
| `test_print_formats_registered_and_idempotent` | installed on site, HTML equals shipped file, installer is idempotent (count unchanged after 2 runs) |
| `test_render_purchase_order_bilingual` | real printview render; Company/Supplier/Project/Department/Item/UOM `<bdi>` pairs; ≥12 `<bdi>` nodes |
| `test_render_sales_invoice_bilingual` | `Prestiga-Biz / بريستيجا بيز`, `Consulting / استشارات`, `Tax Invoice / فاتورة ضريبية` |
| `test_render_stock_entry_bilingual` | `Material Issue / صرف مواد` purpose map + item/UOM pairs |
| `test_render_material_request_bilingual` | `Purchase / شراء` type map + item/UOM pairs |
| `test_fallback_has_no_dangling_separator` | supplier+project without Arabic render alone; no `" / "` tail, no empty `<bdi>`, no `None / ` |
| `test_single_escaping_of_ampersand_values` | `&` escaped once inside `<bdi>` and in a raw expression; injected `<Fine>` never re-emitted |
| `test_no_raw_bilingual_concatenation_without_bdi_join` | ≥8 `bdi_join` calls per template |
| `test_frozen_surfaces_byte_identical_to_base_commit` | 4 frozen files match `234c024` byte-for-byte |

### Known limits / honest notes

- **First matrix attempt failed once** on
  `test_bilingual_account_pilot.test_track_changes_patch_idempotent_and_reversible`
  (`AssertionError: 1 is not false`). That test **passes in isolation** and the **full
  21-module matrix passed on immediate re-run** (273/273). The failure is a pre-existing
  DocType-meta cache/test-ordering flake in an untouched module; it is unrelated to this
  work item, which does not touch `Account`, DocType metadata or patches. The committed
  `regression-matrix.log` is the green re-run; this note preserves the truth of the first run.
- **Concurrency hazard in the shared checkout:** `git status` at session start showed only
  `SESSION_MEMORY.md` and `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md` modified. During this
  session three further files appeared modified —
  `construction/api/bilingual_reports.py`,
  `construction/construction/page/bilingual_report_viewer/bilingual_report_viewer.js`,
  `construction/tests/test_stage7_bilingual_reports.py` — and two new work-item directories
  (`bilingual-financial-reports-expansion/`, `production-cutover-runbook/`). Those belong
  to **Sessions B and D** and were **not read, staged or altered** by this session. The
  regression matrix was run with their in-flight edits present and passed. The committer
  must stage by explicit path list (see §6), never `git add -A`.
- Per-row `frappe.db.get_value` lookups for Item/UOM/Project/Department/Warehouse are
  bounded by the printed document's line count (framed by the briefing's specification).
- The four formats are `custom_format` Jinja HTML with their own scoped `.ct-*` CSS; they
  are not wired to a letterhead and do not cover Purchase Receipt, Delivery Note, Sales
  Order or Purchase Invoice (out of scope).
- `Construction Bilingual *` formats are installed as `standard = "No"`, so a site admin
  can edit them; there is no automatic conflict guard against local edits before re-migrate
  beyond the normal upsert-if-changed behaviour.

---

## 5. Files read (actual)

- `AGENTS.md`, `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md` (full),
  `docs/ai/CONTEXT_INDEX.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`
- `SESSION_MEMORY.md` §1–§2 (sprint/completed-work state; full 1,116-line file not re-read)
- `docs/ai/BRIEFING_TRANSACTION_PRINT_FORMATS.md`, `…_FINANCIAL_REPORTS_EXPANSION.md`,
  `…_TRANSLATION_CATALOG_SYNC.md`, `…_PRODUCTION_CUTOVER_RUNBOOK.md`
- `construction/hooks.py`, `construction/install.py`
- `construction/print_format/boq_print_format/boq_print_format.json`
- `construction/services/narrative_sanitizer.py` (`bdi_join`, lines 244–266)
- `construction/tests/test_bilingual_boq_print.py`
- `scripts/run_bilingual_regression_matrix.sh`
- `docs/ai/work-items/bilingual-uom-phase2c-catalog-closure/evidence/{lint-gates.log,manifest-integrity.log,MANIFEST.json}`
- `docs/ai/work-items/transactional-link-resolution/evidence/MANIFEST.json`
- `docs/ai/work-items/bilingual-adr-evidence-correction/evidence/scripts/reconcile_adr_vs_evidence.py`
- `apps/frappe/frappe/utils/print_utils.py` (`get_print`)
- Live site probes: `SHOW COLUMNS` for the 8 master DocTypes and the 4 transaction
  DocTypes; master/document inventories on `v16.localhost`

---

## 6. Changed / added files for the commit

> **`.gitignore` line 27 is `*.log`.** Evidence logs are therefore **ignored by default**;
> the repository already tracks 142 such files via force-add. Stage the logs with
> `git add -f`.

New (untracked):

```
construction/print_format/bilingual_purchase_order/bilingual_purchase_order.json
construction/print_format/bilingual_sales_invoice/bilingual_sales_invoice.json
construction/print_format/bilingual_stock_entry/bilingual_stock_entry.json
construction/print_format/bilingual_material_request/bilingual_material_request.json
construction/tests/test_bilingual_transaction_print.py
docs/ai/BRIEFING_TRANSACTION_PRINT_FORMATS.md
docs/ai/work-items/bilingual-transaction-print-formats/SCOPE.md
docs/ai/work-items/bilingual-transaction-print-formats/evidence/MANIFEST.json
docs/ai/work-items/bilingual-transaction-print-formats/evidence/gates.log            # needs -f
docs/ai/work-items/bilingual-transaction-print-formats/evidence/test-rendering.log   # needs -f
docs/ai/work-items/bilingual-transaction-print-formats/evidence/regression-matrix.log # needs -f
docs/ai/work-items/bilingual-transaction-print-formats/evidence/manifest-integrity.log # needs -f
```

Modified (shared — verify no concurrent session has altered them before commit):

```
construction/install.py     (+34/-2: setup_transaction_print_formats + _upsert_print_format_file extraction)
construction/hooks.py       (+2: after_install / after_migrate registration)
```

Modified (amendment-only, per D6 — re-pin of `construction/hooks.py` plus one appended
`amendments` entry each; verify `git diff` shows **only** those two changes and that no
concurrent session has appended to the same file in the meantime):

```
docs/ai/work-items/bilingual-asset-master/evidence/MANIFEST.json
docs/ai/work-items/bilingual-boq-title-ar-wiring/evidence/MANIFEST.json
docs/ai/work-items/bilingual-brand-master/evidence/MANIFEST.json
docs/ai/work-items/bilingual-company-master/evidence/MANIFEST.json
docs/ai/work-items/bilingual-desk-link-dispatch/evidence/MANIFEST.json
docs/ai/work-items/bilingual-financial-reports/evidence/MANIFEST.json
docs/ai/work-items/bilingual-narrative-sanitizer/evidence/MANIFEST.json
docs/ai/work-items/bilingual-terms-conditions-master/evidence/MANIFEST.json
```

**Do not stage** (owned by other sessions / pre-existing):
`construction/api/bilingual_reports.py`,
`construction/construction/page/bilingual_report_viewer/bilingual_report_viewer.js`,
`construction/tests/test_stage7_bilingual_reports.py`,
`SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, `dump.rdb`,
`docs/ai/work-items/bilingual-report-statements-allowlist/evidence/MANIFEST.json`
(Session B), `docs/ai/work-items/bilingual-financial-reports-expansion/`,
`docs/ai/work-items/production-cutover-runbook/`, and any `docs/ai/BRIEFING_*.md`
**other than** `docs/ai/BRIEFING_TRANSACTION_PRINT_FORMATS.md` listed above.

---

## 7. Next action

Antigravity verification gate: independent diff review, security/privacy check, re-run of
the 6 lints + reconciler, digest verification of manifest #32 against every other manifest
in the tree (no files missing; the 8 `construction/hooks.py` re-pins are recorded in D6 and
any residual drift is classified by cause in `manifest-integrity.log`), then the local
commit with transmitting hooks disabled per command.
