# F21 — Role workspaces and persona navigation (evidence)

Date: 2026-10-14 · Site: `v16rehearsal.localhost` · App: construction @ working tree (uncommitted)
Method: framework-authoritative server checks, one clean process per persona (no shared request cache)

---

## 1. What was built

**Five role-scoped workspaces** (Workspace docs, `public=1`, each carrying `roles` rows):

| Workspace | Roles gating it | Curated links |
|---|---|---|
| Site Work | Site Engineer, Projects User | BOQ Item Stage, Timesheet, Material Request, BOQ Item |
| Estimating and Commercial | Project Manager, Construction Owner | BOQ Header, BOQ Structure, BOQ Item, BOQ Cost Analysis, BOQ Import Batch, Variation Order, BOQ Quantity Revision, Construction Report Viewer |
| Procurement and Stores | Purchase User, Stock User | Material Request, Purchase Order, Purchase Receipt, Stock Entry, Item |
| Finance | Accounts User, Accounts Manager, Auditor | Purchase Invoice, Sales Invoice, Journal Entry |
| Cost Database | Cost Database Maintainer | Resource Price History, Item, BOQ Cost Analysis, Cost Database Workbench |

**One app-shipped Sidebar document** — `construction/construction/construction/sidebar/construction_home/construction_home.json` (30 items, `standard: 1`) — now backs the construction module's navigation from the repo instead of a hand-made site row. It contains: Home, a "Work areas" section linking the five role workspaces, then BOQ management / Change control / Rates and prices / Reports and views / Themes and scope sections.

Why this shape (v16 behaviour, read in `frappe/desk/desktop.py`, `frappe/boot.py`, `frappe/desk/doctype/sidebar/sidebar.py`):
- one module resolves to **one** shell; workspaces of a module merge into it (`build_sidebar`), so separate per-role shells are not a v16 concept;
- sidebar rows are filtered by `is_item_allowed`: a **DocType** row needs read permission, a **Workspace** row needs the workspace's own roles. Navigation therefore hides what the persona cannot open, and grants nothing;
- the site previously held an undocumented `Construction Home` Sidebar row (created 2026-10-13 during the vendor sidebar fix, `standard=0`, 15 items, no app file). It shadowed the computed merge, which is why the five new workspaces did not appear in navigation at first.

## 2. Workspace reach per persona (pass)

Measured with `frappe.desk.desktop.get_workspaces()` → `Workspace.is_permitted()` (the role gate), one process per persona:

| Persona | Roles | Construction workspaces reachable | Expected |
|---|---|---|---|
| f04-engineer | Site Engineer | Construction, Site Work | pass |
| f04-pm | Project Manager | Construction, Estimating and Commercial | pass |
| f20-buyer | Purchase User | Construction, Procurement and Stores | pass |
| f20-store | Stock User | Construction, Procurement and Stores | pass |
| f20-acc | Accounts User | Construction, Finance | pass |
| f18-maintainer | Cost Database Maintainer | Construction, Cost Database | pass |
| f04-readonly | Read-Only | Construction | pass |

No persona reached a foreign role workspace. `Is permi` spot-checks: engineer denied on Finance/Cost Database, buyer denied on Site Work/Finance/Cost Database, accountant reachable on Finance only.

## 3. Sidebar navigation per persona (permission-filtered)

Measured with `frappe.boot.get_module_sidebars()` — the exact call that builds `bootinfo.module_sidebars`, i.e. what the desk draws:

| Persona | Nav links the persona actually gets |
|---|---|
| engineer | Home, Site Work, BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage, BOQ Cost Analysis, Variation Order, BOQ Quantity Revision, report viewer, cost-database workbench, 4 theme/scope links |
| pm | Home, Estimating and Commercial, BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage, **BOQ Import Batch**, BOQ Cost Analysis, Variation Order, BOQ Quantity Revision, Resource Price History, viewer, workbench, theme/scope |
| buyer | Home, Procurement and Stores, Item, viewer, workbench, theme/scope |
| store | Home, Procurement and Stores, Item, viewer, workbench, theme/scope |
| acc | Home, Finance, Item, viewer, workbench, theme/scope |
| maintainer | Home, Cost Database, BOQ Header, BOQ Item, BOQ Cost Analysis, Resource Price History, Item, Item Price, viewer, workbench, theme/scope |
| readonly | Home, BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage, BOQ Import Batch, BOQ Cost Analysis, BOQ Quantity Revision, viewer, workbench, theme/scope |

Every entry the persona cannot open is absent (e.g. buyer/store/acc see no BOQ, Variation Order or price-history link). Navigation is therefore a *view* of server permission, never a grant.

## 4. Server authority re-checked through the visible pages (owner's condition)

The two viewer pages have no role rows, so their links are drawn for every persona. The APIs behind them were called as each persona:

