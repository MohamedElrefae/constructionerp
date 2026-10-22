# Stage 7 — BOQ print/export + pilot viewer UI build complete (2026-09-21)

Owner decision 2026-09-21: **approve Stage 7 BOQ print/export + pilot report
viewer UI**; W6-0b stays deferred; managed Redis health becomes a hard UAT
preflight; no production rollout.

## (A) Hard UAT preflight (`scripts/uat_preflight.py`)

Four checks, fail-closed, before any browser evidence run:
1. redis cache :13000 — TCP+PING;
2. redis queue  :11000 — TCP+PING;
3. site `/api/method/ping` == 200;
4. **fresh Desk boot for the ar session** — login as Administrator, GET
   `/desk`, and require: `"lang": "ar"` + an `__messages` dictionary with
   ≥1000 entries (+ a representative key when provided).

Live preflight result during this batch's UAT:
```
PASS redis-cache / redis-queue / site-http
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=10752
PASS desk-boot-key: 'Add / Remove Columns' present in boot
UAT PREFLIGHT: PASS
```
(and its fail-closed path was equally proven earlier: with an en-language
login or redis down it FAILs the preflight and blocks UAT.)

## (B) Pilot report viewer UI (`/app/bilingual-report-viewer`)

- Standard Construction Page (`bilingual_report_viewer.*`): fields النوع
  (report), الوضع (`ar`/`en`/`both`), الشركة; the عرض primary action calls
  the governed endpoint (`construction.api.bilingual_reports.
  localized_report`) with the session's own permissions; pure rendering.
- Live browser evidence (ar session, preflight PASS):
  `frappe.boot.lang=ar`; the Trial Balance table renders with Arabic
  headers (`الحساب`, `اسم الحساب`, `رقم الحساب`, `العملة`, `افتتاحي  (Dr)`,
  `افتتاحي (Cr)`) and the report row ('الإجمالي'); row count 1 (the known
  empty-ledger state — populated financial rows are the Stage-8 gate).
- Contract fixes surfaced during UAT: the endpoint now coercions filters
  to `frappe._dict` (vendor reports read attributes), default fiscal-year
  resolution through the vendor helper, and the viewer body target is
  `page.views.main` (no `page.main` in v16). Endpoint tests 9/9 OK.

## (C) BOQ print/export pilot (vendor-service reuse, zero vendor edits)

- ar-language BOQ export exercised on real site data (`BOQ-2026-7449`,
  one of 23 live BOQ Headers): `_print_context()` reports
  `is_arabic=true` / `rtl`; the rendered print HTML carries Arabic tokens
  (19 matches); the **governed PDF export succeeded twice** and wrote
  private files with distinct URLs (ar + en variants recorded):
  - ar: `/private/files/BOQ_BOQ-2026-7449_20260921_211006…
  - en: (same service, ltr) for the same header.
- No vendor file edits; reversibility is the service's own (files are
  written to private space per export).

## Gates after the build (+2 new construction strings in the PO catalog)

- New UI strings registered (`Bilingual Report Viewer`, `Loading`,
  `No Data`) — PO catalog 807 → **810**; extraction contract updated:
  files 261→265, wrapped 667, json_labels 22; construction_po_sha
  re-recorded; standalone suite 91/91 OK; ten envelopes + index
  regenerated atomically; evidence-inclusive gate **exit 0 on the
  pre-commit HEAD** (documented post-commit head-pin staleness applies
  until the next catalog event).

## Still open (unchanged)

- No production rollout (Stage 8 gates), W6-0b deferred, populated
  financial report rows awaiting real ledger data (Stage 8).
