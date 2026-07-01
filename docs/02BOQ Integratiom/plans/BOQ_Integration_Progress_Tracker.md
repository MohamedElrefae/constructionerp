# BOQ Integration Progress Tracker

Source of truth: `BOQ_Integration_Master_Plan_v1.0.md`  
Implementation app: `/home/mohamed/frappe-bench/apps/construction`  
Verification site: `v16.localhost`

Status values: `Not Started`, `In Progress`, `Blocked`, `Needs Verification`, `Complete`

| ID    | Phase        | Task                                                              | Status             | Owner | Verification Required                                     | Evidence                                                                                                      | Notes                                                         |
| ----- | ------------ | ----------------------------------------------------------------- | ------------------ | ----- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| P0-01 | Baseline     | Confirm BOQ controllers, metadata, hooks, and current test layout | Complete           | Dev   | Static inspection                                         | Read `hooks.py`, BOQ Header/Structure/Item controllers and JSON, tests directory                              | Existing wildcard hook confirmed before edits                 |
| P1-01 | Metadata     | Create BOQ Item Stage DocType                                     | Complete           | Dev   | `bench --site v16.localhost migrate` and DocType exists   | Migrate passed twice; `frappe.db.exists("DocType", "BOQ Item Stage")` returned `BOQ Item Stage`               | Added standard DocType metadata/controller                    |
| P1-02 | Metadata     | Add BOQ Item Stage indexes                                        | Complete           | Dev   | `SHOW INDEX FROM tabBOQ Item Stage`                       | Unique index `unique_stage_code_per_item` and lookup indexes present                                          | Added `on_doctype_update` unique and lookup indexes           |
| P2-01 | Validation   | Add BOQ Item Stage operational validation                         | Complete           | Dev   | Targeted BOQ test runner                                  | `bench --site v16.localhost execute construction.tests.boq_integration_test_runner.run_targeted_tests` passed | Includes quantity, percent, uniqueness, lifecycle rules       |
| P3-01 | BOQ Item     | Add `has_stages` only                                             | Complete           | Dev   | Migrate plus BOQ targeted tests                           | Migrate passed; `frappe.db.has_column("BOQ Item", "has_stages")` returned `true`                              | Existing pricing fields preserved                             |
| P4-01 | Accounting   | Add BOQ Item Accounting Dimension setup                           | Complete           | Dev   | Run migrate twice plus accounting tests                   | Migrate passed twice; targeted accounting tests passed; dimension count = 1                                   | Added idempotent install/migrate setup                        |
| P4-02 | Fields       | Add custom fields to 8 child doctypes                             | Complete           | Dev   | Custom field inspection/tests                             | All 8 child doctypes have `boq_item`, `boq_item_stage`, `expense_category`; duplicate query returned no rows  | Adds fields idempotently                                      |
| P5-01 | Hooks        | Add transaction validation hooks while preserving wildcard        | Complete           | Dev   | Targeted hook regression tests                            | Targeted hook tests passed                                                                                    | Wildcard hook retained                                        |
| P5-02 | Transactions | Validate BOQ attribution rules                                    | Complete           | Dev   | Targeted transaction validation tests                     | Targeted transaction tests passed                                                                             | Covers no BOQ, valid BOQ, status block, mismatch, wrong stage |
| P6-01 | Client       | Add BOQ link filters and visibility behavior                      | Needs Verification | Dev   | Build and manual UAT                                      | `bench build --app construction` passed                                                                       | Manual browser UAT still pending                              |
| P7-01 | Docs         | Add ADR for Accounting Dimension cardinality risk                 | Complete           | Dev   | Document review                                           | `docs/ADR-001-accounting-dimension.md` added                                                                  | ADR added under app docs                                      |
| P7-02 | Release      | Final migrate and full app test run                               | Not Started        | Dev   | `bench --site v16.localhost run-tests --app construction` | Pending                                                                                                       | Run after targeted failures are resolved                      |

## Evidence Log

Record verification output here before moving a row to `Complete`.

| Date | Task ID | Command / Check | Result | Notes |
|------|---------|------------------|--------|-------|
| 2026-05-25 | P0-01 | Static inspection | Passed | Local codebase matched master-plan ground truth for namespace, lifecycle, key field names, and wildcard hook |
| 2026-05-25 | P1-01/P4-01 | `bench --site v16.localhost migrate` twice | Passed | Metadata synced and setup was idempotent |
| 2026-05-25 | P1-02 | `SHOW INDEX FROM tabBOQ Item Stage` | Passed | Composite unique index and lookup indexes exist |
| 2026-05-25 | P3-01/P4-02 | Bench execute field checks and custom field SQL inspection | Passed | `has_stages`, GL `boq_item`, and 8 child table custom fields verified |
| 2026-05-25 | P2/P4/P5 | `bench --site v16.localhost execute construction.tests.boq_integration_test_runner.run_targeted_tests` | Passed | 17 tests, 0 failures, 0 errors |
| 2026-05-25 | P6-01 | `bench build --app construction` | Passed | Assets linked and build completed |
| 2026-05-25 | P7-02 | `bench --site v16.localhost run-tests --app construction` | Blocked | Existing test discovery error in `construction/patches/v6_0/test_migration.py`: missing `_darken_hex` import |