| Call | engineer | pm | buyer | store | acc | maintainer | readonly |
|---|---|---|---|---|---|---|---|
| report_view(price_history) | denied | denied | 9 rows → **0 after fix** | 9 → **0** | 9 → **0** | 9 rows | denied |
| report_view(analysis_summary / missing_analysis) | denied | denied | denied | denied | denied | allowed | denied |
| reprice_cost_analyses | denied | denied (Item Price) | denied | denied | denied | allowed | denied |
| import_cost_database | denied | denied | denied | denied | denied | permission passed (request-bound, not callable here) | denied |

## 5. Findings

**F21-D002 — price history reached personas with no cost-database rights (FIXED).**
`boq_report_service.get_resource_price_history` selected no `name` column, so `_readable_rph` always evaluated `row.get("name")` as absent and the old branch answered `return True`. The only remaining gate was `Company` read, which buyer, storekeeper and accountant hold natively — so all three received nine Resource Price History rows with no RPH permission at all. This is the same class of break as the F11/F12 boundary: cost data escaping its scope.

Fix (two parts, both uncommitted):
1. `construction/services/boq_report_service.py` — select `RPH.name` so row identity exists to authorize.
2. `construction/api/construction_reports.py` — `_readable_rph` now **refuses** a row it cannot identify, instead of passing it.

Verified live after the fix: buyer/store/acc get `row_count 0`; maintainer unchanged at 9 rows. `report_export` delegates to `report_view`, so the export path is fixed by the same change.

Regression suite: `construction/tests/test_f21_price_history_row_auth.py` — 4 tests, all pass:
`test_row_without_identity_is_not_readable`, `test_service_returns_document_identity`,
`test_price_history_withheld_from_user_without_rph_read` (Stock User persona, Company read, no RPH read → 0 rows),
`test_price_history_visible_to_user_with_rph_read` (System Manager persona → rows with identity).

**F21-D001 — F19 views are unusable by the personas they were designed for (OPEN, owner decision).**
`report_view` establishes scope with `frappe.has_permission("Company", "read", doc=company)`. Native DocPerm has no Company read for Project Manager, Site Engineer or Read-Only, so the estimating personas are refused at the first check, while buyer/store/acc (who hold Company read natively) pass it. Result: the people who certify and record estimates cannot open the views; commercial roles who should not see cost data can. The gating model needs a decision — either Company read is granted to the construction estimating roles through the reviewed Custom-DocPerm route (never a bare row), or `report_view` derives scope from permitted companies / User Scope Context rather than requiring Company read. Not fixed here: it is a permission change and belongs to the owner.

**F21-D003 — the cost-analysis test module cannot run green while scope enforcement is ON (OPEN, F35 CI).**
`construction.tests.test_cost_analysis_engine` reports 1 failure + 10 errors on this site: `setUp` creates a Project and `scope_enforcement.validate` refuses it ("An active User Scope Context is required"), and `test_non_admin_permissions` fails on "Project Manager should have submit permission". Proven **not** caused by this work: reverting both F21 edits and re-running gives the identical 1 failure + 10 errors. CI (F35) must create a User Scope Context for the test user or run with enforcement off, otherwise the suite is red for environmental reasons.

**Observations (no action):**
- `frappe.desk.desktop.get_workspaces` is not whitelisted (403) and `get_desktop_page` needs `page` as a JSON object (`{"name": ..., "title": ..., "public": ...}`), not a name string. Verification therefore used the boot payload and `resolve_sidebar`, which is the same computation the desk performs.
- Page links (report viewer, cost-database workbench) are drawn for every persona because Page has no role rows. Server side refuses them for the personas that must not use them (section 4), so the link is navigation-only noise rather than an access grant. If the owner wants them hidden, that is a Custom Sidebar (per user) or a Page permission change — not something this work decides.

## 6. Files touched (all uncommitted, queued for the F38 review batch)

- `construction/construction/construction/sidebar/construction_home/construction_home.json` (new app fixture, 30 items)
- `construction/services/boq_report_service.py` (select `RPH.name`)
- `construction/api/construction_reports.py` (`_readable_rph` refuses unidentified rows)
- `construction/tests/test_f21_price_history_row_auth.py` (new, 4 tests)
- site data: 5 Workspace docs with roles; `Sidebar` "Construction Home" now `standard=1`, 30 items, `app=construction`

---

# F21 follow-up: D001 grant, D002 leak-boundary, D003 fixture repair (2026-10-14)

## 7. F21-D001 resolved — Company read granted on the native route

**Grant.** `scripts/apply_report_audience_company_read.py` (new, idempotent, refuses to write a
DocType that has no Custom DocPerm rows yet) added four **read-only** Custom DocPerm rows on
Company: Project Manager, Construction Owner, Site Engineer, Read-Only. No other right is set
(write/create/delete/submit/cancel/amend/report/export/import/share/print/email all 0), and
nothing is granted on any business DocType.

**Who and why.** The instruction named PM/Construction Owner. Site Engineer and Read-Only
follow their documented per-view audience: both hold read on the views' parents (BOQ Header
and BOQ Cost Analysis), so the estimation views exist for them too. Accountant is not granted:
the finance/report disposition keeps that audience separate, and the accountant persona
already reaches Company through Accounts User.

