# F34/F37 lab-fresh-site evidence (2026-10-15, `f31fresh-clean.localhost`)

## F34 UI journey (ordinary personas, 9 checks, all pass)

J0 PM login (site-bound identity) · J1 Draft header form opens · J2 import dialog opens ·
J3 workbook attached (`/private/files/f36-import.xlsx`) · J4 preview renders (Rows: 3) ·
J5 confirm commits (batch, dialog closes, 2 rows persisted) · J6 engineer sees stages ·
J7 engineer login · J8 `certified_qty` input disabled in the form.

Setup prerequisites discovered (lab setup, not product defects — recorded for the guides):
fresh lab sites lack setup-wizard completion (desk redirects), standard masters (Warehouse
Type Transit, UOMs, Item Group "All Item Groups"), and the import-commit flag defaults OFF
(safety gate, ON at rehearsal). The missing-masters question is settled: documented setup
(CUSTOMER_ONBOARDING prerequisite), not installer correction — stock ERPNext behaves
identically. Serving the lab over HTTP needs the static middleware (`bench serve` wraps it;
raw WSGI 404s all assets).

## F37 D1-scale measurement (lab, 200 items)

- Seeding: 190 leaves + items in 116.4s (one item per structure is enforced unique).
- Correctness: header total 268,310.00 == recomputed sum.
- missing_analysis over 200 items: 200 rows in 0.01s.
- Concurrency: 3 sessions × 5 list reads each (engineering test profile only — NOT the
  business workload; D1 concurrency/volumes still to record).
- NOT tested: write concurrency, 50 analyses, 5 VOs, six-month history depth.

## Acceptance dataset reference

`construction_foundation_acceptance_dataset_2026-10-15.md` (ACC company/project, header
6200 total, 3 scoped personas). Legacy records preserved and separate.