**Restriction, verified per company.** Every persona's Company read follows their native
Company User Permission, not their role (one process per persona, no shared cache):

| Persona | permitted company | other company |
|---|---|---|
| engineer / pm / readonly | allowed | **denied** |
| buyer / store / acc | allowed | **denied** |
| maintainer | allowed | **denied** |
| temporary persona (PM + Site Engineer) scoped to Elrefae | allowed (Elrefae) | **denied** (_Test Company) |

That last row is the proof of direction: the same two roles that read `_Test Company` when
scoped to it are refused when scoped elsewhere, and vice versa. Estimation views additionally
require matching Construction scope, which is the intended double gate.

**Fixture hygiene (disclosed).** engineer and readonly carried no Company User Permission, so
their new Company read was unrestricted; both now carry `_Test Company` like every other
persona. readonly also had no User Scope Context, which refused it at the Construction scope
gate; it now carries `_Test Company` / PROJ-0014, matching its audience. The temporary mirror
persona was removed after the test (verified: 0 rows left).

**Reconciliation baseline regenerated** after review: Company now shows 18 custom roles, five
added against standard (Construction Owner, Cost Database Maintainer, Project Manager,
Read-Only, Site Engineer), **zero roles missing vs standard, zero changed rights**. No dropped
roles anywhere; the only `changed` entries in the report are the pre-existing VAT doctypes.

**Report access after the grant (5 reports, permitted company):**

| Persona | analysis_summary | cost_vs_contract | resource_requirements | price_history | missing_analysis |
|---|---|---|---|---|---|
| engineer | 0 rows | 4 | 0 | **0** | 4 |
| pm | 0 | 4 | 0 | 9 | 4 |
| readonly | 0 | 4 | 0 | **0** | 4 |
| buyer / store / acc | denied | denied | denied | 0 rows | denied |
| maintainer | 0 | 4 | 0 | 9 | 4 |

Zeros are correct emptiness for that header (no submitted analyses / no resource rows), not
refusals. `price_history` is 0 for engineer and readonly because neither holds Resource Price
History read — **Company read did not open it**. Foreign-company requests are refused for
everyone.

Regression tests added in `tests/test_f21_price_history_row_auth.py` (9 total, all pass):
narrow grant per role, Company read confers no RPH/analysis access, Company read scoped per
company by User Permission.

## 8. F21-D002 extended — no restricted data in any form

An empty displayed list was not the whole question. For each forbidden persona (buyer, store,
acc) the full payload is now checked, and asserted empty of identifiers:

| Check | Result |
|---|---|
| `row_count` (the total) | 0 |
| `rows` | `[]` |
| `columns` | `[]` (no `source_doctype` / `source_name` column names) |
| `has_more` | `False` |
| view body markers (`RPH-`, `source_name`, `source_doctype`, `Resource Price History`) | absent |
| `report_export` row count | 0, `truncated` False |
| exported file body | `{"rows": []}`, no markers |

Authorized audience still receives its rows in the same run (maintainer: 9), so the boundary
is a permission filter and not a blanket off switch. Covered by the two new tests
`test_view_returns_no_restricted_data` and `test_export_returns_no_restricted_data`.

## 9. F21-D003 resolved — fixture repair, enforcement untouched

Root cause was two separate defects, neither a permission problem:

1. **Session pollution.** `test_non_admin_permissions` switched to the Site Engineer persona
   and never restored the session user, so every later test in the class ran as that persona
   and its `setUp` was refused by scope enforcement — 10 errors. Fixed with
   `self.addCleanup(frappe.set_user, "Administrator")`.
2. **Missing scope for a permitted persona.** The same test asserted PM submit/cancel on a
   document while the PM user had no User Scope Context, and `_scope_allows` refuses
   "missing scope is not a wildcard". Fixed by `_give_scope(...)`, which gives the fixture
   persona a real scope covering the fixture's project/company. The denial path is preserved
   as its own test, `test_missing_scope_context_denies_scoped_access` (permitted role, no
   scope, read *and* write refused).
3. **Shared-table assumptions.** `test_report_price_history_filters` asserted absolute counts
   against the site's Resource Price History table, so any unrelated row broke it. Its
   date-range assertions now filter on the items the test itself created.

Enforcement was **not** disabled anywhere. Result: `test_cost_analysis_engine` went from
1 failure + 10 errors to **38/38 OK**, and the F21 module is 9/9.

## 10. F21 status

**Engineering verified for navigation, with report-access qualification now closed on the
engineering side.** Boot/sidebar computation proves visibility and per-persona reach; server
authority is demonstrated for every view and company boundary. Remaining acceptance is owner
UI work in the consolidated final block: F21 workspace-by-workspace with ordinary personas,
and F22 must verify actual navigation and pages in Arabic/RTL (translated errors,
mixed-direction identifiers, tables, dialogs, exports) rather than visibility alone.
